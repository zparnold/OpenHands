"""Tests for PostgresSessionStore and default org membership creation."""

from datetime import UTC, datetime
from typing import AsyncGenerator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from openhands.app_server.utils.sql_utils import Base
from openhands.storage.models.organization import Organization, OrganizationMembership
from openhands.storage.models.session import Session as StoredSession
from openhands.storage.models.user import User
from openhands.storage.sessions.postgres_session_store import PostgresSessionStore


@pytest.fixture
async def async_engine():
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        poolclass=StaticPool,
        connect_args={'check_same_thread': False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as session:
        yield session


@pytest.mark.asyncio
async def test_upsert_session_creates_user_org_and_session(async_session):
    store = PostgresSessionStore(async_session)

    stored = await store.upsert_session(
        session_id='session-1',
        user_id='user-1',
        conversation_id='conv-1',
        state={'status': 'active'},
        user_email='user@example.com',
        user_display_name='User One',
    )

    assert stored.id == 'session-1'
    assert stored.user_id == 'user-1'
    assert stored.conversation_id == 'conv-1'
    assert stored.state == {'status': 'active'}
    assert stored.last_accessed_at is not None

    result = await async_session.execute(select(User).where(User.id == 'user-1'))
    user = result.scalar_one()
    assert user.email == 'user@example.com'
    assert user.display_name == 'User One'

    result = await async_session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == 'user-1'
        )
    )
    membership = result.scalar_one()
    organization = await async_session.get(Organization, membership.organization_id)
    assert organization is not None
    assert organization.name == 'User One Organization'
    assert stored.organization_id == organization.id


@pytest.mark.asyncio
async def test_upsert_session_updates_existing(async_session):
    store = PostgresSessionStore(async_session)

    stored = await store.upsert_session(
        session_id='session-2',
        user_id='user-2',
        conversation_id='conv-2',
        state={'status': 'active'},
    )
    first_accessed_at = stored.last_accessed_at
    assert first_accessed_at is not None

    stored = await store.upsert_session(
        session_id='session-2',
        user_id='user-2',
        conversation_id=None,
        state={'status': 'paused'},
    )

    assert stored.conversation_id == 'conv-2'
    assert stored.state == {'status': 'paused'}
    assert stored.last_accessed_at >= first_accessed_at

    result = await async_session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == 'user-2'
        )
    )
    memberships = result.scalars().all()
    assert len(memberships) == 1

    result = await async_session.execute(
        select(StoredSession).where(StoredSession.id == 'session-2')
    )
    reloaded = result.scalar_one()
    assert reloaded.conversation_id == 'conv-2'
    assert reloaded.state == {'status': 'paused'}
    assert isinstance(reloaded.last_accessed_at, datetime)
    assert reloaded.last_accessed_at.tzinfo == UTC
