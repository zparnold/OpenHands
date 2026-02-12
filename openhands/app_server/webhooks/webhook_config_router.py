"""CRUD API for webhook configurations and rules."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.app_server.config import depends_db_session, depends_user_context
from openhands.app_server.user.user_context import UserContext
from openhands.app_server.webhooks.webhook_models import (
    WebhookConfigCreate,
    WebhookConfigResponse,
    WebhookConfigUpdate,
    WebhookRuleCreate,
    WebhookRuleResponse,
    WebhookRuleUpdate,
    WebhookTestRequest,
    WebhookTestResponse,
)
from openhands.app_server.webhooks.webhook_processor import (
    evaluate_rules,
    get_matching_rules,
)
from openhands.storage.webhooks.postgres_webhook_config_store import (
    PostgresWebhookConfigStore,
)

router = APIRouter(prefix='/webhooks/configs', tags=['Webhooks'])
db_session_dep = depends_db_session()
user_context_dep = depends_user_context()


def _rule_to_response(rule) -> WebhookRuleResponse:
    return WebhookRuleResponse(
        id=rule.id,
        webhook_config_id=rule.webhook_config_id,
        event_type=rule.event_type,
        conditions=rule.conditions,
        action=rule.action,
        priority=rule.priority,
        enabled=rule.enabled,
    )


def _config_to_response(config) -> WebhookConfigResponse:
    return WebhookConfigResponse(
        id=config.id,
        organization_id=config.organization_id,
        provider=config.provider,
        repository_url=config.repository_url,
        project_name=config.project_name,
        enabled=config.enabled,
        rules=[_rule_to_response(r) for r in (config.rules or [])],
    )


# ── Config CRUD ─────────────────────────────────────────────────────


@router.get('', response_model=list[WebhookConfigResponse])
async def list_webhook_configs(
    organization_id: str,
    db_session: AsyncSession = db_session_dep,
) -> list[WebhookConfigResponse]:
    """List all webhook configurations for an organization."""
    store = PostgresWebhookConfigStore(db_session)
    configs = await store.list_configs(organization_id)
    return [_config_to_response(c) for c in configs]


@router.get('/{config_id}', response_model=WebhookConfigResponse)
async def get_webhook_config(
    config_id: str,
    db_session: AsyncSession = db_session_dep,
) -> WebhookConfigResponse:
    """Get a specific webhook configuration."""
    store = PostgresWebhookConfigStore(db_session)
    config = await store.get_config(config_id)
    if config is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail='Webhook config not found'
        )
    return _config_to_response(config)


@router.post(
    '', response_model=WebhookConfigResponse, status_code=status.HTTP_201_CREATED
)
async def create_webhook_config(
    body: WebhookConfigCreate,
    db_session: AsyncSession = db_session_dep,
    user_context: UserContext = user_context_dep,
) -> WebhookConfigResponse:
    """Create a new webhook configuration."""
    user_id = await user_context.get_user_id()
    store = PostgresWebhookConfigStore(db_session)
    config = await store.create_config(
        organization_id=body.organization_id,
        provider=body.provider,
        repository_url=body.repository_url,
        project_name=body.project_name,
        enabled=body.enabled,
        created_by_user_id=user_id,
    )
    await db_session.commit()
    await db_session.refresh(config, attribute_names=['rules'])
    return _config_to_response(config)


@router.put('/{config_id}', response_model=WebhookConfigResponse)
async def update_webhook_config(
    config_id: str,
    body: WebhookConfigUpdate,
    db_session: AsyncSession = db_session_dep,
) -> WebhookConfigResponse:
    """Update a webhook configuration."""
    store = PostgresWebhookConfigStore(db_session)
    config = await store.update_config(
        config_id,
        repository_url=body.repository_url,
        project_name=body.project_name,
        enabled=body.enabled,
    )
    if config is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail='Webhook config not found'
        )
    await db_session.commit()
    # Re-fetch with rules loaded
    config = await store.get_config(config_id)
    return _config_to_response(config)


@router.delete('/{config_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_config(
    config_id: str,
    db_session: AsyncSession = db_session_dep,
) -> None:
    """Delete a webhook configuration and all its rules."""
    store = PostgresWebhookConfigStore(db_session)
    deleted = await store.delete_config(config_id)
    if not deleted:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail='Webhook config not found'
        )
    await db_session.commit()


# ── Rule CRUD ───────────────────────────────────────────────────────


@router.post(
    '/{config_id}/rules',
    response_model=WebhookRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_webhook_rule(
    config_id: str,
    body: WebhookRuleCreate,
    db_session: AsyncSession = db_session_dep,
) -> WebhookRuleResponse:
    """Add a rule to a webhook configuration."""
    store = PostgresWebhookConfigStore(db_session)
    config = await store.get_config(config_id)
    if config is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail='Webhook config not found'
        )

    rule = await store.create_rule(
        webhook_config_id=config_id,
        event_type=body.event_type,
        action=body.action,
        conditions=body.conditions,
        priority=body.priority,
        enabled=body.enabled,
    )
    await db_session.commit()
    await db_session.refresh(rule)
    return _rule_to_response(rule)


@router.put('/{config_id}/rules/{rule_id}', response_model=WebhookRuleResponse)
async def update_webhook_rule(
    config_id: str,
    rule_id: str,
    body: WebhookRuleUpdate,
    db_session: AsyncSession = db_session_dep,
) -> WebhookRuleResponse:
    """Update a webhook rule."""
    store = PostgresWebhookConfigStore(db_session)
    rule = await store.get_rule(rule_id)
    if rule is None or rule.webhook_config_id != config_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Webhook rule not found')

    updated = await store.update_rule(
        rule_id,
        event_type=body.event_type,
        conditions=body.conditions,
        action=body.action,
        priority=body.priority,
        enabled=body.enabled,
    )
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Webhook rule not found')
    await db_session.commit()
    return _rule_to_response(updated)


@router.delete('/{config_id}/rules/{rule_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_rule(
    config_id: str,
    rule_id: str,
    db_session: AsyncSession = db_session_dep,
) -> None:
    """Delete a webhook rule."""
    store = PostgresWebhookConfigStore(db_session)
    rule = await store.get_rule(rule_id)
    if rule is None or rule.webhook_config_id != config_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Webhook rule not found')
    await store.delete_rule(rule_id)
    await db_session.commit()


# ── Test Endpoint ───────────────────────────────────────────────────


@router.post('/{config_id}/test', response_model=WebhookTestResponse)
async def test_webhook_config(
    config_id: str,
    body: WebhookTestRequest,
    db_session: AsyncSession = db_session_dep,
) -> WebhookTestResponse:
    """Test a webhook configuration against sample event data.

    Returns which rules would match and what action would be taken.
    """
    store = PostgresWebhookConfigStore(db_session)
    config = await store.get_config(config_id)
    if config is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail='Webhook config not found'
        )

    matching = get_matching_rules(config.rules, body.event_type)
    action = evaluate_rules(matching, body.sample_data) if matching else 'ignore'

    return WebhookTestResponse(
        matched_rules=[_rule_to_response(r) for r in matching],
        action=action,
        would_trigger=action == 'trigger_conversation',
    )
