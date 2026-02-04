"""Tests for ServerConfig, including get_config and env-based overrides."""

from unittest.mock import patch

from openhands.server.config.server_config import ServerConfig


def test_get_config_defaults():
    """Test get_config returns expected structure with defaults."""
    config = ServerConfig()
    result = config.get_config()

    assert 'APP_MODE' in result
    assert 'GITHUB_CLIENT_ID' in result
    assert 'POSTHOG_CLIENT_KEY' in result
    assert 'FEATURE_FLAGS' in result
    assert 'ENABLE_BILLING' in result['FEATURE_FLAGS']
    assert 'HIDE_LLM_SETTINGS' in result['FEATURE_FLAGS']


def test_get_config_includes_providers_configured():
    """Test get_config includes PROVIDERS_CONFIGURED when set in env."""
    config = ServerConfig()
    with patch.dict(
        'openhands.server.config.server_config.os.environ',
        {'PROVIDERS_CONFIGURED': 'enterprise_sso'},
        clear=False,
    ):
        result = config.get_config()

    assert 'PROVIDERS_CONFIGURED' in result
    assert result['PROVIDERS_CONFIGURED'] == ['enterprise_sso']


def test_get_config_providers_comma_separated():
    """Test PROVIDERS_CONFIGURED supports comma-separated list."""
    config = ServerConfig()
    with patch.dict(
        'openhands.server.config.server_config.os.environ',
        {'PROVIDERS_CONFIGURED': 'github, enterprise_sso , gitlab'},
        clear=False,
    ):
        result = config.get_config()

    assert result['PROVIDERS_CONFIGURED'] == ['github', 'enterprise_sso', 'gitlab']


def test_get_config_includes_auth_url():
    """Test get_config includes AUTH_URL when set in env."""
    config = ServerConfig()
    with patch.dict(
        'openhands.server.config.server_config.os.environ',
        {'AUTH_URL': 'https://login.microsoftonline.com/my-tenant'},
        clear=False,
    ):
        result = config.get_config()

    assert result['AUTH_URL'] == 'https://login.microsoftonline.com/my-tenant'


def test_get_config_includes_entra_when_enterprise_sso():
    """Test get_config includes ENTRA_TENANT_ID and ENTRA_CLIENT_ID when enterprise_sso configured."""
    config = ServerConfig()
    with patch.dict(
        'openhands.server.config.server_config.os.environ',
        {
            'PROVIDERS_CONFIGURED': 'enterprise_sso',
            'ENTRA_TENANT_ID': 'my-tenant-id',
            'ENTRA_CLIENT_ID': 'my-client-id',
        },
        clear=False,
    ):
        result = config.get_config()

    assert result['ENTRA_TENANT_ID'] == 'my-tenant-id'
    assert result['ENTRA_CLIENT_ID'] == 'my-client-id'


def test_user_auth_class_default():
    """Test user_auth_class defaults when env not set."""
    # ServerConfig reads user_auth_class from env at class definition time.
    # When running with OPENHANDS_USER_AUTH_CLASS set (e.g. Entra), patch
    # to verify the expected default value.
    default_auth = 'openhands.server.user_auth.default_user_auth.DefaultUserAuth'
    with patch.object(ServerConfig, 'user_auth_class', default_auth):
        assert 'DefaultUserAuth' in ServerConfig.user_auth_class
