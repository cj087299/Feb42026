# QuickBooks Online Webhooks Setup Guide

## Overview

This application supports QuickBooks Online (QBO) webhooks to receive real-time notifications when entities change in your QuickBooks account. The webhook implementation supports CloudEvents format and includes proper security measures.

## Features

- **CloudEvents Format Support**: Fully compatible with QBO's CloudEvents-based webhook notifications
- **Verifier Token Authentication**: Secure webhook validation using a dedicated verifier token
- **CSRF Exemption**: Webhook endpoint properly configured to accept external requests
- **Multiple Entity Support**: Handles Customer, Invoice, Payment, and Account entity updates
- **Real-time Updates**: Receive instant notifications when QBO data changes

## Webhook Endpoint

**Endpoint URL**: `https://your-domain.com/api/qbo/webhook`

**Methods**: 
- `GET`: Webhook verification (returns verifier token)
- `POST`: Receives webhook events

**Authentication**: No session authentication required (CSRF exempt)
- Uses verifier token: `eb566143-7dcf-46a0-a51b-dc42962e461d`

## Setting Up Webhooks in QuickBooks Online

### Step 1: Access QuickBooks Developer Portal

1. Go to [QuickBooks Developer Portal](https://developer.intuit.com/)
2. Sign in with your Intuit developer account
3. Navigate to your app in the Dashboard

### Step 2: Configure Webhook Settings

1. Click on your app
2. Go to **Webhooks** section
3. Click **Add webhook**
4. Configure the webhook:
   - **Endpoint URL**: `https://your-domain.com/api/qbo/webhook`
   - **Verifier Token**: `eb566143-7dcf-46a0-a51b-dc42962e461d`
   - Select the entities you want to monitor:
     - ✓ Customer
     - ✓ Invoice
     - ✓ Payment
     - ✓ Account (for bank balance updates)

### Step 3: Verify Webhook

QuickBooks will send a verification request to your endpoint to ensure it's accessible. Your application will respond with:

```json
{
  "status": "ok",
  "message": "Webhook endpoint is active",
  "verifier_token": "eb566143-7dcf-46a0-a51b-dc42962e461d"
}
```

### Step 4: Test the Webhook

1. Make a change in your QuickBooks account (e.g., create an invoice)
2. Check your application logs to verify the webhook was received
3. Look for log entries like:
   ```
   INFO:main:Received webhook: {"specversion": "1.0", "type": "com.intuit.quickbooks.entity.update", ...}
   INFO:src.webhook_handler:Processing webhook event: Invoice Create (ID: 123)
   ```

## CloudEvents Format

QBO webhooks use the CloudEvents specification. Here's an example payload:

```json
{
  "specversion": "1.0",
  "type": "com.intuit.quickbooks.entity.update",
  "source": "//quickbooks.api.intuit.com",
  "id": "unique-event-id-12345",
  "time": "2024-02-13T12:00:00Z",
  "datacontenttype": "application/json",
  "data": {
    "realm": "your-realm-id",
    "name": "Invoice",
    "id": "789",
    "operation": "Update",
    "lastUpdated": "2024-02-13T12:00:00Z"
  }
}
```

### CloudEvents Fields

- **specversion**: CloudEvents specification version (e.g., "1.0")
- **type**: Event type (e.g., `com.intuit.quickbooks.entity.update`)
- **source**: Source of the event (QuickBooks API)
- **id**: Unique identifier for this event
- **time**: Timestamp when the event occurred
- **data**: QBO-specific event data
  - **realm**: Your QuickBooks Company ID (Realm ID)
  - **name**: Entity type (Customer, Invoice, Payment, Account)
  - **id**: Entity ID in QuickBooks
  - **operation**: Type of operation (Create, Update, Delete, Merge)
  - **lastUpdated**: When the entity was last modified

## Supported Entities

### 1. Customer
Triggered when customer records are created, updated, or deleted.

**Use Cases**:
- Sync customer data with external systems
- Track customer changes for analytics

### 2. Invoice
Triggered when invoices are created, updated, or deleted.

**Use Cases**:
- Update cash flow projections in real-time
- Trigger notifications for new invoices
- Invalidate invoice cache

### 3. Payment
Triggered when payments are received or updated.

**Use Cases**:
- Update cash flow projections
- Trigger payment confirmation workflows
- Update invoice payment status

### 4. Account (Bank Accounts)
Triggered when account data changes, including bank balance updates.

**Use Cases**:
- Refresh bank balance displays
- Trigger balance alerts
- Update cash position calculations

**To query current bank balances**:
```bash
GET /api/bank-accounts
```

This endpoint queries the Account entity directly and returns the CurrentBalance field for all bank accounts.

## Webhook Event Processing

The application processes webhook events as follows:

1. **Receive Event**: Webhook endpoint receives CloudEvents payload
2. **Parse CloudEvents**: Extract event type, entity name, operation, and entity ID
3. **Process by Entity Type**: Route to appropriate handler based on entity name
4. **Log Event**: Record the event in application logs
5. **Return Response**: Send success response back to QBO

## Testing Webhooks Locally

### Using ngrok for Local Development

1. Install [ngrok](https://ngrok.com/)
2. Start your application locally:
   ```bash
   python main.py
   ```
3. In another terminal, start ngrok:
   ```bash
   ngrok http 8080
   ```
4. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)
5. Configure this URL in QuickBooks Developer Portal: `https://abc123.ngrok.io/api/qbo/webhook`

### Testing with curl

```bash
# Test webhook verification (GET)
curl -X GET https://your-domain.com/api/qbo/webhook

# Test webhook event (POST)
curl -X POST https://your-domain.com/api/qbo/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "specversion": "1.0",
    "type": "com.intuit.quickbooks.entity.update",
    "source": "//quickbooks.api.intuit.com",
    "id": "test-event-123",
    "data": {
      "realm": "test-realm",
      "name": "Invoice",
      "id": "789",
      "operation": "Update"
    }
  }'
```

## Bank Account Balance Integration

The webhook implementation works seamlessly with the existing bank account balance API:

### Querying Current Balances

```bash
GET /api/bank-accounts
```

**Response**:
```json
{
  "accounts": [
    {
      "id": "123",
      "name": "Main Checking",
      "account_number": "****1234",
      "balance": 25000.00,
      "currency": "USD"
    }
  ],
  "total_balance": 25000.00,
  "as_of": "2024-02-13T12:00:00"
}
```

### How It Works

1. The API queries the Account entity directly using QBO's query API:
   ```sql
   SELECT * FROM Account WHERE AccountType = 'Bank' AND AccountSubType = 'Checking'
   ```
2. Extracts the `CurrentBalance` field from each account
3. Returns formatted, easy-to-read balance data

### Use Cases

- **Dashboard Displays**: Show current bank balances on main dashboard
- **Cash Flow Projections**: Use as starting balance for projections
- **Balance Alerts**: Monitor balance changes via webhooks
- **Financial Reports**: Include current balances in reports

## Troubleshooting

### Webhook Not Receiving Events

1. **Check URL accessibility**: Ensure your webhook URL is publicly accessible
2. **Verify HTTPS**: QBO requires HTTPS for webhook endpoints (not HTTP)
3. **Check firewall**: Ensure your server allows incoming requests from Intuit's IP ranges
4. **Review logs**: Check application logs for errors

### CloudEvents Parsing Errors

If you see parsing errors:
1. Check that the payload matches CloudEvents format
2. Verify all required fields are present (specversion, type, source, id)
3. Review application logs for detailed error messages

### Bank Balance Not Updating

1. **Verify Account webhook is configured** in QuickBooks Developer Portal
2. **Check that the account type is 'Bank'** and subtype is 'Checking'
3. **Review the query** in `qbo_client.py`'s `fetch_bank_accounts()` method
4. **Test the API directly**: `GET /api/bank-accounts`

## Security Considerations

### CSRF Exemption

The webhook endpoint is exempt from CSRF protection because:
- It's called by external QBO servers (not browser-based)
- Uses verifier token for authentication instead of session cookies
- Does not modify user session data

### Verifier Token

The verifier token (`eb566143-7dcf-46a0-a51b-dc42962e461d`) provides basic authentication:
- Should be kept consistent between your app and QBO configuration
- Consider changing in production for added security
- Stored as a constant in `src/webhook_handler.py`

### Additional Security Measures

Consider implementing:
- **IP Whitelisting**: Restrict webhook endpoint to Intuit's IP ranges
- **Request Signing**: Validate webhook signatures (if QBO provides them)
- **Rate Limiting**: Prevent webhook flooding
- **Payload Validation**: Strict CloudEvents format validation (already implemented)

## Monitoring and Logging

All webhook events are logged with the following information:
- Event type and entity name
- Operation (Create, Update, Delete)
- Entity ID
- Timestamp
- Processing result

**Log Levels**:
- `INFO`: Successful webhook processing
- `ERROR`: Parsing or processing errors
- `WARNING`: Unhandled entity types

**Example logs**:
```
INFO:main:Received webhook: {"specversion": "1.0", "type": "com.intuit.quickbooks.entity.update", ...}
INFO:src.webhook_handler:Parsed CloudEvents: type=com.intuit.quickbooks.entity.update, entity=Invoice, operation=Update
INFO:src.webhook_handler:Processing webhook event: Invoice Update (ID: 789)
INFO:src.webhook_handler:Invoice Update: ID 789
```

## API Documentation

### GET /api/qbo/webhook

Webhook verification endpoint.

**Response**:
```json
{
  "status": "ok",
  "message": "Webhook endpoint is active",
  "verifier_token": "eb566143-7dcf-46a0-a51b-dc42962e461d"
}
```

### POST /api/qbo/webhook

Webhook event receiver.

**Request Body**: CloudEvents format (single event or array)

**Response**:
```json
{
  "status": "success",
  "processed": 2,
  "results": [
    {
      "status": "processed",
      "entity": "Invoice",
      "operation": "Update",
      "entity_id": "123"
    },
    {
      "status": "processed",
      "entity": "Payment",
      "operation": "Create",
      "entity_id": "456"
    }
  ]
}
```

### GET /api/bank-accounts

Get current bank account balances.

**Authentication**: Required (session-based)

**Response**:
```json
{
  "accounts": [
    {
      "id": "123",
      "name": "Main Checking",
      "account_number": "****1234",
      "balance": 25000.00,
      "currency": "USD"
    }
  ],
  "total_balance": 25000.00,
  "as_of": "2024-02-13T12:00:00"
}
```

## Further Reading

- [QuickBooks Webhooks Documentation](https://developer.intuit.com/app/developer/qbo/docs/develop/webhooks)
- [CloudEvents Specification](https://cloudevents.io/)
- [QuickBooks API Reference](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/account)

## Support

For issues or questions:
1. Check application logs for detailed error messages
2. Review this documentation
3. Test webhook endpoint with curl
4. Verify QuickBooks Developer Portal configuration
