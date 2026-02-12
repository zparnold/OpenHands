"""Pydantic models for webhook configuration API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WebhookRuleCreate(BaseModel):
    event_type: str = Field(
        ..., description="Event type to match (e.g. 'pr_opened', 'build_completed')"
    )
    conditions: dict | None = Field(
        default=None, description='JSON conditions to evaluate'
    )
    action: str = Field(
        default='trigger_conversation',
        description="Action: 'trigger_conversation' or 'ignore'",
    )
    priority: int = Field(
        default=0, description='Higher priority rules are evaluated first'
    )
    enabled: bool = Field(default=True)


class WebhookRuleUpdate(BaseModel):
    event_type: str | None = None
    conditions: dict | None = None
    action: str | None = None
    priority: int | None = None
    enabled: bool | None = None


class WebhookRuleResponse(BaseModel):
    id: str
    webhook_config_id: str
    event_type: str
    conditions: dict | None
    action: str
    priority: int
    enabled: bool


class WebhookConfigCreate(BaseModel):
    organization_id: str
    provider: str = Field(default='azure_devops')
    repository_url: str
    project_name: str | None = None
    enabled: bool = Field(default=True)


class WebhookConfigUpdate(BaseModel):
    repository_url: str | None = None
    project_name: str | None = None
    enabled: bool | None = None


class WebhookConfigResponse(BaseModel):
    id: str
    organization_id: str
    provider: str
    repository_url: str
    project_name: str | None
    enabled: bool
    rules: list[WebhookRuleResponse] = Field(default_factory=list)


class WebhookTestRequest(BaseModel):
    event_type: str = Field(..., description='Azure DevOps eventType string')
    sample_data: dict = Field(default_factory=dict, description='Sample event payload')


class WebhookTestResponse(BaseModel):
    matched_rules: list[WebhookRuleResponse]
    action: str
    would_trigger: bool
