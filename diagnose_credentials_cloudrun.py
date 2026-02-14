#!/usr/bin/env python3
"""
Credential Diagnostic Script for Cloud Run

This script helps diagnose OAuth credential issues in Cloud Run.
It checks what credentials are available and from which source.

Run this in your Cloud Run environment to see exactly what credentials
the application is finding.
"""

import os
import sys

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def main():
    print("🔍 QuickBooks OAuth Credential Diagnostic for Cloud Run")
    print("=" * 70)
    
    # Check environment
    print_section("Environment Check")
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    print(f"GOOGLE_CLOUD_PROJECT: {project_id or 'NOT SET'}")
    print(f"QBO_CLIENT_ID env var: {'SET' if os.environ.get('QBO_CLIENT_ID') else 'NOT SET'}")
    print(f"QBO_CLIENT_SECRET env var: {'SET' if os.environ.get('QBO_CLIENT_SECRET') else 'NOT SET'}")
    print(f"QBO_REFRESH_TOKEN env var: {'SET' if os.environ.get('QBO_REFRESH_TOKEN') else 'NOT SET'}")
    print(f"QBO_REALM_ID env var: {'SET' if os.environ.get('QBO_REALM_ID') else 'NOT SET'}")
    
    # Try to initialize SecretManager
    print_section("Secret Manager Check")
    try:
        from src.secret_manager import SecretManager
        from src.database import Database
        
        database = Database()
        secret_manager = SecretManager(database=database)
        
        print(f"✅ SecretManager initialized")
        print(f"   Project: {secret_manager.project_id}")
        print(f"   Client available: {secret_manager.client is not None}")
        
        # Try to get credentials
        print_section("Credential Retrieval")
        creds = secret_manager.get_qbo_credentials()
        
        print("Retrieved credentials:")
        print(f"   Client ID: {creds.get('client_id', 'None')[:20]}...")
        print(f"   Client Secret: {'*' * 20 if creds.get('client_secret') else 'None'}")
        print(f"   Refresh Token: {creds.get('refresh_token', 'None')[:20]}...")
        print(f"   Realm ID: {creds.get('realm_id', 'None')}")
        print(f"   Is Valid: {creds.get('is_valid', 'Unknown')}")
        
        # Check specific secret retrieval
        print_section("Individual Secret Check")
        
        qbo_id = secret_manager.get_secret('QBO_ID_2-3-26')
        if qbo_id:
            print(f"✅ QBO_ID_2-3-26: Found (length: {len(qbo_id)})")
        else:
            print(f"❌ QBO_ID_2-3-26: NOT FOUND in Secret Manager")
            print(f"   This secret should be created in Google Secret Manager")
        
        qbo_secret = secret_manager.get_secret('QBO_Secret_2-3-26')
        if qbo_secret:
            print(f"✅ QBO_Secret_2-3-26: Found (length: {len(qbo_secret)})")
        else:
            print(f"❌ QBO_Secret_2-3-26: NOT FOUND in Secret Manager")
            print(f"   This secret should be created in Google Secret Manager")
        
        # Check database credentials
        print_section("Database Credentials Check")
        db_creds = database.get_qbo_credentials()
        if db_creds:
            print("✅ Credentials found in database")
            print(f"   Client ID: {db_creds.get('client_id', 'None')[:20]}...")
            print(f"   Realm ID: {db_creds.get('realm_id', 'None')}")
            print(f"   Has refresh token: {bool(db_creds.get('refresh_token'))}")
            print(f"   Access token expires: {db_creds.get('access_token_expires_at', 'Unknown')}")
            print(f"   Refresh token expires: {db_creds.get('refresh_token_expires_at', 'Unknown')}")
        else:
            print("❌ No credentials in database")
            print("   Configure via /qbo-settings")
        
        # Final assessment
        print_section("Assessment")
        
        if creds.get('is_valid'):
            print("✅ Valid credentials are available")
            print("   Source:", end=" ")
            if db_creds:
                print("Database (highest priority)")
            elif qbo_id:
                print("Google Secret Manager")
            elif os.environ.get('QBO_CLIENT_ID'):
                print("Environment variables")
            print("\n   The application should be able to refresh OAuth tokens.")
        else:
            print("❌ NO VALID CREDENTIALS FOUND")
            print("\n   Possible causes:")
            print("   1. Secrets not created in Google Secret Manager")
            print("   2. No credentials in database")
            print("   3. Environment variables not set")
            print("\n   Solution:")
            print("   → Configure credentials at /qbo-settings by connecting to QuickBooks")
            print("   → OR create secrets in Google Secret Manager:")
            print("      gcloud secrets create QBO_ID_2-3-26 --data-file=<file>")
            print("      gcloud secrets create QBO_Secret_2-3-26 --data-file=<file>")
            print("   → OR set environment variables in Cloud Run")
        
        if creds.get('is_valid') and creds.get('client_id') != 'dummy_id':
            print("\n⚠️  Note: Even with valid-looking credentials, you may get 401 errors if:")
            print("   - The refresh token has expired (after 101 days)")
            print("   - The client credentials are incorrect")
            print("   - The QuickBooks app has been deleted or revoked")
            print("\n   If you're getting 401 errors, reconnect at /qbo-settings")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
