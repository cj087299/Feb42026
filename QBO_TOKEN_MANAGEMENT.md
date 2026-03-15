# QBO Token Management System

## Overview

The VZT Accounting application now includes a centralized QBO (QuickBooks Online) token management system. This allows administrators to configure QBO credentials once, which are then shared across all users in the system.

## Key Features

### 1. **Centralized Credential Storage**
- QBO credentials are stored in the database, not in environment variables
- One set of credentials serves all users
- Credentials are automatically refreshed before expiration

### 2. **Admin-Only Management**
- Only users with `admin` or `master_admin` roles can manage QBO credentials
- All credential changes are logged in the audit log
- Secure credential input with masked sensitive fields

### 3. **Automatic Token Refresh**
- Access tokens are automatically refreshed when they expire (every ~1 hour)
- Refresh tokens are valid for 101 days
- New refresh tokens are saved automatically when provided by QBO

### 4. **Token Expiration Tracking**
- Visual indicators show token status (Active, Expiring Soon, Expired)
- Automatic calculation of time until expiration
- Manual refresh option available

## How It Works

### Token Lifecycle

1. **Initial Setup**: Admin enters credentials via the QBO Settings page
2. **Storage**: Credentials are encrypted and stored in the database
3. **Usage**: All API calls to QuickBooks use the stored credentials
4. **Refresh**: Access tokens are automatically refreshed before expiration
5. **Update**: New tokens are saved back to the database

### Database Schema

The `qbo_tokens` table stores:
- `client_id`: OAuth Client ID
- `client_secret`: OAuth Client Secret (encrypted)
- `refresh_token`: Long-lived refresh token (101 days)
- `access_token`: Short-lived access token (~1 hour)
- `realm_id`: QuickBooks Company ID
- `access_token_expires_at`: Access token expiration timestamp
- `refresh_token_expires_at`: Refresh token expiration timestamp
- `created_by_user_id`: ID of admin who set the credentials
- Timestamps: `created_at`, `updated_at`

## Setting Up QBO Credentials

### Step 1: Get QuickBooks OAuth Credentials

1. Go to [Intuit Developer Portal](https://developer.intuit.com/)
2. Sign in and navigate to your app
3. Go to "Keys & credentials" section
4. Copy your **Client ID** and **Client Secret**

### Step 2: Get Authorization Code and Tokens

#### Option A: Using Provided Tokens (Recommended)

If you already have the tokens (as provided in the problem statement):
- **Refresh Token**: `RT1-171-H0-1779750488n874s07gtvnsxko4m5z7`
- **Realm ID**: `9341453050298464`

#### Option B: OAuth Flow (For New Tokens)

1. Construct the authorization URL:
   ```
   https://appcenter.intuit.com/connect/oauth2?
   client_id=YOUR_CLIENT_ID
   &scope=com.intuit.quickbooks.accounting
   &redirect_uri=YOUR_REDIRECT_URI
   &response_type=code
   &state=security_token
   ```

2. Visit the URL and authorize your app
3. You'll be redirected with an authorization code
4. Exchange the code for tokens:
   ```bash
   curl -X POST \
     https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer \
     -H 'Accept: application/json' \
     -H 'Content-Type: application/x-www-form-urlencoded' \
     -u 'CLIENT_ID:CLIENT_SECRET' \
     -d 'grant_type=authorization_code&code=AUTHORIZATION_CODE&redirect_uri=YOUR_REDIRECT_URI'
   ```

### Step 3: Configure Credentials in VZT Accounting

1. Log in as an admin or master admin
2. Navigate to **QBO Settings** from the home page or navigation menu
3. Enter your credentials:
   - Client ID
   - Client Secret
   - Refresh Token
   - Realm ID
4. Click **Save Credentials**
5. The system will validate and store the credentials
6. Click **Refresh Access Token** to get an initial access token

## Using the QBO Settings Page

### Accessing the Page

- **URL**: `/qbo-settings`
- **Required Role**: `admin` or `master_admin`
- **Navigation**: Home → QBO Settings

### Features

#### 1. Connection Status
Shows current status of QBO credentials:
- Client ID (masked for security)
- Realm ID
- Access Token status (Active, Expiring Soon, Expired)
- Refresh Token status
- Last update timestamp

#### 2. Credential Form
- **Client ID**: Your QuickBooks OAuth Client ID
- **Client Secret**: Your OAuth Client Secret (password field)
- **Refresh Token**: Long-lived token from QuickBooks
- **Realm ID**: Your QuickBooks Company ID

#### 3. Actions
- **Save Credentials**: Store new credentials
- **Refresh Access Token**: Manually refresh the access token

## API Endpoints

### GET /api/qbo/credentials
Get current QBO credential status (admin/master_admin only)

**Response:**
```json
{
  "client_id": "ABqhvKuQNB...",
  "realm_id": "9341453050298464",
  "has_refresh_token": true,
  "has_access_token": true,
  "access_token_expires_at": "2026-02-14T00:19:50.430719",
  "refresh_token_expires_at": "2026-05-25T23:19:50.430725",
  "created_at": "2026-02-13T23:19:50.430711",
  "updated_at": "2026-02-13T23:19:50.430711"
}
```

### POST /api/qbo/credentials
Save or update QBO credentials (admin/master_admin only)

**Request Body:**
```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "refresh_token": "your_refresh_token",
  "realm_id": "your_realm_id"
}
```

**Response:**
```json
{
  "message": "QBO credentials saved successfully"
}
```

### POST /api/qbo/refresh
Manually refresh QBO access token (admin/master_admin only)

**Response:**
```json
{
  "message": "QBO access token refreshed successfully"
}
```

## Security Considerations

### Data Protection
- Sensitive credentials are stored in the database
- Client secrets and refresh tokens should be treated as passwords
- Only admins can view or modify credentials
- Client ID is partially masked in the UI

### Audit Logging
All credential operations are logged:
- Credential updates
- Manual token refreshes
- Access attempts

View audit logs at `/audit` (admin/master_admin only)

### Access Control
- Only `admin` and `master_admin` roles can access QBO settings
- Regular users cannot view or modify credentials
- All API endpoints verify user permissions

## Troubleshooting

### "No QBO credentials configured"
**Solution**: Navigate to QBO Settings and enter your credentials

### "401 Unauthorized" on token refresh
**Causes:**
- Invalid Client ID or Client Secret
- Expired refresh token (after 101 days)
- Incorrect credentials

**Solution:**
1. Verify credentials in Intuit Developer Portal
2. Get new authorization code and refresh token
3. Update credentials in QBO Settings

### Token expires too quickly
**Note**: Access tokens expire after ~1 hour by design. The system automatically refreshes them. If you're seeing frequent expirations:
- Check the audit log for refresh attempts
- Verify the refresh token hasn't expired
- Ensure the system can reach QuickBooks API

### Refresh token expired
**Solution**: 
1. Get a new authorization code from QuickBooks OAuth flow
2. Exchange it for new tokens
3. Update credentials in QBO Settings

Refresh tokens expire after 101 days, so this needs to be done approximately every 3 months.

## Maintenance Schedule

### Regular Tasks

**Every 3 Months** (before 101 days):
- Get new refresh token through OAuth flow
- Update credentials in QBO Settings
- Verify connection is working

**Weekly** (recommended):
- Check token expiration status
- Review audit logs for any authentication issues
- Verify all users can access QBO data

### Monitoring

Monitor these indicators:
- Token expiration dates in QBO Settings
- Audit log for failed refresh attempts
- API errors related to authentication

## Migration from Environment Variables

If you previously used environment variables for QBO credentials:

1. Log in as admin/master_admin
2. Navigate to QBO Settings
3. Enter the same credentials that were in your environment variables
4. Save credentials
5. The system will now use database credentials instead
6. You can optionally remove the environment variables

**Note**: Database credentials take priority over environment variables.

## Additional Resources

- [QBO Authentication Setup Guide](QBO_AUTHENTICATION_SETUP.md)
- [QuickBooks API Documentation](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/account)
- [OAuth 2.0 Guide](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)

## Support

For assistance:
1. Check the audit log at `/audit` for error details
2. Review system logs at `/logs` (master_admin only)
3. Verify credentials in Intuit Developer Portal
4. Contact your system administrator
