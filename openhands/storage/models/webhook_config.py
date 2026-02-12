"""Webhook configuration models for Azure DevOps Service Bus integration."""

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from openhands.app_server.utils.sql_utils import Base


class WebhookConfig(Base):
    """Webhook configuration linking an organization to an Azure DevOps project."""

    __tablename__ = 'webhook_configs'

    id = Column(String, primary_key=True, nullable=False)
    organization_id = Column(
        String, ForeignKey('organizations.id'), nullable=False, index=True
    )
    provider = Column(String(50), nullable=False)  # 'azure_devops'
    repository_url = Column(String, nullable=False)
    project_name = Column(String(255), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_by_user_id = Column(String, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    rules = relationship(
        'WebhookRule',
        back_populates='config',
        cascade='all, delete-orphan',
    )
    organization = relationship('Organization')
    created_by = relationship('User')

    def __repr__(self):
        return f"<WebhookConfig(id='{self.id}', provider='{self.provider}', repository_url='{self.repository_url}')>"


class WebhookRule(Base):
    """A rule that determines when a webhook event should trigger a conversation."""

    __tablename__ = 'webhook_rules'

    id = Column(String, primary_key=True, nullable=False)
    webhook_config_id = Column(
        String, ForeignKey('webhook_configs.id'), nullable=False, index=True
    )
    event_type = Column(
        String(50), nullable=False
    )  # 'pr_opened', 'build_completed', etc.
    conditions = Column(JSON, nullable=True)  # Flexible JSON conditions
    action = Column(String(50), nullable=False)  # 'trigger_conversation' or 'ignore'
    priority = Column(Integer, nullable=False, default=0)
    enabled = Column(Boolean, nullable=False, default=True)

    # Relationships
    config = relationship('WebhookConfig', back_populates='rules')

    def __repr__(self):
        return f"<WebhookRule(id='{self.id}', event_type='{self.event_type}', action='{self.action}')>"
