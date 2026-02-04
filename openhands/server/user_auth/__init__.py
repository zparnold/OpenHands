from fastapi import Depends, Request
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.integrations.provider import PROVIDER_TOKEN_TYPE
from openhands.server.settings import Settings
from openhands.server.shared import SecretsStoreImpl, SettingsStoreImpl, server_config
from openhands.server.user_auth.user_auth import AuthType, UserAuth, get_user_auth
from openhands.storage.data_models.secrets import Secrets
from openhands.storage.secrets.postgres_secrets_store import PostgresSecretsStore
from openhands.storage.secrets.secrets_store import SecretsStore
from openhands.storage.settings.postgres_settings_store import PostgresSettingsStore
from openhands.storage.settings.settings_store import SettingsStore

_use_postgres_settings = (
    SettingsStoreImpl is PostgresSettingsStore
    or 'postgres' in server_config.settings_store_class.lower()
)
_use_postgres_secrets = (
    SecretsStoreImpl is PostgresSecretsStore
    or 'postgres' in server_config.secret_store_class.lower()
)


async def _get_user_auth_dependency(request: Request) -> UserAuth:
    """Wrapper so get_user_auth is resolved at request time (allows tests to patch it)."""
    return await get_user_auth(request)


async def get_provider_tokens(request: Request) -> PROVIDER_TOKEN_TYPE | None:
    user_auth = await get_user_auth(request)
    provider_tokens = await user_auth.get_provider_tokens()
    return provider_tokens


async def get_access_token(request: Request) -> SecretStr | None:
    user_auth = await get_user_auth(request)
    access_token = await user_auth.get_access_token()
    return access_token


async def get_user_id(request: Request) -> str | None:
    user_auth = await get_user_auth(request)
    user_id = await user_auth.get_user_id()
    return user_id


async def get_user_settings(request: Request) -> Settings | None:
    user_auth = await get_user_auth(request)
    user_settings = await user_auth.get_user_settings()
    return user_settings


async def _get_secrets_store_file(
    user_auth: UserAuth = Depends(_get_user_auth_dependency),
) -> SecretsStore:
    return await user_auth.get_secrets_store()


async def _db_session_dependency(request: Request) -> AsyncSession:
    """Lazy dependency: imports app_server.config only at request time to avoid circular import."""
    from openhands.app_server.config import get_db_session

    async with get_db_session(request.state, request) as session:
        yield session


if _use_postgres_secrets:

    async def _get_secrets_store_postgres(
        user_auth: UserAuth = Depends(_get_user_auth_dependency),
        db_session: AsyncSession = Depends(_db_session_dependency),
    ) -> SecretsStore:
        user_id = await user_auth.get_user_id()
        return PostgresSecretsStore(db_session, user_id)

    get_secrets_store = _get_secrets_store_postgres  # type: ignore[assignment]
else:
    get_secrets_store = _get_secrets_store_file  # type: ignore[assignment]


async def get_secrets(request: Request) -> Secrets | None:
    user_auth = await get_user_auth(request)
    user_secrets = await user_auth.get_secrets()
    return user_secrets


async def _get_user_settings_store_file(
    user_auth: UserAuth = Depends(_get_user_auth_dependency),
) -> SettingsStore | None:
    return await user_auth.get_user_settings_store()


if _use_postgres_settings:

    async def _get_user_settings_store_postgres(
        user_auth: UserAuth = Depends(_get_user_auth_dependency),
        db_session: AsyncSession = Depends(_db_session_dependency),
    ) -> SettingsStore | None:
        user_id = await user_auth.get_user_id()
        return PostgresSettingsStore(db_session, user_id)

    get_user_settings_store = _get_user_settings_store_postgres  # type: ignore[assignment]
else:
    get_user_settings_store = _get_user_settings_store_file  # type: ignore[assignment]


async def get_auth_type(request: Request) -> AuthType | None:
    user_auth = await get_user_auth(request)
    return user_auth.get_auth_type()
