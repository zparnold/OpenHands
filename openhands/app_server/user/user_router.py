"""User router for OpenHands App Server. For the moment, this simply implements the /me endpoint."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.app_server.config import depends_db_session, depends_user_context
from openhands.app_server.user.user_context import UserContext
from openhands.app_server.user.user_models import UserInfo
from openhands.storage.organizations.postgres_organization_store import (
    DEFAULT_ORGANIZATION_ID,
    PostgresOrganizationStore,
)

router = APIRouter(prefix='/users', tags=['User'])
user_dependency = depends_user_context()
db_session_dependency = depends_db_session()

# Read methods


@router.get('/me')
async def get_current_user(
    user_context: UserContext = user_dependency,
    db_session: AsyncSession = db_session_dependency,
) -> UserInfo:
    """Get the current authenticated user."""
    user = await user_context.get_user_info()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')

    # Check if the user is an admin of the shared org (or any org)
    if user.id and DEFAULT_ORGANIZATION_ID:
        store = PostgresOrganizationStore(db_session)
        membership = await store.get_membership(user.id, DEFAULT_ORGANIZATION_ID)
        if membership and membership.role == 'admin':
            user.is_org_admin = True

    return user
