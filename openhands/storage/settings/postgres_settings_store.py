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
ORG_SETTINGS_KEY = 'org_settings'

# LLM fields that support org-level fallback
_LLM_FIELDS = ('llm_model', 'llm_api_key', 'llm_base_url', 'llm_api_version')


class PostgresSettingsStore(SettingsStore):
    """PostgreSQL-backed settings store that persists user settings to database.

    Reuses the secrets table with key='settings' to store full Settings as JSON.
    Supports organization-level LLM defaults that individual users can override.
    """

    def __init__(
        self,
        session: AsyncSession,
        user_id: str | None,
        organization_id: str | None = None,
    ):
        self.session = session
        self.user_id = user_id
        self.organization_id = organization_id

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
                    settings = Settings(
                        email=user.email,
                        git_user_name=user.display_name,
                    )
                    return await self._merge_org_llm_defaults(settings)
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
                    settings = Settings(
                        email=user.email,
                        git_user_name=user.display_name,
                    )
                    return await self._merge_org_llm_defaults(settings)
                return None
            try:
                kwargs = json.loads(raw_value)
            except json.JSONDecodeError:
                result = await self.session.execute(
                    select(User).where(User.id == self.user_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    settings = Settings(
                        email=user.email,
                        git_user_name=user.display_name,
                    )
                    return await self._merge_org_llm_defaults(settings)
                return None
            settings = Settings(**kwargs)
            settings.v1_enabled = True

            # Merge org-level LLM defaults as fallback
            settings = await self._merge_org_llm_defaults(settings)

            return settings
        except Exception as e:
            logger.exception(f'Failed to load settings for user {self.user_id}: {e}')
            return None

    async def _load_org_settings(self) -> dict | None:
        """Load org-level LLM settings from the secrets table."""
        if not self.organization_id:
            return None
        try:
            result = await self.session.execute(
                select(Secret).where(
                    Secret.organization_id == self.organization_id,
                    Secret.user_id.is_(None),
                    Secret.key == ORG_SETTINGS_KEY,
                )
            )
            row = result.scalar_one_or_none()
            if not row or not row.value:
                return None

            raw_value = (
                row.value.get_secret_value()
                if hasattr(row.value, 'get_secret_value')
                else row.value
            )
            if not raw_value or not str(raw_value).strip():
                return None

            # Decrypt JWE-encrypted value if needed (StoredSecretStr encrypts on write)
            if str(raw_value).strip().startswith('eyJ'):
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

            return json.loads(raw_value)
        except Exception as e:
            logger.warning(f'Failed to load org settings: {e}')
            return None

    async def _merge_org_llm_defaults(self, settings: Settings) -> Settings:
        """Fill in missing LLM fields from org-level defaults."""
        if not self.organization_id:
            return settings
        org_data = await self._load_org_settings()
        if not org_data:
            return settings
        updates = {}
        for field in _LLM_FIELDS:
            user_val = getattr(settings, field, None)
            if user_val is None and field in org_data and org_data[field] is not None:
                updates[field] = org_data[field]
        if updates:
            # Convert llm_api_key string back to SecretStr if present
            if 'llm_api_key' in updates and isinstance(updates['llm_api_key'], str):
                updates['llm_api_key'] = SecretStr(updates['llm_api_key'])
            settings = settings.model_copy(update=updates)
        return settings

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

    async def store_org_settings(self, settings: Settings) -> None:
        """Store LLM fields as org-level defaults (admin only)."""
        if not self.organization_id:
            logger.warning('Cannot store org settings without organization_id')
            return

        try:
            org_data: dict = {}
            for field in _LLM_FIELDS:
                val = getattr(settings, field, None)
                if val is not None:
                    if hasattr(val, 'get_secret_value'):
                        org_data[field] = val.get_secret_value()
                    else:
                        org_data[field] = val

            org_json = json.dumps(org_data)

            result = await self.session.execute(
                select(Secret).where(
                    Secret.organization_id == self.organization_id,
                    Secret.user_id.is_(None),
                    Secret.key == ORG_SETTINGS_KEY,
                )
            )
            secret_row = result.scalar_one_or_none()

            if secret_row:
                secret_row.value = SecretStr(org_json)
            else:
                self.session.add(
                    Secret(
                        id=str(uuid4()),
                        user_id=None,
                        organization_id=self.organization_id,
                        key=ORG_SETTINGS_KEY,
                        value=SecretStr(org_json),
                        description='Organization-level LLM defaults',
                    )
                )

            await self.session.commit()
            logger.info(
                f'Org LLM settings stored for organization {self.organization_id}'
            )
        except Exception as e:
            await self.session.rollback()
            logger.exception(
                f'Failed to store org settings for {self.organization_id}: {e}'
            )
            raise
