"""PostgreSQL-backed session store for SaaS mode."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.storage.models.session import Session as StoredSession
from openhands.storage.models.user import User
from openhands.storage.organizations.postgres_organization_store import (
    PostgresOrganizationStore,
)


class PostgresSessionStore:
    """Persist session metadata in the database."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_session(
        self,
        session_id: str,
        user_id: str,
        conversation_id: str | None = None,
        state: dict | None = None,
        organization_id: str | None = None,
        user_email: str | None = None,
        user_display_name: str | None = None,
    ) -> StoredSession:
        """Create or update a session record."""
        if not user_id:
            raise ValueError('user_id is required to persist sessions')

        await self._ensure_user(user_id, user_email, user_display_name)

        resolved_org_id = organization_id
        if resolved_org_id is None:
            org_store = PostgresOrganizationStore(self.session)
            org = await org_store.ensure_default_org_for_user(
                user_id=user_id,
                email=user_email,
                display_name=user_display_name,
            )
            resolved_org_id = org.id

        result = await self.session.execute(
            select(StoredSession).where(StoredSession.id == session_id)
        )
        stored = result.scalar_one_or_none()
        now = datetime.now(UTC)

        if stored:
            if conversation_id is not None:
                stored.conversation_id = conversation_id
            if state is not None:
                stored.state = state
            if resolved_org_id is not None:
                stored.organization_id = resolved_org_id
            stored.last_accessed_at = now
            await self.session.commit()
            return stored

        stored = StoredSession(
            id=session_id,
            user_id=user_id,
            organization_id=resolved_org_id,
            conversation_id=conversation_id,
            state=state,
            last_accessed_at=now,
        )
        self.session.add(stored)
        await self.session.commit()
        return stored

    async def _ensure_user(
        self,
        user_id: str,
        email: str | None,
        display_name: str | None,
    ) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            if email and email.strip() and user.email != email.strip():
                user.email = email.strip()
            if display_name and display_name.strip() and not user.display_name:
                user.display_name = display_name.strip()
            return user

        email_value = email.strip() if email and email.strip() else None
        if not email_value:
            email_value = f'{user_id}@example.com'

        user = User(id=user_id, email=email_value, display_name=display_name)
        self.session.add(user)
        return user
