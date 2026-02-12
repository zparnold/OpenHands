"""Azure Service Bus consumer for Azure DevOps webhook events.

This module runs a background task that listens to an Azure Service Bus
subscription for webhook events from Azure DevOps. When a message arrives,
it is evaluated against configured webhook rules and, if matched, triggers
an OpenHands conversation.

Required environment variables:
    AZURE_SERVICEBUS_CONNECTION_STRING - Service Bus connection string
    AZURE_SERVICEBUS_TOPIC_NAME       - Topic name (default: 'azuredevops-events')
    AZURE_SERVICEBUS_SUBSCRIPTION_NAME - Subscription name (default: 'openhands')
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)

# Service Bus configuration from environment
SERVICEBUS_CONNECTION_STRING = os.environ.get('AZURE_SERVICEBUS_CONNECTION_STRING', '')
SERVICEBUS_TOPIC_NAME = os.environ.get(
    'AZURE_SERVICEBUS_TOPIC_NAME', 'azuredevops-events'
)
SERVICEBUS_SUBSCRIPTION_NAME = os.environ.get(
    'AZURE_SERVICEBUS_SUBSCRIPTION_NAME', 'openhands'
)


async def _process_message(message_body: dict) -> None:
    """Process a single Service Bus message containing an Azure DevOps event.

    The message is expected to follow the Azure DevOps Service Hook payload
    format with at minimum an ``eventType`` field and a ``resource`` object.
    """
    from openhands.app_server.config import get_db_session_from_config
    from openhands.app_server.webhooks.webhook_processor import (
        EVENT_TYPE_MAP,
        evaluate_rules,
        get_matching_rules,
    )
    from openhands.storage.webhooks.postgres_webhook_config_store import (
        PostgresWebhookConfigStore,
    )

    azure_event_type = message_body.get('eventType', '')
    if not azure_event_type:
        logger.warning('Service Bus message missing eventType, skipping')
        return

    mapped_type = EVENT_TYPE_MAP.get(azure_event_type, azure_event_type)
    logger.info(
        'Processing Service Bus event: %s (mapped: %s)', azure_event_type, mapped_type
    )

    # Extract repository URL from the event payload
    resource = message_body.get('resource', {})
    repo_url = resource.get('repository', {}).get('remoteUrl', '') or resource.get(
        'repository', {}
    ).get('url', '')

    if not repo_url:
        logger.warning('Could not extract repository URL from event, skipping')
        return

    # Look up matching webhook configs
    async with get_db_session_from_config() as session:
        store = PostgresWebhookConfigStore(session)
        configs = await store.list_configs_for_event(
            provider='azure_devops',
            repository_url=repo_url,
        )

        if not configs:
            logger.debug('No webhook configs found for repo %s', repo_url)
            return

        for config in configs:
            matching_rules = get_matching_rules(config.rules, azure_event_type)
            if not matching_rules:
                continue

            action = evaluate_rules(matching_rules, message_body)
            logger.info(
                'Config %s: action=%s for event %s on %s',
                config.id,
                action,
                azure_event_type,
                repo_url,
            )

            if action == 'trigger_conversation':
                await _trigger_conversation(config, message_body, azure_event_type)

        await session.commit()


async def _trigger_conversation(
    config,  # WebhookConfig
    event_data: dict,
    azure_event_type: str,
) -> None:
    """Trigger an OpenHands conversation based on the webhook event."""
    from openhands.storage.data_models.conversation_metadata import ConversationTrigger

    resource = event_data.get('resource', {})
    repository = resource.get('repository', {}).get('name', '')
    pr_number = resource.get('pullRequestId')
    branch = resource.get('sourceRefName', '').replace(
        'refs/heads/', ''
    ) or resource.get('refUpdates', [{}])[0].get('name', '').replace('refs/heads/', '')

    # Build a descriptive initial message
    if 'pullrequest' in azure_event_type:
        title = resource.get('title', f'PR #{pr_number}')
        initial_message = f'Review pull request #{pr_number}: {title} in {repository}'
    elif azure_event_type == 'build.complete':
        result = resource.get('result', 'unknown')
        initial_message = (
            f'Investigate build {result} in {repository} on branch {branch}'
        )
    elif 'workitem' in azure_event_type:
        wi_title = resource.get('fields', {}).get('System.Title', 'work item')
        initial_message = f'Address work item: {wi_title} in {repository}'
    else:
        initial_message = f'Process {azure_event_type} event in {repository}'

    logger.info(
        'Triggering conversation: org=%s repo=%s event=%s message=%s',
        config.organization_id,
        repository,
        azure_event_type,
        initial_message[:100],
    )

    # TODO: Wire into AppConversationService.start_app_conversation() once
    # the service supports system-triggered conversations. For now, log the
    # event so it can be picked up by operators.
    logger.info(
        'WEBHOOK_TRIGGER: org_id=%s provider=%s repo=%s branch=%s pr=%s '
        'event_type=%s trigger=%s message=%s',
        config.organization_id,
        config.provider,
        repository,
        branch,
        pr_number,
        azure_event_type,
        ConversationTrigger.AZURE_DEVOPS.value,
        initial_message,
    )


async def run_servicebus_consumer() -> None:
    """Long-running task that consumes messages from Azure Service Bus.

    This is designed to be launched as a background asyncio task during
    application lifespan startup.
    """
    if not SERVICEBUS_CONNECTION_STRING:
        logger.info(
            'AZURE_SERVICEBUS_CONNECTION_STRING not set, Service Bus consumer disabled'
        )
        return

    try:
        from azure.servicebus import TransportType
        from azure.servicebus.aio import ServiceBusClient
    except ImportError:
        logger.error(
            'azure-servicebus package is not installed. '
            'Install it with: pip install azure-servicebus'
        )
        return

    logger.info(
        'Starting Service Bus consumer: topic=%s subscription=%s',
        SERVICEBUS_TOPIC_NAME,
        SERVICEBUS_SUBSCRIPTION_NAME,
    )

    while True:
        try:
            async with ServiceBusClient.from_connection_string(
                SERVICEBUS_CONNECTION_STRING,
                transport_type=TransportType.AmqpOverWebsocket,
            ) as client:
                receiver = client.get_subscription_receiver(
                    topic_name=SERVICEBUS_TOPIC_NAME,
                    subscription_name=SERVICEBUS_SUBSCRIPTION_NAME,
                    max_wait_time=30,  # seconds to wait for messages
                )
                async with receiver:
                    logger.info(
                        'Service Bus receiver connected, listening for messages...'
                    )
                    async for message in receiver:
                        try:
                            body_bytes = b''.join(message.body)
                            body_str = body_bytes.decode('utf-8')
                            event_data = json.loads(body_str)

                            await _process_message(event_data)
                            await receiver.complete_message(message)
                            logger.debug('Message completed successfully')
                        except json.JSONDecodeError:
                            logger.error(
                                'Failed to parse Service Bus message as JSON, dead-lettering'
                            )
                            await receiver.dead_letter_message(
                                message,
                                reason='InvalidJSON',
                                error_description='Message body is not valid JSON',
                            )
                        except Exception:
                            logger.exception(
                                'Error processing Service Bus message, abandoning'
                            )
                            await receiver.abandon_message(message)

        except asyncio.CancelledError:
            logger.info('Service Bus consumer task cancelled, shutting down')
            return
        except Exception:
            logger.exception(
                'Service Bus consumer error, reconnecting in 10 seconds...'
            )
            await asyncio.sleep(10)
