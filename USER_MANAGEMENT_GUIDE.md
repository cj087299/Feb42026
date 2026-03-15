# User Management and Force Password Reset - Feature Summary

## Overview

This document describes the user management features available to administrators and master administrators in VZT Accounting, including the ability to force reset user passwords.

## User Management Features

### Access Control
- **Accessible To**: Admin and Master Admin roles only
- **URL**: `/users`
- **Permission Required**: `master_admin` role

### Available Functions

#### 1. View All Users
- Display table with all system users
- Shows:
  - Email address
  - Full name
  - Role (View Only, AP, AR, Admin, Master Admin)
  - Status (Active/Inactive)
  - Last login date
  - Action buttons

#### 2. Add New User
- Create new user accounts
- Required fields:
  - Email (must be unique)
  - Password (minimum requirements enforced)
  - Role
- Optional fields:
  - Full name
  - Active status (default: Active)

#### 3. Edit User
- Modify user information
- Can update:
  - Email
  - Full name
  - Role
  - Active status
- Password can be changed but not required

#### 4. Delete User
- Remove users from the system
- Confirmation required
- Cannot delete your own account
- All actions logged in audit log

#### 5. **Force Reset Password** (NEW)
- Administrators can immediately reset any user's password
- Features:
  - Set custom password or generate secure random password
  - Optional email notification to user
  - Instant password change
  - Audit logging

## Force Password Reset Feature

### How It Works

1. **Admin Action**:
   - Navigate to User Management page
   - Click "Reset Password" button for target user
   - Modal opens with password reset form

2. **Password Options**:
   - **Manual Entry**: Type a new password
   - **Generate Secure Password**: Click link to auto-generate
     - 12 characters long
     - Includes uppercase, lowercase, numbers, and symbols
     - Uses cryptographically secure randomization
   - Password visibility toggle for verification

3. **Email Notification**:
   - Optional checkbox to send email to user
   - If enabled, user receives:
     - Professional HTML email
     - New temporary password displayed clearly
     - Security instructions
     - Link to login
     - Warning about administrator reset

4. **Immediate Effect**:
   - Password changed instantly
   - Old password no longer works
   - User must use new password to login
   - Action logged in audit log

### API Endpoint

```
POST /api/users/{user_id}/force-reset-password
```

**Request Body**:
```json
{
  "password": "new_password_here",
  "send_email": true
}
```

**Response** (Success):
```json
{
  "message": "Password reset successfully",
  "email_sent": true
}
```

**Response** (Error):
```json
{
  "error": "Error message here"
}
```

### Security Features

1. **Role-Based Access**:
   - Only admin and master_admin can use this feature
   - Regular users cannot access endpoint
   - Permission checked on every request

2. **Secure Password Generation**:
   - Uses `crypto.getRandomValues()` for cryptographic randomness
   - Fisher-Yates shuffle algorithm for secure mixing
   - Guarantees character diversity (uppercase, lowercase, numbers, symbols)

3. **Password Hashing**:
   - Passwords hashed using SHA-256 with salt
   - Never stored in plain text
   - Same hashing as regular password changes

4. **Audit Logging**:
   - All password resets logged
   - Records:
     - Admin user who performed reset
     - Target user
     - Timestamp
     - IP address
     - User agent

5. **Email Notification**:
   - User immediately informed of change
   - Security checklist included
   - Temporary password clearly marked
   - Instructions to change password

### Email Notification Template

When email notification is enabled, the user receives:

**Subject**: Password Reset by Administrator - VZT Accounting

**Content**:
- Clear header: "Password Reset by Administrator"
- Personalized greeting with full name
- Temporary password in highlighted box
- Security checklist:
  1. Log in with temporary password
  2. Change password immediately
  3. Don't share password
  4. Contact admin if unexpected
- Direct login link
- Warning about administrator action

### Use Cases

#### 1. User Forgot Password
- Admin can quickly reset without waiting for email token
- Faster than standard password reset flow
- Can communicate new password directly

#### 2. Security Incident
- Immediate password change for compromised accounts
- Admin can enforce new password instantly
- Email notification alerts user

#### 3. New Employee Setup
- Admin can set initial password
- Send via email or communicate securely
- User changes on first login

#### 4. Password Policy Enforcement
- Force users to change weak passwords
- Implement password rotation policy
- Ensure compliance

### Best Practices

#### For Administrators

1. **Use Secure Passwords**:
   - Always use the password generator
   - Don't reuse passwords
   - Don't use simple patterns

2. **Enable Email Notification**:
   - User should always be informed
   - Prevents unauthorized access
   - Creates audit trail

3. **Document Reason**:
   - Note why password was reset
   - Keep record of security incidents
   - Reference audit log entry

4. **Verify User Identity**:
   - Confirm user request via phone/video
   - Don't reset based on email alone
   - Prevent social engineering

#### For Users

1. **Change Password Immediately**:
   - Don't keep temporary password
   - Use strong, unique password
   - Enable password manager

2. **Report Unexpected Resets**:
   - Contact administrator if not requested
   - May indicate security breach
   - Check audit log

3. **Secure Communication**:
   - Don't share temporary password
   - Delete notification email after use
   - Use secure channels only

## Audit Log Integration

All password reset actions are logged:

**Action**: `force_reset_password`  
**Resource Type**: `user`  
**Resource ID**: Target user ID  
**Details**: "Force reset password for {email}"  
**Timestamp**: Exact time of reset  
**Admin User**: Who performed reset  
**IP Address**: Admin's IP  
**User Agent**: Admin's browser

### Viewing Audit Logs

1. Navigate to Audit Log page
2. Filter by action: `force_reset_password`
3. Filter by resource type: `user`
4. Filter by specific user if needed

## Testing the Feature

### Manual Testing Steps

1. Log in as admin or master admin
2. Go to User Management page (`/users`)
3. Locate test user in table
4. Click "Reset Password" button
5. In modal:
   - Enter new password or click "generate secure password"
   - Check/uncheck email notification
   - Verify password visibility toggle works
6. Click "Reset Password" button
7. Confirm success message
8. Verify:
   - User can login with new password
   - Old password doesn't work
   - Email sent if enabled
   - Audit log entry created

### Automated Testing

```python
# Test force password reset
response = client.post(
    f'/api/users/{user_id}/force-reset-password',
    data=json.dumps({
        'password': 'NewPassword123!',
        'send_email': False
    }),
    content_type='application/json'
)

assert response.status_code == 200
assert response.get_json()['message'] == 'Password reset successfully'
```

## Troubleshooting

### Password Reset Fails

**Symptoms**: API returns error  
**Possible Causes**:
- Not logged in as admin/master_admin
- Invalid user ID
- Database connection issue
- Password validation failed

**Solution**:
- Check user role in session
- Verify user exists
- Check database connection
- Review error message

### Email Not Sent

**Symptoms**: Password reset succeeds but no email  
**Possible Causes**:
- Email service disabled
- Invalid SMTP configuration
- User email address invalid
- Email provider blocking

**Solution**:
- Check email configuration
- Verify SMTP credentials
- Test email service
- Review email service logs

### Cannot Access Feature

**Symptoms**: User management page not accessible  
**Possible Causes**:
- Insufficient permissions
- Not logged in
- Session expired

**Solution**:
- Verify user has admin or master_admin role
- Re-login if needed
- Check session validity

## Security Considerations

1. **Access Control**: Feature restricted to administrators only
2. **Audit Trail**: All actions logged with full details
3. **User Notification**: Users informed of password changes
4. **Secure Generation**: Cryptographically secure random passwords
5. **Password Hashing**: All passwords hashed before storage
6. **No Plain Text**: Passwords never stored or transmitted in plain text

## Related Documentation

- `EMAIL_CONFIGURATION.md` - Email setup for notifications
- `README.md` - User roles and permissions
- Audit log feature - View all password resets
- User authentication system - Password hashing details
