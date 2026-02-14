# QuickBooks Settings Page v2

## Overview

This document describes the new QuickBooks Settings Page v2, which provides a simplified OAuth flow for connecting to QuickBooks Online.

## What Changed

The v2 page addresses issues with the original QBO settings page where users were experiencing redirect loops when entering credentials. The new implementation:

1. **Simplifies the UI** - Single "Connect to QuickBooks" button instead of multiple form fields
2. **Hardcodes Credentials** - OAuth Client ID and Secret are pre-configured in the backend
3. **Streamlined Flow** - Users only need to authorize access via QuickBooks login, no manual credential entry

## Architecture

### Frontend (`templates/qbo_settings_v2.html`)

The new template provides:
- Clean, modern UI with connection status display
- Single "Connect to QuickBooks" button
- Real-time status updates showing connection state
- OAuth popup window handling
- Success/error message handling

### Backend Routes

#### `GET /qbo-settings-v2`
- Serves the new settings page v2
- Requires login and admin/master_admin role

#### `POST /api/qbo/oauth/authorize-v2`
- Initiates OAuth flow with hardcoded credentials
- Credentials used:
  - Client ID: `AB224ne26KUlOjJebeDLMIwgIZcTRQkb6AieFqwJQg0sWCzXXA`
  - Client Secret: `8LyYgJtmfo7znuWjilV5B3HUGzeiOmZ8hw0dt1Yl`
- Generates authorization URL and CSRF state token
- Stores credentials in session for callback processing

#### `GET /api/qbo/oauth/callback` (Existing)
- Handles OAuth callback from QuickBooks
- Exchanges authorization code for access and refresh tokens
- Saves tokens to database
- Renders success/error callback page

## User Flow

1. Admin navigates to `/qbo-settings-v2`
2. Page loads and displays current connection status
3. User clicks "Connect to QuickBooks" button
4. Backend generates OAuth authorization URL with hardcoded credentials
5. Popup window opens showing QuickBooks login page
6. User logs in with their QuickBooks credentials and authorizes access
7. QuickBooks redirects to callback URL with authorization code
8. Backend exchanges code for tokens and saves to database
9. Callback page notifies parent window of success
10. Popup closes automatically
11. Main page refreshes connection status

## Security

- OAuth state parameter prevents CSRF attacks
- Credentials stored in session are cleared after successful callback
- All endpoints require authentication
- Only admin and master_admin roles can access settings

## Advantages Over v1

1. **No User Input Required** - Eliminates form validation issues
2. **No Redirect Loops** - Simplified flow prevents navigation issues
3. **Faster Setup** - One-click connection process
4. **Better UX** - Clear status indicators and error messages
5. **Consistent Experience** - Uses standard OAuth popup flow

## Migration Notes

- The original `/qbo-settings` page remains available
- Both pages use the same OAuth callback handler
- Credentials saved via v2 work with the entire application
- No database schema changes required

## Testing

To test the v2 page:

1. Ensure you have admin or master_admin role
2. Navigate to `/qbo-settings-v2`
3. Click "Connect to QuickBooks"
4. Authorize in the popup window
5. Verify connection status updates on success

## Troubleshooting

### Popup Blocked
- Enable popups for the application domain
- Try clicking the button again after enabling popups

### OAuth Errors
- Verify the redirect URI matches QuickBooks app settings
- Check that Client ID and Secret are valid
- Review server logs for detailed error messages

### Token Refresh
- If access token expires, it will be automatically refreshed
- Refresh token is valid for 101 days
- User will need to reconnect after refresh token expires
