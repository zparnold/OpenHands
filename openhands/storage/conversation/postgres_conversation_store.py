"""PostgreSQL-backed conversation store implementation."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import State

from openhands.core.config.openhands_config import OpenHandsConfig
from openhands.integrations.service_types import ProviderType
from openhands.storage.conversation.conversation_store import ConversationStore
from openhands.storage.data_models.conversation_metadata import (
    ConversationMetadata,
    ConversationTrigger,
)
from openhands.storage.data_models.conversation_metadata_result_set import (
    ConversationMetadataResultSet,
)
from openhands.utils.search_utils import offset_to_page_id, page_id_to_offset

logger = logging.getLogger(__name__)

V0_VERSION = 'V0'


def _stored_to_metadata(row) -> ConversationMetadata:
    """Convert StoredConversationMetadata row to ConversationMetadata dataclass."""
    trigger = None
    if row.trigger:
        try:
            trigger = ConversationTrigger(row.trigger)
        except ValueError:
            pass

    git_provider = None
    if row.git_provider:
        try:
            git_provider = ProviderType(row.git_provider)
        except ValueError:
            pass

    return ConversationMetadata(
        conversation_id=row.conversation_id,
        selected_repository=row.selected_repository,
        user_id=getattr(row, 'user_id', None),
        selected_branch=row.selected_branch,
        git_provider=git_provider,
        title=row.title,
        last_updated_at=row.last_updated_at,
        trigger=trigger,
        pr_number=row.pr_number or [],
        created_at=row.created_at,
        llm_model=row.llm_model,
        accumulated_cost=row.accumulated_cost or 0.0,
        prompt_tokens=row.prompt_tokens or 0,
        completion_tokens=row.completion_tokens or 0,
        total_tokens=row.total_tokens or 0,
        sandbox_id=row.sandbox_id,
        conversation_version=row.conversation_version,
        public=row.public,
    )


class PostgresConversationStore(ConversationStore):
    """PostgreSQL-backed conversation store that persists conversation metadata to database.

    Uses the conversation_metadata table with conversation_version='V0' for V0 conversations.
    Supports both session-injection (for request-scoped use) and per-operation sessions
    (for use without request context, e.g. from conversation manager).
    """

    def __init__(
        self,
        session: AsyncSession | None,
        user_id: str | None,
    ):
        """Initialize store. session=None creates a new session per operation."""
        self.session = session
        self.user_id = user_id

    async def _with_session(self, fn):
        """Run fn(session), creating a session if none was injected."""
        if self.session is not None:
            return await fn(self.session)
        from openhands.app_server.config import get_db_session

        async with get_db_session(State(), None) as session:
            return await fn(session)

    def _get_stored_model(self):
        from openhands.app_server.app_conversation.sql_app_conversation_info_service import (
            StoredConversationMetadata,
        )

        return StoredConversationMetadata

    async def save_metadata(self, metadata: ConversationMetadata) -> None:
        """Store conversation metadata to the database."""

        async def _do(session: AsyncSession) -> None:
            Stored = self._get_stored_model()
            try:
                stored = Stored(
                    conversation_id=metadata.conversation_id,
                    user_id=metadata.user_id or self.user_id,
                    selected_repository=metadata.selected_repository,
                    selected_branch=metadata.selected_branch,
                    git_provider=(
                        metadata.git_provider.value if metadata.git_provider else None
                    ),
                    title=metadata.title,
                    last_updated_at=metadata.last_updated_at,
                    created_at=metadata.created_at,
                    trigger=metadata.trigger.value if metadata.trigger else None,
                    pr_number=metadata.pr_number,
                    accumulated_cost=metadata.accumulated_cost,
                    prompt_tokens=metadata.prompt_tokens,
                    completion_tokens=metadata.completion_tokens,
                    total_tokens=metadata.total_tokens,
                    llm_model=metadata.llm_model,
                    conversation_version=V0_VERSION,
                    sandbox_id=metadata.sandbox_id,
                    parent_conversation_id=None,
                    public=metadata.public,
                )
                await session.merge(stored)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.exception(
                    f'Failed to save conversation metadata '
                    f'{metadata.conversation_id}: {e}'
                )
                raise

        await self._with_session(_do)

    async def get_metadata(self, conversation_id: str) -> ConversationMetadata:
        """Load conversation metadata from the database."""

        async def _do(session: AsyncSession) -> ConversationMetadata:
            Stored = self._get_stored_model()
            result = await session.execute(
                select(Stored).where(
                    Stored.conversation_id == conversation_id,
                    Stored.conversation_version == V0_VERSION,
                )
            )
            row = result.scalar_one_or_none()
            if not row:
                raise FileNotFoundError(conversation_id)
            return _stored_to_metadata(row)

        return await self._with_session(_do)

    async def delete_metadata(self, conversation_id: str) -> None:
        """Delete conversation metadata from the database."""
        from sqlalchemy import delete

        async def _do(session: AsyncSession) -> None:
            Stored = self._get_stored_model()
            try:
                await session.execute(
                    delete(Stored).where(
                        Stored.conversation_id == conversation_id,
                        Stored.conversation_version == V0_VERSION,
                    )
                )
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.exception(
                    f'Failed to delete conversation metadata {conversation_id}: {e}'
                )
                raise

        await self._with_session(_do)

    async def exists(self, conversation_id: str) -> bool:
        """Check if conversation exists in the database."""

        async def _do(session: AsyncSession) -> bool:
            Stored = self._get_stored_model()
            result = await session.execute(
                select(Stored.conversation_id).where(
                    Stored.conversation_id == conversation_id,
                    Stored.conversation_version == V0_VERSION,
                )
            )
            return result.scalar_one_or_none() is not None

        return await self._with_session(_do)

    async def search(
        self,
        page_id: str | None = None,
        limit: int = 20,
    ) -> ConversationMetadataResultSet:
        """Search conversations in the database, optionally filtered by user_id."""

        async def _do(session: AsyncSession) -> ConversationMetadataResultSet:
            Stored = self._get_stored_model()
            query = select(Stored).where(
                Stored.conversation_version == V0_VERSION,
            )
            if self.user_id and hasattr(Stored, 'user_id'):
                query = query.where(Stored.user_id == self.user_id)
            query = query.order_by(Stored.created_at.desc())

            offset = page_id_to_offset(page_id)
            query = query.offset(offset).limit(limit + 1)

            result = await session.execute(query)
            rows = list(result.scalars().all())

            has_more = len(rows) > limit
            if has_more:
                rows = rows[:limit]

            conversations = [_stored_to_metadata(row) for row in rows]
            next_page_id = offset_to_page_id(offset + limit, has_more)
            return ConversationMetadataResultSet(conversations, next_page_id)

        return await self._with_session(_do)

    @classmethod
    async def get_instance(
        cls, config: OpenHandsConfig, user_id: str | None
    ) -> ConversationStore:
        """Get a store for the user.

        When used without request context (e.g. from conversation manager), creates
        a new session per operation. For request-scoped use with session injection,
        use PostgresConversationStore(session, user_id) directly.
        """
        return cls(session=None, user_id=user_id)
