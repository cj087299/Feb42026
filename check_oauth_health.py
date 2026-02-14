#!/usr/bin/env python3
"""
QuickBooks OAuth Health Check Script

This script checks the health of your QuickBooks OAuth configuration
and helps diagnose common issues.

Usage:
    python check_oauth_health.py
"""

import sys
import os
import sqlite3
from datetime import datetime, timezone
import json

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def check_database_credentials():
    """Check if credentials exist in the database."""
    print_header("Database Credentials Check")
    
    db_path = 'vzt_accounting.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file not found at:", db_path)
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if qbo_tokens table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='qbo_tokens'
        """)
        
        if not cursor.fetchone():
            print("❌ qbo_tokens table does not exist in database")
            print("   Run the application once to initialize the database schema")
            conn.close()
            return False
        
        # Get credentials
        cursor.execute("""
            SELECT client_id, client_secret, refresh_token, realm_id,
                   access_token, access_token_expires_at, refresh_token_expires_at,
                   created_at, updated_at
            FROM qbo_tokens
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            print("❌ No credentials found in database")
            print("   Configure credentials via /qbo-settings or environment variables")
            return False
        
        client_id, client_secret, refresh_token, realm_id, access_token, \
            access_token_expires, refresh_token_expires, created_at, updated_at = row
        
        # Check for dummy values
        is_dummy = (client_id == 'dummy_id' or 
                   client_secret == 'dummy_secret' or 
                   refresh_token == 'dummy_refresh' or 
                   realm_id == 'dummy_realm')
        
        if is_dummy:
            print("❌ Credentials are using dummy/placeholder values")
            print("   Configure real credentials via /qbo-settings")
            return False
        
        print("✅ Credentials found in database")
        print(f"   Client ID: {client_id[:10]}...")
        print(f"   Realm ID: {realm_id}")
        print(f"   Has Access Token: {'Yes' if access_token else 'No'}")
        print(f"   Has Refresh Token: {'Yes' if refresh_token else 'No'}")
        
        # Check token expiration
        now = datetime.now(timezone.utc)
        
        if access_token_expires:
            try:
                # Try to parse ISO format
                expires = datetime.fromisoformat(access_token_expires.replace('Z', '+00:00'))
                if expires < now:
                    print(f"   ⚠️  Access token expired at: {access_token_expires}")
                else:
                    print(f"   ✅ Access token valid until: {access_token_expires}")
            except:
                print(f"   Access token expires: {access_token_expires}")
        
        if refresh_token_expires:
            try:
                expires = datetime.fromisoformat(refresh_token_expires.replace('Z', '+00:00'))
                if expires < now:
                    print(f"   ❌ Refresh token EXPIRED at: {refresh_token_expires}")
                    print(f"   ACTION REQUIRED: Reconnect to QuickBooks at /qbo-settings")
                    return False
                else:
                    print(f"   ✅ Refresh token valid until: {refresh_token_expires}")
            except:
                print(f"   Refresh token expires: {refresh_token_expires}")
        
        print(f"   Created: {created_at}")
        print(f"   Updated: {updated_at}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False

def check_environment_variables():
    """Check if OAuth credentials are set in environment variables."""
    print_header("Environment Variables Check")
    
    env_vars = {
        'QBO_CLIENT_ID': os.environ.get('QBO_CLIENT_ID'),
        'QBO_CLIENT_SECRET': os.environ.get('QBO_CLIENT_SECRET'),
        'QBO_REFRESH_TOKEN': os.environ.get('QBO_REFRESH_TOKEN'),
        'QBO_REALM_ID': os.environ.get('QBO_REALM_ID'),
        'GOOGLE_CLOUD_PROJECT': os.environ.get('GOOGLE_CLOUD_PROJECT'),
    }
    
    all_set = True
    for var, value in env_vars.items():
        if value:
            if 'SECRET' in var or 'TOKEN' in var:
                print(f"✅ {var}: ****** (set)")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")
            if var != 'GOOGLE_CLOUD_PROJECT':
                all_set = False
    
    if not all_set:
        print("\n⚠️  Some environment variables are not set")
        print("   This is OK if credentials are configured in the database")
    
    return True

def check_google_secret_manager():
    """Check if Google Secret Manager is available and has credentials."""
    print_header("Google Secret Manager Check")
    
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    
    if not project_id:
        print("⚠️  GOOGLE_CLOUD_PROJECT not set")
        print("   Skipping Secret Manager check")
        return True
    
    try:
        from google.cloud import secretmanager
        
        client = secretmanager.SecretManagerServiceClient()
        print(f"✅ Secret Manager client initialized")
        print(f"   Project: {project_id}")
        
        # Try to access secrets
        secrets = ['QBO_ID_2-3-26', 'QBO_Secret_2-3-26']
        for secret_name in secrets:
            try:
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                secret_value = response.payload.data.decode('UTF-8')
                print(f"✅ {secret_name}: Found (length: {len(secret_value)})")
            except Exception as e:
                print(f"❌ {secret_name}: Not found or error - {e}")
        
        return True
        
    except ImportError:
        print("⚠️  google-cloud-secret-manager not installed")
        print("   Install with: pip install google-cloud-secret-manager")
        return True
    except Exception as e:
        print(f"❌ Error accessing Secret Manager: {e}")
        return True

def print_recommendations():
    """Print recommendations based on the health check."""
    print_header("Recommendations")
    
    print("""
To resolve QuickBooks OAuth issues:

1. Configure Credentials via Web UI (Recommended):
   - Log in as admin/master_admin
   - Go to /qbo-settings
   - Click "Connect to QuickBooks"
   - Authorize your QuickBooks account

2. Manual Configuration:
   - Get credentials from QuickBooks Developer Portal
   - Enter them at /qbo-settings
   - Or set environment variables (see OAUTH_CREDENTIAL_SETUP_GUIDE.md)

3. Verify Connection:
   - Check status at /api/qbo/credentials
   - Try manual refresh at /api/qbo/refresh
   - Test by fetching invoices at /api/invoices

For detailed instructions, see: OAUTH_CREDENTIAL_SETUP_GUIDE.md
    """)

def main():
    """Run all health checks."""
    print("\n" + "🔍" * 30)
    print("  QuickBooks OAuth Health Check")
    print("🔍" * 30)
    
    # Run all checks
    db_ok = check_database_credentials()
    env_ok = check_environment_variables()
    sm_ok = check_google_secret_manager()
    
    # Summary
    print_header("Health Check Summary")
    
    if db_ok:
        print("✅ Database credentials: CONFIGURED AND VALID")
        print("   Your application should be working correctly.")
    else:
        print("❌ Database credentials: NOT CONFIGURED OR INVALID")
        print("   ACTION REQUIRED: Configure credentials to use QuickBooks features")
    
    print_recommendations()
    
    # Exit code
    sys.exit(0 if db_ok else 1)

if __name__ == '__main__':
    main()
