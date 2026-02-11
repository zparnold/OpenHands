"""Role-based access control for OpenHands organizations."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Callable

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.app_server.config import depends_db_session, depends_user_context
from openhands.app_server.errors import AuthError, PermissionsError
from openhands.app_server.user.user_context import UserContext
from openhands.storage.organizations.postgres_organization_store import (
    PostgresOrganizationStore,
)

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """Permissions that can be checked against a user's organization role."""

    ORG_READ = 'org:read'
    ORG_UPDATE = 'org:update'
    ORG_DELETE = 'org:delete'
    ORG_MANAGE_MEMBERS = 'org:manage_members'
    SESSION_READ = 'session:read'
    SESSION_CREATE = 'session:create'
    SESSION_DELETE = 'session:delete'
    SETTINGS_READ = 'settings:read'
    SETTINGS_UPDATE = 'settings:update'


# Maps each role to the set of permissions it grants.
ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    'admin': set(Permission),
    'member': {
        Permission.ORG_READ,
        Permission.SESSION_READ,
        Permission.SESSION_CREATE,
        Permission.SETTINGS_READ,
    },
}


def role_has_permission(role: str, permission: Permission) -> bool:
    """Check whether *role* includes *permission*."""
    perms = ROLE_PERMISSIONS.get(role)
    if perms is None:
        return False
    return permission in perms


async def check_org_permission(
    user_id: str,
    org_id: str,
    permission: Permission,
    db_session: AsyncSession,
) -> None:
    """Raise ``PermissionsError`` if the user lacks *permission* in *org_id*.

    Also raises ``AuthError`` if the user is not authenticated (no user_id).
    """
    if not user_id:
        raise AuthError(detail='Authentication required')

    store = PostgresOrganizationStore(db_session)
    membership = await store.get_membership(user_id, org_id)
    if membership is None:
        raise PermissionsError(detail='You are not a member of this organization')
    if not role_has_permission(membership.role, permission):
        raise PermissionsError(
            detail=f'Permission denied: {permission.value} requires a higher role'
        )


# ── FastAPI dependency factories ────────────────────────────────────

_user_dep = depends_user_context()
_db_dep = depends_db_session()


def require_permission(permission: Permission) -> Callable:
    """Return a FastAPI dependency that enforces *permission* for the org
    identified by the ``org_id`` path parameter.

    Usage::

        @router.get('/organizations/{org_id}')
        async def get_org(
            org_id: str,
            _auth: None = Depends(require_permission(Permission.ORG_READ)),
        ):
            ...
    """

    async def _dependency(
        org_id: str,
        request: Request,
        user_context: UserContext = _user_dep,
        db_session: AsyncSession = _db_dep,
    ) -> None:
        user_id = await user_context.get_user_id()
        if not user_id:
            raise AuthError(detail='Authentication required')
        await check_org_permission(user_id, org_id, permission, db_session)

    return Depends(_dependency)
