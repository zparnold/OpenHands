# IMPORTANT: LEGACY V0 CODE - Deprecated since version 1.0.0, scheduled for removal April 1, 2026
# This file is part of the legacy (V0) implementation of OpenHands and will be removed soon as we complete the migration to V1.
# OpenHands V1 uses the Software Agent SDK for the agentic core and runs a new application server. Please refer to:
#   - V1 agentic core (SDK): https://github.com/OpenHands/software-agent-sdk
#   - V1 application server (in this repo): openhands/app_server/
# Unless you are working on deprecation, please avoid extending this legacy file and consult the V1 codepaths above.
# Tag: Legacy-V0
# This module belongs to the old V0 web server. The V1 application server lives under openhands/app_server/.
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from openhands.core.config.llm_config import LLMConfig
from openhands.core.logger import openhands_logger as logger
from openhands.integrations.provider import (
    PROVIDER_TOKEN_TYPE,
    ProviderType,
)
from openhands.llm.llm import LLM
from openhands.server.dependencies import get_dependencies
from openhands.server.routes.secrets import invalidate_legacy_secrets_store
from openhands.server.settings import (
    GETSettingsModel,
)
from openhands.server.shared import config
from openhands.server.user_auth import (
    get_provider_tokens,
    get_secrets_store,
    get_user_settings,
    get_user_settings_store,
)
from openhands.storage.data_models.settings import Settings
from openhands.storage.secrets.secrets_store import SecretsStore
from openhands.storage.settings.settings_store import SettingsStore
from openhands.utils.environment import get_effective_llm_base_url

app = APIRouter(prefix='/api', dependencies=get_dependencies())


@app.get(
    '/settings',
    response_model=GETSettingsModel,
    responses={
        404: {'description': 'Settings not found', 'model': dict},
        401: {'description': 'Invalid token', 'model': dict},
    },
)
async def load_settings(
    provider_tokens: PROVIDER_TOKEN_TYPE | None = Depends(get_provider_tokens),
    settings_store: SettingsStore = Depends(get_user_settings_store),
    settings: Settings = Depends(get_user_settings),
    secrets_store: SecretsStore = Depends(get_secrets_store),
) -> GETSettingsModel | JSONResponse:
    try:
        if not settings:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={'error': 'Settings not found'},
            )

        # On initial load, user secrets may not be populated with values migrated from settings store
        user_secrets = await invalidate_legacy_secrets_store(
            settings, settings_store, secrets_store
        )

        # If invalidation is successful, then the returned user secrets holds the most recent values
        git_providers = (
            user_secrets.provider_tokens if user_secrets else provider_tokens
        )

        provider_tokens_set: dict[ProviderType, str | None] = {}
        if git_providers:
            for provider_type, provider_token in git_providers.items():
                if provider_token.token or provider_token.user_id:
                    provider_tokens_set[provider_type] = provider_token.host

        settings_with_token_data = GETSettingsModel(
            **settings.model_dump(exclude={'secrets_store'}),
            llm_api_key_set=settings.llm_api_key is not None
            and bool(settings.llm_api_key),
            search_api_key_set=settings.search_api_key is not None
            and bool(settings.search_api_key),
            provider_tokens_set=provider_tokens_set,
        )
        settings_with_token_data.llm_api_key = None
        settings_with_token_data.search_api_key = None
        settings_with_token_data.sandbox_api_key = None
        return settings_with_token_data
    except Exception as e:
        logger.warning(f'Invalid token: {e}')
        # Get user_id from settings if available
        user_id = getattr(settings, 'user_id', 'unknown') if settings else 'unknown'
        logger.info(
            f'Returning 401 Unauthorized - Invalid token for user_id: {user_id}'
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={'error': 'Invalid token'},
        )


@app.post(
    '/reset-settings',
    responses={
        410: {
            'description': 'Reset settings functionality has been removed',
            'model': dict,
        }
    },
)
async def reset_settings() -> JSONResponse:
    """Resets user settings. (Deprecated)"""
    logger.warning('Deprecated endpoint /api/reset-settings called by user')
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={'error': 'Reset settings functionality has been removed.'},
    )


async def store_llm_settings(
    settings: Settings, settings_store: SettingsStore
) -> Settings:
    existing_settings = await settings_store.load()

    # Convert to Settings model and merge with existing settings
    if existing_settings:
        # Keep existing LLM settings if not provided
        if settings.llm_api_key is None:
            settings.llm_api_key = existing_settings.llm_api_key
        if settings.llm_model is None:
            settings.llm_model = existing_settings.llm_model
        if settings.llm_base_url is None:
            settings.llm_base_url = existing_settings.llm_base_url
        # Keep search API key if missing or empty
        if not settings.search_api_key:
            settings.search_api_key = existing_settings.search_api_key

    return settings


# NOTE: We use response_model=None for endpoints that return JSONResponse directly.
# This is because FastAPI's response_model expects a Pydantic model, but we're returning
# a response object directly. We document the possible responses using the 'responses'
# parameter and maintain proper type annotations for mypy.
@app.post(
    '/settings',
    response_model=None,
    responses={
        200: {'description': 'Settings stored successfully', 'model': dict},
        500: {'description': 'Error storing settings', 'model': dict},
    },
)
async def store_settings(
    settings: Settings,
    settings_store: SettingsStore = Depends(get_user_settings_store),
) -> JSONResponse:
    # Check provider tokens are valid
    try:
        existing_settings = await settings_store.load()

        # Convert to Settings model and merge with existing settings
        if existing_settings:
            settings = await store_llm_settings(settings, settings_store)

            # Keep existing analytics consent if not provided
            if settings.user_consents_to_analytics is None:
                settings.user_consents_to_analytics = (
                    existing_settings.user_consents_to_analytics
                )

        # Update sandbox config with new settings
        if settings.remote_runtime_resource_factor is not None:
            config.sandbox.remote_runtime_resource_factor = (
                settings.remote_runtime_resource_factor
            )

        # Update git configuration with new settings
        git_config_updated = False
        if settings.git_user_name is not None:
            config.git_user_name = settings.git_user_name
            git_config_updated = True
        if settings.git_user_email is not None:
            config.git_user_email = settings.git_user_email
            git_config_updated = True

        # Note: Git configuration will be applied when new sessions are initialized
        # Existing sessions will continue with their current git configuration
        if git_config_updated:
            logger.info(
                f'Updated global git configuration: name={config.git_user_name}, email={config.git_user_email}'
            )

        settings = convert_to_settings(settings)
        await settings_store.store(settings)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': 'Settings stored'},
        )
    except Exception as e:
        logger.warning(f'Something went wrong storing settings: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': 'Something went wrong storing settings'},
        )


def convert_to_settings(settings_with_token_data: Settings) -> Settings:
    settings_data = settings_with_token_data.model_dump()

    # Filter out additional fields from `SettingsWithTokenData`
    filtered_settings_data = {
        key: value
        for key, value in settings_data.items()
        if key in Settings.model_fields  # Ensures only `Settings` fields are included
    }

    # Convert the API keys to `SecretStr` instances
    filtered_settings_data['llm_api_key'] = settings_with_token_data.llm_api_key
    filtered_settings_data['search_api_key'] = settings_with_token_data.search_api_key

    # Create a new Settings instance
    settings = Settings(**filtered_settings_data)
    return settings


@app.post(
    '/validate-llm',
    response_model=None,
    responses={
        200: {'description': 'LLM configuration is valid', 'model': dict},
        400: {'description': 'LLM configuration is invalid', 'model': dict},
        500: {'description': 'Error validating LLM configuration', 'model': dict},
    },
)
async def validate_llm(
    settings: Settings,
    settings_store: SettingsStore = Depends(get_user_settings_store),
) -> JSONResponse:
    """Validate that the LLM configuration will work in chat sessions.

    This endpoint tests the LLM configuration by:
    1. Creating an LLMConfig from the provided settings
    2. Initializing an LLM instance
    3. Making a test completion call to verify the configuration works
    
    Note: This endpoint merges the provided settings with existing settings to validate
    the complete configuration that will be used, ensuring that partially-specified
    settings are tested with their full context.
    """
    try:
        # Merge with existing settings to get complete configuration.
        # This ensures we validate the actual configuration that will be used
        # when the settings are later saved via /api/settings
        settings = await store_llm_settings(settings, settings_store)

        # Validate required fields
        if not settings.llm_model:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={'error': 'LLM model is required'},
            )

        # Get effective base URL (handles docker/lemonade provider logic)
        effective_base_url = get_effective_llm_base_url(
            settings.llm_model,
            settings.llm_base_url,
        )

        # Create LLM config
        llm_config = LLMConfig(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=effective_base_url,
        )

        # Initialize LLM with a unique service ID for validation
        test_llm = LLM(
            config=llm_config,
            service_id=f'validation-{settings.llm_model}',
        )

        # Test with a simple completion call
        # Use a minimal message to keep costs low
        test_messages = [{'role': 'user', 'content': 'Hello'}]

        # Make a synchronous completion call with a short timeout
        # This will test authentication and connectivity
        test_llm.completion(
            messages=test_messages,
            stream=False,
            max_tokens=5,  # Keep it minimal to reduce costs
        )

        # If we got here, the configuration is valid
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': 'LLM configuration is valid', 'model': settings.llm_model},
        )

    except ValueError as e:
        # Configuration errors (invalid parameters, missing required fields)
        logger.info(f'LLM configuration validation failed: {e}')
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={'error': f'Invalid LLM configuration: {str(e)}'},
        )
    except (ConnectionError, TimeoutError) as e:
        # Network/connection errors
        logger.warning(f'Connection error validating LLM configuration: {e}')
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={'error': 'Connection failed. Please check your base URL and network connection.'},
        )
    except Exception as e:
        # Catch-all for other LLM-related errors (authentication, rate limiting, etc.)
        # We use string matching here because LiteLLM can throw many different exception types
        # from various providers, and we can't import all of them. This is a pragmatic approach
        # to provide user-friendly error messages.
        logger.warning(f'Error validating LLM configuration: {e}')
        error_message = str(e)

        # Extract more specific error messages based on common error patterns
        # Check exception class name and message content
        exception_type = type(e).__name__
        if 'AuthenticationError' in exception_type or 'AuthenticationError' in error_message or 'Unauthorized' in error_message or 'Invalid' in error_message:
            error_message = 'Authentication failed. Please check your API key.'
        elif 'not found' in error_message.lower() or '404' in error_message:
            error_message = 'Model not found. Please check your model name.'
        elif 'rate limit' in error_message.lower() or 'RateLimitError' in exception_type:
            error_message = 'Rate limit exceeded. Please try again later.'

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={'error': error_message},
        )
