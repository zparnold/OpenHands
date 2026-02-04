# IMPORTANT: LEGACY V0 CODE - Deprecated since version 1.0.0, scheduled for removal April 1, 2026
# This file is part of the legacy (V0) implementation of OpenHands and will be removed soon as we complete the migration to V1.
# OpenHands V1 uses the Software Agent SDK for the agentic core and runs a new application server. Please refer to:
#   - V1 agentic core (SDK): https://github.com/OpenHands/software-agent-sdk
#   - V1 application server (in this repo): openhands/app_server/
# Unless you are working on deprecation, please avoid extending this legacy file and consult the V1 codepaths above.
# Tag: Legacy-V0
# This module belongs to the old V0 web server. The V1 application server lives under openhands/app_server/.
from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    SecretStr,
    model_validator,
)

from openhands.core.config.mcp_config import MCPConfig
from openhands.integrations.provider import CustomSecret, ProviderToken
from openhands.integrations.service_types import ProviderType
from openhands.storage.data_models.settings import Settings


def _normalize_provider_tokens(
    value: dict[str, object] | dict[ProviderType, ProviderToken],
) -> dict[ProviderType, ProviderToken]:
    """Convert dict with string keys (from JSON) to dict[ProviderType, ProviderToken]."""
    if not value:
        return {}
    result: dict[ProviderType, ProviderToken] = {}
    for k, v in value.items():
        if isinstance(k, ProviderType):
            if isinstance(v, ProviderToken):
                result[k] = v
            else:
                result[k] = ProviderToken.model_validate(v)
        else:
            try:
                pt = ProviderType(str(k).lower())
                result[pt] = (
                    v
                    if isinstance(v, ProviderToken)
                    else ProviderToken.model_validate(v)
                )
            except (ValueError, TypeError):
                continue
    return result


class POSTProviderModel(BaseModel):
    """Settings for POST requests"""

    mcp_config: MCPConfig | None = None
    provider_tokens: dict[ProviderType, ProviderToken] = {}

    @model_validator(mode='before')
    @classmethod
    def coerce_provider_tokens_keys(cls, data: object) -> object:
        """Accept JSON string keys (e.g. 'github') for provider_tokens."""
        if not isinstance(data, dict):
            return data
        raw = data.get('provider_tokens')
        if not isinstance(raw, dict):
            return data
        data = dict(data)
        data['provider_tokens'] = _normalize_provider_tokens(raw)
        return data


class POSTCustomSecrets(BaseModel):
    """Adding new custom secret"""

    custom_secrets: dict[str, CustomSecret] = {}


class GETSettingsModel(Settings):
    """Settings with additional token data for the frontend"""

    provider_tokens_set: dict[ProviderType, str | None] | None = (
        None  # provider + base_domain key-value pair
    )
    llm_api_key_set: bool
    search_api_key_set: bool = False

    model_config = ConfigDict(use_enum_values=True)


class CustomSecretWithoutValueModel(BaseModel):
    """Custom secret model without value"""

    name: str
    description: str | None = None


class CustomSecretModel(CustomSecretWithoutValueModel):
    """Custom secret model with value"""

    value: SecretStr


class GETCustomSecrets(BaseModel):
    """Custom secrets names"""

    custom_secrets: list[CustomSecretWithoutValueModel] | None = None
