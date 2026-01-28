"""PostgreSQL-backed secrets store implementation."""

from __future__ import annotations

import logging
from uuid import uuid4

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.storage.models.secret import Secret
from openhands.storage.secrets.secrets_store import SecretsStore

logger = logging.getLogger(__name__)


class PostgresSecretsStore(SecretsStore):
    """PostgreSQL-backed secrets store that persists secrets to database with encryption."""

    def __init__(self, session: AsyncSession, user_id: str | None, organization_id: str | None = None):
        self.session = session
        self.user_id = user_id
        self.organization_id = organization_id

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

    async def store_secret(self, key: str, value: SecretStr, description: str | None = None) -> None:
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
