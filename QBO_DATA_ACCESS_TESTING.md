# Testing QBO Integration - Guide

## Overview

This guide explains how to test that your QuickBooks Online integration can access real data from QBO (invoices, customers, bank accounts, etc.).

## Prerequisites

1. **QBO Developer Account**: Sign up at https://developer.intuit.com/
2. **QBO App Created**: Create an app in the developer portal
3. **OAuth Credentials**: Get Client ID and Client Secret
4. **Test Company**: Sandbox or production QBO company

## Quick Test - Using the Integration Test Script

### Step 1: Configure QBO Credentials

**Option A: Via Web UI** (Recommended)
1. Start the application: `python3 main.py`
2. Log in as admin or master_admin user
3. Navigate to `/qbo-settings`
4. Click "Connect to QuickBooks"
5. Enter credentials in popup:
   - Username: `cjones@vzsolutions.com`
   - Password: Your QBO password
6. Authorize the app

**Option B: Via Environment Variables**
```bash
export QBO_CLIENT_ID="your-client-id"
export QBO_CLIENT_SECRET="your-client-secret"
export QBO_REFRESH_TOKEN="your-refresh-token"
export QBO_REALM_ID="your-company-id"
```

### Step 2: Run Integration Test

```bash
python3 test_qbo_integration.py
```

**Expected Output:**
```
============================================================
QuickBooks Online Integration Test Suite
============================================================

============================================================
TEST 1: QBO Client Initialization
============================================================
✓ Found credentials in database
  Client ID: AB...
  Realm ID: 9130...
✓ QBO Client initialized successfully

============================================================
TEST 2: OAuth Token Refresh
============================================================
✓ Access token refreshed successfully
  Token: eyJlbmMiOiJBM...

============================================================
TEST 3: Fetch Company Information
============================================================
✓ Company information fetched successfully
  Company Name: Your Company Name
  Legal Name: Your Legal Name
  Email: email@example.com
  Country: US

============================================================
TEST 4: Fetch Invoices from QBO
============================================================
✓ Fetched 15 invoice(s) from QBO

  Invoice 1:
    ID: 123
    Number: INV-001
    Customer: ABC Corp
    Amount: $5,000.00
    Balance: $5,000.00
    Due Date: 2024-03-15
    Status: Open

  ... and 12 more invoices

============================================================
TEST 5: Fetch Bank Accounts from QBO
============================================================
✓ Fetched 2 bank account(s) from QBO

  Account 1:
    ID: 35
    Name: Main Checking
    Account #: ****1234
    Balance: $25,000.00
    Type: Bank/Checking

  Total Balance: $25,000.00

============================================================
TEST 6: Query Customers from QBO
============================================================
✓ Fetched 5 customer(s) from QBO

  Customer 1:
    ID: 1
    Name: ABC Corp
    Email: contact@abccorp.com
    Phone: (555) 123-4567

============================================================
TEST 7: Webhook Handler - CloudEvents Parsing
============================================================
✓ CloudEvents parsing successful
  Event Type: com.intuit.quickbooks.entity.update
  Entity: Invoice
  Operation: Update
  Entity ID: 789
  Processing Result: processed

============================================================
TEST SUMMARY
============================================================
✓ PASS: QBO Client Initialization
✓ PASS: OAuth Token Refresh
✓ PASS: Fetch Company Info
✓ PASS: Fetch Invoices
✓ PASS: Fetch Bank Accounts
✓ PASS: Query Customers
✓ PASS: Webhook Handler

============================================================
Results: 7 passed, 0 failed out of 7 tests
============================================================

✓ ALL TESTS PASSED!
QuickBooks Online integration is working correctly.
```

## What Data Can Be Accessed?

### 1. Company Information
- Company name and legal name
- Contact information (email, phone, address)
- Tax ID and fiscal year details
- Supported features and preferences

**API Call:**
```python
qbo_client.make_request(f"companyinfo/{realm_id}")
```

### 2. Invoices
- Invoice number and amount
- Customer details
- Line items with products/services
- Payment status and due dates
- Tax information
- Custom fields

**API Call:**
```python
invoice_manager.fetch_invoices()
```

**Example Invoice Data:**
```json
{
  "id": "123",
  "doc_number": "INV-1001",
  "customer_name": "ABC Corporation",
  "total_amount": 5000.00,
  "balance": 5000.00,
  "due_date": "2024-03-15",
  "status": "Open",
  "terms": "Net 30",
  "line_items": [
    {
      "description": "Consulting Services",
      "amount": 5000.00,
      "quantity": 1
    }
  ]
}
```

### 3. Bank Accounts
- Account names and numbers
- Current balances
- Account types (Checking, Savings, etc.)
- Bank details

**API Call:**
```python
qbo_client.fetch_bank_accounts()
```

**Example Bank Account Data:**
```json
{
  "Id": "35",
  "Name": "Main Checking",
  "AcctNum": "****1234",
  "CurrentBalance": 25000.00,
  "AccountType": "Bank",
  "AccountSubType": "Checking"
}
```

### 4. Customers
- Customer names and contact info
- Email addresses and phone numbers
- Billing and shipping addresses
- Customer balance and terms
- Custom fields

**API Call:**
```python
qbo_client.make_request("query", params={
    "query": "SELECT * FROM Customer"
})
```

### 5. Payments
- Payment amounts and dates
- Payment methods
- Applied to which invoices
- Reference numbers

### 6. Vendors
- Vendor names and details
- Contact information
- Payment terms
- Balance owed

### 7. Products/Services (Items)
- Item names and descriptions
- Prices and costs
- Inventory quantities (if tracked)
- Income/expense accounts

### 8. Purchase Orders
- PO numbers and amounts
- Vendor details
- Line items
- Status

### 9. Bills (Accounts Payable)
- Bill amounts and due dates
- Vendor information
- Line items
- Payment status

### 10. Estimates/Quotes
- Estimate numbers
- Customer details
- Total amounts
- Expiration dates

## Manual Testing via API Endpoints

Once your Flask app is running, you can test these endpoints:

### 1. Test Invoices Endpoint
```bash
curl -b cookies.txt http://localhost:8080/api/invoices
```

**Expected Response:**
```json
{
  "invoices": [
    {
      "id": "123",
      "doc_number": "INV-1001",
      "customer_name": "ABC Corp",
      "total_amount": 5000.00,
      "balance": 5000.00,
      "due_date": "2024-03-15",
      "status": "Open"
    }
  ],
  "count": 15
}
```

### 2. Test Bank Accounts Endpoint
```bash
curl -b cookies.txt http://localhost:8080/api/bank-accounts
```

**Expected Response:**
```json
{
  "accounts": [
    {
      "id": "35",
      "name": "Main Checking",
      "account_number": "****1234",
      "balance": 25000.00,
      "currency": "USD"
    }
  ],
  "total_balance": 25000.00,
  "as_of": "2024-02-14T18:00:00Z"
}
```

### 3. Test Cash Flow Projection
```bash
curl -b cookies.txt "http://localhost:8080/api/cashflow/projection?days=30"
```

### 4. Test Webhook (Simulated)
```bash
curl -X POST http://localhost:8080/api/qbo/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "specversion": "1.0",
    "type": "com.intuit.quickbooks.entity.update",
    "source": "//quickbooks.api.intuit.com",
    "id": "test-123",
    "data": {
      "realm": "your-realm-id",
      "name": "Invoice",
      "id": "789",
      "operation": "Update"
    }
  }'
```

**Expected Response (< 1 second):**
```json
{
  "status": "accepted",
  "message": "Received 1 event(s), queued for processing",
  "queued": 1
}
```

## Troubleshooting

### Error: "QBO credentials are not configured"
- **Solution**: Configure credentials via `/qbo-settings` or environment variables

### Error: "401 Unauthorized"
- **Cause**: Access token expired
- **Solution**: Token will auto-refresh, or manually click "Refresh Token" button

### Error: "Refresh token expired"
- **Cause**: Refresh token is only valid for 101 days
- **Solution**: Re-authorize via OAuth flow (click "Connect to QuickBooks")

### Error: "No invoices found"
- **Cause**: May be normal for new/sandbox accounts
- **Solution**: Create test invoices in QBO dashboard first

### Error: "Cannot connect to QBO API"
- **Cause**: Network issue or QBO service down
- **Solution**: Check https://status.developer.intuit.com/

## QBO Data Query Language

You can query any QBO entity using SQL-like syntax:

```python
# Get all customers
query = "SELECT * FROM Customer"

# Get invoices with balance > 0
query = "SELECT * FROM Invoice WHERE Balance > 0"

# Get recent payments
query = "SELECT * FROM Payment WHERE TxnDate > '2024-01-01'"

# Limit results
query = "SELECT * FROM Invoice MAXRESULTS 100"

# Order results
query = "SELECT * FROM Customer ORDERBY DisplayName"
```

**Supported Entities:**
- Account, Bill, Customer, Employee, Estimate, Invoice
- Item, JournalEntry, Payment, PaymentMethod, Purchase
- PurchaseOrder, SalesReceipt, TaxCode, TaxRate, Vendor
- And many more...

## Security Notes

1. **Never commit credentials** to version control
2. **Use environment variables** for production
3. **Rotate refresh tokens** every 90 days
4. **Monitor audit logs** for suspicious activity
5. **Restrict access** to admin/master_admin only

## Next Steps

After successful testing:

1. ✅ Verify all 7 tests pass
2. ✅ Check that invoices display in web UI
3. ✅ Verify bank balances update
4. ✅ Test cash flow projections
5. ✅ Confirm webhooks work (check logs)
6. 🚀 Deploy to production

## Support

For issues:
- Check logs: `tail -f /var/log/app.log`
- Test token: `curl https://your-app.com/api/qbo/credentials`
- Refresh token: Click "Refresh Access Token" in settings
- Re-authorize: Click "Connect to QuickBooks" button
