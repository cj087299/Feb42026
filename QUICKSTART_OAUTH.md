# QuickBooks OAuth Setup Guide (Quick Start)

## What This Does

One admin user connects to QuickBooks Online using their QBO username and password. All users in the system can then access QuickBooks data for **101 days** without additional logins.

## Step-by-Step Setup

### Before You Start

Get your QuickBooks OAuth credentials:
1. Go to https://developer.intuit.com/
2. Log in and select your app
3. Go to "Keys & OAuth" or "Keys & credentials"
4. Copy your **Client ID** and **Client Secret**
5. Add this redirect URI to your app:
   ```
   https://your-domain.com/api/qbo/oauth/callback
   ```
   (or `http://localhost:8080/api/qbo/oauth/callback` for local testing)

### Setup Process

#### 1. Login as Admin

Navigate to your VZT Accounting application and log in with an admin or master_admin account:
- Email: `admin@vzt.com` or `cjones@vztsolutions.com`
- Password: `admin1234` (change this after first login!)

#### 2. Go to QBO Settings

Click on "QBO Settings" from the navigation menu or go to:
```
https://your-domain.com/qbo-settings
```

#### 3. Enter Your Credentials

In the "Connect to QuickBooks Online" section, enter:

- **Client ID**: Paste your Client ID from Intuit Developer Portal
- **Client Secret**: Paste your Client Secret
- **Redirect URI**: Auto-filled (should be `https://your-domain.com/api/qbo/oauth/callback`)

#### 4. Connect to QuickBooks

Click the **"🔐 Connect to QuickBooks"** button.

You'll be redirected to QuickBooks Online.

#### 5. Log Into QuickBooks

On the QuickBooks login page:
1. Enter your QuickBooks Online **username**
2. Enter your QuickBooks Online **password**
3. Click "Sign In"

#### 6. Authorize the App

QuickBooks will show an authorization screen:
1. Review the permissions requested
2. Select the QuickBooks company you want to connect
3. Click "Authorize" or "Connect"

#### 7. Done!

You'll be automatically redirected back to the QBO Settings page with a success message:
```
✓ Successfully connected to QuickBooks Online!
```

### What Happens Behind the Scenes

1. Your browser is redirected to QuickBooks with a unique security token
2. You log in with your QBO username and password
3. QuickBooks sends back an authorization code
4. The app exchanges this code for tokens (access token + refresh token)
5. Tokens are saved to the database with expiration times
6. All users can now use QuickBooks features

### Token Information

- **Access Token**: Expires in 1 hour, automatically refreshed
- **Refresh Token**: Expires in 101 days
- **Storage**: Centralized database, shared by all users
- **Security**: Only admins can configure, all changes logged

## After Setup

### For Admin Users

- Check token status anytime at `/qbo-settings`
- See expiration dates and times
- Manually refresh tokens if needed
- View audit logs at `/audit`

### For All Users

- Access invoices at `/invoices`
- View cash flow at `/cashflow`
- Use AI chat features
- No additional setup required!

### Token Status Indicators

In QBO Settings, you'll see:

- ✅ **Active** (green): Token is valid
- ⚠️ **Expiring Soon** (yellow): Renew within 24 hours
- ❌ **Expired** (red): Click "Refresh Access Token" or reconnect

## Maintenance

### Every 3 Months (Before 101 Days)

To renew the refresh token:
1. Go to QBO Settings
2. Click "🔐 Connect to QuickBooks" again
3. Log in with your QBO credentials
4. Authorize again
5. Done! Another 101 days of access

### Alternative: Manual Token Entry

If you already have tokens, you can skip OAuth and enter them manually:
1. Scroll to "Manual Credentials Entry" section
2. Enter Client ID, Client Secret, Refresh Token, and Realm ID
3. Click "Save Credentials"

## Troubleshooting

### "Invalid Redirect URI"

**Problem**: The redirect URI doesn't match what's in your QuickBooks app settings

**Solution**: 
- Check your redirect URI in QBO Settings matches exactly
- Update it in Intuit Developer Portal if needed
- Include protocol (http:// or https://) and port if applicable

### "Invalid State Parameter"

**Problem**: Security token mismatch (CSRF protection)

**Solution**:
- Clear browser cookies and cache
- Try the OAuth flow again
- Ensure cookies are enabled

### "401 Unauthorized"

**Problem**: Invalid Client ID or Client Secret

**Solution**:
- Double-check credentials in Intuit Developer Portal
- Ensure you're using Production credentials for production app
- Copy/paste carefully to avoid extra spaces

### Connection Expired

After 101 days, the refresh token expires. Simply reconnect:
1. Go to QBO Settings
2. Click "Connect to QuickBooks"
3. Log in again
4. Get another 101 days!

## Security Notes

- ✅ Client Secret is never exposed in the UI
- ✅ Tokens are encrypted in the database
- ✅ All OAuth actions are logged in audit trail
- ✅ Only admins can configure credentials
- ✅ CSRF protection prevents unauthorized access
- ✅ Session data cleared after token exchange

## Need Help?

1. **Documentation**: 
   - `QBO_OAUTH_FLOW.md` - Detailed OAuth guide
   - `QBO_TOKEN_MANAGEMENT.md` - Token management
   - `OAUTH_IMPLEMENTATION_SUMMARY.md` - Technical details

2. **Logs**: 
   - Application logs for errors
   - Audit logs at `/audit` for OAuth actions

3. **Support**:
   - Check QuickBooks Developer Portal
   - Review OAuth 2.0 documentation
   - Contact your system administrator

## Summary

✅ One-time setup by admin
✅ All users benefit for 101 days
✅ Secure OAuth 2.0 flow
✅ Automatic token refresh
✅ No coding required
✅ User-friendly interface

Connect once, use for 101 days! 🎉
