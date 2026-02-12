"""Tests for PostgresEventService.

This module tests the PostgreSQL-backed implementation of EventService,
using SQLite as an in-memory database for compatibility.
"""

from typing import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from openhands.agent_server.models import EventPage
from openhands.app_server.event.postgres_event_service import (
    PostgresEventService,
)
from openhands.app_server.utils.sql_utils import Base
from openhands.sdk.event import PauseEvent, TokenEvent


@pytest.fixture
async def async_engine():
    """Create an async SQLite engine for testing."""
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        poolclass=StaticPool,
        connect_args={'check_same_thread': False},
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def async_db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create an async db_session for testing."""
    async_db_session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_db_session_maker() as db_session:
        yield db_session


@pytest.fixture
def service(async_db_session: AsyncSession) -> PostgresEventService:
    """Create a PostgresEventService instance for testing."""
    return PostgresEventService(
        db_session=async_db_session,
        user_id='test_user',
        app_conversation_info_service=None,
        app_conversation_info_load_tasks={},
    )


def create_token_event() -> TokenEvent:
    """Helper to create a TokenEvent for testing."""
    return TokenEvent(
        source='agent', prompt_token_ids=[1, 2], response_token_ids=[3, 4]
    )


def create_pause_event() -> PauseEvent:
    """Helper to create a PauseEvent for testing."""
    return PauseEvent(source='user')


class TestPostgresEventService:
    """Test cases for PostgresEventService."""

    @pytest.mark.asyncio
    async def test_save_and_get_event(self, service: PostgresEventService):
        """Test saving and retrieving a single event."""
        conversation_id = uuid4()
        event = create_token_event()

        await service.save_event(conversation_id, event)

        result = await service.get_event(conversation_id, event.id)
        assert result is not None
        assert result.id == event.id

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, service: PostgresEventService):
        """Test get_event returns None when event does not exist."""
        conversation_id = uuid4()
        event_id = uuid4()

        result = await service.get_event(conversation_id, event_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_search_events_returns_all(self, service: PostgresEventService):
        """Test that search_events returns all events when no filters are applied."""
        conversation_id = uuid4()
        events = [create_token_event() for _ in range(3)]

        for event in events:
            await service.save_event(conversation_id, event)

        result = await service.search_events(conversation_id)

        assert isinstance(result, EventPage)
        assert len(result.items) == 3
        assert result.next_page_id is None

    @pytest.mark.asyncio
    async def test_search_events_empty(self, service: PostgresEventService):
        """Test search_events returns empty page for a conversation with no events."""
        conversation_id = uuid4()

        result = await service.search_events(conversation_id)

        assert isinstance(result, EventPage)
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_count_events(self, service: PostgresEventService):
        """Test count_events returns correct count."""
        conversation_id = uuid4()
        for _ in range(5):
            await service.save_event(conversation_id, create_token_event())

        count = await service.count_events(conversation_id)

        assert count == 5

    @pytest.mark.asyncio
    async def test_batch_get_events(self, service: PostgresEventService):
        """Test batch_get_events returns correct events."""
        conversation_id = uuid4()
        events = [create_token_event() for _ in range(3)]
        for event in events:
            await service.save_event(conversation_id, event)

        event_ids = [e.id for e in events]
        results = await service.batch_get_events(conversation_id, event_ids)

        assert len(results) == 3
        assert all(r is not None for r in results)
