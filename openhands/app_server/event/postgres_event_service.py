"""PostgreSQL-backed EventService implementation."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy import JSON, Column, DateTime, String, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Uuid as SqlUuid

from openhands.agent_server.models import EventPage, EventSortOrder
from openhands.app_server.app_conversation.app_conversation_info_service import (
    AppConversationInfoService,
)
from openhands.app_server.app_conversation.app_conversation_models import (
    AppConversationInfo,
)
from openhands.app_server.event.event_service import EventService, EventServiceInjector
from openhands.app_server.event_callback.event_callback_models import EventKind
from openhands.app_server.services.injector import InjectorState
from openhands.app_server.utils.sql_utils import Base
from openhands.sdk import Event

_logger = logging.getLogger(__name__)


class StoredConversationEvent(Base):  # type: ignore
    """SQLAlchemy model for conversation events stored in PostgreSQL."""

    __tablename__ = 'conversation_events'
    event_id = Column(SqlUuid(as_uuid=True), primary_key=True)
    conversation_id = Column(SqlUuid(as_uuid=True), nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    kind = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)


@dataclass
class PostgresEventService(EventService):
    """Event service backed by PostgreSQL."""

    db_session: AsyncSession
    user_id: str | None
    app_conversation_info_service: AppConversationInfoService | None
    app_conversation_info_load_tasks: dict[
        UUID, asyncio.Task[AppConversationInfo | None]
    ]

    async def _get_user_id_for_conversation(self, conversation_id: UUID) -> str | None:
        """Resolve user_id for a conversation, used for permission scoping."""
        if self.user_id:
            return self.user_id
        if not self.app_conversation_info_service:
            return None
        task = self.app_conversation_info_load_tasks.get(conversation_id)
        if task is None:
            task = asyncio.create_task(
                self.app_conversation_info_service.get_app_conversation_info(
                    conversation_id
                )
            )
            self.app_conversation_info_load_tasks[conversation_id] = task
        info = await task
        return info.created_by_user_id if info else None

    def _event_to_uuid(self, value: UUID | str) -> UUID:
        """Convert value to UUID, handling string IDs from Event models."""
        if isinstance(value, str):
            return UUID(value.replace('-', ''))
        return value

    async def get_event(
        self, conversation_id: UUID, event_id: UUID
    ) -> Event | None:
        # Event.id may be str in some SDK versions
        event_id = self._event_to_uuid(event_id)
        user_id = await self._get_user_id_for_conversation(conversation_id)
        query = select(StoredConversationEvent).where(
            and_(
                StoredConversationEvent.conversation_id == conversation_id,
                StoredConversationEvent.event_id == event_id,
            )
        )
        if user_id is not None:
            query = query.where(StoredConversationEvent.user_id == user_id)

        result = await self.db_session.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        try:
            return Event.model_validate(row.event_data)
        except Exception:
            _logger.exception('Error deserializing event')
            return None

    async def search_events(
        self,
        conversation_id: UUID,
        kind__eq: EventKind | None = None,
        timestamp__gte: datetime | None = None,
        timestamp__lt: datetime | None = None,
        sort_order: EventSortOrder = EventSortOrder.TIMESTAMP,
        page_id: str | None = None,
        limit: int = 100,
    ) -> EventPage:
        user_id = await self._get_user_id_for_conversation(conversation_id)
        query = select(StoredConversationEvent).where(
            StoredConversationEvent.conversation_id == conversation_id
        )
        if user_id is not None:
            query = query.where(StoredConversationEvent.user_id == user_id)
        if kind__eq is not None:
            query = query.where(StoredConversationEvent.kind == kind__eq)
        if timestamp__gte is not None:
            query = query.where(StoredConversationEvent.timestamp >= timestamp__gte)
        if timestamp__lt is not None:
            query = query.where(StoredConversationEvent.timestamp < timestamp__lt)

        if sort_order == EventSortOrder.TIMESTAMP:
            query = query.order_by(StoredConversationEvent.timestamp)
        else:
            query = query.order_by(StoredConversationEvent.timestamp.desc())

        offset = int(page_id) if page_id else 0
        query = query.offset(offset).limit(limit + 1)

        result = await self.db_session.execute(query)
        rows = result.scalars().all()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = []
        for row in rows:
            try:
                event = Event.model_validate(row.event_data)
                items.append(event)
            except Exception:
                _logger.exception('Error deserializing event')
                continue

        next_page_id = str(offset + limit) if has_more else None
        return EventPage(items=items, next_page_id=next_page_id)

    async def count_events(
        self,
        conversation_id: UUID,
        kind__eq: EventKind | None = None,
        timestamp__gte: datetime | None = None,
        timestamp__lt: datetime | None = None,
    ) -> int:
        user_id = await self._get_user_id_for_conversation(conversation_id)
        query = select(func.count(StoredConversationEvent.event_id)).where(
            StoredConversationEvent.conversation_id == conversation_id
        )
        if user_id is not None:
            query = query.where(StoredConversationEvent.user_id == user_id)
        if kind__eq is not None:
            query = query.where(StoredConversationEvent.kind == kind__eq)
        if timestamp__gte is not None:
            query = query.where(StoredConversationEvent.timestamp >= timestamp__gte)
        if timestamp__lt is not None:
            query = query.where(StoredConversationEvent.timestamp < timestamp__lt)

        result = await self.db_session.execute(query)
        return result.scalar() or 0

    async def save_event(self, conversation_id: UUID, event: Event) -> None:
        user_id = await self._get_user_id_for_conversation(conversation_id)
        event_id = self._event_to_uuid(event.id)
        event_data = event.model_dump(mode='json')
        kind = getattr(event, 'kind', event.__class__.__name__)
        timestamp = getattr(event, 'timestamp', None)
        if timestamp is None:
            from openhands.agent_server.utils import utc_now

            timestamp = utc_now()
        elif isinstance(timestamp, str):
            from datetime import datetime as dt

            timestamp = dt.fromisoformat(timestamp.replace('Z', '+00:00'))

        row = StoredConversationEvent(
            event_id=event_id,
            conversation_id=conversation_id,
            user_id=user_id,
            kind=kind,
            timestamp=timestamp,
            event_data=event_data,
        )
        self.db_session.add(row)
        await self.db_session.commit()


class PostgresEventServiceInjector(EventServiceInjector):
    """Injector for Postgres-backed EventService."""

    async def inject(self, state: InjectorState, request: Request | None = None):
        from openhands.app_server.config import (
            get_app_conversation_info_service,
            get_db_session,
            get_user_context,
        )

        async with (
            get_user_context(state, request) as user_context,
            get_db_session(state, request) as db_session,
            get_app_conversation_info_service(
                state, request
            ) as app_conversation_info_service,
        ):
            user_id = await user_context.get_user_id()

            yield PostgresEventService(
                db_session=db_session,
                user_id=user_id,
                app_conversation_info_service=app_conversation_info_service,
                app_conversation_info_load_tasks={},
            )
