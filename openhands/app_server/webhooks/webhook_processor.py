"""Webhook rule evaluation engine.

Evaluates webhook rules against incoming event data using a flexible
condition system with operators like equals, matches, in, etc.
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any

from openhands.storage.models.webhook_config import WebhookRule

logger = logging.getLogger(__name__)


class AzureDevOpsEventType(str, Enum):
    """Azure DevOps service hook event types."""

    # Git events
    PR_CREATED = 'git.pullrequest.created'
    PR_UPDATED = 'git.pullrequest.updated'
    PR_MERGED = 'git.pullrequest.merged'
    PUSH = 'git.push'

    # Build events
    BUILD_COMPLETED = 'build.complete'

    # Work item events
    WORK_ITEM_CREATED = 'workitem.created'
    WORK_ITEM_UPDATED = 'workitem.updated'
    WORK_ITEM_DELETED = 'workitem.deleted'
    WORK_ITEM_COMMENTED = 'workitem.commented'

    # Release events
    RELEASE_CREATED = 'ms.vss-release.release-created-event'
    RELEASE_DEPLOYMENT_COMPLETED = 'ms.vss-release.deployment-completed-event'


# Map Azure DevOps eventType strings to simpler rule event_type values
EVENT_TYPE_MAP: dict[str, str] = {
    'git.pullrequest.created': 'pr_opened',
    'git.pullrequest.updated': 'pr_updated',
    'git.pullrequest.merged': 'pr_merged',
    'git.push': 'push',
    'build.complete': 'build_completed',
    'workitem.created': 'work_item_created',
    'workitem.updated': 'work_item_updated',
    'workitem.deleted': 'work_item_deleted',
    'workitem.commented': 'work_item_commented',
    'ms.vss-release.release-created-event': 'release_created',
    'ms.vss-release.deployment-completed-event': 'release_deployment_completed',
}


def extract_field(data: dict, field_path: str) -> Any:
    """Extract a nested field from event data using dot notation.

    Example: extract_field({"resource": {"repository": {"name": "repo"}}},
                           "resource.repository.name") -> "repo"
    """
    parts = field_path.split('.')
    current: Any = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def evaluate_operator(operator: str, actual: Any, expected: Any) -> bool:
    """Evaluate a single condition operator against a value."""
    if operator == 'equals':
        return actual == expected
    if operator == 'not_equals':
        return actual != expected
    if operator == 'matches':
        return (
            re.search(str(expected), str(actual)) is not None
            if actual is not None
            else False
        )
    if operator == 'in':
        return actual in expected if isinstance(expected, list) else False
    if operator == 'not_in':
        return actual not in expected if isinstance(expected, list) else True
    if operator == 'contains':
        if isinstance(actual, str):
            return str(expected) in actual
        if isinstance(actual, list):
            return expected in actual
        return False
    if operator == 'greater_than':
        try:
            return float(actual) > float(expected)
        except (TypeError, ValueError):
            return False
    if operator == 'less_than':
        try:
            return float(actual) < float(expected)
        except (TypeError, ValueError):
            return False
    if operator == 'exists':
        return actual is not None
    logger.warning('Unknown operator: %s', operator)
    return False


def evaluate_conditions(conditions: dict | None, event_data: dict) -> bool:
    """Evaluate all conditions against event data. Returns True if all match."""
    if not conditions:
        return True

    for field_path, condition in conditions.items():
        value = extract_field(event_data, field_path)
        if isinstance(condition, dict):
            for op_name, expected in condition.items():
                if not evaluate_operator(op_name, value, expected):
                    return False
        else:
            # Shorthand: {"field": value} means equals
            if not evaluate_operator('equals', value, condition):
                return False
    return True


def evaluate_rules(rules: list[WebhookRule], event_data: dict) -> str:
    """Evaluate rules in priority order and return the action of the first match.

    Returns 'ignore' if no rules match.
    """
    sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)

    for rule in sorted_rules:
        if not rule.enabled:
            continue
        if evaluate_conditions(rule.conditions, event_data):
            logger.info(
                'Rule %s matched (event_type=%s, action=%s)',
                rule.id,
                rule.event_type,
                rule.action,
            )
            return rule.action

    return 'ignore'


def get_matching_rules(
    rules: list[WebhookRule],
    azure_event_type: str,
) -> list[WebhookRule]:
    """Filter rules to those matching the Azure DevOps event type."""
    mapped_type = EVENT_TYPE_MAP.get(azure_event_type, azure_event_type)
    return [r for r in rules if r.event_type == mapped_type]
