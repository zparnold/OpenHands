from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException, Request

from openhands.server.user_auth.entra_user_auth import EntraUserAuth


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
