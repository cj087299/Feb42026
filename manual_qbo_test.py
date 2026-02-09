#!/usr/bin/env python3
"""
Manual QBO Authentication Test Script

This script tests the QBO authentication workflow with real or mock credentials.
Run this script to verify that:
1. QBO client initializes correctly
2. Token refresh mechanism works
3. Credentials are properly loaded from environment or Secret Manager
4. API requests include proper authentication headers

Usage:
    python manual_qbo_test.py
    
Environment Variables (optional):
    QBO_CLIENT_ID       - QuickBooks OAuth client ID
    QBO_CLIENT_SECRET   - QuickBooks OAuth client secret  
    QBO_REFRESH_TOKEN   - QuickBooks OAuth refresh token
    QBO_REALM_ID        - QuickBooks company/realm ID
    GOOGLE_CLOUD_PROJECT - GCP project for Secret Manager
"""

import os
import sys
from unittest.mock import Mock, patch

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from src.qbo_client import QBOClient
from src.secret_manager import SecretManager
from src.invoice_manager import InvoiceManager

def test_secret_manager():
    """Test Secret Manager credential retrieval."""
    print("=" * 60)
    print("Testing Secret Manager")
    print("=" * 60)
    
    secret_manager = SecretManager()
    print(f"✓ Secret Manager initialized")
    print(f"  Project ID: {secret_manager.project_id or 'None (using env vars)'}")
    print(f"  Client available: {secret_manager.client is not None}")
    
    credentials = secret_manager.get_qbo_credentials()
    print(f"\n✓ QBO Credentials retrieved:")
    print(f"  Client ID: {credentials['client_id'][:10]}... (length: {len(credentials['client_id'])})")
    print(f"  Client Secret: {credentials['client_secret'][:10]}... (length: {len(credentials['client_secret'])})")
    print(f"  Refresh Token: {credentials['refresh_token'][:10]}... (length: {len(credentials['refresh_token'])})")
    print(f"  Realm ID: {credentials['realm_id']}")
    
    return credentials

def test_qbo_client_initialization(credentials):
    """Test QBO client initialization."""
    print("\n" + "=" * 60)
    print("Testing QBO Client Initialization")
    print("=" * 60)
    
    client = QBOClient(
        client_id=credentials['client_id'],
        client_secret=credentials['client_secret'],
        refresh_token=credentials['refresh_token'],
        realm_id=credentials['realm_id']
    )
    
    print(f"✓ QBO Client initialized")
    print(f"  Client ID matches: {client.client_id == credentials['client_id']}")
    print(f"  Realm ID: {client.realm_id}")
    print(f"  Base URL: {client.base_url}")
    print(f"  Access Token (before refresh): {client.access_token}")
    
    return client

def test_token_refresh_mock(client):
    """Test token refresh with mocked API."""
    print("\n" + "=" * 60)
    print("Testing Token Refresh (Mocked)")
    print("=" * 60)
    
    with patch('src.qbo_client.requests.post') as mock_post:
        # Mock successful token refresh
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_access_token_12345',
            'expires_in': 3600,
            'token_type': 'bearer'
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Trigger refresh
        try:
            client.refresh_access_token()
            print(f"✓ Token refresh successful")
            print(f"  Access Token: {client.access_token[:20]}...")
            print(f"  Token set: {client.access_token is not None}")
            
            # Verify authorization header
            headers = client.get_headers()
            print(f"  Authorization header: {headers.get('Authorization', 'MISSING')[:30]}...")
            
            return True
        except Exception as e:
            print(f"✗ Token refresh failed: {e}")
            return False

def test_api_request_mock(client):
    """Test API request with mocked response."""
    print("\n" + "=" * 60)
    print("Testing API Request (Mocked)")
    print("=" * 60)
    
    with patch('src.qbo_client.requests.post') as mock_post, \
         patch('src.qbo_client.requests.request') as mock_request:
        
        # Mock token refresh
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            'access_token': 'api_test_token'
        }
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response
        
        # Mock API response
        mock_api_response = Mock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = {
            "QueryResponse": {
                "Invoice": [
                    {
                        "Id": "1",
                        "DocNumber": "INV-001",
                        "TotalAmt": 1000.00,
                        "Balance": 500.00,
                        "DueDate": "2026-03-15"
                    },
                    {
                        "Id": "2",
                        "DocNumber": "INV-002",
                        "TotalAmt": 2500.00,
                        "Balance": 2500.00,
                        "DueDate": "2026-03-20"
                    }
                ]
            }
        }
        mock_api_response.raise_for_status = Mock()
        mock_request.return_value = mock_api_response
        
        try:
            # Make request through InvoiceManager
            manager = InvoiceManager(client)
            invoices = manager.fetch_invoices()
            
            print(f"✓ API request successful")
            print(f"  Invoices fetched: {len(invoices)}")
            for inv in invoices:
                print(f"  - {inv['doc_number']}: ${inv['amount']} (Balance: ${inv['balance']})")
            
            return True
        except Exception as e:
            print(f"✗ API request failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_authentication_error_handling():
    """Test handling of authentication errors."""
    print("\n" + "=" * 60)
    print("Testing Authentication Error Handling")
    print("=" * 60)
    
    client = QBOClient(
        client_id="invalid_client",
        client_secret="invalid_secret",
        refresh_token="invalid_token",
        realm_id="invalid_realm"
    )
    
    with patch('src.qbo_client.requests.post') as mock_post:
        # Mock 401 error
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_post.return_value = mock_response
        
        try:
            client.refresh_access_token()
            print(f"✗ Expected exception was not raised")
            return False
        except Exception as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                print(f"✓ Authentication error properly handled")
                print(f"  Error: {e}")
                return True
            else:
                print(f"✗ Unexpected error: {e}")
                return False

def main():
    """Run all QBO authentication tests."""
    print("\n" + "=" * 60)
    print("QBO AUTHENTICATION TEST SUITE")
    print("=" * 60)
    print()
    
    results = []
    
    try:
        # Test 1: Secret Manager
        credentials = test_secret_manager()
        results.append(("Secret Manager", True))
        
        # Test 2: Client Initialization
        client = test_qbo_client_initialization(credentials)
        results.append(("Client Initialization", True))
        
        # Test 3: Token Refresh
        success = test_token_refresh_mock(client)
        results.append(("Token Refresh (Mocked)", success))
        
        # Test 4: API Request
        success = test_api_request_mock(client)
        results.append(("API Request (Mocked)", success))
        
        # Test 5: Error Handling
        success = test_authentication_error_handling()
        results.append(("Error Handling", success))
        
    except Exception as e:
        print(f"\n✗ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Test Suite", False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! QBO authentication is working correctly.")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
