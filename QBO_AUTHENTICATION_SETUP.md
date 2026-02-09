# QuickBooks Online (QBO) Authentication Setup

This document explains how to configure QuickBooks Online authentication for the VZT Accounting application.

## Overview

The application uses OAuth 2.0 to authenticate with QuickBooks Online API. The authentication flow requires:
- Client ID (OAuth application ID)
- Client Secret (OAuth application secret)
- Refresh Token (Long-lived token for refreshing access tokens)
- Realm ID (QuickBooks company ID)

## Configuration Methods

### Method 1: Google Cloud Secret Manager (Recommended for Production)

1. Set the `GOOGLE_CLOUD_PROJECT` environment variable:
   ```bash
   export GOOGLE_CLOUD_PROJECT=your-project-id
   ```

2. Store your QBO credentials as secrets in Google Secret Manager:
   ```bash
   # Store QBO Client ID
   echo -n "your_client_id" | gcloud secrets create QBO_ID_2-3-26 --data-file=-
   
   # Store QBO Client Secret
   echo -n "your_client_secret" | gcloud secrets create QBO_Secret_2-3-26 --data-file=-
   ```

3. Set additional credentials as environment variables:
   ```bash
   export QBO_REFRESH_TOKEN=your_refresh_token
   export QBO_REALM_ID=your_realm_id
   ```

### Method 2: Environment Variables (Development/Testing)

Set all credentials as environment variables:

```bash
export QBO_CLIENT_ID=your_client_id
export QBO_CLIENT_SECRET=your_client_secret
export QBO_REFRESH_TOKEN=your_refresh_token
export QBO_REALM_ID=your_realm_id
```

### Method 3: Default Values (Testing Only)

If no credentials are configured, the application uses default dummy values:
- Client ID: `dummy_id`
- Client Secret: `dummy_secret`
- Refresh Token: `dummy_refresh`
- Realm ID: `dummy_realm`

**Note:** These defaults will not work with real QBO API calls.

## Getting QuickBooks OAuth Credentials

### 1. Create a QuickBooks App

1. Go to [Intuit Developer Portal](https://developer.intuit.com/)
2. Sign in with your Intuit account
3. Click "Create an app" and select "QuickBooks Online API"
4. Fill in your app details and create the app

### 2. Get Client ID and Secret

1. In your app's dashboard, go to "Keys & credentials"
2. Copy your **Client ID** and **Client Secret**
3. Note the environment (Sandbox or Production)

### 3. Get Authorization Code (First Time Setup)

1. Construct the authorization URL:
   ```
   https://appcenter.intuit.com/connect/oauth2?
   client_id=YOUR_CLIENT_ID
   &scope=com.intuit.quickbooks.accounting
   &redirect_uri=YOUR_REDIRECT_URI
   &response_type=code
   &state=security_token
   ```

2. Visit the URL in a browser and authorize your app
3. You'll be redirected with an authorization code in the URL

### 4. Exchange Code for Tokens

Use the authorization code to get access and refresh tokens:

```bash
curl -X POST \
  https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -u 'CLIENT_ID:CLIENT_SECRET' \
  -d 'grant_type=authorization_code&code=AUTHORIZATION_CODE&redirect_uri=YOUR_REDIRECT_URI'
```

The response includes:
- `access_token` (expires in 1 hour)
- `refresh_token` (expires in 101 days, used to get new access tokens)

### 5. Get Realm ID

The Realm ID (Company ID) is returned during the OAuth flow in the `realmId` parameter of the redirect URL.

Alternatively, you can find it in the QBO company settings or by decoding the ID token.

## Token Refresh

The application automatically refreshes access tokens using the refresh token when:
- Making the first API request (if no access token exists)
- Receiving a 401 Unauthorized response from QBO API

Token refresh happens transparently in the background.

## Testing QBO Authentication

### Run Unit Tests

```bash
python -m unittest tests.test_qbo_authentication
```

This runs 13 comprehensive tests covering:
- Client initialization
- Token refresh mechanism
- API request authentication
- Error handling
- Secret Manager integration

### Run Manual Test

```bash
python manual_qbo_test.py
```

This interactive test script verifies:
- Secret Manager credential retrieval
- QBO client initialization
- Token refresh with mocked API
- API requests with authentication
- Error handling

## Troubleshooting

### "401 Unauthorized" Errors

**Cause:** Invalid or expired credentials

**Solutions:**
1. Verify your Client ID and Secret are correct
2. Check if your refresh token has expired (refresh tokens expire after 101 days)
3. Get a new authorization code and refresh token
4. Ensure you're using the correct environment (Sandbox vs Production)

### "Secret not found" Warnings

**Cause:** Credentials not configured in Google Secret Manager

**Solutions:**
1. Verify `GOOGLE_CLOUD_PROJECT` is set
2. Check that secrets exist: `gcloud secrets list`
3. Ensure the service account has permission to access secrets
4. Fallback to environment variables if Secret Manager is unavailable

### Rate Limiting

QuickBooks API has rate limits:
- Sandbox: 500 requests per minute, 5000 per day
- Production: More generous, but still limited

If you hit rate limits:
1. Implement request throttling
2. Cache frequently accessed data
3. Use batch APIs where possible

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use Secret Manager** in production environments
3. **Rotate credentials** regularly
4. **Monitor access logs** for suspicious activity
5. **Use least-privilege** service accounts
6. **Encrypt tokens** at rest if storing in a database

## API Documentation

- [QuickBooks Online API Reference](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/account)
- [OAuth 2.0 Guide](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- [Token Management](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0#refresh-token)

## Support

For issues with:
- **This application:** Create an issue in the repository
- **QuickBooks API:** Contact [Intuit Developer Support](https://help.developer.intuit.com/)
- **OAuth/Authentication:** Review [OAuth 2.0 documentation](https://oauth.net/2/)
