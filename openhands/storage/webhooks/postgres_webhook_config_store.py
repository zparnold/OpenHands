"""PostgreSQL-backed webhook configuration store."""

from __future__ import annotations

import logging
from enum import Enum
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from openhands.storage.models.webhook_config import WebhookConfig, WebhookRule


class _Sentinel(Enum):
    UNSET = 'UNSET'


_UNSET = _Sentinel.UNSET

logger = logging.getLogger(__name__)


class PostgresWebhookConfigStore:
    """CRUD helpers for webhook configurations and rules."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── WebhookConfig CRUD ──────────────────────────────────────────

    async def create_config(
        self,
        organization_id: str,
        provider: str,
        repository_url: str,
        project_name: str | None = None,
        enabled: bool = True,
        created_by_user_id: str | None = None,
    ) -> WebhookConfig:
        """Create a new webhook configuration."""
        config = WebhookConfig(
            id=str(uuid4()),
            organization_id=organization_id,
            provider=provider,
            repository_url=repository_url,
            project_name=project_name,
            enabled=enabled,
            created_by_user_id=created_by_user_id,
        )
        self.session.add(config)
        return config

    async def get_config(self, config_id: str) -> WebhookConfig | None:
        """Get a webhook configuration by ID, with rules loaded."""
        result = await self.session.execute(
            select(WebhookConfig)
            .options(joinedload(WebhookConfig.rules))
            .where(WebhookConfig.id == config_id)
        )
        return result.scalars().unique().first()

    async def list_configs(self, organization_id: str) -> list[WebhookConfig]:
        """List all webhook configurations for an organization."""
        result = await self.session.execute(
            select(WebhookConfig)
            .options(joinedload(WebhookConfig.rules))
            .where(WebhookConfig.organization_id == organization_id)
        )
        return list(result.scalars().unique().all())

    async def list_configs_for_event(
        self,
        provider: str,
        repository_url: str,
    ) -> list[WebhookConfig]:
        """Find enabled configs matching a provider and repository URL."""
        result = await self.session.execute(
            select(WebhookConfig)
            .options(joinedload(WebhookConfig.rules))
            .where(
                and_(
                    WebhookConfig.provider == provider,
                    WebhookConfig.repository_url == repository_url,
                    WebhookConfig.enabled.is_(True),
                )
            )
        )
        return list(result.scalars().unique().all())

    async def update_config(
        self,
        config_id: str,
        *,
        repository_url: str | None = None,
        project_name: str | None = None,
        enabled: bool | None = None,
    ) -> WebhookConfig | None:
        """Update a webhook configuration. Returns None if not found."""
        config = await self.session.get(WebhookConfig, config_id)
        if config is None:
            return None
        if repository_url is not None:
            config.repository_url = repository_url
        if project_name is not None:
            config.project_name = project_name
        if enabled is not None:
            config.enabled = enabled
        return config

    async def delete_config(self, config_id: str) -> bool:
        """Delete a webhook configuration and its rules. Returns False if not found."""
        config = await self.session.get(WebhookConfig, config_id)
        if config is None:
            return False
        await self.session.delete(config)
        return True

    # ── WebhookRule CRUD ────────────────────────────────────────────

    async def create_rule(
        self,
        webhook_config_id: str,
        event_type: str,
        action: str,
        conditions: dict | None = None,
        priority: int = 0,
        enabled: bool = True,
    ) -> WebhookRule:
        """Create a new webhook rule."""
        rule = WebhookRule(
            id=str(uuid4()),
            webhook_config_id=webhook_config_id,
            event_type=event_type,
            conditions=conditions,
            action=action,
            priority=priority,
            enabled=enabled,
        )
        self.session.add(rule)
        return rule

    async def get_rule(self, rule_id: str) -> WebhookRule | None:
        """Get a webhook rule by ID."""
        return await self.session.get(WebhookRule, rule_id)

    async def update_rule(
        self,
        rule_id: str,
        *,
        event_type: str | None = None,
        conditions: dict | None | _Sentinel = _UNSET,
        action: str | None = None,
        priority: int | None = None,
        enabled: bool | None = None,
    ) -> WebhookRule | None:
        """Update a webhook rule. Returns None if not found."""
        rule = await self.session.get(WebhookRule, rule_id)
        if rule is None:
            return None
        if event_type is not None:
            rule.event_type = event_type
        if not isinstance(conditions, _Sentinel):
            rule.conditions = conditions
        if action is not None:
            rule.action = action
        if priority is not None:
            rule.priority = priority
        if enabled is not None:
            rule.enabled = enabled
        return rule

    async def delete_rule(self, rule_id: str) -> bool:
        """Delete a webhook rule. Returns False if not found."""
        rule = await self.session.get(WebhookRule, rule_id)
        if rule is None:
            return False
        await self.session.delete(rule)
        return True
