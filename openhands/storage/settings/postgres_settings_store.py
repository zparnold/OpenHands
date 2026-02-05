"""PostgreSQL-backed settings store implementation."""

from __future__ import annotations

import json
import logging
from uuid import uuid4

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.core.config.openhands_config import OpenHandsConfig
from openhands.storage.data_models.settings import Settings
from openhands.storage.models.secret import Secret
from openhands.storage.models.user import User
from openhands.storage.organizations.postgres_organization_store import (
    PostgresOrganizationStore,
)
from openhands.storage.settings.settings_store import SettingsStore

logger = logging.getLogger(__name__)

SETTINGS_KEY = 'settings'


class PostgresSettingsStore(SettingsStore):
    """PostgreSQL-backed settings store that persists user settings to database.

    Reuses the secrets table with key='settings' to store full Settings as JSON.
    """

    def __init__(self, session: AsyncSession, user_id: str | None):
        self.session = session
        self.user_id = user_id

    @classmethod
    async def get_instance(
        cls, config: OpenHandsConfig, user_id: str | None
    ) -> SettingsStore:
        """Get a store for the user represented by the user_id given.

        Note: This requires an active database session from the request context.
        Use PostgresSettingsStore(session, user_id) directly when session is available.
        """
        raise NotImplementedError(
            'PostgresSettingsStore requires session injection through request context'
        )

    async def load(self) -> Settings | None:
        """Load settings from the database for the current user."""
        if not self.user_id:
            return None

        try:
            result = await self.session.execute(
                select(Secret).where(
                    Secret.user_id == self.user_id,
                    Secret.key == SETTINGS_KEY,
                )
            )
            row = result.scalar_one_or_none()

            if not row or not row.value:
                result = await self.session.execute(
                    select(User).where(User.id == self.user_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    return Settings(
                        email=user.email,
                        git_user_name=user.display_name,
                    )
                return None

            raw_value = (
                row.value.get_secret_value()
                if hasattr(row.value, 'get_secret_value')
                else row.value
            )
            if raw_value and str(raw_value).strip().startswith('eyJ'):
                try:
                    from openhands.app_server.config import get_global_config

                    jwt_injector = get_global_config().jwt
                    if jwt_injector is not None:
                        payload = jwt_injector.get_jwt_service().decrypt_jwe_token(
                            raw_value
                        )
                        raw_value = payload.get('v', raw_value)
                except Exception:
                    pass
            if not raw_value or not str(raw_value).strip():
                result = await self.session.execute(
                    select(User).where(User.id == self.user_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    return Settings(
                        email=user.email,
                        git_user_name=user.display_name,
                    )
                return None
            try:
                kwargs = json.loads(raw_value)
            except json.JSONDecodeError:
                result = await self.session.execute(
                    select(User).where(User.id == self.user_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    return Settings(
                        email=user.email,
                        git_user_name=user.display_name,
                    )
                return None
            settings = Settings(**kwargs)
            settings.v1_enabled = True
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
            result = await self.session.execute(
                select(User).where(User.id == self.user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                user = User(
                    id=self.user_id,
                    email=settings.email or f'{self.user_id}@example.com',
                    display_name=settings.git_user_name,
                )
                self.session.add(user)
            else:
                if settings.email:
                    user.email = settings.email
                if settings.git_user_name:
                    user.display_name = settings.git_user_name

            org_store = PostgresOrganizationStore(self.session)
            await org_store.ensure_default_org_for_user(
                user_id=self.user_id,
                email=user.email,
                display_name=user.display_name,
            )

            settings_json = settings.model_dump_json(context={'expose_secrets': True})

            result = await self.session.execute(
                select(Secret).where(
                    Secret.user_id == self.user_id,
                    Secret.key == SETTINGS_KEY,
                )
            )
            secret_row = result.scalar_one_or_none()

            if secret_row:
                secret_row.value = SecretStr(settings_json)
            else:
                self.session.add(
                    Secret(
                        id=str(uuid4()),
                        user_id=self.user_id,
                        organization_id=None,
                        key=SETTINGS_KEY,
                        value=SecretStr(settings_json),
                        description=None,
                    )
                )

            await self.session.commit()
            logger.info(f'Settings stored successfully for user {self.user_id}')
        except Exception as e:
            await self.session.rollback()
            logger.exception(f'Failed to store settings for user {self.user_id}: {e}')
            raise
