import os
from typing import Optional

import jwt
from fastapi import HTTPException, Request, status
from jwt import PyJWKClient
from pydantic import SecretStr

from openhands.integrations.provider import PROVIDER_TOKEN_TYPE
from openhands.server import shared
from openhands.server.settings import Settings
from openhands.server.user_auth.user_auth import AuthType, UserAuth
from openhands.storage.data_models.secrets import Secrets
from openhands.storage.secrets.secrets_store import SecretsStore
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

    async def get_user_id(self) -> str | None:
        return self.user_id

    async def get_user_email(self) -> str | None:
        return self.email

    async def get_access_token(self) -> SecretStr | None:
        return SecretStr(self.access_token)

    async def get_provider_tokens(self) -> PROVIDER_TOKEN_TYPE | None:
        # In a real implementation, we might exchange the Entra token for other provider tokens
        # or look them up in a database. For now, returning None as per base contract/default behavior.
        return None

    async def get_user_settings_store(self) -> SettingsStore:
        if self._settings_store:
            return self._settings_store

        # Reuse the default SettingsStore logic, scoping it to the user_id
        self._settings_store = await shared.SettingsStoreImpl.get_instance(
            shared.config, self.user_id
        )
        return self._settings_store

    async def get_secrets_store(self) -> SecretsStore:
        if self._secrets_store:
            return self._secrets_store

        # Reuse the default SecretsStore logic, scoping it to the user_id
        self._secrets_store = await shared.SecretsStoreImpl.get_instance(
            shared.config, self.user_id
        )
        return self._secrets_store

    async def get_secrets(self) -> Secrets | None:
        store = await self.get_secrets_store()
        return await store.load()

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

            # 'email' or 'preferred_username' or 'upn'
            email = (
                payload.get('email')
                or payload.get('preferred_username')
                or payload.get('upn')
            )

            # 'name'
            name = payload.get('name', '')

            if not user_id:
                raise HTTPException(
                    status_code=401, detail='Token missing user identifier (oid)'
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
