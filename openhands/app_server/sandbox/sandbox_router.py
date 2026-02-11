"""Runtime Containers router for OpenHands App Server."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.agent_server.models import Success
from openhands.app_server.authorization.org_scope import validate_org_access
from openhands.app_server.config import (
    depends_db_session,
    depends_sandbox_service,
    depends_user_context,
)
from openhands.app_server.sandbox.sandbox_models import SandboxInfo, SandboxPage
from openhands.app_server.sandbox.sandbox_service import (
    SandboxService,
)
from openhands.app_server.user.user_context import UserContext

router = APIRouter(prefix='/sandboxes', tags=['Sandbox'])
sandbox_service_dependency = depends_sandbox_service()
user_context_dependency = depends_user_context()
db_session_dependency = depends_db_session()

# Read methods


@router.get('/search')
async def search_sandboxes(
    page_id: Annotated[
        str | None,
        Query(title='Optional next_page_id from the previously returned page'),
    ] = None,
    limit: Annotated[
        int,
        Query(title='The max number of results in the page', gt=0, lte=100),
    ] = 100,
    org_id: Annotated[
        str | None,
        Query(title='Filter by organization ID. If provided, validates membership.'),
    ] = None,
    sandbox_service: SandboxService = sandbox_service_dependency,
    user_context: UserContext = user_context_dependency,
    db_session: AsyncSession = db_session_dependency,
) -> SandboxPage:
    """Search / list sandboxes owned by the current user."""
    assert limit > 0
    assert limit <= 100

    # When org_id is supplied, validate the caller is a member of that org.
    if org_id:
        await validate_org_access(user_context, org_id, db_session)

    return await sandbox_service.search_sandboxes(page_id=page_id, limit=limit)


@router.get('')
async def batch_get_sandboxes(
    id: Annotated[list[str], Query()],
    sandbox_service: SandboxService = sandbox_service_dependency,
) -> list[SandboxInfo | None]:
    """Get a batch of sandboxes given their ids, returning null for any missing."""
    assert len(id) < 100
    sandboxes = await sandbox_service.batch_get_sandboxes(id)
    return sandboxes


# Write Methods


@router.post('')
async def start_sandbox(
    sandbox_spec_id: str | None = None,
    sandbox_service: SandboxService = sandbox_service_dependency,
) -> SandboxInfo:
    info = await sandbox_service.start_sandbox(sandbox_spec_id)
    return info


@router.post('/{sandbox_id}/pause', responses={404: {'description': 'Item not found'}})
async def pause_sandbox(
    sandbox_id: str,
    sandbox_service: SandboxService = sandbox_service_dependency,
) -> Success:
    exists = await sandbox_service.pause_sandbox(sandbox_id)
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return Success()


@router.post('/{sandbox_id}/resume', responses={404: {'description': 'Item not found'}})
async def resume_sandbox(
    sandbox_id: str,
    sandbox_service: SandboxService = sandbox_service_dependency,
) -> Success:
    exists = await sandbox_service.resume_sandbox(sandbox_id)
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return Success()


@router.delete('/{id}', responses={404: {'description': 'Item not found'}})
async def delete_sandbox(
    sandbox_id: str,
    sandbox_service: SandboxService = sandbox_service_dependency,
) -> Success:
    exists = await sandbox_service.delete_sandbox(sandbox_id)
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return Success()
