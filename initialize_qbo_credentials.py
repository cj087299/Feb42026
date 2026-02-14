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
    
    These credentials are from the QuickBooks OAuth 2.0 Playground
    and include valid access and refresh tokens.
    """
    
    print("=" * 70)
    print("  QuickBooks OAuth Credential Initialization")
    print("=" * 70)
    
    # Initialize database
    print("\n📦 Initializing database...")
    database = Database('vzt_accounting.db')
    print("✅ Database initialized")
    
    # OAuth credentials from QuickBooks OAuth 2.0 Playground
    credentials = {
        'client_id': 'AB224ne26KUlOjJebeDLMIwgIZcTRQkb6AieFqwJQg0sWCzXXA',
        'client_secret': '8LyYgJtmfo7znuWjilV5B3HUGzeiOmZ8hw0dt1Yl',
        'refresh_token': 'RT1-179-H0-1779755712nwk7zh3ezbzyx74bcywg',
        'access_token': 'eyJhbGciOiJkaXIiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2IiwieC5vcmciOiJIMCJ9..-QU4ZCiyr0tXb4DA76pICA.NhozMoPfnB4hKu59spusb5sBldEYe_AxrBTQe27Lm4m2zISmhYtTepfMjtw74Xtx_xJZZDGAXCtrXJeswd53JbKGpwH0G2tzri5tjUTdHF3fi0GSdlVwD9OS8DwczaUjKeoB77PeY8uSSNR4tAqHFlFlQgiWoR_WgxiOe7ypZFCRRb-YWs_g3lcHojGE6yFkh6_npU1NET5z-oJbM6yRoAghHAKtVHdrAh058QAN6jTgocr_O2N4nun0y4357GpC_hVEQhOYIs7rZToGzakAKGEjX9MKCWrqG9LgxaUdIf71suZ6No5BLBsNmXrtTlVL701irm1JWRy3LRa-6z5WxC57neJdC8tK_up2k0nLkiH1ZmfBqCu2LvkDDRs-5-LpFQS2az2KDbMneFmEkY_LNlZz8fnKEkZVp7A3Bby7U2ttkD5kXlY7zEG4MbW6IY1NW6dbsy13hqKKxI5-wY6uXfX_eeZTG9OVm4PWCnfB9_gORFEYQQa3pJ5-9jwcu1r07hB4BztiIVB1Ve2GBktuoLLdQKcDn712tBKtKYJGmf0iXKtkSoKnVOJrrfP-TmycyVMCuiUHg9M3GlBo8r5poeU_L54XQ0jinccIYGUDLIjV_gkmsbqqfJRQv4J9z35b.8xh1SjsgKxpIpD5LUD3B7A',
        'realm_id': '9341453050298464',
        'expires_in': 3600,  # Access token expires in 1 hour
        'x_refresh_token_expires_in': 8726400  # Refresh token expires in 101 days
    }
    
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
