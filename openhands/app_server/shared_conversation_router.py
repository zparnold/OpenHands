"""Unauthenticated router for shared (public) conversations."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.agent_server.models import EventPage, EventSortOrder
from openhands.app_server.app_conversation.app_conversation_models import (
    AppConversationInfo,
)
from openhands.app_server.app_conversation.sql_app_conversation_info_service import (
    StoredConversationMetadata,
)
from openhands.app_server.config import depends_db_session, depends_event_service
from openhands.app_server.event.event_service import EventService
from openhands.integrations.provider import ProviderType
from openhands.sdk.llm import MetricsSnapshot
from openhands.sdk.llm.utils.metrics import TokenUsage
from openhands.storage.data_models.conversation_metadata import ConversationTrigger

router = APIRouter(prefix='/api', tags=['Shared Conversations'])
logger = logging.getLogger(__name__)

db_session_dependency = depends_db_session()
event_service_dependency = depends_event_service()


def _to_info(stored: StoredConversationMetadata) -> AppConversationInfo:
    """Convert a StoredConversationMetadata row to AppConversationInfo."""
    token_usage = TokenUsage(
        prompt_tokens=stored.prompt_tokens,
        completion_tokens=stored.completion_tokens,
        cache_read_tokens=stored.cache_read_tokens,
        cache_write_tokens=stored.cache_write_tokens,
        context_window=stored.context_window,
        per_turn_token=stored.per_turn_token,
    )
    metrics = MetricsSnapshot(
        accumulated_cost=stored.accumulated_cost,
        max_budget_per_task=stored.max_budget_per_task,
        accumulated_token_usage=token_usage,
    )

    return AppConversationInfo(
        id=UUID(stored.conversation_id),
        created_by_user_id=None,
        sandbox_id=stored.sandbox_id,
        selected_repository=stored.selected_repository,
        selected_branch=stored.selected_branch,
        git_provider=(
            ProviderType(stored.git_provider) if stored.git_provider else None
        ),
        title=stored.title,
        trigger=ConversationTrigger(stored.trigger) if stored.trigger else None,
        pr_number=stored.pr_number,
        llm_model=stored.llm_model,
        metrics=metrics,
        parent_conversation_id=(
            UUID(stored.parent_conversation_id)
            if stored.parent_conversation_id
            else None
        ),
        sub_conversation_ids=[],
        public=stored.public,
        created_at=stored.created_at,
        updated_at=stored.last_updated_at,
    )


@router.get('/shared-conversations')
async def get_shared_conversations(
    ids: Annotated[list[str], Query()],
    db_session: AsyncSession = db_session_dependency,
) -> list[AppConversationInfo | None]:
    """Get public conversations by IDs. Unauthenticated."""
    if len(ids) >= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Too many ids requested. Maximum is 99.',
        )

    uuids: list[UUID] = []
    invalid_ids: list[str] = []
    for id_str in ids:
        try:
            uuids.append(UUID(id_str))
        except ValueError:
            invalid_ids.append(id_str)

    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid UUID format for ids: {invalid_ids}',
        )

    conversation_id_strs = [str(u) for u in uuids]
    query = (
        select(StoredConversationMetadata)
        .where(StoredConversationMetadata.conversation_version == 'V1')
        .where(StoredConversationMetadata.public == True)  # noqa: E712
        .where(StoredConversationMetadata.conversation_id.in_(conversation_id_strs))
    )

    result = await db_session.execute(query)
    rows = result.scalars().all()
    info_by_id = {row.conversation_id: row for row in rows}

    results: list[AppConversationInfo | None] = []
    for cid in conversation_id_strs:
        row = info_by_id.get(cid)
        results.append(_to_info(row) if row else None)

    return results


@router.get('/shared-events/search')
async def search_shared_events(
    conversation_id: Annotated[str, Query()],
    limit: Annotated[int, Query(gt=0, le=100)] = 100,
    page_id: Annotated[str | None, Query()] = None,
    db_session: AsyncSession = db_session_dependency,
    event_service: EventService = event_service_dependency,
) -> EventPage:
    """Get events for a public conversation. Unauthenticated."""
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid UUID format: {conversation_id}',
        )

    # Verify conversation exists and is public
    query = (
        select(StoredConversationMetadata)
        .where(StoredConversationMetadata.conversation_version == 'V1')
        .where(StoredConversationMetadata.public == True)  # noqa: E712
        .where(StoredConversationMetadata.conversation_id == str(conv_uuid))
    )
    result = await db_session.execute(query)
    stored = result.scalar_one_or_none()

    if not stored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Conversation not found or not public.',
        )

    return await event_service.search_events(
        conversation_id=conv_uuid,
        sort_order=EventSortOrder.TIMESTAMP,
        page_id=page_id,
        limit=limit,
    )
