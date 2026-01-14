# Microsoft Entra (Azure AD) OAuth2 Integration Guide

This guide explains how to configure Microsoft Entra ID (formerly Azure Active Directory) as an OAuth2 identity provider in OpenHands using Keycloak.

## Prerequisites

- Access to Microsoft Entra admin center (Azure Portal)
- Keycloak admin access
- OpenHands enterprise instance running

## Step 1: Register Application in Microsoft Entra

1. Navigate to [Azure Portal](https://portal.azure.com)
2. Go to **Microsoft Entra ID** > **App registrations** > **New registration**
3. Configure the application:
   - **Name**: OpenHands (or your preferred name)
   - **Supported account types**: Choose based on your requirements
     - "Accounts in this organizational directory only" for single tenant
     - "Accounts in any organizational directory" for multi-tenant
   - **Redirect URI**: 
     - Type: Web
     - URL: `https://YOUR_KEYCLOAK_URL/realms/YOUR_REALM/broker/microsoft/endpoint`
     - Example: `https://auth.example.com/realms/openhands/broker/microsoft/endpoint`

4. Click **Register**

## Step 2: Configure Application Secrets

1. In your newly created app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description (e.g., "OpenHands Keycloak Integration")
4. Choose an expiration period
5. Click **Add**
6. **IMPORTANT**: Copy the secret value immediately - it won't be shown again

## Step 3: Configure API Permissions

1. Go to **API permissions** in your app registration
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Add the following permissions:
   - `openid` (required)
   - `profile` (required)
   - `email` (required)
   - `User.Read` (recommended)
6. Click **Add permissions**
7. (Optional) Click **Grant admin consent** if you have admin rights

## Step 4: Note Application Details

From the **Overview** page of your app registration, note down:
- **Application (client) ID**: e.g., `12345678-1234-1234-1234-123456789abc`
- **Directory (tenant) ID**: e.g., `87654321-4321-4321-4321-cba987654321`
- **Client secret** (from Step 2)

## Step 5: Configure Keycloak Identity Provider

1. Log in to your Keycloak admin console
2. Select your realm (e.g., `openhands`)
3. Go to **Identity Providers**
4. Click **Add provider** and select **OpenID Connect v1.0**
5. Configure the provider:

### Basic Settings
- **Alias**: `microsoft` (must match the redirect URI path)
- **Display Name**: `Microsoft Entra ID` or `Microsoft`
- **Enabled**: ON
- **Store Tokens**: ON
- **Stored Tokens Readable**: ON
- **Trust Email**: ON
- **First Login Flow**: `first broker login`

### OpenID Connect Config
- **Authorization URL**: `https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize`
  - Replace `{TENANT_ID}` with your tenant ID
- **Token URL**: `https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token`
  - Replace `{TENANT_ID}` with your tenant ID
- **Logout URL**: `https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/logout`
  - Replace `{TENANT_ID}` with your tenant ID
- **User Info URL**: `https://graph.microsoft.com/oidc/userinfo`
- **Client ID**: Your Application (client) ID from Step 4
- **Client Secret**: Your client secret from Step 2
- **Client Authentication**: `Client secret sent as post`
- **Default Scopes**: `openid profile email`

### Advanced Settings (Optional)
- **Backchannel Logout**: OFF (unless you need it)
- **Disable User Info**: OFF
- **Validate Signatures**: ON
- **Use JWKS URL**: ON
- **JWKS URL**: `https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys`
  - Replace `{TENANT_ID}` with your tenant ID

6. Click **Save**

## Step 6: Configure Mappers (Optional but Recommended)

Mappers help sync user attributes from Microsoft Entra to Keycloak:

1. In your identity provider configuration, go to the **Mappers** tab
2. Create mappers for the following attributes:

### Email Mapper
- **Name**: email
- **Sync Mode Override**: force
- **Mapper Type**: Attribute Importer
- **Claim**: email
- **User Attribute Name**: email

### First Name Mapper
- **Name**: firstName
- **Sync Mode Override**: force
- **Mapper Type**: Attribute Importer
- **Claim**: given_name
- **User Attribute Name**: firstName

### Last Name Mapper
- **Name**: lastName
- **Sync Mode Override**: force
- **Mapper Type**: Attribute Importer
- **Claim**: family_name
- **User Attribute Name**: lastName

### Username Mapper
- **Name**: username
- **Sync Mode Override**: force
- **Mapper Type**: Attribute Importer
- **Claim**: preferred_username
- **User Attribute Name**: username

## Step 7: Update OpenHands Configuration

Update your OpenHands environment variables:

```bash
# Keycloak Configuration
KEYCLOAK_SERVER_URL=https://YOUR_KEYCLOAK_URL
KEYCLOAK_REALM_NAME=YOUR_REALM
KEYCLOAK_CLIENT_ID=YOUR_CLIENT_ID
KEYCLOAK_CLIENT_SECRET=YOUR_CLIENT_SECRET
KEYCLOAK_PROVIDER_NAME=microsoft  # This should match your IDP alias

# Frontend Configuration
AUTH_URL=https://YOUR_KEYCLOAK_URL/realms/YOUR_REALM/protocol/openid-connect/auth
```

## Step 8: Configure Frontend Provider

Update your OpenHands configuration to include Microsoft as a configured provider. This is typically done through the `PROVIDERS_CONFIGURED` environment variable or config:

```bash
PROVIDERS_CONFIGURED=microsoft
```

Or if you have multiple providers:
```bash
PROVIDERS_CONFIGURED=github,gitlab,microsoft
```

## Step 9: Test the Integration

1. Navigate to your OpenHands login page
2. You should see a "Connect with Microsoft" button (if frontend is configured)
3. Click the button to initiate OAuth flow
4. You should be redirected to Microsoft login
5. After successful authentication, you should be redirected back to OpenHands
6. Verify that user data is correctly synchronized

## Step 10: Configure Invite System (Optional)

If you want to control access using the invite system:

1. Users who attempt to log in without an approved invite will be able to request one
2. Admins can review and approve invite requests through the OpenHands admin interface
3. Approved users can be manually added to a Microsoft Entra group for access control

### Environment Variables for Invite System

```bash
# Disable automatic access (requires invite approval)
DISABLE_WAITLIST=false

# Optional: Configure allowed users via file
GITHUB_USER_LIST_FILE=/path/to/allowed_users.txt

# Optional: Configure allowed users via Google Sheets
GITHUB_USERS_SHEET_ID=your_sheet_id
```

## Troubleshooting

### Common Issues

1. **Redirect URI Mismatch**
   - Ensure the redirect URI in Azure exactly matches: `https://YOUR_KEYCLOAK_URL/realms/YOUR_REALM/broker/microsoft/endpoint`
   - Check that the IDP alias in Keycloak is `microsoft`

2. **Client Secret Expired**
   - Client secrets in Azure expire - check the expiration date
   - Generate a new secret if expired and update Keycloak configuration

3. **Invalid Scopes**
   - Ensure the app registration has the required API permissions
   - Grant admin consent if needed

4. **Token Validation Errors**
   - Verify the JWKS URL is correct
   - Check that token validation is properly configured

5. **User Not Found After Login**
   - Check mapper configuration
   - Verify that email/username claims are being received
   - Review Keycloak logs for detailed error messages

### Logs to Check

- Keycloak server logs: `/opt/keycloak/data/log/keycloak.log`
- OpenHands backend logs: Check Docker logs or application logs
- Browser console: Check for frontend errors

## Security Considerations

1. **Client Secrets**: Store client secrets securely using environment variables or secret management systems
2. **Token Storage**: Ensure tokens are stored securely in Keycloak
3. **HTTPS**: Always use HTTPS in production for Keycloak and OpenHands
4. **Scope Minimization**: Only request the minimum required scopes
5. **Token Expiration**: Configure appropriate token expiration times
6. **Logging**: Enable comprehensive logging for security auditing
7. **Access Control**: Use the invite system or Microsoft Entra groups to control access

## Multi-Tenant Support

For multi-tenant Azure AD applications:

1. Use `https://login.microsoftonline.com/common/` instead of tenant-specific URLs
2. Update configuration:
   - **Authorization URL**: `https://login.microsoftonline.com/common/oauth2/v2.0/authorize`
   - **Token URL**: `https://login.microsoftonline.com/common/oauth2/v2.0/token`
   - **JWKS URL**: `https://login.microsoftonline.com/common/discovery/v2.0/keys`

## References

- [Microsoft Entra ID Documentation](https://learn.microsoft.com/en-us/entra/identity/)
- [Keycloak Identity Providers](https://www.keycloak.org/docs/latest/server_admin/#_identity_broker)
- [Microsoft Identity Platform OAuth 2.0](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)
