"""PostgreSQL-backed secrets store implementation."""

from __future__ import annotations

import json
import logging
from uuid import uuid4

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.core.config.openhands_config import OpenHandsConfig
from openhands.integrations.provider import CustomSecret, ProviderToken
from openhands.storage.data_models.secrets import Secrets
from openhands.storage.models.secret import Secret
from openhands.storage.secrets.secrets_store import SecretsStore

logger = logging.getLogger(__name__)

PROVIDER_TOKENS_KEY = 'provider_tokens'


class PostgresSecretsStore(SecretsStore):
    """PostgreSQL-backed secrets store that persists secrets to database with encryption."""

    def __init__(
        self,
        session: AsyncSession,
        user_id: str | None,
        organization_id: str | None = None,
    ):
        self.session = session
        self.user_id = user_id
        self.organization_id = organization_id

    async def load(self) -> Secrets | None:
        """Load secrets from the database."""
        if not self.user_id and not self.organization_id:
            return None

        try:
            if self.organization_id:
                result = await self.session.execute(
                    select(Secret).where(Secret.organization_id == self.organization_id)
                )
            else:
                result = await self.session.execute(
                    select(Secret).where(Secret.user_id == self.user_id)
                )

            rows = list(result.scalars())
            if not rows:
                return None

            provider_tokens: dict = {}
            custom_secrets: dict = {}

            for row in rows:
                if row.key == PROVIDER_TOKENS_KEY:
                    try:
                        data = json.loads(row.value.get_secret_value())
                        for k, v in (data or {}).items():
                            if v and v.get('token'):
                                try:
                                    provider_tokens[k] = ProviderToken.from_value(v)
                                except ValueError:
                                    continue
                    except (json.JSONDecodeError, AttributeError):
                        logger.warning('Failed to parse provider_tokens from database')
                else:
                    try:
                        custom_secrets[row.key] = CustomSecret.from_value(
                            {
                                'secret': row.value.get_secret_value(),
                                'description': row.description or '',
                            }
                        )
                    except (ValueError, AttributeError):
                        logger.warning(f'Failed to parse custom secret {row.key}')

            return Secrets(
                provider_tokens=provider_tokens,
                custom_secrets=custom_secrets,
            )
        except Exception as e:
            logger.exception(f'Failed to load secrets: {e}')
            return None

    async def store(self, secrets: Secrets) -> None:
        """Store secrets to the database."""
        if not self.user_id and not self.organization_id:
            logger.warning('Cannot store secrets without user_id or organization_id')
            return

        try:
            provider_tokens_data = secrets.model_dump(
                context={'expose_secrets': True}
            ).get('provider_tokens', {})
            if self.organization_id:
                result = await self.session.execute(
                    select(Secret).where(
                        Secret.organization_id == self.organization_id
                    )
                )
            else:
                result = await self.session.execute(
                    select(Secret).where(Secret.user_id == self.user_id)
                )

            existing_rows = list(result.scalars())
            existing_by_key = {row.key: row for row in existing_rows}

            desired_keys: set[str] = set()
            if provider_tokens_data:
                desired_keys.add(PROVIDER_TOKENS_KEY)

            for name, custom_secret in (secrets.custom_secrets or {}).items():
                if custom_secret is None:
                    continue
                desired_keys.add(name)

            for key in set(existing_by_key.keys()) - desired_keys:
                await self.session.delete(existing_by_key[key])

            if provider_tokens_data:
                json_val = json.dumps(provider_tokens_data)
                await self._upsert_secret(
                    PROVIDER_TOKENS_KEY, SecretStr(json_val), None
                )

            for name, custom_secret in (secrets.custom_secrets or {}).items():
                if custom_secret is None:
                    continue
                await self._upsert_secret(
                    name,
                    custom_secret.secret,
                    custom_secret.description or None,
                )

            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.exception(f'Failed to store secrets: {e}')
            raise

    async def _upsert_secret(
        self, key: str, value: SecretStr, description: str | None
    ) -> None:
        """Insert or update a secret by key."""
        if self.organization_id:
            result = await self.session.execute(
                select(Secret).where(
                    Secret.organization_id == self.organization_id,
                    Secret.key == key,
                )
            )
        else:
            result = await self.session.execute(
                select(Secret).where(
                    Secret.user_id == self.user_id,
                    Secret.key == key,
                )
            )

        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value
            existing.description = description
        else:
            self.session.add(
                Secret(
                    id=str(uuid4()),
                    user_id=self.user_id,
                    organization_id=self.organization_id,
                    key=key,
                    value=value,
                    description=description,
                )
            )

    @classmethod
    async def get_instance(
        cls, config: OpenHandsConfig, user_id: str | None
    ) -> SecretsStore:
        """PostgresSecretsStore requires session injection through request context.

        Use PostgresSecretsStore(session, user_id) directly when session is available.
        """
        raise NotImplementedError(
            'PostgresSecretsStore requires session injection through request context'
        )

    async def get_secret(self, key: str) -> SecretStr | None:
        """Retrieve a secret by key."""
        try:
            # Try organization-level secret first if organization_id is set
            if self.organization_id:
                result = await self.session.execute(
                    select(Secret).where(
                        Secret.organization_id == self.organization_id,
                        Secret.key == key,
                    )
                )
                secret = result.scalar_one_or_none()
                if secret:
                    return secret.value

            # Fall back to user-level secret
            if self.user_id:
                result = await self.session.execute(
                    select(Secret).where(
                        Secret.user_id == self.user_id,
                        Secret.key == key,
                    )
                )
                secret = result.scalar_one_or_none()
                if secret:
                    return secret.value

            return None
        except Exception as e:
            logger.exception(f'Failed to retrieve secret {key}: {e}')
            return None

    async def store_secret(
        self, key: str, value: SecretStr, description: str | None = None
    ) -> None:
        """Store a secret with encryption."""
        if not self.user_id and not self.organization_id:
            logger.warning('Cannot store secret without user_id or organization_id')
            return

        try:
            # Check if secret already exists
            if self.organization_id:
                result = await self.session.execute(
                    select(Secret).where(
                        Secret.organization_id == self.organization_id,
                        Secret.key == key,
                    )
                )
            else:
                result = await self.session.execute(
                    select(Secret).where(
                        Secret.user_id == self.user_id,
                        Secret.key == key,
                    )
                )

            secret = result.scalar_one_or_none()

            if secret:
                # Update existing secret
                secret.value = value
                if description:
                    secret.description = description
            else:
                # Create new secret
                secret = Secret(
                    id=str(uuid4()),
                    user_id=self.user_id,
                    organization_id=self.organization_id,
                    key=key,
                    value=value,
                    description=description,
                )
                self.session.add(secret)

            await self.session.commit()
            logger.info(f'Secret {key} stored successfully')
        except Exception as e:
            await self.session.rollback()
            logger.exception(f'Failed to store secret {key}: {e}')
            raise

    async def delete_secret(self, key: str) -> None:
        """Delete a secret by key."""
        try:
            # Try to delete organization-level secret first
            if self.organization_id:
                result = await self.session.execute(
                    select(Secret).where(
                        Secret.organization_id == self.organization_id,
                        Secret.key == key,
                    )
                )
                secret = result.scalar_one_or_none()
                if secret:
                    await self.session.delete(secret)
                    await self.session.commit()
                    logger.info(f'Organization secret {key} deleted successfully')
                    return

            # Try to delete user-level secret
            if self.user_id:
                result = await self.session.execute(
                    select(Secret).where(
                        Secret.user_id == self.user_id,
                        Secret.key == key,
                    )
                )
                secret = result.scalar_one_or_none()
                if secret:
                    await self.session.delete(secret)
                    await self.session.commit()
                    logger.info(f'User secret {key} deleted successfully')
                    return

            logger.warning(f'Secret {key} not found for deletion')
        except Exception as e:
            await self.session.rollback()
            logger.exception(f'Failed to delete secret {key}: {e}')
            raise

    async def list_secrets(self) -> list[tuple[str, str | None]]:
        """List all secrets (returns key and description only, not values)."""
        try:
            secrets = []

            # List organization secrets
            if self.organization_id:
                result = await self.session.execute(
                    select(Secret).where(Secret.organization_id == self.organization_id)
                )
                for secret in result.scalars():
                    secrets.append((secret.key, secret.description))

            # List user secrets
            if self.user_id:
                result = await self.session.execute(
                    select(Secret).where(Secret.user_id == self.user_id)
                )
                for secret in result.scalars():
                    # Avoid duplicates from organization secrets
                    if not any(s[0] == secret.key for s in secrets):
                        secrets.append((secret.key, secret.description))

            return secrets
        except Exception as e:
            logger.exception(f'Failed to list secrets: {e}')
            return []
