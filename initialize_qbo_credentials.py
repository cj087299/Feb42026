#!/usr/bin/env python3
"""
Initialize QuickBooks OAuth Credentials in Database

This script populates the database with valid OAuth credentials
from the QuickBooks OAuth 2.0 playground.

Usage:
    python3 initialize_qbo_credentials.py
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import Database

def initialize_credentials():
    """
    Initialize the database with valid QuickBooks OAuth credentials.
    
    Credentials can be provided in two ways:
    1. Edit this script and replace the placeholder values (not recommended for production)
    2. Set environment variables (recommended for production):
       - QBO_INIT_CLIENT_ID
       - QBO_INIT_CLIENT_SECRET
       - QBO_INIT_REFRESH_TOKEN
       - QBO_INIT_ACCESS_TOKEN
       - QBO_INIT_REALM_ID
    """
    
    print("=" * 70)
    print("  QuickBooks OAuth Credential Initialization")
    print("=" * 70)
    
    # Initialize database
    print("\n📦 Initializing database...")
    database = Database('vzt_accounting.db')
    print("✅ Database initialized")
    
    # OAuth credentials - check environment variables first, then fall back to hardcoded values
    credentials = {
        'client_id': os.environ.get('QBO_INIT_CLIENT_ID', 'YOUR_CLIENT_ID_HERE'),
        'client_secret': os.environ.get('QBO_INIT_CLIENT_SECRET', 'YOUR_CLIENT_SECRET_HERE'),
        'refresh_token': os.environ.get('QBO_INIT_REFRESH_TOKEN', 'YOUR_REFRESH_TOKEN_HERE'),
        'access_token': os.environ.get('QBO_INIT_ACCESS_TOKEN', 'YOUR_ACCESS_TOKEN_HERE'),
        'realm_id': os.environ.get('QBO_INIT_REALM_ID', 'YOUR_REALM_ID_HERE'),
        'expires_in': 3600,  # Access token expires in 1 hour
        'x_refresh_token_expires_in': 8726400  # Refresh token expires in 101 days
    }
    
    # Check if placeholders are still present
    if any('YOUR_' in str(v) and '_HERE' in str(v) for v in credentials.values()):
        print("\n❌ ERROR: Placeholder values detected!")
        print("\nYou must provide your actual credentials using one of these methods:")
        print("\n1. Environment Variables (Recommended):")
        print("   export QBO_INIT_CLIENT_ID='your_client_id'")
        print("   export QBO_INIT_CLIENT_SECRET='your_client_secret'")
        print("   export QBO_INIT_REFRESH_TOKEN='your_refresh_token'")
        print("   export QBO_INIT_ACCESS_TOKEN='your_access_token'")
        print("   export QBO_INIT_REALM_ID='your_realm_id'")
        print("\n2. Edit Script (Not recommended for production):")
        print("   Edit initialize_qbo_credentials.py and replace the placeholders")
        print("\nGet credentials from: https://developer.intuit.com/app/developer/playground")
        return 1
    
    print("\n🔑 Saving OAuth credentials to database...")
    print(f"   Client ID: {credentials['client_id'][:20]}...")
    print(f"   Client Secret: {'*' * 40}")
    print(f"   Refresh Token: {credentials['refresh_token'][:20]}...")
    print(f"   Access Token: {credentials['access_token'][:50]}...")
    print(f"   Realm ID: {credentials['realm_id']}")
    
    # Calculate expiration times
    now = datetime.now()
    access_expires = now + timedelta(seconds=credentials['expires_in'])
    refresh_expires = now + timedelta(seconds=credentials['x_refresh_token_expires_in'])
    
    print(f"\n⏰ Token Expiration:")
    print(f"   Access token expires: {access_expires.strftime('%Y-%m-%d %H:%M:%S')} ({credentials['expires_in']} seconds)")
    print(f"   Refresh token expires: {refresh_expires.strftime('%Y-%m-%d %H:%M:%S')} (~{credentials['x_refresh_token_expires_in'] // 86400} days)")
    
    # Save credentials to database
    success = database.save_qbo_credentials(credentials)
    
    if success:
        print("\n✅ SUCCESS! OAuth credentials saved to database")
        print("\nThe application will now use these credentials for QuickBooks API calls.")
        print("These credentials will take priority over Secret Manager and environment variables.")
        
        # Verify credentials were saved
        print("\n🔍 Verifying credentials in database...")
        saved_creds = database.get_qbo_credentials()
        
        if saved_creds:
            print("✅ Credentials verified in database:")
            print(f"   Client ID: {saved_creds['client_id'][:20]}...")
            print(f"   Realm ID: {saved_creds['realm_id']}")
            print(f"   Has Access Token: {bool(saved_creds.get('access_token'))}")
            print(f"   Has Refresh Token: {bool(saved_creds.get('refresh_token'))}")
            print(f"   Access Token Expires: {saved_creds.get('access_token_expires_at')}")
            print(f"   Refresh Token Expires: {saved_creds.get('refresh_token_expires_at')}")
            
            print("\n" + "=" * 70)
            print("  ✨ Setup Complete!")
            print("=" * 70)
            print("\nNext steps:")
            print("1. Restart your application (if running)")
            print("2. The application will automatically use these credentials")
            print("3. Access tokens will refresh automatically when needed")
            print("4. Refresh token is valid for 101 days")
            print("\nTo check credential status:")
            print("  • Run: python3 check_oauth_health.py")
            print("  • Or visit: /api/qbo/credentials (requires login)")
            
            return 0
        else:
            print("❌ ERROR: Could not verify credentials in database")
            return 1
    else:
        print("\n❌ ERROR: Failed to save credentials to database")
        print("Check the error messages above for details.")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(initialize_credentials())
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
