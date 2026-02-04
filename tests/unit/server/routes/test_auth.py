from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from fastapi.testclient import TestClient

from openhands.server.app import app
from openhands.server.user_auth import get_user_auth

# Create TestClient
client = TestClient(app)


def test_authenticate_endpoint_success():
    # Mock successful user auth
    mock_user_auth = MagicMock()
    # Mocking async method get_user_id
    mock_user_auth.get_user_id = AsyncMock(return_value='test-user-id')

    async def mock_get_user_auth_dep():
        return mock_user_auth

    # Override dependency
    app.dependency_overrides[get_user_auth] = mock_get_user_auth_dep

    try:
        response = client.post('/api/authenticate')
        assert response.status_code == 200
        assert response.json() == {'status': 'ok', 'user_id': 'test-user-id'}
    finally:
        # Clean up override
        app.dependency_overrides = {}


def test_authenticate_endpoint_unauthorized():
    # Mock unauthorized error
    async def mock_get_user_auth_dep_fail():
        raise HTTPException(status_code=401, detail='Unauthorized')

    app.dependency_overrides[get_user_auth] = mock_get_user_auth_dep_fail

    try:
        response = client.post('/api/authenticate')
        assert response.status_code == 401
    finally:
        app.dependency_overrides = {}


def test_logout_endpoint():
    """Test logout endpoint returns 200 (no-op for Bearer token auth)."""
    response = client.post('/api/logout')
    assert response.status_code == 200
    assert response.json() == {}
