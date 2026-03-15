# QuickBooks OAuth 2.0 Troubleshooting Guide

## Problem: OAuth Not Showing QuickBooks Login Screen

### Symptom
When clicking "Connect to QuickBooks", the OAuth flow doesn't display the QuickBooks login screen where you can enter your QuickBooks username and password.

### Common Causes and Solutions

#### 1. Redirect URI Not Registered in QuickBooks Developer Portal

**This is the most common cause of OAuth issues.**

**What to check:**
- Log into [developer.intuit.com](https://developer.intuit.com)
- Go to your app's dashboard
- Navigate to "Keys & OAuth" or "Keys & credentials"
- Check the "Redirect URIs" section

**What it should be:**
The redirect URI must **exactly match** what the application is using. To find your redirect URI:

1. Navigate to `/qbo-settings-v2` in your application
2. Click "View OAuth Diagnostics"
3. Look for the "Redirect URI" value in the "Current Setup" section
4. Example: `https://your-domain.com/api/qbo/oauth/callback`

**How to fix:**
1. Add the exact redirect URI to your QBO app settings
2. **Important:** The URI is case-sensitive and must match exactly, including:
   - Protocol (`https://` not `http://`)
   - Domain name
   - Port (if any)
   - Path (`/api/qbo/oauth/callback`)
   - No trailing slash
3. Save the changes in the developer portal
4. Wait a few minutes for the changes to propagate
5. Try the OAuth flow again

#### 2. Client ID Doesn't Match

**What to check:**
The client ID hardcoded in the application must match the client ID in your QuickBooks app.

**Current client ID in code:**
```
AB224ne26KUlOjJebeDLMIwgIZcTRQkb6AieFqwJQg0sWCzXXA
```

**How to verify:**
1. Go to [developer.intuit.com](https://developer.intuit.com)
2. Open your app's dashboard
3. Go to "Keys & OAuth" or "Keys & credentials"
4. Compare the "Client ID" shown there with the value above

**How to fix if they don't match:**
The client ID is hardcoded in `main.py` at line ~1725. You need to update it to match your QBO app's client ID.

#### 3. Wrong Environment (Sandbox vs Production)

**What to check:**
Ensure your client credentials are from the same environment as your API endpoints.

**Current configuration:**
- Authorization endpoint: `https://appcenter.intuit.com/connect/oauth2`
- API endpoint: `https://sandbox-quickbooks.api.intuit.com/v3/company/`

This indicates the application is configured for **Sandbox** environment.

**How to verify:**
1. In the QuickBooks Developer Portal, check which environment your keys are from
2. Look for "Development" or "Production" keys
3. For Sandbox, use Development keys
4. For Production, use Production keys

**How to fix:**
- If using Sandbox: Ensure you're using Development keys from the developer portal
- If using Production: Update the API endpoint in the code to remove "sandbox-"

#### 4. Browser Popup Blocker

**What to check:**
The OAuth flow opens in a popup window. If popups are blocked, you won't see the login screen.

**How to fix:**
1. Check your browser's address bar for a popup blocked icon
2. Click it and allow popups for your domain
3. Try the OAuth flow again

**To test:**
1. Open your browser's console (F12)
2. Click "Connect to QuickBooks"
3. Look for messages about popup blockers

#### 5. Client Secret is Incorrect

**Symptoms:**
You might see the login screen, but the callback fails with a 401 error.

**What to check:**
The client secret must match the one in your QuickBooks app.

**Current client secret location:**
Hardcoded in `main.py` at line ~1726

**How to verify:**
1. Go to [developer.intuit.com](https://developer.intuit.com)
2. Open your app's dashboard
3. Go to "Keys & OAuth" or "Keys & credentials"
4. Compare the "Client Secret" (you may need to reveal it)

**How to fix:**
Update the client secret in `main.py` to match your QBO app.

#### 6. Refresh Token Expired (403 Forbidden Error)

**Symptoms:**
After connecting via OAuth, API calls fail with 403 Forbidden errors.

**Cause:**
Refresh tokens expire after 101 days. If you successfully connected but are still getting 403 errors, your old refresh token may have expired.

**How to fix:**
1. Navigate to `/qbo-settings-v2`
2. Click "Connect to QuickBooks" to start a new OAuth flow
3. Complete the authorization
4. This will get new access and refresh tokens

## Step-by-Step Diagnostic Process

### Step 1: View Diagnostics

1. Navigate to `/qbo-settings-v2` in your browser
2. Click "View OAuth Diagnostics"
3. Review the diagnostic information

### Step 2: Check Server Logs

When you click "Connect to QuickBooks", the server logs will show:
```
================================================================================
QuickBooks OAuth 2.0 Flow Initiated
================================================================================
Client ID: AB224ne26...
Redirect URI (unencoded): https://your-domain.com/api/qbo/oauth/callback
Redirect URI (encoded): https%3A%2F%2Fyour-domain.com%2Fapi%2Fqbo%2Foauth%2Fcallback
State Token: 12345678-1234-1234-1234-123456789012
Full Authorization URL: https://appcenter.intuit.com/connect/oauth2?...
================================================================================
```

Look for:
- The redirect URI being used
- The client ID being used
- Any error messages

### Step 3: Verify QuickBooks Developer Portal Settings

1. Log into [developer.intuit.com](https://developer.intuit.com)
2. Open your app
3. Go to "Keys & OAuth" or "Keys & credentials"
4. Verify:
   - ✅ Redirect URI is registered exactly as shown in logs
   - ✅ Client ID matches the one in logs
   - ✅ Client Secret is correct (compare with code)
   - ✅ App is in the correct environment (Sandbox/Production)
   - ✅ Scopes include `com.intuit.quickbooks.accounting`

### Step 4: Test the OAuth Flow

1. Click "Connect to QuickBooks"
2. Watch the browser:
   - Does a popup window open?
   - Do you see the QuickBooks login screen?
   - Do you see any error messages?
3. Check browser console (F12) for JavaScript errors
4. Check server logs for detailed OAuth flow information

### Step 5: If Still Not Working

If the above steps don't resolve the issue:

1. **Try in incognito/private mode** - Rules out browser cache/cookie issues
2. **Try a different browser** - Rules out browser-specific issues
3. **Check network tab** - Look for 4xx/5xx HTTP responses
4. **Verify SSL certificate** - Ensure your domain has a valid HTTPS certificate
5. **Contact support** - Provide:
   - Server logs from OAuth initiation
   - Browser console errors
   - Diagnostic output from `/api/qbo/oauth/diagnostic`

## Quick Reference Checklist

Use this checklist to verify your OAuth setup:

- [ ] Redirect URI is registered in QBO Developer Portal
- [ ] Redirect URI exactly matches (no typos, correct protocol, no trailing slash)
- [ ] Client ID in code matches QBO Developer Portal
- [ ] Client Secret in code matches QBO Developer Portal
- [ ] Using correct environment (Sandbox vs Production)
- [ ] Browser allows popups
- [ ] Domain has valid HTTPS certificate
- [ ] Scopes include `com.intuit.quickbooks.accounting`
- [ ] All server logs show expected values

## Additional Resources

- [Intuit OAuth 2.0 Documentation](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- [Common OAuth Errors](https://help.developer.intuit.com/s/article/Common-Authentication-and-Authorization-OAuth2-0-errors)
- [OAuth Discovery Document](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-openid-discovery-doc)

## Getting Help

If you need additional assistance:

1. **View the diagnostic page**: `/qbo-settings-v2` → Click "View OAuth Diagnostics"
2. **Check server logs**: Look for detailed OAuth flow information
3. **Enable debug logging**: Set log level to DEBUG for more details
4. **Test with OAuth Playground**: Use [Intuit's OAuth Playground](https://developer.intuit.com/app/developer/playground) to verify credentials work

## Common Error Messages and Fixes

### "Redirect URI mismatch"
- **Fix**: Ensure redirect URI in code exactly matches one registered in QBO app

### "Invalid client"
- **Fix**: Verify client ID and secret are correct and from the right environment

### "Access denied"
- **Fix**: User cancelled the authorization or doesn't have access to the company

### "Invalid grant"
- **Fix**: Authorization code was already used or expired; restart OAuth flow

### "403 Forbidden"
- **Fix**: Complete a new OAuth flow to get fresh tokens

### No popup window appears
- **Fix**: Allow popups in browser settings, disable popup blockers
