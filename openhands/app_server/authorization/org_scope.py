"""Organization-scoped resource access helpers.

Provides utilities for validating that the current user has access to resources
within a specific organization, and for filtering queries by organization_id.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from openhands.app_server.errors import AuthError, PermissionsError
from openhands.app_server.user.user_context import UserContext
from openhands.storage.organizations.postgres_organization_store import (
    PostgresOrganizationStore,
)

logger = logging.getLogger(__name__)


async def validate_org_access(
    user_context: UserContext,
    org_id: str,
    db_session: AsyncSession,
) -> str:
    """Validate that the current user is a member of *org_id*.

    Returns the authenticated user_id on success.

    Raises:
        AuthError: if the user is not authenticated.
        PermissionsError: if the user is not a member of the organization.
    """
    user_id = await user_context.get_user_id()
    if not user_id:
        raise AuthError(detail='Authentication required')

    store = PostgresOrganizationStore(db_session)
    membership = await store.get_membership(user_id, org_id)
    if membership is None:
        raise PermissionsError(detail='You are not a member of this organization')
    return user_id


async def get_user_org_id(
    user_context: UserContext,
    db_session: AsyncSession,
) -> str | None:
    """Return the user's primary (first) organization_id, or None.

    This is a convenience for defaulting to the user's org when no org_id
    is explicitly provided.
    """
    user_id = await user_context.get_user_id()
    if not user_id:
        return None
    store = PostgresOrganizationStore(db_session)
    orgs = await store.list_user_organizations(user_id)
    if orgs:
        return orgs[0].id
    return None
