# QuickBooks OAuth Credential Setup Guide

## Problem: 401 Unauthorized Error When Refreshing OAuth Token

If you're seeing this error in your logs:
```
ERROR:src.qbo_client:Failed to refresh access token: 401 Client Error: Unauthorized for url: https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer
```

This means your QuickBooks OAuth credentials are either:
1. Not configured
2. Invalid or expired
3. Using dummy/placeholder values

## Solution: Configure Valid OAuth Credentials

### Step 1: Check Current Credential Status

Visit the QBO Settings page in your application:
```
https://your-app-url.com/qbo-settings
```

Or check the API endpoint:
```bash
GET /api/qbo/credentials
```

This will show you:
- Whether credentials are configured
- If they're valid or using dummy values
- Token expiration dates

### Step 2: Set Up QuickBooks OAuth Connection

You have three options:

#### Option A: Use the Initialization Script (Fastest)

If you have credentials from QuickBooks OAuth 2.0 Playground, use the initialization script:

```bash
python3 initialize_qbo_credentials.py
```

This script:
- Initializes the database schema if needed
- Inserts valid OAuth credentials directly into the database
- Sets proper token expiration timestamps
- Verifies the credentials were saved correctly

**Note**: Edit the script first to replace the example credentials with your actual QuickBooks credentials.

#### Option B: Use the Web UI (Recommended for Production)

1. Log in to your application as an admin or master_admin
2. Navigate to **QBO Settings** (`/qbo-settings`)
3. Click **"Connect to QuickBooks"**
4. You'll be redirected to QuickBooks to authorize the connection
5. After authorization, you'll be redirected back with valid credentials

This is the easiest method and handles all token exchange automatically.

#### Option C: Manually Enter Credentials

If you have credentials from QuickBooks OAuth 2.0 Playground or your app:

1. Go to **QBO Settings** (`/qbo-settings`)
2. Enter the following information:
   - **Client ID**: Your QuickBooks OAuth Client ID
   - **Client Secret**: Your QuickBooks OAuth Client Secret
   - **Refresh Token**: A valid refresh token from QuickBooks
   - **Realm ID**: Your QuickBooks Company ID
3. Click **"Save Credentials"**

### Step 3: Getting OAuth Credentials from QuickBooks

If you don't have credentials yet:

1. **Create a QuickBooks App**:
   - Go to [QuickBooks Developer Portal](https://developer.intuit.com/)
   - Create a new app or use an existing one
   - Note your Client ID and Client Secret

2. **Get Authorization Code**:
   - Use the OAuth 2.0 authorization flow to get a code
   - Redirect URL must match what's configured in your QuickBooks app

3. **Exchange for Tokens**:
   - Exchange the authorization code for access and refresh tokens
   - The refresh token is valid for 101 days

### Step 4: Verify the Connection

After configuring credentials:

1. Check the credential status:
   ```bash
   GET /api/qbo/credentials
   ```
   
2. Try manually refreshing the token:
   ```bash
   POST /api/qbo/refresh
   ```

3. Test by fetching invoices:
   ```bash
   GET /api/invoices
   ```

## Using Environment Variables (Alternative)

For production deployments, you can also set credentials via environment variables:

```bash
export QBO_CLIENT_ID=your_client_id
export QBO_CLIENT_SECRET=your_client_secret
export QBO_REFRESH_TOKEN=your_refresh_token
export QBO_REALM_ID=your_realm_id
```

Or use Google Secret Manager:
```bash
echo -n "your_client_id" | gcloud secrets create QBO_ID_2-3-26 --data-file=-
echo -n "your_client_secret" | gcloud secrets create QBO_Secret_2-3-26 --data-file=-
export QBO_REFRESH_TOKEN=your_refresh_token
export QBO_REALM_ID=your_realm_id
```

**Note**: Database-stored credentials (via the web UI) take priority over environment variables.

## Credential Priority Order

The application checks for credentials in this order:

1. **Database** (set via `/qbo-settings` web UI) - Highest Priority
2. **Google Secret Manager** (QBO_ID_2-3-26, QBO_Secret_2-3-26)
3. **Environment Variables** (QBO_CLIENT_ID, QBO_CLIENT_SECRET, etc.)
4. **Dummy Values** (causes errors) - Lowest Priority

## Token Lifecycle

- **Access Token**: Valid for 1 hour, automatically refreshed
- **Refresh Token**: Valid for 101 days (8,726,400 seconds)
- **Automatic Refresh**: Access tokens refresh automatically when expired
- **Manual Refresh**: Admins can manually refresh via `/api/qbo/refresh`

## Common Issues

### Issue: "Cannot refresh access token: QBO credentials are not configured"

**Solution**: The application is using dummy values. Follow Step 2 above to configure real credentials.

### Issue: "401 Unauthorized" error

**Solution**: Your credentials are invalid or expired. Reconnect to QuickBooks via the web UI.

### Issue: Refresh token expired (after 101 days)

**Solution**: Reconnect to QuickBooks to get a new refresh token. The old refresh token is automatically replaced.

## Security Notes

- Client Secret is sensitive - never expose it in logs or UI
- Credentials are stored securely in the database
- Dummy values are used as safe fallbacks to prevent app crashes
- All credential operations are logged in the audit log
- Only admin and master_admin users can manage credentials

## Need Help?

If you continue to experience issues:

1. Check the application logs for detailed error messages
2. Verify your QuickBooks app is properly configured
3. Ensure your redirect URLs match exactly
4. Check that your QuickBooks subscription is active

For more information, see:
- `QBO_OAUTH_FLOW.md` - Detailed OAuth flow documentation
- `QBO_TOKEN_MANAGEMENT.md` - Token management details
- `QBO_AUTHENTICATION_SETUP.md` - Authentication setup guide
