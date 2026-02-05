# IMPORTANT: LEGACY V0 CODE - Deprecated since version 1.0.0, scheduled for removal April 1, 2026
# This file is part of the legacy (V0) implementation of OpenHands and will be removed soon as we complete the migration to V1.
# OpenHands V1 uses the Software Agent SDK for the agentic core and runs a new application server. Please refer to:
#   - V1 agentic core (SDK): https://github.com/OpenHands/software-agent-sdk
#   - V1 application server (in this repo): openhands/app_server/
# Unless you are working on deprecation, please avoid extending this legacy file and consult the V1 codepaths above.
# Tag: Legacy-V0
# This module belongs to the old V0 web server. The V1 application server lives under openhands/app_server/.
import os

from openhands.core.logger import openhands_logger as logger
from openhands.server.types import AppMode, ServerConfigInterface
from openhands.utils.import_utils import get_impl


def _get_app_mode() -> AppMode:
    mode = os.environ.get('APP_MODE', 'oss')
    try:
        return AppMode(mode)
    except ValueError:
        return AppMode.OPENHANDS


_app_mode = _get_app_mode()
_settings_store_class = (
    'openhands.storage.settings.postgres_settings_store.PostgresSettingsStore'
    if _app_mode == AppMode.SAAS
    else 'openhands.storage.settings.file_settings_store.FileSettingsStore'
)
_secret_store_class = (
    'openhands.storage.secrets.postgres_secrets_store.PostgresSecretsStore'
    if _app_mode == AppMode.SAAS
    else 'openhands.storage.secrets.file_secrets_store.FileSecretsStore'
)
_conversation_store_class = (
    'openhands.storage.conversation.postgres_conversation_store.PostgresConversationStore'
    if _app_mode == AppMode.SAAS
    else 'openhands.storage.conversation.file_conversation_store.FileConversationStore'
)


class ServerConfig(ServerConfigInterface):
    config_cls = os.environ.get('OPENHANDS_CONFIG_CLS', None)
    app_mode = _app_mode
    posthog_client_key = 'phc_3ESMmY9SgqEAGBB6sMGK5ayYHkeUuknH2vP6FmWH9RA'
    github_client_id = os.environ.get('GITHUB_APP_CLIENT_ID', '')
    enable_billing = os.environ.get('ENABLE_BILLING', 'false') == 'true'
    hide_llm_settings = os.environ.get('HIDE_LLM_SETTINGS', 'false') == 'true'
    # This config is used to hide the microagent management page from the users for now. We will remove this once we release the new microagent management page.
    settings_store_class: str = _settings_store_class
    secret_store_class: str = _secret_store_class
    conversation_store_class: str = _conversation_store_class
    conversation_manager_class: str = os.environ.get(
        'CONVERSATION_MANAGER_CLASS',
        'openhands.server.conversation_manager.standalone_conversation_manager.StandaloneConversationManager',
    )
    monitoring_listener_class: str = 'openhands.server.monitoring.MonitoringListener'
    user_auth_class: str = os.environ.get(
        'OPENHANDS_USER_AUTH_CLASS',
        'openhands.server.user_auth.default_user_auth.DefaultUserAuth',
    )
    enable_v1: bool = os.getenv('ENABLE_V1') != '0'

    def verify_config(self):
        if self.config_cls:
            raise ValueError('Unexpected config path provided')

    def get_config(self):
        providers_raw = os.environ.get('PROVIDERS_CONFIGURED', '')
        providers_configured: list[str] = []
        if providers_raw:
            providers_configured = [
                p.strip() for p in providers_raw.split(',') if p.strip()
            ]

        config: dict = {
            'APP_MODE': self.app_mode,
            'GITHUB_CLIENT_ID': self.github_client_id,
            'POSTHOG_CLIENT_KEY': self.posthog_client_key,
            'FEATURE_FLAGS': {
                'ENABLE_BILLING': self.enable_billing,
                'HIDE_LLM_SETTINGS': self.hide_llm_settings,
            },
        }
        if providers_configured:
            config['PROVIDERS_CONFIGURED'] = providers_configured
        auth_url = os.environ.get('AUTH_URL')
        if auth_url:
            config['AUTH_URL'] = auth_url

        # Entra PKCE (SPA) - client_id and tenant_id are public, no secret needed
        if 'enterprise_sso' in providers_configured:
            entra_tenant = os.environ.get('ENTRA_TENANT_ID')
            entra_client = os.environ.get('ENTRA_CLIENT_ID')
            if entra_tenant and entra_client:
                config['ENTRA_TENANT_ID'] = entra_tenant
                config['ENTRA_CLIENT_ID'] = entra_client

        # Git providers to show in integrations (github, gitlab, bitbucket, azure_devops, forgejo)
        # Comma-separated. If empty, all are shown.
        git_providers_raw = os.environ.get('GIT_PROVIDERS_ENABLED', '')
        if git_providers_raw:
            config['GIT_PROVIDERS_ENABLED'] = [
                p.strip() for p in git_providers_raw.split(',') if p.strip()
            ]

        return config


def load_server_config() -> ServerConfig:
    config_cls = os.environ.get('OPENHANDS_CONFIG_CLS', None)
    logger.info(f'Using config class {config_cls}')

    server_config_cls = get_impl(ServerConfig, config_cls)
    server_config: ServerConfig = server_config_cls()
    server_config.verify_config()

    return server_config
