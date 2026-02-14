# QuickBooks Online - Data Access Summary

## 🎯 What This Application Can Access from QBO

Based on the implemented integration, this application can retrieve and work with the following QuickBooks Online data:

### ✅ Currently Implemented & Tested

#### 1. **Company Information**
```python
# API: GET companyinfo/{realmId}
- Company Name
- Legal Name  
- Email Address
- Phone Number
- Address (billing, shipping)
- Country & Currency
- Fiscal Year information
- Tax ID
```

**Use Cases:**
- Display company name in dashboard header
- Verify connected QBO company
- Show company details in settings

---

#### 2. **Invoices** (Full CRUD Access)
```python
# API: Query, Create, Update, Delete Invoice entities
- Invoice ID & Number
- Customer Name & Details
- Total Amount & Balance Due
- Due Date & Invoice Date
- Payment Terms (Net 30, etc.)
- Status (Open, Paid, Overdue)
- Line Items (products/services)
- Tax Information
- Custom Fields
- Currency
```

**Use Cases:**
- Display all invoices in dashboard
- Filter by status (open, paid, overdue)
- Show overdue invoices with aging
- Calculate accounts receivable
- Track payment history
- Cash flow projections

**Example Data:**
```json
{
  "id": "1047",
  "doc_number": "INV-1001",
  "customer_name": "ABC Corporation",
  "total_amount": 5000.00,
  "balance": 5000.00,
  "due_date": "2024-03-15",
  "status": "Open",
  "days_overdue": 5,
  "terms": "Net 30"
}
```

---

#### 3. **Bank Accounts**
```python
# API: Query Account entities where AccountType = 'Bank'
- Account ID
- Account Name
- Account Number (masked)
- Current Balance
- Account Type (Checking, Savings, Money Market)
- Currency
- Bank Name
- Routing Number
```

**Use Cases:**
- Display current bank balances
- Show total available cash
- Track balance changes via webhooks
- Cash position monitoring
- Multi-account management

**Example Data:**
```json
{
  "Id": "35",
  "Name": "Main Checking Account",
  "AcctNum": "****1234",
  "CurrentBalance": 25000.00,
  "AccountType": "Bank",
  "AccountSubType": "Checking"
}
```

---

#### 4. **Customers** (Full Access)
```python
# API: Query Customer entities
- Customer ID
- Display Name & Company Name
- Primary Email Address
- Primary Phone Number
- Billing Address
- Shipping Address
- Payment Terms
- Balance (Amount Owed)
- Active/Inactive Status
- Tax ID
- Custom Fields
```

**Use Cases:**
- Customer list management
- Contact information lookup
- Payment terms tracking
- Customer balance summaries
- Email communication

---

#### 5. **Payments**
```python
# API: Query Payment entities
- Payment ID & Number
- Payment Amount
- Payment Date
- Payment Method (Check, Cash, Credit Card, etc.)
- Reference Number
- Customer Name
- Applied to Invoices (which invoices paid)
- Deposit to Account
```

**Use Cases:**
- Track received payments
- Match payments to invoices
- Cash flow tracking
- Payment method analysis
- Reconciliation

---

#### 6. **Webhooks (Real-time Notifications)**
```python
# Supported Entity Types via CloudEvents:
- Customer events (Create, Update, Delete, Merge)
- Invoice events (Create, Update, Delete, Merge)
- Payment events (Create, Update, Delete, Merge)
- Account events (Update - for bank balance changes)
```

**Use Cases:**
- Real-time data synchronization
- Instant notification of new invoices
- Auto-refresh when payments received
- Bank balance update notifications
- Trigger automated workflows

**Example Webhook:**
```json
{
  "specversion": "1.0",
  "type": "com.intuit.quickbooks.entity.update",
  "source": "//quickbooks.api.intuit.com",
  "id": "evt-inv-123",
  "data": {
    "realm": "9130356118716283",
    "name": "Invoice",
    "id": "1047",
    "operation": "Update",
    "lastUpdated": "2024-02-14T12:00:00Z"
  }
}
```

---

### 🔄 Easily Accessible (Not Yet Implemented)

The QBO API integration supports querying ANY QBO entity. Here's what else you can access with minimal code:

#### 7. **Vendors**
- Vendor names and contact info
- Payment terms
- Balance owed
- Tax ID

#### 8. **Bills (Accounts Payable)**
- Bill amounts and due dates
- Vendor details
- Line items
- Payment status

#### 9. **Purchase Orders**
- PO numbers and amounts
- Vendor information
- Line items and quantities
- Status (Open, Closed)

#### 10. **Items (Products/Services)**
- Item names and descriptions
- Sales price and purchase cost
- Inventory quantity (if tracked)
- Income/Expense accounts
- Tax information

#### 11. **Estimates/Quotes**
- Estimate numbers
- Customer details
- Line items
- Total amounts
- Status (Pending, Accepted, Rejected)

#### 12. **Sales Receipts**
- Receipt numbers
- Customer information
- Line items
- Payment method
- Total amount

#### 13. **Expenses**
- Expense amounts
- Vendors/Payees
- Expense categories
- Payment method
- Receipts/Attachments

#### 14. **Journal Entries**
- Entry numbers
- Date
- Debit/Credit lines
- Accounts affected
- Memo/Description

#### 15. **Time Activities**
- Employee/Vendor name
- Hours worked
- Hourly rate
- Date
- Customer/Project
- Billable status

#### 16. **Tax Rates & Codes**
- Tax rate percentages
- Tax codes
- Jurisdictions
- Active/Inactive status

---

## 📊 Data Available for Analysis

### Financial Metrics You Can Calculate

1. **Accounts Receivable**
   - Total outstanding invoices
   - Aging buckets (30, 60, 90+ days)
   - Average days to payment
   - Bad debt projection

2. **Cash Position**
   - Current bank balances (all accounts)
   - Available cash
   - Cash flow trends
   - Runway calculation

3. **Revenue Analytics**
   - Revenue by customer
   - Revenue by time period
   - Invoice creation trends
   - Payment collection rates

4. **Customer Insights**
   - Top customers by revenue
   - Customer payment behavior
   - Average invoice value
   - Customer lifetime value

---

## 🔐 Access Control

### Who Can Access QBO Data?

**Admin Users** (`role = 'admin'`):
- ✅ View all invoices
- ✅ View bank accounts
- ✅ View customers
- ✅ View cash flow projections
- ✅ Configure QBO OAuth connection

**Master Admin Users** (`role = 'master_admin'`):
- ✅ All admin permissions
- ✅ Configure QBO OAuth connection
- ✅ Manage user accounts
- ✅ View audit logs

**Other Roles** (view_only, ap, ar):
- ✅ View data based on role permissions
- ❌ Cannot configure QBO connection

---

## 🧪 How to Test Data Access

### Quick Test (Automated)

```bash
# Run integration test script
python3 test_qbo_integration.py
```

This will test:
1. ✅ OAuth token refresh
2. ✅ Company info retrieval
3. ✅ Invoice fetching
4. ✅ Bank account queries
5. ✅ Customer queries
6. ✅ Webhook parsing

### Manual Test (API Endpoints)

```bash
# Test invoices
curl http://localhost:8080/api/invoices

# Test bank accounts  
curl http://localhost:8080/api/bank-accounts

# Test cash flow
curl http://localhost:8080/api/cashflow/projection?days=30

# Test webhook (simulated)
curl -X POST http://localhost:8080/api/qbo/webhook \
  -H "Content-Type: application/json" \
  -d '{"specversion": "1.0", ...}'
```

---

## 📈 Real-World Example

### Scenario: Cash Flow Management

**What the app can do:**

1. **Fetch current bank balance**: $25,000
2. **Get open invoices**: $50,000 (total receivable)
   - $20,000 due this week
   - $15,000 due next week
   - $15,000 due in 30 days
3. **Get overdue invoices**: $8,000 (collection priority)
4. **Calculate projected balance**:
   - Today: $25,000
   - +7 days: $45,000 (after collections)
   - +14 days: $60,000
   - +30 days: $75,000

5. **Receive webhook**: "Invoice #1047 paid"
   - Update balance immediately
   - Recalculate projections
   - Show notification

---

## 🚀 What You Can Build

With this QBO data access, you can build:

1. **Dashboard Widgets**
   - Total AR chart
   - Bank balance gauge
   - Overdue invoice list
   - Payment trend graph

2. **Automated Reports**
   - Aging reports
   - Cash flow statements
   - Revenue by customer
   - Collection reports

3. **Alerts & Notifications**
   - Low bank balance alerts
   - Overdue payment reminders
   - Large payment received
   - Invoice aging notifications

4. **AI-Powered Features**
   - Payment prediction (when will invoice be paid?)
   - Cash flow forecasting
   - Customer payment patterns
   - Anomaly detection

---

## 🔧 Technical Details

### API Rate Limits

- **Sandbox**: 100 requests per minute per app
- **Production**: 500 requests per minute per company
- **Burst**: Up to 1000 requests over 5 minutes

### Token Expiration

- **Access Token**: 1 hour (auto-refreshes)
- **Refresh Token**: 101 days (requires re-authorization)

### Data Freshness

- **Manual Fetch**: On-demand via API calls
- **Webhooks**: Real-time (< 1 second notification)
- **Cache**: Application manages caching strategy

---

## 📝 Summary

### ✅ What Works NOW

- Full invoice access (read/filter/sort)
- Bank account balances
- Customer information
- Company details
- Real-time webhooks
- OAuth authentication
- Automatic token refresh

### 🎯 What You Can Add Easily

- Any other QBO entity (vendors, bills, POs, etc.)
- Additional calculations and reports
- More webhook entity types
- Custom integrations

### 🔒 What's Protected

- Credentials stored securely
- Role-based access control
- Audit logging
- CSRF protection
- OAuth state validation

---

**Ready to Test?**

1. Configure QBO credentials via `/qbo-settings`
2. Run `python3 test_qbo_integration.py`
3. Check the logs for successful data retrieval
4. Start building features with QBO data!
