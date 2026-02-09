import os
from datetime import datetime

from pydantic import Field

from openhands.app_server.web_client.web_client_config_injector import (
    WebClientConfigInjector,
)
from openhands.app_server.web_client.web_client_models import (
    WebClientConfig,
    WebClientFeatureFlags,
)
from openhands.integrations.service_types import ProviderType


class DefaultWebClientConfigInjector(WebClientConfigInjector):
    posthog_client_key: str | None = 'phc_3ESMmY9SgqEAGBB6sMGK5ayYHkeUuknH2vP6FmWH9RA'
    feature_flags: WebClientFeatureFlags = Field(default_factory=WebClientFeatureFlags)
    providers_configured: list[ProviderType] = Field(default_factory=list)
    maintenance_start_time: datetime | None = None
    auth_url: str | None = None
    recaptcha_site_key: str | None = None
    faulty_models: list[str] = Field(default_factory=list)
    error_message: str | None = None
    updated_at: datetime = Field(
        default=datetime.fromisoformat('2026-01-01T00:00:00Z'),
        description=(
            'The timestamp when error messages and faulty models were last updated. '
            'The frontend uses this value to determine whether error messages are '
            'new and should be displayed. (Default to start of 2026)'
        ),
    )
    github_app_slug: str | None = None
    # Entra PKCE (SPA) - public client id and tenant id for frontend OAuth flow
    entra_tenant_id: str | None = None
    entra_client_id: str | None = None
    git_providers_enabled: list[str] | None = None

    async def get_web_client_config(self) -> WebClientConfig:
        from openhands.app_server.config import get_global_config

        config = get_global_config()
        # Entra: prefer injector (OH_WEB_CLIENT_ENTRA_*), then ENTRA_*, then OH_ENTRA_*
        entra_tenant_id = (
            self.entra_tenant_id
            or os.environ.get('ENTRA_TENANT_ID')
            or os.environ.get('OH_ENTRA_TENANT_ID')
        )
        entra_client_id = (
            self.entra_client_id
            or os.environ.get('ENTRA_CLIENT_ID')
            or os.environ.get('OH_ENTRA_CLIENT_ID')
        )
        # Git providers to show in integrations (GIT_PROVIDERS_ENABLED or OH_WEB_CLIENT_*)
        git_providers_raw = (
            self.git_providers_enabled
            or os.environ.get('GIT_PROVIDERS_ENABLED')
            or os.environ.get('OH_WEB_CLIENT_GIT_PROVIDERS_ENABLED')
        )
        git_providers_enabled: list[str] | None
        if isinstance(git_providers_raw, list) and git_providers_raw:
            git_providers_enabled = git_providers_raw
        elif isinstance(git_providers_raw, str) and git_providers_raw.strip():
            parsed = [
                p.strip().lower() for p in git_providers_raw.split(',') if p.strip()
            ]
            git_providers_enabled = parsed if parsed else None
        else:
            git_providers_enabled = None
        result = WebClientConfig(
            app_mode=config.app_mode,
            posthog_client_key=self.posthog_client_key,
            feature_flags=self.feature_flags,
            providers_configured=self.providers_configured,
            maintenance_start_time=self.maintenance_start_time,
            auth_url=self.auth_url,
            recaptcha_site_key=self.recaptcha_site_key,
            faulty_models=self.faulty_models,
            error_message=self.error_message,
            updated_at=self.updated_at,
            github_app_slug=self.github_app_slug,
            entra_tenant_id=entra_tenant_id,
            entra_client_id=entra_client_id,
            git_providers_enabled=git_providers_enabled,
        )
        return result
