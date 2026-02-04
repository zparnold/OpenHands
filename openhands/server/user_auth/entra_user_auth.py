import os
from typing import Optional

import jwt
from fastapi import HTTPException, Request, status
from jwt import PyJWKClient
from pydantic import SecretStr
from starlette.datastructures import State

from openhands.integrations.provider import PROVIDER_TOKEN_TYPE
from openhands.server import shared
from openhands.server.settings import Settings
from openhands.server.types import AppMode
from openhands.server.user_auth.user_auth import AuthType, UserAuth
from openhands.storage.data_models.secrets import Secrets
from openhands.storage.secrets.postgres_secrets_store import PostgresSecretsStore
from openhands.storage.secrets.secrets_store import SecretsStore
from openhands.storage.settings.postgres_settings_store import PostgresSettingsStore
from openhands.storage.settings.settings_store import SettingsStore

# Check for required environment variables
ENTRA_TENANT_ID = os.getenv('ENTRA_TENANT_ID')
ENTRA_CLIENT_ID = os.getenv('ENTRA_CLIENT_ID')

# Construct OpenID Connect URLs
# Common endpoint for multi-tenant or specific tenant endpoint
AUTHORITY_URL = f'https://login.microsoftonline.com/{ENTRA_TENANT_ID or "common"}'
JWKS_URL = f'{AUTHORITY_URL}/discovery/v2.0/keys'
ISSUER_PREFIX = f'https://login.microsoftonline.com/{ENTRA_TENANT_ID or ""}'


class EntraUserAuth(UserAuth):
    """
    UserAuth implementation for Microsoft Entra ID (formerly Azure AD).
    Validates JWT Bearer tokens issued by Entra ID.
    """

    def __init__(self, user_id: str, email: str, access_token: str, name: str = ''):
        self.user_id = user_id
        self.email = email
        self.name = name
        self.access_token = access_token
        self._settings: Optional[Settings] = None
        self._settings_store: Optional[SettingsStore] = None
        self._secrets_store: Optional[SecretsStore] = None
        self._secrets: Optional[Secrets] = None

    async def get_user_id(self) -> str | None:
        return self.user_id

    async def get_user_email(self) -> str | None:
        return self.email

    async def get_access_token(self) -> SecretStr | None:
        return SecretStr(self.access_token)

    async def get_provider_tokens(self) -> PROVIDER_TOKEN_TYPE | None:
        secrets = await self.get_secrets()
        if secrets is None:
            return None
        return secrets.provider_tokens

    async def get_user_settings_store(self) -> SettingsStore:
        if self._settings_store:
            return self._settings_store

        # Reuse the default SettingsStore logic, scoping it to the user_id
        self._settings_store = await shared.SettingsStoreImpl.get_instance(
            shared.config, self.user_id
        )
        return self._settings_store

    async def get_user_settings(self) -> Settings | None:
        settings = self._settings
        if settings:
            return settings
        if self._should_use_postgres_settings():
            settings = await self._load_settings_from_postgres()
        else:
            settings = await super().get_user_settings()
        self._settings = settings
        return settings

    async def get_secrets_store(self) -> SecretsStore:
        if self._secrets_store:
            return self._secrets_store

        # Reuse the default SecretsStore logic, scoping it to the user_id
        self._secrets_store = await shared.SecretsStoreImpl.get_instance(
            shared.config, self.user_id
        )
        return self._secrets_store

    async def get_secrets(self) -> Secrets | None:
        secrets = self._secrets
        if secrets:
            return secrets
        if self._should_use_postgres_secrets():
            secrets = await self._load_secrets_from_postgres()
        else:
            store = await self.get_secrets_store()
            secrets = await store.load()
        self._secrets = secrets
        return secrets

    def get_auth_type(self) -> AuthType | None:
        return AuthType.BEARER

    async def get_mcp_api_key(self) -> str | None:
        # TODO: Implement MCP API Key generation/retrieval linked to Entra identity
        return None

    @classmethod
    async def get_instance(cls, request: Request) -> UserAuth:
        if not ENTRA_TENANT_ID or not ENTRA_CLIENT_ID:
            # Fallback or error if not configured.
            # If entra is not configured but this class is used, we should probably error.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Entra ID configuration missing (ENTRA_TENANT_ID, ENTRA_CLIENT_ID)',
            )

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Missing or invalid Authorization header',
            )

        token = auth_header.split(' ')[1]

        try:
            # Fetch signing keys from Entra ID
            # PyJWKClient handles caching roughly, but for production a more robust cache is recommended
            jwks_client = PyJWKClient(JWKS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            # Verify the token
            # We skip 'aud' verification here if we want to support multiple audiences,
            # otherwise set audience=ENTRA_CLIENT_ID
            options = {'verify_signature': True, 'verify_aud': True, 'verify_exp': True}

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=['RS256'],
                audience=ENTRA_CLIENT_ID,
                # Issuer validation can be tricky with v1/v2 endpoints and tenant variations.
                # For single tenant, it should match strictly.
                # issuer=f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/v2.0",
                options=options,
            )

            # Extract Identity
            # 'oid' (Object ID) is the immutable identifier for the user in the tenant
            user_id = payload.get('oid') or payload.get('sub')

            # Entra ID token claims (in order of preference).
            # email/preferred_username/upn may require optional claims in app registration.
            # unique_name is legacy but sometimes present.
            email_raw = (
                payload.get('email')
                or payload.get('preferred_username')
                or payload.get('upn')
                or payload.get('unique_name')
            )
            email = email_raw if email_raw is not None else ''

            # 'name'
            name = payload.get('name', '') or ''

            if not user_id:
                raise HTTPException(
                    status_code=401, detail='Token missing user identifier (oid)'
                )

            # In SAAS + Postgres, ensure the user row exists so secrets/settings can be stored
            if (
                shared.server_config.app_mode == AppMode.SAAS
                and 'postgres' in shared.server_config.settings_store_class.lower()
            ):
                await cls._ensure_user_in_db(
                    request, user_id, email or None, name or None
                )

            return cls(user_id=user_id, email=email, access_token=token, name=name)

        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f'Token validation failed: {str(e)}',
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f'Authentication error: {str(e)}',
            )

    @classmethod
    async def get_for_user(cls, user_id: str) -> UserAuth:
        # This method is used for internal calls or background tasks where we have the ID.
        # Without a full token, we might operate with limited context.
        return cls(user_id=user_id, email='', access_token='', name='')

    @classmethod
    async def _ensure_user_in_db(
        cls,
        request: Request,
        user_id: str,
        email: str | None,
        display_name: str | None,
    ) -> None:
        """Create or update the user in the DB on successful auth when using Postgres."""
        if shared.server_config.app_mode != AppMode.SAAS:
            return
        if 'postgres' not in shared.server_config.settings_store_class.lower():
            return
        try:
            from sqlalchemy import select

            from openhands.app_server.config import get_db_session
            from openhands.storage.models.user import User
            from openhands.storage.organizations.postgres_organization_store import (
                PostgresOrganizationStore,
            )

            state = getattr(request, 'state', None)
            if state is None:
                return
            async with get_db_session(state, request) as db_session:
                result = await db_session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                email_val = email or f'{user_id}@openhands.placeholder'
                if not user:
                    user = User(
                        id=user_id,
                        email=email_val,
                        display_name=display_name or None,
                    )
                    db_session.add(user)
                else:
                    if email:
                        user.email = email
                    if display_name:
                        user.display_name = display_name
                org_store = PostgresOrganizationStore(db_session)
                await org_store.ensure_default_org_for_user(
                    user_id=user_id,
                    email=user.email,
                    display_name=user.display_name,
                )
                await db_session.commit()
        except Exception:  # noqa: S110 - allow broad catch so auth still succeeds
            # If DB is unavailable or not configured, auth still succeeds; later
            # requests (e.g. secrets store) may fail or create user then.
            pass

    def _should_use_postgres_settings(self) -> bool:
        return (
            shared.server_config.app_mode == AppMode.SAAS
            and 'postgres' in shared.server_config.settings_store_class.lower()
        )

    def _should_use_postgres_secrets(self) -> bool:
        return (
            shared.server_config.app_mode == AppMode.SAAS
            and 'postgres' in shared.server_config.secret_store_class.lower()
        )

    def _get_request_state(self) -> State:
        request = getattr(self, '_request', None)
        if request is not None:
            return request.state
        state = getattr(self, '_request_state', None)
        if state is None:
            state = State()
            setattr(self, '_request_state', state)
        return state

    async def _load_settings_from_postgres(self) -> Settings | None:
        user_id = await self.get_user_id()
        if not user_id:
            return None
        from openhands.app_server.config import get_db_session

        request = getattr(self, '_request', None)
        state = self._get_request_state()
        async with get_db_session(state, request) as db_session:
            store = PostgresSettingsStore(db_session, user_id)
            return await store.load()

    async def _load_secrets_from_postgres(self) -> Secrets | None:
        user_id = await self.get_user_id()
        if not user_id:
            return None
        from openhands.app_server.config import get_db_session

        request = getattr(self, '_request', None)
        state = self._get_request_state()
        async with get_db_session(state, request) as db_session:
            store = PostgresSecretsStore(db_session, user_id)
            return await store.load()
