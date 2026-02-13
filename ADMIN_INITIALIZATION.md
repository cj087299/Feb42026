# Admin User Initialization Guide

## Overview

The VZT Accounting application automatically initializes admin users when the server starts. This eliminates the need to manually run initialization scripts after deployment, especially important for Cloud Run deployments where you don't have direct terminal access.

## Automatic Initialization

### How It Works

When the application starts (e.g., when `main.py` runs), it automatically:

1. **Checks for existing admin users** in the database
2. **Creates missing admin users** if they don't exist
3. **Logs the initialization process** for transparency
4. **Is completely idempotent** - safe to restart the server multiple times

### Default Admin Credentials

Two master admin users are automatically created on first startup:

**User 1:**
- **Email**: `admin@vzt.com`
- **Password**: `admin1234`
- **Role**: Master Admin
- **Full Name**: Admin

**User 2:**
- **Email**: `cjones@vztsolutions.com`
- **Password**: `admin1234`
- **Role**: Master Admin
- **Full Name**: CJones

### ⚠️ Security Warning

**IMPORTANT**: The default password `admin1234` is intentionally simple for initial setup. You **MUST** change these passwords immediately after first login!

## Cloud Run Deployment

### Why Automatic Initialization Matters

On Cloud Run:
- You don't have persistent terminal access after deployment
- The server starts automatically when the container is deployed
- Admin users are created immediately, allowing you to log in right away
- No need to worry about running initialization scripts

### Deployment Flow

1. **Deploy to Cloud Run** (via Cloud Build or gcloud CLI)
2. **Server starts automatically**
3. **Admin users are initialized** (on first run only)
4. **Log in immediately** using default credentials
5. **Change your passwords** through the UI

### Viewing Initialization Logs

On Cloud Run, you can view the initialization logs:

```bash
# View logs in Cloud Console
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=YOUR_SERVICE_NAME" --limit 50

# Or use Cloud Shell to view logs for your deployed service
gcloud run logs read YOUR_SERVICE_NAME --region=YOUR_REGION
```

Replace `YOUR_SERVICE_NAME` with your actual Cloud Run service name (e.g., `vzt-accounting`) and `YOUR_REGION` with your deployment region (e.g., `us-central1`).

Look for log entries like:
```
INFO:__main__:Checking for admin users...
INFO:__main__:✓ Admin user created: admin@vzt.com
INFO:__main__:✓ Admin user created: cjones@vztsolutions.com
WARNING:__main__:Admin users initialized with default passwords!
WARNING:__main__:⚠️  IMPORTANT: Change these passwords immediately after first login!
```

On subsequent restarts, you'll see:
```
INFO:__main__:Checking for admin users...
INFO:__main__:Admin user cjones@vztsolutions.com already exists. Skipping.
INFO:__main__:Admin user admin@vzt.com already exists. Skipping.
INFO:__main__:Admin users already initialized.
```

## Local Development

### Starting the Application

```bash
# Navigate to project directory
cd /path/to/Feb42026

# Install dependencies
pip install -r requirements.txt

# Start the server
python main.py
```

The admin users will be automatically created on first startup.

### Database Location

- **SQLite** (default): `vzt_accounting.db` in the project root
- **Cloud SQL** (production): Configured via environment variables

## Manual Initialization (Optional)

If you need to manually create or recreate admin users:

```bash
python init_admin.py
```

This script:
- Uses the same logic as automatic initialization
- Checks if users exist before creating them
- Can be run multiple times safely (idempotent)
- Useful for resetting to defaults if needed

## Troubleshooting

### Can't Log In After Deployment

**Problem**: Login fails with "Invalid email or password"

**Solutions**:
1. **Check the logs** to verify admin users were created
2. **Ensure you're using the correct credentials**:
   - `admin@vzt.com` / `admin1234`
   - `cjones@vztsolutions.com` / `admin1234`
3. **Check database connectivity** - ensure the database is accessible
4. **Verify email format** - no extra spaces or typos

### Admin Users Not Created

**Problem**: Logs show errors during initialization

**Possible Causes**:
- Database connection failure
- Database schema not initialized
- Insufficient permissions

**Solutions**:
1. Check database environment variables
2. Ensure database schema is created (happens automatically)
3. Review full error logs for details
4. Run `python init_admin.py` manually to see detailed error messages

### Password Changed But Can't Remember It

**Problem**: Changed password but forgot what you set

**Solutions**:
1. Use the "Forgot Password" link on the login page
2. Have another admin reset your password (if available)
3. As a last resort, manually run `init_admin.py` to reset to defaults:
   ```bash
   # First, delete the existing user from database
   # Then run init_admin.py to recreate with default password
   python init_admin.py
   ```

### Multiple Users Created Accidentally

**Problem**: Duplicate users or unexpected users in database

**Explanation**: This shouldn't happen due to idempotent checks, but if it does:

**Solution**:
1. Log in as a master admin
2. Go to User Management (`/users`)
3. Delete duplicate or unwanted users
4. The system prevents deleting your own account

## Database Queries

If you need to manually check the database (advanced users only):

### SQLite (Local)
```bash
# Open database
sqlite3 vzt_accounting.db

# List all users
SELECT email, role, is_active, created_at FROM users;

# Check specific user
SELECT * FROM users WHERE email = 'admin@vzt.com';

# Exit
.quit
```

### Cloud SQL (Production)
```bash
# Connect to Cloud SQL
gcloud sql connect companydatabase2-4-26 --user=root

# Use database
USE accounting_app;

# List all users
SELECT email, role, is_active, created_at FROM users;

# Exit
EXIT;
```

## Security Best Practices

1. **Change Default Passwords Immediately**
   - Log in with default credentials
   - Go to your profile or settings
   - Change to a strong, unique password

2. **Use Strong Passwords**
   - Minimum 12 characters
   - Mix of uppercase, lowercase, numbers, and symbols
   - Don't reuse passwords from other accounts
   - Consider using a password manager

3. **Review User Access Regularly**
   - Check the User Management page
   - Remove accounts for former employees
   - Verify roles are appropriate
   - Monitor the audit log for suspicious activity

4. **Enable Email Notifications**
   - Configure SMTP settings (see `EMAIL_CONFIGURATION.md`)
   - Receive alerts for password changes
   - Get notifications for important events

5. **Monitor Audit Logs**
   - Review login attempts regularly
   - Check for unauthorized access attempts
   - Investigate unusual activity patterns

## Related Documentation

- **README.md** - Main application documentation
- **USER_MANAGEMENT_GUIDE.md** - Detailed user management features
- **LOGIN_FIX_SUMMARY.md** - Historical context for login fixes
- **EMAIL_CONFIGURATION.md** - Email setup for password reset
- **QBO_AUTHENTICATION_SETUP.md** - QuickBooks integration

## Summary

✅ **Admin users initialize automatically** - No manual steps required  
✅ **Works on Cloud Run** - Immediate access after deployment  
✅ **Safe to restart** - Idempotent initialization won't duplicate users  
✅ **Secure by design** - Default passwords must be changed  
✅ **Transparent** - Full logging of initialization process  

You can start using the application immediately after deployment by logging in with the default credentials, then changing your password through the web interface.
