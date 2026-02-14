#!/usr/bin/env python3
"""
QBO Integration Test Script

This script tests the QuickBooks Online integration to verify:
1. OAuth token refresh works
2. Can fetch invoices from QBO
3. Can fetch bank accounts from QBO
4. Can query company info
5. Webhook handler can parse CloudEvents

Usage:
    python3 test_qbo_integration.py

Requirements:
    - QBO credentials configured (via OAuth or environment variables)
    - Internet connectivity
    - Flask app not required to be running
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from qbo_client import QBOClient
from invoice_manager import InvoiceManager
from webhook_handler import WebhookHandler
from database import Database


def test_qbo_client_initialization():
    """Test 1: QBO Client Initialization"""
    print("\n" + "=" * 60)
    print("TEST 1: QBO Client Initialization")
    print("=" * 60)
    
    try:
        # Try to get credentials from database
        database = Database()
        credentials = database.get_qbo_credentials()
        
        if not credentials:
            print("❌ FAIL: No QBO credentials found in database")
            print("   Please configure credentials via /qbo-settings page")
            return False
        
        print(f"✓ Found credentials in database")
        print(f"  Client ID: {credentials['client_id'][:20]}...")
        print(f"  Realm ID: {credentials['realm_id']}")
        
        # Initialize QBO client
        qbo_client = QBOClient(
            client_id=credentials['client_id'],
            client_secret=credentials['client_secret'],
            refresh_token=credentials['refresh_token'],
            realm_id=credentials['realm_id'],
            database=database
        )
        
        if not qbo_client.credentials_valid:
            print("❌ FAIL: Credentials are marked as invalid (dummy values)")
            return False
        
        print("✓ QBO Client initialized successfully")
        return True, qbo_client, database
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def test_token_refresh(qbo_client):
    """Test 2: OAuth Token Refresh"""
    print("\n" + "=" * 60)
    print("TEST 2: OAuth Token Refresh")
    print("=" * 60)
    
    try:
        # Attempt to refresh access token
        qbo_client.refresh_access_token()
        
        if qbo_client.access_token:
            print(f"✓ Access token refreshed successfully")
            print(f"  Token: {qbo_client.access_token[:30]}...")
            return True
        else:
            print("❌ FAIL: No access token after refresh")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Token refresh error: {e}")
        return False


def test_fetch_company_info(qbo_client):
    """Test 3: Fetch Company Information"""
    print("\n" + "=" * 60)
    print("TEST 3: Fetch Company Information")
    print("=" * 60)
    
    try:
        # Fetch company info
        response = qbo_client.make_request("companyinfo/" + qbo_client.realm_id)
        
        if response and "CompanyInfo" in response:
            company = response["CompanyInfo"]
            print("✓ Company information fetched successfully")
            print(f"  Company Name: {company.get('CompanyName', 'N/A')}")
            print(f"  Legal Name: {company.get('LegalName', 'N/A')}")
            print(f"  Email: {company.get('Email', {}).get('Address', 'N/A')}")
            print(f"  Country: {company.get('Country', 'N/A')}")
            return True
        else:
            print("❌ FAIL: No company info in response")
            print(f"  Response: {response}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def test_fetch_invoices(qbo_client):
    """Test 4: Fetch Invoices"""
    print("\n" + "=" * 60)
    print("TEST 4: Fetch Invoices from QBO")
    print("=" * 60)
    
    try:
        invoice_manager = InvoiceManager(qbo_client)
        invoices = invoice_manager.fetch_invoices()
        
        if invoices:
            print(f"✓ Fetched {len(invoices)} invoice(s) from QBO")
            
            # Show details of first 3 invoices
            for i, inv in enumerate(invoices[:3]):
                print(f"\n  Invoice {i+1}:")
                print(f"    ID: {inv.get('id', 'N/A')}")
                print(f"    Number: {inv.get('doc_number', 'N/A')}")
                print(f"    Customer: {inv.get('customer_name', 'N/A')}")
                print(f"    Amount: ${inv.get('total_amount', 0):.2f}")
                print(f"    Balance: ${inv.get('balance', 0):.2f}")
                print(f"    Due Date: {inv.get('due_date', 'N/A')}")
                print(f"    Status: {inv.get('status', 'N/A')}")
            
            if len(invoices) > 3:
                print(f"\n  ... and {len(invoices) - 3} more invoices")
            
            return True
        else:
            print("⚠️  WARNING: No invoices found (this may be normal for new QBO accounts)")
            return True  # Not a failure, just no data
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fetch_bank_accounts(qbo_client):
    """Test 5: Fetch Bank Accounts"""
    print("\n" + "=" * 60)
    print("TEST 5: Fetch Bank Accounts from QBO")
    print("=" * 60)
    
    try:
        accounts = qbo_client.fetch_bank_accounts()
        
        if accounts:
            print(f"✓ Fetched {len(accounts)} bank account(s) from QBO")
            
            total_balance = 0
            for i, account in enumerate(accounts):
                print(f"\n  Account {i+1}:")
                print(f"    ID: {account.get('Id', 'N/A')}")
                print(f"    Name: {account.get('Name', 'N/A')}")
                print(f"    Account #: {account.get('AcctNum', 'N/A')}")
                print(f"    Balance: ${account.get('CurrentBalance', 0):.2f}")
                print(f"    Type: {account.get('AccountType', 'N/A')}/{account.get('AccountSubType', 'N/A')}")
                total_balance += account.get('CurrentBalance', 0)
            
            print(f"\n  Total Balance: ${total_balance:.2f}")
            return True
        else:
            print("⚠️  WARNING: No bank accounts found")
            print("   This may be normal for sandbox environments")
            return True  # Not a failure, just no data
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_customers(qbo_client):
    """Test 6: Query Customers"""
    print("\n" + "=" * 60)
    print("TEST 6: Query Customers from QBO")
    print("=" * 60)
    
    try:
        query = "SELECT * FROM Customer MAXRESULTS 5"
        response = qbo_client.make_request("query", params={"query": query})
        
        if response and "QueryResponse" in response:
            customers = response["QueryResponse"].get("Customer", [])
            
            if customers:
                print(f"✓ Fetched {len(customers)} customer(s) from QBO")
                
                for i, customer in enumerate(customers):
                    print(f"\n  Customer {i+1}:")
                    print(f"    ID: {customer.get('Id', 'N/A')}")
                    print(f"    Name: {customer.get('DisplayName', 'N/A')}")
                    print(f"    Email: {customer.get('PrimaryEmailAddr', {}).get('Address', 'N/A')}")
                    print(f"    Phone: {customer.get('PrimaryPhone', {}).get('FreeFormNumber', 'N/A')}")
                
                return True
            else:
                print("⚠️  WARNING: No customers found")
                return True  # Not a failure
        else:
            print("❌ FAIL: Invalid response format")
            print(f"  Response: {response}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def test_webhook_handler():
    """Test 7: Webhook Handler (CloudEvents Parsing)"""
    print("\n" + "=" * 60)
    print("TEST 7: Webhook Handler - CloudEvents Parsing")
    print("=" * 60)
    
    try:
        handler = WebhookHandler()
        
        # Test CloudEvents payload
        test_payload = {
            "specversion": "1.0",
            "type": "com.intuit.quickbooks.entity.update",
            "source": "//quickbooks.api.intuit.com",
            "id": "test-event-123",
            "time": "2024-02-14T12:00:00Z",
            "data": {
                "realm": "test-realm-id",
                "name": "Invoice",
                "id": "789",
                "operation": "Update",
                "lastUpdated": "2024-02-14T12:00:00Z"
            }
        }
        
        # Parse CloudEvents
        parsed = handler.parse_cloudevents(test_payload)
        
        if parsed:
            print("✓ CloudEvents parsing successful")
            print(f"  Event Type: {parsed['event_type']}")
            print(f"  Entity: {parsed['entity_name']}")
            print(f"  Operation: {parsed['operation']}")
            print(f"  Entity ID: {parsed['entity_id']}")
            
            # Test processing
            result = handler.process_webhook_event(parsed)
            print(f"  Processing Result: {result['status']}")
            
            return True
        else:
            print("❌ FAIL: CloudEvents parsing failed")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("QuickBooks Online Integration Test Suite")
    print("=" * 60)
    print("\nThis will test connectivity to QuickBooks Online API")
    print("and verify all integration points are working.\n")
    
    results = []
    
    # Test 1: Initialize QBO Client
    result = test_qbo_client_initialization()
    if not result or result is False:
        print("\n❌ Cannot proceed without valid QBO credentials")
        return 1
    
    success, qbo_client, database = result
    results.append(("QBO Client Initialization", success))
    
    # Test 2: Token Refresh
    success = test_token_refresh(qbo_client)
    results.append(("OAuth Token Refresh", success))
    if not success:
        print("\n❌ Cannot proceed without valid access token")
        return 1
    
    # Test 3: Company Info
    success = test_fetch_company_info(qbo_client)
    results.append(("Fetch Company Info", success))
    
    # Test 4: Invoices
    success = test_fetch_invoices(qbo_client)
    results.append(("Fetch Invoices", success))
    
    # Test 5: Bank Accounts
    success = test_fetch_bank_accounts(qbo_client)
    results.append(("Fetch Bank Accounts", success))
    
    # Test 6: Customers
    success = test_query_customers(qbo_client)
    results.append(("Query Customers", success))
    
    # Test 7: Webhook Handler
    success = test_webhook_handler()
    results.append(("Webhook Handler", success))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
    print("=" * 60)
    
    if failed == 0:
        print("\n✓ ALL TESTS PASSED!")
        print("QuickBooks Online integration is working correctly.")
        return 0
    else:
        print(f"\n❌ {failed} TEST(S) FAILED")
        print("Please check the errors above and verify your QBO credentials.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
