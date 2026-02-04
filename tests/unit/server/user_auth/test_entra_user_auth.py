from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from openhands.app_server.utils.sql_utils import Base
from openhands.server.types import AppMode
from openhands.server.user_auth.entra_user_auth import EntraUserAuth
from openhands.storage.models.organization import OrganizationMembership
from openhands.storage.models.user import User


@pytest.fixture
def mock_entra_env():
    with (
        patch(
            'openhands.server.user_auth.entra_user_auth.ENTRA_TENANT_ID',
            'test-tenant-id',
        ),
        patch(
            'openhands.server.user_auth.entra_user_auth.ENTRA_CLIENT_ID',
            'test-client-id',
        ),
        patch(
            'openhands.server.user_auth.entra_user_auth.JWKS_URL',
            'https://login.microsoftonline.com/test-tenant-id/discovery/v2.0/keys',
        ),
    ):
        yield


@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.headers = {'Authorization': 'Bearer valid.token.here'}
    return request


@pytest.mark.asyncio
async def test_get_instance_success(mock_entra_env, mock_request):
    with (
        patch(
            'openhands.server.user_auth.entra_user_auth.PyJWKClient'
        ) as MockPyJWKClient,
        patch('openhands.server.user_auth.entra_user_auth.jwt.decode') as mock_decode,
    ):
        # Mock JWKS Client
        mock_jwks_client = MockPyJWKClient.return_value
        mock_signing_key = MagicMock()
        mock_signing_key.key = 'public_key'
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        # Mock JWT Decode
        mock_decode.return_value = {
            'oid': 'user-123',
            'email': 'test@example.com',
            'name': 'Test User',
        }

        user_auth = await EntraUserAuth.get_instance(mock_request)

        assert isinstance(user_auth, EntraUserAuth)
        assert user_auth.user_id == 'user-123'
        assert user_auth.email == 'test@example.com'
        assert user_auth.name == 'Test User'


@pytest.mark.asyncio
async def test_get_instance_missing_config(mock_request):
    # Ensure env vars are None/Empty
    with (
        patch('openhands.server.user_auth.entra_user_auth.ENTRA_TENANT_ID', None),
        patch('openhands.server.user_auth.entra_user_auth.ENTRA_CLIENT_ID', None),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await EntraUserAuth.get_instance(mock_request)

        assert exc_info.value.status_code == 500
        assert 'configuration missing' in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_instance_missing_header():
    with (
        patch('openhands.server.user_auth.entra_user_auth.ENTRA_TENANT_ID', 'id'),
        patch('openhands.server.user_auth.entra_user_auth.ENTRA_CLIENT_ID', 'id'),
    ):
        request = MagicMock(spec=Request)
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await EntraUserAuth.get_instance(request)

        assert exc_info.value.status_code == 401
        assert 'Missing or invalid Authorization header' in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_instance_invalid_token(mock_entra_env, mock_request):
    with (
        patch(
            'openhands.server.user_auth.entra_user_auth.PyJWKClient'
        ) as MockPyJWKClient,
        patch('openhands.server.user_auth.entra_user_auth.jwt.decode'),
    ):
        MockPyJWKClient.side_effect = Exception('JWKS Error')

        with pytest.raises(HTTPException) as exc_info:
            await EntraUserAuth.get_instance(mock_request)

        assert exc_info.value.status_code == 401
        assert 'Authentication error' in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_instance_jwt_error(mock_entra_env, mock_request):
    with (
        patch(
            'openhands.server.user_auth.entra_user_auth.PyJWKClient'
        ) as MockPyJWKClient,
        patch('openhands.server.user_auth.entra_user_auth.jwt.decode') as mock_decode,
    ):
        # Mock JWKS Client success
        mock_jwks_client = MockPyJWKClient.return_value
        mock_signing_key = MagicMock()
        mock_signing_key.key = 'public_key'
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        # Fail decode
        mock_decode.side_effect = jwt.PyJWTError('Invalid signature')

        with pytest.raises(HTTPException) as exc_info:
            await EntraUserAuth.get_instance(mock_request)

        assert exc_info.value.status_code == 401
        assert 'Token validation failed' in exc_info.value.detail


# ---- Tests for user creation on successful auth (SAAS + Postgres) ----


@pytest.mark.asyncio
async def test_get_instance_calls_ensure_user_in_db_when_saas_postgres(
    mock_entra_env, mock_request
):
    """On successful auth with SAAS + Postgres, get_instance ensures user exists in DB."""
    with (
        patch(
            'openhands.server.user_auth.entra_user_auth.shared.server_config'
        ) as mock_config,
        patch(
            'openhands.server.user_auth.entra_user_auth.PyJWKClient'
        ) as MockPyJWKClient,
        patch('openhands.server.user_auth.entra_user_auth.jwt.decode') as mock_decode,
        patch(
            'openhands.server.user_auth.entra_user_auth.EntraUserAuth._ensure_user_in_db',
            new_callable=AsyncMock,
        ) as mock_ensure_user,
    ):
        mock_config.app_mode = AppMode.SAAS
        mock_config.settings_store_class = (
            'openhands.storage.settings.postgres_settings_store.PostgresSettingsStore'
        )

        mock_jwks_client = MockPyJWKClient.return_value
        mock_signing_key = MagicMock()
        mock_signing_key.key = 'public_key'
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_decode.return_value = {
            'oid': 'user-456',
            'email': 'auth@example.com',
            'name': 'Auth User',
        }

        user_auth = await EntraUserAuth.get_instance(mock_request)

        assert user_auth.user_id == 'user-456'
        mock_ensure_user.assert_awaited_once_with(
            mock_request, 'user-456', 'auth@example.com', 'Auth User'
        )


@pytest.mark.asyncio
async def test_get_instance_does_not_call_ensure_user_in_db_when_not_saas(
    mock_entra_env, mock_request
):
    """When app_mode is not SAAS, get_instance does not call _ensure_user_in_db."""
    with (
        patch(
            'openhands.server.user_auth.entra_user_auth.shared.server_config'
        ) as mock_config,
        patch(
            'openhands.server.user_auth.entra_user_auth.PyJWKClient'
        ) as MockPyJWKClient,
        patch('openhands.server.user_auth.entra_user_auth.jwt.decode') as mock_decode,
        patch(
            'openhands.server.user_auth.entra_user_auth.EntraUserAuth._ensure_user_in_db',
            new_callable=AsyncMock,
        ) as mock_ensure_user,
    ):
        mock_config.app_mode = AppMode.OPENHANDS

        mock_jwks_client = MockPyJWKClient.return_value
        mock_signing_key = MagicMock()
        mock_signing_key.key = 'public_key'
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_decode.return_value = {'oid': 'user-789', 'email': 'u@ex.com', 'name': ''}

        await EntraUserAuth.get_instance(mock_request)

        mock_ensure_user.assert_not_awaited()


@pytest.fixture
async def async_engine():
    """In-memory SQLite engine with app_server Base tables (users, organizations, etc.)."""
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
    """Async session for tests."""
    session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as session:
        yield session


@pytest.mark.asyncio
async def test_ensure_user_in_db_creates_user_and_org_when_missing(
    async_session, mock_entra_env
):
    """_ensure_user_in_db creates User and default org when they do not exist."""
    request = MagicMock(spec=Request)
    request.state = MagicMock()

    class Cm:
        def __init__(self, session):
            self.session = session

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, *args):
            pass

    with (
        patch(
            'openhands.server.user_auth.entra_user_auth.shared.server_config'
        ) as mock_config,
        patch(
            'openhands.app_server.config.get_db_session',
            return_value=Cm(async_session),
        ),
    ):
        mock_config.app_mode = AppMode.SAAS
        mock_config.settings_store_class = (
            'openhands.storage.settings.postgres_settings_store.PostgresSettingsStore'
        )

        await EntraUserAuth._ensure_user_in_db(
            request,
            user_id='new-user-id',
            email='newuser@example.com',
            display_name='New User',
        )

    result = await async_session.execute(select(User).where(User.id == 'new-user-id'))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.email == 'newuser@example.com'
    assert user.display_name == 'New User'

    result = await async_session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == 'new-user-id'
        )
    )
    membership = result.scalar_one_or_none()
    assert membership is not None


@pytest.mark.asyncio
async def test_ensure_user_in_db_uses_placeholder_email_when_email_missing(
    async_session, mock_entra_env
):
    """_ensure_user_in_db uses placeholder email when token has no email."""
    request = MagicMock(spec=Request)
    request.state = MagicMock()

    class Cm:
        def __init__(self, session):
            self.session = session

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, *args):
            pass

    with (
        patch(
            'openhands.server.user_auth.entra_user_auth.shared.server_config'
        ) as mock_config,
        patch(
            'openhands.app_server.config.get_db_session',
            return_value=Cm(async_session),
        ),
    ):
        mock_config.app_mode = AppMode.SAAS
        mock_config.settings_store_class = (
            'openhands.storage.settings.postgres_settings_store.PostgresSettingsStore'
        )

        await EntraUserAuth._ensure_user_in_db(
            request,
            user_id='no-email-user',
            email=None,
            display_name=None,
        )

    result = await async_session.execute(select(User).where(User.id == 'no-email-user'))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.email == 'no-email-user@openhands.placeholder'
    assert user.display_name is None
