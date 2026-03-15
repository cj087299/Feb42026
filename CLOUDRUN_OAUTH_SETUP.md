# Cloud Run OAuth Redirect URI Configuration

## Deployed Application Details

### Cloud Run URL
```
https://feb42026-286597576168.us-central1.run.app
```

### OAuth Redirect URI
```
https://feb42026-286597576168.us-central1.run.app/api/qbo/oauth/callback
```

## QuickBooks Developer Portal Configuration

### ✅ VERIFIED: Redirect URI is Registered

The redirect URI has been registered in the QuickBooks Developer Portal:
```
https://feb42026-286597576168.us-central1.run.app/api/qbo/oauth/callback
```

**This URI must match EXACTLY** - including:
- Protocol: `https://` (required)
- Domain: `feb42026-286597576168.us-central1.run.app` (Cloud Run hostname)
- Path: `/api/qbo/oauth/callback` (OAuth callback endpoint)
- No trailing slash

## How the Redirect URI is Constructed

The application automatically constructs the redirect URI based on the incoming request's host:

```python
# From main.py - qbo_oauth_authorize_v2()
parsed_url = urlparse(request.host_url.rstrip('/'))
https_url = urlunparse((
    'https',  # Always use HTTPS
    parsed_url.netloc,  # Cloud Run hostname
    parsed_url.path,
    parsed_url.params,
    parsed_url.query,
    parsed_url.fragment
))
redirect_uri = https_url + '/api/qbo/oauth/callback'
```

### On Cloud Run
- `request.host_url` returns: `https://feb42026-286597576168.us-central1.run.app/`
- Constructed redirect URI: `https://feb42026-286597576168.us-central1.run.app/api/qbo/oauth/callback`
- **This matches the registered URI** ✅

## Testing OAuth Flow

### 1. Access the Settings Page
Navigate to either:
- `https://feb42026-286597576168.us-central1.run.app/qbo-settings`
- `https://feb42026-286597576168.us-central1.run.app/qbo-settings-v2`

### 2. View Diagnostics
Click "View OAuth Diagnostics" to verify:
- Redirect URI matches the registered URI
- Client ID is correct
- Using HTTPS
- Configuration is correct

### 3. Connect to QuickBooks
1. Click "Connect to QuickBooks"
2. Allow browser popups if prompted
3. **You should see the QuickBooks login screen**
4. Log in with your QuickBooks credentials
5. Authorize the application
6. You'll be redirected back with a success message

### 4. Check Server Logs
The logs will show:
```
================================================================================
QuickBooks OAuth 2.0 Flow Initiated
================================================================================
Client ID: AB224ne26K... (masked for security)
Redirect URI (unencoded): https://feb42026-286597576168.us-central1.run.app/api/qbo/oauth/callback
Redirect URI (encoded): https%3A%2F%2Ffeb42026-286597576168.us-central1.run.app%2Fapi%2Fqbo%2Foauth%2Fcallback
State Token: [UUID]
================================================================================
```

## Troubleshooting

### If OAuth Still Doesn't Work

1. **Verify in QuickBooks Developer Portal**:
   - Go to [developer.intuit.com](https://developer.intuit.com)
   - Open your app's dashboard
   - Go to "Keys & OAuth" or "Keys & credentials"
   - Verify this exact URI is listed:
     ```
     https://feb42026-286597576168.us-central1.run.app/api/qbo/oauth/callback
     ```

2. **Check Browser Console**:
   - Open browser DevTools (F12)
   - Look for popup blocker warnings
   - Check for JavaScript errors

3. **Check Server Logs**:
   - View Cloud Run logs in Google Cloud Console
   - Look for OAuth flow initiation messages
   - Check for callback errors

4. **Test Redirect URI**:
   - Run the test script:
     ```bash
     python test_redirect_uri.py
     ```
   - Verify all tests pass

### Common Issues

**Issue: "Redirect URI mismatch"**
- **Cause**: URI in code doesn't match QuickBooks settings
- **Solution**: The URI is auto-generated from Cloud Run hostname, so this should work automatically

**Issue: No login screen appears**
- **Cause**: Popup blocker or browser extension
- **Solution**: Allow popups for `feb42026-286597576168.us-central1.run.app`

**Issue: 403 Forbidden after connecting**
- **Cause**: Tokens expired or invalid
- **Solution**: Reconnect via OAuth flow to get new tokens

## Client Credentials

### Current Configuration
The application uses hardcoded client credentials (per requirements):
- **Client ID**: `AB224ne26KUlOjJebeDLMIwgIZcTRQkb6AieFqwJQg0sWCzXXA`
- **Client Secret**: `8LyYgJtmfo7znuWjilV5B3HUGzeiOmZ8hw0dt1Yl`
- **Environment**: Sandbox (Development)

These credentials must match the ones in your QuickBooks Developer Portal app.

## Next Steps

1. ✅ **Redirect URI is registered** - Confirmed by user
2. ✅ **Application constructs URI correctly** - Verified by tests
3. **Test OAuth flow**:
   - Navigate to `/qbo-settings-v2`
   - Click "Connect to QuickBooks"
   - Should see QuickBooks login screen
   - Complete authorization
   - Verify tokens are saved

4. **Verify API Access**:
   - After connecting, test API calls
   - Check for 403 Forbidden errors
   - If errors persist, check token expiration

## Deployment Verification

The application is configured to work with Cloud Run's environment:
- ✅ HTTPS enforcement (Cloud Run provides SSL)
- ✅ Dynamic redirect URI construction
- ✅ Session management with secure cookies
- ✅ Proper URL parsing without trailing slashes

## Support

For issues:
1. Check diagnostics at `/qbo-settings-v2`
2. Review `OAUTH_TROUBLESHOOTING_GUIDE.md`
3. Check Cloud Run logs in Google Cloud Console
4. Verify redirect URI in QuickBooks Developer Portal
