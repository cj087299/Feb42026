# OAuth Popup Window Implementation

## Overview

Implemented a modern OAuth flow using a popup window instead of full-page redirects. This provides a better user experience by:
- Keeping the settings page context visible
- Opening QuickBooks login in a separate window
- Automatically closing the popup after authorization
- Refreshing credentials status without page reload

## User Experience

### Flow

1. **User clicks "Connect to QuickBooks" button**
   - Popup window opens (600x700px, centered)
   - Parent page remains visible in background

2. **User enters QBO credentials in popup**
   - Username: `cjones@vzsolutions.com`
   - Password: (entered directly in QBO popup)
   - User authorizes the app

3. **Popup auto-closes after success**
   - Shows "Authorization Successful!" message
   - Closes after 2 seconds
   - Parent page receives success notification

4. **Parent page updates automatically**
   - Shows success message
   - Reloads credential status
   - Displays updated connection info

## Implementation Details

### Frontend Changes

#### 1. QBO Settings Page (`templates/qbo_settings.html`)

**Button Click Handler** - Opens popup:
```javascript
async function initiateOAuth() {
    // ... validate inputs ...
    
    // Get authorization URL from backend
    const response = await fetch('/api/qbo/oauth/authorize', {
        method: 'POST',
        body: JSON.stringify({ client_id, client_secret, redirect_uri })
    });
    
    const data = await response.json();
    
    // Open popup window (centered)
    const width = 600, height = 700;
    const left = (screen.width / 2) - (width / 2);
    const top = (screen.height / 2) - (height / 2);
    
    const popup = window.open(
        data.authorization_url,
        'QuickBooks Authorization',
        `width=${width},height=${height},left=${left},top=${top}`
    );
}
```

**Message Listener** - Receives popup notifications:
```javascript
window.addEventListener('message', function oauthCallback(event) {
    // Verify origin for security
    if (event.origin !== window.location.origin) return;
    
    if (event.data.type === 'qbo_oauth_success') {
        showAlert('Successfully connected!', 'success');
        loadStatus(); // Refresh credentials display
    } else if (event.data.type === 'qbo_oauth_error') {
        showAlert(event.data.message, 'error');
    }
});
```

#### 2. OAuth Callback Page (`templates/oauth_callback.html`)

**Success Flow**:
```javascript
if (success) {
    // Notify parent window
    if (window.opener) {
        window.opener.postMessage({
            type: 'qbo_oauth_success'
        }, window.location.origin);
    }
    
    // Auto-close after 2 seconds
    setTimeout(() => window.close(), 2000);
}
```

**Error Flow**:
```javascript
if (error) {
    // Notify parent with error message
    if (window.opener) {
        window.opener.postMessage({
            type: 'qbo_oauth_error',
            message: error
        }, window.location.origin);
    }
    
    // Auto-close after 5 seconds
    setTimeout(() => window.close(), 5000);
}
```

### Backend Changes

#### OAuth Callback Handler (`main.py`)

**Before** (Full-page redirect):
```python
return redirect(url_for('qbo_settings_page') + '?oauth_success=true')
```

**After** (Popup template):
```python
return render_template('oauth_callback.html', success='true')
```

**Error Handling** - All errors use template:
```python
try:
    # ... token exchange ...
except Exception as e:
    return render_template('oauth_callback.html', error=str(e))
```

## Security Features

### 1. Origin Verification
```javascript
if (event.origin !== window.location.origin) {
    return; // Ignore messages from other domains
}
```

### 2. CSRF Protection (Unchanged)
- State token still validated in callback
- Session-based credential storage
- Admin/master_admin role enforcement

### 3. Popup Blocker Handling
```javascript
if (!popup) {
    showAlert('Please allow popups for this site', 'error');
    return;
}
```

## User Interface

### Popup Window
- **Size**: 600px × 700px
- **Position**: Centered on screen
- **Features**: Resizable, scrollbars enabled
- **Title**: "QuickBooks Authorization"

### Status Messages

**Success**:
```
✓ Authorization Successful!
Your QuickBooks account has been connected successfully.
This window will close automatically.
```

**Error**:
```
✗ Authorization Failed
[Error message from QBO or server]
You can close this window and try again.
```

## Browser Compatibility

- ✅ Modern browsers (Chrome, Firefox, Safari, Edge)
- ✅ `window.open()` popup support required
- ✅ `postMessage` API for cross-window communication
- ⚠️ Popup blockers may prevent opening (user notification shown)

## Testing Checklist

- [ ] Click "Connect to QuickBooks" button
- [ ] Popup opens centered on screen
- [ ] Enter QBO credentials in popup
- [ ] Authorize the application
- [ ] Popup shows success message
- [ ] Popup closes automatically
- [ ] Parent page shows success alert
- [ ] Credentials status refreshes
- [ ] Test with popup blocker enabled
- [ ] Test error scenarios (invalid credentials, network error)

## Access Control

**Who can use this feature?**
- ✅ Admin users (`role = 'admin'`)
- ✅ Master Admin users (`role = 'master_admin'`)
- ❌ Other roles (view_only, ap, ar)

**Enforcement**:
```python
@login_required
def qbo_oauth_callback():
    user_role = session.get('user_role')
    if user_role not in ['admin', 'master_admin']:
        return render_template('oauth_callback.html', 
                             error='Permission denied')
```

## Benefits Over Full-Page Redirect

1. **Context Preservation**: Settings page remains visible
2. **Better UX**: Clear separation of OAuth flow
3. **Faster Feedback**: No page reload on parent
4. **Modern Pattern**: Common in SaaS applications
5. **Error Recovery**: Easy to retry without losing form data

## Files Changed

1. `templates/qbo_settings.html` - Popup initiation
2. `templates/oauth_callback.html` - New popup callback page
3. `main.py` - Updated callback handler

## Related Documentation

- `QBO_OAUTH_FLOW.md` - Overall OAuth flow
- `QBO_AUTHENTICATION_SETUP.md` - Initial setup guide
- `USER_MANAGEMENT_GUIDE.md` - Role-based access control
