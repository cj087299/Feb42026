# VZT Accounting

## QuickBooks Online Cash Flow Projection and Invoice Management

This project provides comprehensive tools for managing QuickBooks Online invoices and projecting cash flow with an advanced web interface.

## Features

### Web Interface
- **Navigation Landing Page**: Easy-to-use home page with quick access to all features
- **Invoice Management**: Interactive page to view, filter, and manage invoices with VZT tracking
- **Cash Flow Calendar**: Advanced calendar-style view with daily breakdown and interactive projections
- **System Status**: Health check and API documentation page

### Core Modules

- `qbo_client`: Handles authentication and API requests to QuickBooks Online.
- `invoice_manager`: Fetches and manages invoices.
- `cash_flow`: Projects cash flow based on invoice due dates.
- `cash_flow_calendar`: Enhanced calendar-style daily cash flow projections.
- `ai_predictor`: Machine learning model for payment date prediction.
- `database`: SQLite database for invoice metadata and custom cash flows.
- `secret_manager`: Google Cloud Secret Manager integration for secure credential storage.

## New Features in VZT Accounting

### 1. Branding Update
- Application rebranded as "VZT Accounting"
- Updated all templates and API responses with new branding

### 2. Google Secret Manager Integration
- Secure credential storage for QuickBooks Online API credentials
- Automatically retrieves `QBO_ID_2-3-26` and `QBO_Secret_2-3-26` from Google Cloud Secret Manager
- Falls back to environment variables if Secret Manager is not available

### 3. Enhanced Invoice Management
Track additional metadata for each invoice:
- **VZT Rep**: Name of the VZT representative handling the invoice
- **Sent to VZT Rep Date**: Date when invoice was sent to the VZT rep
- **Customer Portal**: Which customer portal the invoice is associated with
- **Customer Portal Submission Date**: Date when customer submitted through portal

All metadata is stored in SQLite database and can be edited through the UI.

### 4. Advanced Calendar Cash Flow View
Interactive calendar-style cash flow projection with:
- **Daily Breakdown**: See cash flow details for each day
- **Bank Balance Tracking**: View running bank balance calculations
- **Toggle Controls**: Show/hide different flow types:
  - Projected Inflows (from invoices)
  - Projected Outflows (from accounts payable)
  - Custom Inflows
  - Custom Outflows
- **Clickable Days**: Click any day to see detailed breakdown of all cash flows
- **Custom Cash Flows**: Add one-time or recurring custom inflows/outflows

### 5. Custom Cash Flow Management
Add custom cash flows (inflows or outflows) with:
- **One-time entries**: Single date, amount, and description
- **Recurring entries**: Weekly, monthly, or custom interval recurrence
  - Define start and end dates for recurring flows
  - Automatically calculates all occurrences in projection period
- **Full CRUD operations**: Create, read, update, and delete custom flows

### 6. Smart Payment Date Calculation
The calendar uses intelligent payment date calculation:
1. Customer Portal Submission Date + Invoice Terms (if available)
2. AI-predicted payment date (if predictor is trained)
3. Invoice due date (fallback)

## Getting Started

### Installation

```bash
pip install -r requirements.txt
```

### Environment Variables

The application supports the following environment variables:

```bash
# QuickBooks Online Credentials (fallback if Secret Manager not available)
QBO_CLIENT_ID=your_client_id
QBO_CLIENT_SECRET=your_client_secret
QBO_REFRESH_TOKEN=your_refresh_token
QBO_REALM_ID=your_realm_id

# Google Cloud (for Secret Manager)
GOOGLE_CLOUD_PROJECT=your_project_id
```

### Running the Application

```bash
python main.py
```

The application will start on `http://localhost:8080`

### Using the Web Interface

1. **Home Page** (`/`): Landing page with navigation to all features
2. **Invoices** (`/invoices`): View and manage invoices with VZT tracking:
   - Filter by date range, status, customer, amount, and region
   - Sort by due date, amount, customer, or status
   - Click "Edit" to add VZT tracking metadata
3. **Cash Flow Calendar** (`/cashflow`): Interactive cash flow calendar:
   - Select projection period (30, 60, 90, or 180 days)
   - Set initial bank balance
   - Toggle visibility of different flow types
   - Click on any day to see detailed breakdown
   - Add custom inflows/outflows (one-time or recurring)
4. **Status** (`/health`): Check system health and view API documentation

### API Endpoints

The application provides comprehensive REST API endpoints:

#### Invoice APIs
- `GET /api/invoices` - Fetch and filter invoices (includes metadata)
- `GET /api/invoices/<invoice_id>/metadata` - Get invoice metadata
- `POST /api/invoices/<invoice_id>/metadata` - Save invoice metadata

#### Cash Flow APIs
- `GET /api/cashflow?days=30` - Get simple cash flow projections
- `GET /api/cashflow/calendar?days=90&initial_balance=10000` - Get calendar-style projections with daily breakdown

#### Custom Cash Flow APIs
- `GET /api/custom-cash-flows` - Get all custom cash flows
- `POST /api/custom-cash-flows` - Add new custom cash flow
- `GET /api/custom-cash-flows/<id>` - Get specific custom cash flow
- `PUT /api/custom-cash-flows/<id>` - Update custom cash flow
- `DELETE /api/custom-cash-flows/<id>` - Delete custom cash flow

#### System APIs
- `GET /health` - Health check

For detailed API usage examples, visit the Status page in the web interface.

## Database Schema

The application uses SQLite with two main tables:

### invoice_metadata
Stores VZT tracking information for invoices:
- `invoice_id` (PRIMARY KEY)
- `vzt_rep`
- `sent_to_vzt_rep_date`
- `customer_portal`
- `customer_portal_submission_date`
- `created_at`
- `updated_at`

### custom_cash_flows
Stores custom inflows and outflows:
- `id` (PRIMARY KEY)
- `flow_type` (inflow/outflow)
- `amount`
- `date` (optional for recurring)
- `description`
- `is_recurring`
- `recurrence_type` (weekly/monthly/custom_days)
- `recurrence_interval`
- `recurrence_start_date`
- `recurrence_end_date`
- `created_at`
- `updated_at`

## Testing

Run all tests:

```bash
python -m unittest discover tests/ -v
```

Run specific test file:

```bash
python -m unittest tests.test_new_features -v
```

## Future Enhancements

- Full QuickBooks Online accounts payable integration
- Real-time sync with QuickBooks Online
- Advanced AI models for payment prediction
- Multi-currency support
- Export capabilities (PDF, Excel)
- Email notifications for cash flow alerts

## Security

- QuickBooks credentials stored securely in Google Cloud Secret Manager
- All sensitive data encrypted in transit
- Database stored locally with appropriate permissions
- No credentials stored in code or version control
