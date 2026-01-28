"""PostgreSQL-backed settings store implementation."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.core.config.openhands_config import OpenHandsConfig
from openhands.storage.data_models.settings import Settings
from openhands.storage.models.user import User
from openhands.storage.settings.settings_store import SettingsStore

logger = logging.getLogger(__name__)


class PostgresSettingsStore(SettingsStore):
    """PostgreSQL-backed settings store that persists user settings to database."""

    def __init__(self, session: AsyncSession, user_id: str | None):
        self.session = session
        self.user_id = user_id

    @classmethod
    async def get_instance(
        cls, config: OpenHandsConfig, user_id: str | None
    ) -> SettingsStore:
        """Get a store for the user represented by the user_id given.

        Note: This requires an active database session from the request context.
        This method is called from the dependency injection system.
        """
        # This will be injected through the request context
        raise NotImplementedError(
            'PostgresSettingsStore requires session injection through request context'
        )

    async def load(self) -> Settings | None:
        """Load settings from the database for the current user."""
        if not self.user_id:
            return None

        try:
            # Load user from database
            result = await self.session.execute(select(User).where(User.id == self.user_id))
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f'User {self.user_id} not found in database')
                return None

            # For now, return basic settings from user data
            # This can be extended to include more fields from a dedicated settings table
            settings = Settings(
                email=user.email,
                git_user_name=user.display_name,
            )

            return settings
        except Exception as e:
            logger.exception(f'Failed to load settings for user {self.user_id}: {e}')
            return None

    async def store(self, settings: Settings) -> None:
        """Store settings to the database for the current user."""
        if not self.user_id:
            logger.warning('Cannot store settings without user_id')
            return

        try:
            # Load user from database
            result = await self.session.execute(select(User).where(User.id == self.user_id))
            user = result.scalar_one_or_none()

            if not user:
                # Create new user if doesn't exist
                user = User(
                    id=self.user_id,
                    email=settings.email or f'{self.user_id}@example.com',
                    display_name=settings.git_user_name,
                )
                self.session.add(user)
            else:
                # Update existing user
                if settings.email:
                    user.email = settings.email
                if settings.git_user_name:
                    user.display_name = settings.git_user_name

            await self.session.commit()
            logger.info(f'Settings stored successfully for user {self.user_id}')
        except Exception as e:
            await self.session.rollback()
            logger.exception(f'Failed to store settings for user {self.user_id}: {e}')
            raise
