"""Tests for PostgresConversationStore."""

from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from openhands.app_server.utils.sql_utils import Base
from openhands.integrations.service_types import ProviderType
from openhands.storage.conversation.postgres_conversation_store import (
    PostgresConversationStore,
)
from openhands.storage.data_models.conversation_metadata import (
    ConversationMetadata,
    ConversationTrigger,
)


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
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create an async session for testing."""
    session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as session:
        yield session


@pytest.fixture
def store(async_session) -> PostgresConversationStore:
    """Create a PostgresConversationStore with session injection."""
    return PostgresConversationStore(session=async_session, user_id='user-123')


@pytest.mark.asyncio
async def test_save_and_get_metadata(store):
    """Test saving and loading conversation metadata."""
    metadata = ConversationMetadata(
        conversation_id='conv-1',
        user_id='user-123',
        selected_repository='https://github.com/test/repo',
        selected_branch='main',
        git_provider=ProviderType.GITHUB,
        title='Test conversation',
        trigger=ConversationTrigger.GUI,
        pr_number=[1, 2],
        created_at=datetime(2025, 1, 16, 19, 51, 4, tzinfo=timezone.utc),
    )
    await store.save_metadata(metadata)

    found = await store.get_metadata('conv-1')
    assert found.conversation_id == metadata.conversation_id
    assert found.user_id == metadata.user_id
    assert found.selected_repository == metadata.selected_repository
    assert found.title == metadata.title
    assert found.trigger == metadata.trigger
    assert found.pr_number == metadata.pr_number


@pytest.mark.asyncio
async def test_get_metadata_not_found_raises(store):
    """Test that get_metadata raises FileNotFoundError for missing conversation."""
    with pytest.raises(FileNotFoundError, match='conv-nonexistent'):
        await store.get_metadata('conv-nonexistent')


@pytest.mark.asyncio
async def test_exists(store):
    """Test exists returns True for existing and False for non-existing."""
    metadata = ConversationMetadata(
        conversation_id='conv-exists',
        selected_repository='repo',
        title='Exists',
    )
    await store.save_metadata(metadata)

    assert await store.exists('conv-exists') is True
    assert await store.exists('conv-not-exists') is False


@pytest.mark.asyncio
async def test_delete_metadata(store):
    """Test deleting conversation metadata."""
    metadata = ConversationMetadata(
        conversation_id='conv-to-delete',
        selected_repository='repo',
        title='To delete',
    )
    await store.save_metadata(metadata)
    assert await store.exists('conv-to-delete') is True

    await store.delete_metadata('conv-to-delete')
    assert await store.exists('conv-to-delete') is False

    with pytest.raises(FileNotFoundError):
        await store.get_metadata('conv-to-delete')


@pytest.mark.asyncio
async def test_search_empty(store):
    """Test search returns empty result when no conversations exist."""
    result = await store.search()
    assert len(result.results) == 0
    assert result.next_page_id is None


@pytest.mark.asyncio
async def test_search_basic(store):
    """Test search returns conversations sorted by created_at descending."""
    for i in range(1, 4):
        metadata = ConversationMetadata(
            conversation_id=f'conv{i}',
            user_id='user-123',
            selected_repository='repo',
            title=f'Conversation {i}',
            created_at=datetime(2025, 1, 14 + i, 12, 0, 0, tzinfo=timezone.utc),
        )
        await store.save_metadata(metadata)

    result = await store.search()
    assert len(result.results) == 3
    assert result.results[0].conversation_id == 'conv3'
    assert result.results[1].conversation_id == 'conv2'
    assert result.results[2].conversation_id == 'conv1'
    assert result.next_page_id is None


@pytest.mark.asyncio
async def test_search_filtered_by_user_id(async_session):
    """Test search filters by user_id when provided."""
    store_user1 = PostgresConversationStore(async_session, 'user-1')
    store_user2 = PostgresConversationStore(async_session, 'user-2')

    await store_user1.save_metadata(
        ConversationMetadata(
            conversation_id='conv-user1',
            user_id='user-1',
            selected_repository='repo',
            title='User 1 conv',
        )
    )
    await store_user2.save_metadata(
        ConversationMetadata(
            conversation_id='conv-user2',
            user_id='user-2',
            selected_repository='repo',
            title='User 2 conv',
        )
    )

    result1 = await store_user1.search()
    assert len(result1.results) == 1
    assert result1.results[0].conversation_id == 'conv-user1'

    result2 = await store_user2.search()
    assert len(result2.results) == 1
    assert result2.results[0].conversation_id == 'conv-user2'


@pytest.mark.asyncio
async def test_search_pagination(store):
    """Test search pagination with page_id and limit."""
    for i in range(1, 6):
        await store.save_metadata(
            ConversationMetadata(
                conversation_id=f'conv{i}',
                user_id='user-123',
                selected_repository='repo',
                title=f'Conversation {i}',
                created_at=datetime(2025, 1, 14 + i, 12, 0, 0, tzinfo=timezone.utc),
            )
        )

    result = await store.search(limit=2)
    assert len(result.results) == 2
    assert result.results[0].conversation_id == 'conv5'
    assert result.results[1].conversation_id == 'conv4'
    assert result.next_page_id is not None

    result2 = await store.search(page_id=result.next_page_id, limit=2)
    assert len(result2.results) == 2
    assert result2.results[0].conversation_id == 'conv3'
    assert result2.results[1].conversation_id == 'conv2'
    assert result2.next_page_id is not None

    result3 = await store.search(page_id=result2.next_page_id, limit=2)
    assert len(result3.results) == 1
    assert result3.results[0].conversation_id == 'conv1'
    assert result3.next_page_id is None


@pytest.mark.asyncio
async def test_get_all_metadata(store):
    """Test get_all_metadata returns metadata for multiple conversations."""
    await store.save_metadata(
        ConversationMetadata(
            conversation_id='conv-a',
            user_id='user-123',
            selected_repository='repo',
            title='First',
            created_at=datetime(2025, 1, 16, 12, 0, 0, tzinfo=timezone.utc),
        )
    )
    await store.save_metadata(
        ConversationMetadata(
            conversation_id='conv-b',
            user_id='user-123',
            selected_repository='repo',
            title='Second',
            created_at=datetime(2025, 1, 17, 12, 0, 0, tzinfo=timezone.utc),
        )
    )

    results = await store.get_all_metadata(['conv-a', 'conv-b'])
    assert len(results) == 2
    titles = {r.conversation_id: r.title for r in results}
    assert titles['conv-a'] == 'First'
    assert titles['conv-b'] == 'Second'


@pytest.mark.asyncio
async def test_validate_metadata(store):
    """Test validate_metadata returns True when user matches, False otherwise."""
    await store.save_metadata(
        ConversationMetadata(
            conversation_id='conv-validate',
            user_id='user-123',
            selected_repository='repo',
            title='Validate test',
        )
    )

    assert await store.validate_metadata('conv-validate', 'user-123') is True
    assert await store.validate_metadata('conv-validate', 'other-user') is False


@pytest.mark.asyncio
async def test_get_instance_returns_store_without_session():
    """Test get_instance returns a store that creates sessions per operation."""
    from openhands.core.config.openhands_config import OpenHandsConfig

    config = OpenHandsConfig()
    store = await PostgresConversationStore.get_instance(config, 'user-123')
    assert isinstance(store, PostgresConversationStore)
    assert store.session is None
    assert store.user_id == 'user-123'


@pytest.mark.asyncio
async def test_save_updates_existing(store):
    """Test save_metadata updates existing conversation."""
    metadata = ConversationMetadata(
        conversation_id='conv-update',
        user_id='user-123',
        selected_repository='repo',
        title='Original title',
    )
    await store.save_metadata(metadata)

    metadata.title = 'Updated title'
    metadata.selected_branch = 'feature'
    await store.save_metadata(metadata)

    found = await store.get_metadata('conv-update')
    assert found.title == 'Updated title'
    assert found.selected_branch == 'feature'
