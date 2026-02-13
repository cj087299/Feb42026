# QuickBooks Online OAuth 2.0 Authentication Flow

## Overview

This application now supports full OAuth 2.0 authentication for QuickBooks Online (QBO). This allows one admin user to connect to QuickBooks using their QBO username and password, and the tokens are automatically stored in the database and shared across all users for 101 days.

## How It Works

### User Experience

1. **Admin logs in** to the VZT Accounting application
2. **Navigates to QBO Settings** (`/qbo-settings`)
3. **Enters credentials** (Client ID, Client Secret, Redirect URI)
4. **Clicks "Connect to QuickBooks"**
5. **Redirected to QuickBooks** where they log in with their QBO username and password
6. **Authorizes the application** to access their QuickBooks data
7. **Redirected back** to the VZT Accounting application
8. **Tokens are automatically saved** to the database
9. **All users can now access QBO** for the next 101 days

### Technical Flow

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│    Admin    │         │  VZT App    │         │  QuickBooks │
└──────┬──────┘         └──────┬──────┘         └──────┬──────┘
       │                       │                        │
       │  1. Click Connect     │                        │
       ├──────────────────────>│                        │
       │                       │                        │
       │  2. POST /oauth/auth  │                        │
       │                       │  3. GET /connect/oauth2│
       │                       ├───────────────────────>│
       │  4. Redirect to QBO   │                        │
       │<──────────────────────┤                        │
       │                       │                        │
       │  5. Login & Authorize │                        │
       ├──────────────────────────────────────────────>│
       │                       │                        │
       │  6. Redirect with code│                        │
       │<──────────────────────────────────────────────┤
       │                       │                        │
       │  7. GET /oauth/callback?code=...&realmId=...  │
       ├──────────────────────>│                        │
       │                       │                        │
       │                       │  8. POST /tokens/bearer│
       │                       ├───────────────────────>│
       │                       │                        │
       │                       │  9. Return tokens      │
       │                       │<───────────────────────┤
       │                       │                        │
       │                       │  10. Save to database  │
       │                       │                        │
       │  11. Success & Redirect                        │
       │<──────────────────────┤                        │
       │                       │                        │
```

## Setup Instructions

### Prerequisites

1. **QuickBooks Developer Account**: Sign up at [developer.intuit.com](https://developer.intuit.com/)
2. **Create a QBO App**: 
   - Log in to the Intuit Developer Portal
   - Create a new app for QuickBooks Online API
   - Note your **Client ID** and **Client Secret**

### Configure Redirect URI

The redirect URI must be configured in your QuickBooks app settings:

1. In the Intuit Developer Portal, go to your app
2. Navigate to "Keys & OAuth" or "Keys & credentials"
3. Add the following redirect URI:
   ```
   https://your-domain.com/api/qbo/oauth/callback
   ```
   For local development:
   ```
   http://localhost:8080/api/qbo/oauth/callback
   ```

### Connect to QuickBooks

1. Log in as an admin or master_admin user
2. Navigate to **QBO Settings** (`/qbo-settings`)
3. In the "Connect to QuickBooks Online" section:
   - Enter your **Client ID**
   - Enter your **Client Secret**
   - Verify the **Redirect URI** (auto-filled)
4. Click **"Connect to QuickBooks"**
5. You'll be redirected to QuickBooks
6. Log in with your QuickBooks username and password
7. Authorize the application
8. You'll be redirected back to the settings page with a success message

## Token Management

### Token Storage

All tokens are stored in the `qbo_tokens` table in the database:

- **Client ID**: OAuth Client ID
- **Client Secret**: OAuth Client Secret (encrypted)
- **Access Token**: Short-lived token (1 hour)
- **Refresh Token**: Long-lived token (101 days)
- **Realm ID**: QuickBooks Company ID
- **Expiration Times**: Calculated from QBO's response

### Token Lifecycle

1. **Access Token**: 
   - Expires after 1 hour (3600 seconds)
   - Automatically refreshed when needed
   - Used for all API requests

2. **Refresh Token**:
   - Expires after 101 days (8726400 seconds)
   - Used to get new access tokens
   - Must be renewed every ~3 months

### Automatic Token Refresh

The application automatically refreshes access tokens:

- When making API requests and the token has expired
- When a 401 Unauthorized response is received
- The new tokens are automatically saved to the database

## API Endpoints

### POST /api/qbo/oauth/authorize

Initiates the OAuth 2.0 flow.

**Access**: Admin and master_admin only

**Request Body**:
```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "redirect_uri": "https://your-domain.com/api/qbo/oauth/callback"
}
```

**Response**:
```json
{
  "authorization_url": "https://appcenter.intuit.com/connect/oauth2?..."
}
```

**What it does**:
1. Stores credentials in session
2. Generates a CSRF state token
3. Returns the QuickBooks authorization URL
4. Frontend redirects user to this URL

### GET /api/qbo/oauth/callback

Handles the OAuth callback from QuickBooks.

**Access**: Admin and master_admin only

**Query Parameters**:
- `code`: Authorization code from QuickBooks
- `state`: CSRF token for validation
- `realmId`: QuickBooks Company ID
- `error`: Error message if authorization failed

**What it does**:
1. Validates the state token (CSRF protection)
2. Exchanges authorization code for tokens
3. Saves tokens to database
4. Updates the global QBO client
5. Redirects to QBO settings page

**Token Exchange Request** (internal):
```http
POST https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer
Content-Type: application/x-www-form-urlencoded
Authorization: Basic [base64(client_id:client_secret)]

grant_type=authorization_code
code=[authorization_code]
redirect_uri=[redirect_uri]
```

**Token Exchange Response**:
```json
{
  "accessToken": "eyJhbGci...",
  "refreshToken": "RT1-171-...",
  "expires_in": 3600,
  "x_refresh_token_expires_in": 8726400,
  "idToken": "eyJraWQi..."
}
```

## Security Considerations

### CSRF Protection

- A unique state token is generated for each OAuth flow
- Stored in the user's session
- Validated in the callback to prevent CSRF attacks

### Token Security

- Client Secret is never exposed to the frontend
- Tokens are stored securely in the database
- Only admins can initiate OAuth or view credentials
- All OAuth actions are logged in the audit log

### Session Management

- OAuth credentials are stored in the session temporarily
- Cleared after successful token exchange
- Session data is never logged or exposed

## Troubleshooting

### "Invalid Redirect URI"

**Cause**: The redirect URI in your request doesn't match the one configured in your QBO app

**Solution**:
1. Check your QBO app settings in the Intuit Developer Portal
2. Ensure the redirect URI exactly matches (including protocol and trailing slashes)
3. Update the redirect URI in the QBO Settings page

### "Invalid State Parameter"

**Cause**: CSRF validation failed (possible reasons: session expired, cookies disabled, or security attack)

**Solution**:
1. Clear your browser cookies and session data
2. Try the OAuth flow again
3. Ensure cookies are enabled in your browser

### "Failed to Exchange Authorization Code"

**Cause**: The authorization code is invalid, expired, or already used

**Solution**:
1. Authorization codes are single-use and expire quickly
2. Restart the OAuth flow
3. Complete the flow quickly without delays

### "401 Unauthorized" from QuickBooks

**Cause**: Invalid Client ID or Client Secret

**Solution**:
1. Verify your credentials in the Intuit Developer Portal
2. Ensure you're using credentials from the correct environment (Sandbox vs Production)
3. Check for typos in the Client ID or Client Secret

### Tokens Expired

**Refresh Token Expired (after 101 days)**:
- Simply reconnect using the "Connect to QuickBooks" button
- You'll need to authorize the app again

**Access Token Expired (after 1 hour)**:
- This happens automatically and is handled by the application
- No user action required

## Manual Token Entry (Alternative)

If you already have tokens (e.g., from a previous OAuth flow or provided by QuickBooks), you can still enter them manually:

1. Navigate to **QBO Settings**
2. Scroll to "Manual Credentials Entry"
3. Enter:
   - Client ID
   - Client Secret
   - Refresh Token
   - Realm ID
4. Click "Save Credentials"

## Maintenance

### Regular Tasks

**Every 3 Months** (before refresh token expires):
- Click "Connect to QuickBooks" to renew tokens
- Or use the manual token entry method

**Weekly** (recommended):
- Check token status in QBO Settings
- Review audit logs for any authentication issues

### Monitoring

Monitor these indicators in QBO Settings:
- Access Token expiration (should auto-refresh)
- Refresh Token expiration (needs manual renewal after 101 days)
- Last updated timestamp

## Additional Resources

- [QuickBooks OAuth 2.0 Documentation](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- [QBO API Reference](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/account)
- [Token Management Guide](QBO_TOKEN_MANAGEMENT.md)
- [Authentication Setup Guide](QBO_AUTHENTICATION_SETUP.md)

## Support

For issues:
1. Check the audit log at `/audit` for detailed error messages
2. Review the application logs
3. Verify credentials in the Intuit Developer Portal
4. Ensure the redirect URI is correctly configured
5. Contact your system administrator
