"""Pydantic request/response models for organization endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ── Response models ─────────────────────────────────────────────────


class OrganizationResponse(BaseModel):
    id: str
    name: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MemberResponse(BaseModel):
    user_id: str
    email: str | None = None
    display_name: str | None = None
    role: str
    joined_at: datetime | None = None


# ── Request models ──────────────────────────────────────────────────


class UpdateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class AddMemberRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    role: str = Field(default='member', pattern=r'^(admin|member)$')


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(..., pattern=r'^(admin|member)$')
