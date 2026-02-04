# Desired Features Point 1: Authentication & Identity – Implementation Plan

Direct Microsoft Entra ID (Azure AD) integration via OAuth2/OIDC, without Keycloak.

---

## Alignment with DESIRED_FEATURES.md Point #1

- **OAuth2/OIDC Integration**: Standard Entra OAuth2/OIDC flow
- **User Identity**: `EntraUserAuth` extracts `oid`, `email`, `name` from JWT
- **Token Management**: JWT validation via JWKS (already in `EntraUserAuth`)

---

## Flow (PKCE – SPA, No Backend Token Exchange)

1. **Frontend** → User clicks "Sign in with Microsoft" → Generate PKCE code_verifier/code_challenge, store in sessionStorage, redirect to Entra with code_challenge
2. **Entra** → User authenticates → Redirects to **frontend** `/oauth/entra/callback` with `code`
3. **Frontend** → Exchanges `code` + `code_verifier` directly with Entra token endpoint (no client_secret, no backend)
4. **Frontend** → Stores token, redirects to app
5. **Frontend** → Sends token as `Authorization: Bearer <token>` on all API requests
6. **Backend** → `EntraUserAuth` validates the JWT (already implemented)

PKCE is the standard for SPAs – no backend involvement in token exchange, no client_secret, no URL length issues.

---

## Entra URLs (Direct, No Keycloak)

- **Authorize**: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize`
- **Token**: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`
- **JWKS**: `https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys` (already used in `EntraUserAuth`)

---

## Auth URL Format (Entra PKCE)

```
https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize
  ?client_id={ENTRA_CLIENT_ID}
  &response_type=code
  &redirect_uri={frontend_callback_url}
  &scope=openid%20email%20profile
  &state={return_url}
  &code_challenge={base64url(sha256(code_verifier))}
  &code_challenge_method=S256
  &response_mode=query
```

---

## Implementation Summary (Completed)

### Backend

- `OPENHANDS_USER_AUTH_CLASS` env var support in ServerConfig
- `APP_MODE`, `PROVIDERS_CONFIGURED`, `AUTH_URL` in config API
- `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID` in config API when enterprise_sso configured (for PKCE – no client_secret)
- `POST /api/logout` – no-op for Bearer token auth compatibility

### Frontend

- `useEntraPkceLogin` hook – generates PKCE pair, builds authorize URL, redirects
- `entra-pkce.ts` – PKCE utilities (code_verifier, code_challenge, token exchange)
- Enterprise SSO button in `LoginContent` (Microsoft blue)
- `/oauth/entra/callback` route – receives code, exchanges with Entra directly, stores token
- Axios request interceptor adds `Authorization: Bearer <token>`
- Logout clears `clearAccessToken()` and `clearLoginData()`

### Environment Variables

- `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID` (for PKCE – no client_secret needed)
- `ENTRA_CLIENT_SECRET` – only needed for backend JWT validation (EntraUserAuth uses JWKS)
- `APP_MODE=saas`
- `PROVIDERS_CONFIGURED=enterprise_sso` (comma-separated for multiple)
- `OPENHANDS_USER_AUTH_CLASS=openhands.server.user_auth.entra_user_auth.EntraUserAuth`

### Entra App Registration

1. Add **Single-page application** platform in Azure Portal → App registrations → Your app → Authentication
2. Add redirect URI: `http://localhost:3001/oauth/entra/callback` (dev) or `https://your-domain.com/oauth/entra/callback` (production)
3. No client_secret needed for PKCE flow

---

## Test Plan

### Backend Tests (pytest)

**Location**: `tests/unit/server/`

| Test File | Coverage |
|-----------|----------|
| `routes/test_auth.py` | Logout endpoint returns 200 |
| `test_server_config.py` | get_config includes PROVIDERS_CONFIGURED, AUTH_URL, ENTRA_TENANT_ID/ENTRA_CLIENT_ID when enterprise_sso; user_auth_class default |
| `user_auth/test_entra_user_auth.py` | (existing) JWT validation, missing config, invalid token |

**Run:**
```bash
poetry run pytest tests/unit/server/test_server_config.py tests/unit/server/routes/test_auth.py -v
```

### Frontend Tests (vitest)

**Location**: `frontend/__tests__/`

| Test File | Coverage |
|-----------|----------|
| `components/features/auth/login-content.test.tsx` | Enterprise SSO button visibility, redirect on click, multi-provider display |
| `routes/oauth-entra-callback.test.tsx` | Loading state, successful token exchange and storage, error display, missing code |

**Run:**
```bash
cd frontend && npm run test -- login-content oauth-entra-callback
```

### Manual Test Checklist

1. Set env: `APP_MODE=saas`, `PROVIDERS_CONFIGURED=enterprise_sso`, `ENTRA_*`, `OPENHANDS_USER_AUTH_CLASS`
2. Register redirect URI in Entra app
3. Start app, navigate to login → Enterprise SSO button visible
4. Click button → redirect to Entra → sign in → redirect back with token
5. Verify API calls include `Authorization: Bearer <token>`
6. Logout → token cleared, redirect to login
