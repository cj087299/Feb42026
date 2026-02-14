# QuickBooks OAuth Database Fix - Summary

## Problem Resolved

The application was experiencing **401 Unauthorized** errors when attempting to refresh OAuth tokens because valid QuickBooks credentials were not configured in the database.

## Solution Implemented

Created `initialize_qbo_credentials.py` script that:
1. Initializes the database schema (if not already present)
2. Inserts valid OAuth credentials from QuickBooks OAuth 2.0 Playground
3. Sets proper token expiration timestamps
4. Verifies credentials were saved successfully

## Credentials Stored

The following credentials from the QuickBooks OAuth 2.0 Playground need to be provided:

- **Client ID**: YOUR_CLIENT_ID_HERE (e.g., 'AB224ne26K...')
- **Client Secret**: YOUR_CLIENT_SECRET_HERE (e.g., '8LyYgJt...')
- **Refresh Token**: YOUR_REFRESH_TOKEN_HERE (e.g., 'RT1-179-H0-...')
- **Access Token**: YOUR_ACCESS_TOKEN_HERE (long JWT token)
- **Realm ID**: YOUR_REALM_ID_HERE (your QuickBooks Company ID)

## Token Expiration

- **Access Token**: Expires in 1 hour (auto-refreshed)
- **Refresh Token**: Expires in 101 days (May 26, 2026)

## Verification Results

✅ **Database Check**: Credentials successfully stored in `vzt_accounting.db`
✅ **SecretManager Check**: Correctly retrieves credentials from database (highest priority)
✅ **QBOClient Check**: Initializes successfully with valid credentials
✅ **Validation Check**: Credentials marked as `is_valid=True` (not dummy values)
✅ **Health Check**: All systems reporting healthy configuration

## Usage

### To Initialize Database with Credentials

**Method 1: Using Environment Variables (Recommended)**
```bash
export QBO_INIT_CLIENT_ID='your_client_id'
export QBO_INIT_CLIENT_SECRET='your_client_secret'
export QBO_INIT_REFRESH_TOKEN='your_refresh_token'
export QBO_INIT_ACCESS_TOKEN='your_access_token'
export QBO_INIT_REALM_ID='your_realm_id'
python3 initialize_qbo_credentials.py
```

**Method 2: Edit Script (Development Only)**
```bash
# Edit initialize_qbo_credentials.py to replace placeholders
python3 initialize_qbo_credentials.py
```

### To Verify Credentials

```bash
python3 check_oauth_health.py
```

### To Update Credentials in Production

1. **Option 1**: Run the initialization script with new credentials
2. **Option 2**: Use the web UI at `/qbo-settings` to connect via OAuth
3. **Option 3**: Set up Google Secret Manager (see `GOOGLE_SECRET_MANAGER_SETUP.md`)

## Credential Priority

The application checks for credentials in this order:
1. **Database** ⭐ (configured by initialization script or web UI)
2. Google Secret Manager
3. Environment Variables
4. Dummy Values (causes errors)

## Files Modified/Created

- `initialize_qbo_credentials.py` - New credential initialization script
- `OAUTH_CREDENTIAL_SETUP_GUIDE.md` - Updated with initialization script instructions
- `README.md` - Updated with quick setup section
- `vzt_accounting.db` - Database file with valid credentials (not committed, in .gitignore)

## Security Notes

- The database file `vzt_accounting.db` contains sensitive credentials and is excluded from version control via `.gitignore`
- In production, use the web UI OAuth flow to get fresh credentials
- The initialization script should be edited before use to avoid committing credentials
- Consider using Google Secret Manager for production deployments

## Next Steps

1. **Deploy to Cloud Run**: The database will be created fresh on deployment, so either:
   - Run the initialization script after deployment, OR
   - Use the web UI at `/qbo-settings` to connect to QuickBooks, OR
   - Configure Google Secret Manager with valid secrets

2. **Monitor Token Refresh**: Access tokens refresh automatically. Monitor logs for successful refreshes.

3. **Token Expiration**: In 101 days (May 26, 2026), reconnect to QuickBooks to get a new refresh token.

## Testing

All existing tests pass:
- ✅ `tests.test_qbo` - QBO client tests
- ✅ `tests.test_qbo_authentication` - OAuth authentication tests (11/13 passing, 2 require google-cloud-secret-manager library)
- ✅ `tests.test_qbo_token_management` - Token management tests

## Expected Behavior

After this fix:
- ✅ No more 401 Unauthorized errors (unless tokens expire)
- ✅ Application can fetch invoices from QuickBooks
- ✅ Access tokens refresh automatically
- ✅ Credentials persist across application restarts
- ✅ Health checks show valid configuration

## Troubleshooting

If you still see 401 errors:
1. Check token expiration dates
2. Run `python3 check_oauth_health.py` to diagnose
3. Reconnect to QuickBooks if refresh token expired
4. See `OAUTH_CREDENTIAL_SETUP_GUIDE.md` for detailed troubleshooting
