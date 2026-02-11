"""Organization management router for OpenHands App Server."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.app_server.authorization.rbac import Permission, require_permission
from openhands.app_server.config import depends_db_session, depends_user_context
from openhands.app_server.errors import AuthError
from openhands.app_server.organization.organization_models import (
    AddMemberRequest,
    MemberResponse,
    OrganizationResponse,
    UpdateMemberRoleRequest,
    UpdateOrganizationRequest,
)
from openhands.app_server.user.user_context import UserContext
from openhands.storage.models.user import User
from openhands.storage.organizations.postgres_organization_store import (
    PostgresOrganizationStore,
)

router = APIRouter(prefix='/organizations', tags=['Organizations'])
logger = logging.getLogger(__name__)

user_context_dependency = depends_user_context()
db_session_dependency = depends_db_session()
require_org_read = require_permission(Permission.ORG_READ)
require_org_update = require_permission(Permission.ORG_UPDATE)
require_org_manage_members = require_permission(Permission.ORG_MANAGE_MEMBERS)


# ── Helpers ─────────────────────────────────────────────────────────


def _org_to_response(org) -> OrganizationResponse:
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


def _membership_to_response(m) -> MemberResponse:
    user = m.user
    return MemberResponse(
        user_id=m.user_id,
        email=user.email if user else None,
        display_name=user.display_name if user else None,
        role=m.role,
        joined_at=m.created_at,
    )


# ── Organization CRUD ──────────────────────────────────────────────


@router.get('')
async def list_organizations(
    user_context: UserContext = user_context_dependency,
    db_session: AsyncSession = db_session_dependency,
) -> list[OrganizationResponse]:
    """List organizations the current user belongs to."""
    user_id = await user_context.get_user_id()
    if not user_id:
        raise AuthError(detail='Authentication required')
    store = PostgresOrganizationStore(db_session)
    orgs = await store.list_user_organizations(user_id)
    return [_org_to_response(o) for o in orgs]


@router.get('/{org_id}')
async def get_organization(
    org_id: str,
    db_session: AsyncSession = db_session_dependency,
    _auth: Any = require_org_read,
) -> OrganizationResponse:
    """Get organization details."""
    store = PostgresOrganizationStore(db_session)
    org = await store.get_organization(org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Organization not found')
    return _org_to_response(org)


@router.put('/{org_id}')
async def update_organization(
    org_id: str,
    body: UpdateOrganizationRequest,
    db_session: AsyncSession = db_session_dependency,
    _auth: Any = require_org_update,
) -> OrganizationResponse:
    """Update organization name (admin only)."""
    store = PostgresOrganizationStore(db_session)
    org = await store.update_organization(org_id, body.name)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Organization not found')
    logger.info('Organization %s renamed to %r', org_id, body.name)
    return _org_to_response(org)


# ── Membership Management ──────────────────────────────────────────


@router.get('/{org_id}/members')
async def list_members(
    org_id: str,
    db_session: AsyncSession = db_session_dependency,
    _auth: Any = require_org_read,
) -> list[MemberResponse]:
    """List organization members."""
    store = PostgresOrganizationStore(db_session)
    members = await store.list_org_members(org_id)
    return [_membership_to_response(m) for m in members]


@router.post('/{org_id}/members', status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: str,
    body: AddMemberRequest,
    db_session: AsyncSession = db_session_dependency,
    _auth: Any = require_org_manage_members,
) -> MemberResponse:
    """Add a member to the organization (admin only)."""
    store = PostgresOrganizationStore(db_session)

    # Verify the target user exists
    user = await db_session.get(User, body.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='User not found')

    # Verify the org exists
    org = await store.get_organization(org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Organization not found')

    try:
        membership = await store.add_member(org_id, body.user_id, body.role)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    logger.info('User %s added to org %s with role %s', body.user_id, org_id, body.role)
    return MemberResponse(
        user_id=membership.user_id,
        email=user.email,
        display_name=user.display_name,
        role=membership.role,
        joined_at=membership.created_at,
    )


@router.put('/{org_id}/members/{user_id}')
async def update_member_role(
    org_id: str,
    user_id: str,
    body: UpdateMemberRoleRequest,
    user_context: UserContext = user_context_dependency,
    db_session: AsyncSession = db_session_dependency,
    _auth: Any = require_org_manage_members,
) -> MemberResponse:
    """Update a member's role (admin only). Members cannot change their own role."""
    current_user_id = await user_context.get_user_id()
    if current_user_id == user_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail='Cannot change your own role',
        )

    store = PostgresOrganizationStore(db_session)
    membership = await store.update_member_role(org_id, user_id, body.role)
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Member not found')

    logger.info('User %s role in org %s changed to %s', user_id, org_id, body.role)
    # Re-fetch with user relationship for the response
    members = await store.list_org_members(org_id)
    for m in members:
        if m.user_id == user_id:
            return _membership_to_response(m)
    # Fallback (shouldn't happen)
    return MemberResponse(
        user_id=user_id,
        role=body.role,
    )


@router.delete('/{org_id}/members/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: str,
    user_id: str,
    db_session: AsyncSession = db_session_dependency,
    _auth: Any = require_org_manage_members,
) -> None:
    """Remove a member from the organization (admin only).

    Cannot remove the last admin.
    """
    store = PostgresOrganizationStore(db_session)
    try:
        removed = await store.remove_member(org_id, user_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Member not found')
    logger.info('User %s removed from org %s', user_id, org_id)
