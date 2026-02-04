# Desired Features Point 1: Authentication & Identity – Implementation Plan

> Full implementation details and test plan: [docs/DESIRED_FEATURES_POINT1_IMPLEMENTATION_PLAN.md](docs/DESIRED_FEATURES_POINT1_IMPLEMENTATION_PLAN.md)

Direct Microsoft Entra ID (Azure AD) integration via OAuth2/OIDC, without Keycloak.

**Key env vars**: `APP_MODE=saas`, `PROVIDERS_CONFIGURED=enterprise_sso`, `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `OPENHANDS_USER_AUTH_CLASS=openhands.server.user_auth.entra_user_auth.EntraUserAuth`
