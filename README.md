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

### 1. QuickBooks Online OAuth 2.0 Authentication (New!)
- **One-Click Connection**: Admin clicks "Connect to QuickBooks" and logs in with their QBO username/password
- **Automatic Token Management**: Tokens are automatically exchanged, stored, and refreshed
- **Shared Access**: One admin connects, all users can access QBO for 101 days
- **Secure Flow**: Full OAuth 2.0 implementation with CSRF protection
- **No Manual Token Entry Required**: Just connect and go!
- **Credential Validation**: Automatic detection of invalid or expired credentials with helpful error messages
- **Health Check**: Use `check_oauth_health.py` to diagnose OAuth issues
- See `QBO_OAUTH_FLOW.md` for step-by-step instructions
- See `OAUTH_CREDENTIAL_SETUP_GUIDE.md` for troubleshooting OAuth errors

### 2. Centralized QBO Token Management
- **Admin-Configured Credentials**: Master admin and admin users can configure QuickBooks Online credentials once for all users
- **Automatic Token Refresh**: Access tokens automatically refresh before expiration
- **Token Expiration Tracking**: Visual indicators show token status and expiration times
- **Credential Validation**: System validates credentials before use and provides actionable error messages
- **Secure Storage**: Credentials stored in database with audit logging
- **Easy Setup**: Web-based UI at `/qbo-settings` for credential management
- **Long-Lived Sessions**: Refresh tokens valid for 101 days
- **Manual Entry Option**: Can still manually enter tokens if preferred
- See `QBO_TOKEN_MANAGEMENT.md` for detailed documentation

### 3. Branding Update
- Application rebranded as "VZT Accounting"
- Updated all templates and API responses with new branding

### 3. Google Secret Manager Integration
- Secure credential storage for QuickBooks Online API credentials
- Automatically retrieves `QBO_ID_2-3-26` and `QBO_Secret_2-3-26` from Google Cloud Secret Manager
- Falls back to environment variables if Secret Manager is not available
- **NOTE**: Database-stored credentials (configured via admin UI) take priority

### 4. Enhanced Invoice Management
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

### QuickBooks OAuth Setup

**IMPORTANT**: Before running the application, you must configure valid QuickBooks OAuth credentials.

#### Quick Setup (For Development/Testing)

If you have credentials from QuickBooks OAuth 2.0 Playground:

```bash
# Edit initialize_qbo_credentials.py with your credentials
python3 initialize_qbo_credentials.py
```

This initializes the database with valid credentials. The application will use these automatically.

#### Production Setup

Use the web UI at `/qbo-settings` to connect to QuickBooks via OAuth 2.0 flow. See `OAUTH_CREDENTIAL_SETUP_GUIDE.md` for details.

### Environment Variables

The application supports the following environment variables:

```bash
# QuickBooks Online Credentials (fallback if not configured via admin UI)
# NOTE: It's recommended to configure QBO credentials via the admin UI at /qbo-settings
# Environment variables are used as fallback only
QBO_CLIENT_ID=your_client_id
QBO_CLIENT_SECRET=your_client_secret
QBO_REFRESH_TOKEN=your_refresh_token
QBO_REALM_ID=your_realm_id

# Google Cloud (for Secret Manager)
GOOGLE_CLOUD_PROJECT=your_project_id

# Google Cloud SQL Configuration (optional, defaults to SQLite)
USE_CLOUD_SQL=true                    # Set to 'true' to enable Cloud SQL
CLOUD_SQL_CONNECTION_NAME=project-df2be397-d2f7-4b71-944:us-south1:companydatabase2-4-26
CLOUD_SQL_DATABASE_NAME=accounting_app  # Database name in Cloud SQL
CLOUD_SQL_USER=root                    # Database user
CLOUD_SQL_PASSWORD=your_password        # Database password

# Email Configuration (REQUIRED for password reset functionality)
BASE_URL=https://your-domain.com       # Your application's base URL (required for reset links)
SMTP_HOST=smtp.gmail.com               # SMTP server hostname
SMTP_PORT=587                          # SMTP port (587 for TLS)
SMTP_USER=your-email@gmail.com         # SMTP username - REQUIRED
SMTP_PASSWORD=your-app-password        # SMTP password - REQUIRED
FROM_EMAIL=your-email@gmail.com        # Email address in "From" field
FROM_NAME=VZT Accounting               # Name in "From" field

# Optional: Disable email (not recommended for production)
# EMAIL_ENABLED=false                  # Set to 'false' only for testing
```

⚠️ **IMPORTANT**: Email configuration is now mandatory. The application requires valid SMTP credentials (SMTP_USER and SMTP_PASSWORD) to start. Without these, users cannot reset passwords.

See `EMAIL_CONFIGURATION.md` for detailed email setup instructions.

### Database Configuration

The application supports two database backends:

1. **SQLite** (default): Stores data in a local `vzt_accounting.db` file. Great for development and testing.
2. **Google Cloud SQL**: Connects to a MySQL database in Google Cloud. Ideal for production deployments.

To use Google Cloud SQL:
- Set `USE_CLOUD_SQL=true`
- Configure the connection details with the environment variables above
- Install required packages: `cloud-sql-python-connector` and `pymysql` (included in requirements.txt)

The database will automatically initialize with the required tables (`invoice_metadata` and `custom_cash_flows`) in the specified database.

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
   - **Note**: Invoices are fetched directly from QuickBooks Online
3. **Cash Flow Calendar** (`/cashflow`): Interactive cash flow calendar:
   - Select custom date range (start and end dates) or use quick buttons (30, 60, 90, 180 days)
   - **Bank balance automatically pulled from QuickBooks Online**
   - Toggle visibility of different flow types
   - Click on any day to see detailed breakdown
   - Add custom inflows/outflows (one-time or recurring)
4. **Status** (`/health`): Check system health and view API documentation

### API Endpoints

The application provides comprehensive REST API endpoints:

#### Invoice APIs
- `GET /api/invoices` - Fetch and filter invoices (includes metadata, **fetches from QBO**)
- `GET /api/invoices/<invoice_id>/metadata` - Get invoice metadata
- `POST /api/invoices/<invoice_id>/metadata` - Save invoice metadata

#### Cash Flow APIs
- `GET /api/cashflow?days=30` - Get simple cash flow projections
- `GET /api/cashflow/calendar?start_date=2024-01-01&end_date=2024-03-31` - Get calendar-style projections with daily breakdown (supports custom date ranges)
- `GET /api/bank-accounts` - Get current bank account balances from QuickBooks Online

#### Custom Cash Flow APIs
- `GET /api/custom-cash-flows` - Get all custom cash flows
- `POST /api/custom-cash-flows` - Add new custom cash flow
- `GET /api/custom-cash-flows/<id>` - Get specific custom cash flow
- `PUT /api/custom-cash-flows/<id>` - Update custom cash flow
- `DELETE /api/custom-cash-flows/<id>` - Delete custom cash flow

#### Webhook APIs
- `GET /api/qbo/webhook` - Webhook verification endpoint
- `POST /api/qbo/webhook` - Receive QuickBooks Online webhook events (CloudEvents format)

See `QBO_WEBHOOKS_SETUP.md` for detailed webhook configuration.

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

## Authentication and User Management

### Automatic Admin Initialization

The application includes a complete user authentication and role-based access control system. **Admin users are automatically created when the server starts** if they don't already exist.

The following master admin users are automatically initialized on first startup:

**User 1:**
- **Email**: admin@vzt.com
- **Password**: admin1234

**User 2:**
- **Email**: cjones@vztsolutions.com
- **Password**: admin1234

**⚠️ IMPORTANT**: Change these default passwords immediately after first login!

**📖 For detailed information**, including Cloud Run deployment, troubleshooting, and security best practices, see `ADMIN_INITIALIZATION.md`.

### Manual Admin Initialization (Optional)

If you need to manually create admin users (e.g., to reset to defaults), you can run:

```bash
python init_admin.py
```

This script is idempotent - it checks if users already exist before creating them.

### Password Reset and Username Recovery

The system includes email-based password reset and username reminder functionality:

- **Forgot Password**: Users can request a password reset link via email
- **Forgot Username**: Users can request a username reminder via email

⚠️ **REQUIRED**: Email must be configured for password reset to work. Set SMTP credentials as described in `EMAIL_CONFIGURATION.md`. The application will not start without valid SMTP configuration.

### User Roles

The system supports five user roles with different permission levels:

1. **Master Admin**
   - Full system access including user management
   - Can create, edit, and delete users
   - Can assign roles and manage permissions
   - Access to all features and audit logs

2. **Admin**
   - Can manage all accounting functions
   - Can view audit logs
   - Cannot manage users

3. **Accounts Receivable (AR)**
   - Can view invoices and cash flow
   - Can edit invoice metadata
   - Can add custom inflows

4. **Accounts Payable (AP)**
   - Can view invoices and cash flow
   - Can manage accounts payable
   - Can add custom outflows

5. **View Only**
   - Can view all pages
   - Cannot make any changes

### Audit Logging

All critical system actions are automatically logged to the audit log, including:
- User login/logout
- User creation, updates, and deletion
- Invoice metadata changes
- Custom cash flow additions, updates, and deletions
- All data access operations

Audit logs include:
- Timestamp
- User email
- Action performed
- Resource type and ID
- IP address
- User agent
- Additional details

### User Management

Master admins can manage users through the `/users` page:
- Create new users with specific roles
- Edit user information and roles
- Activate/deactivate user accounts
- Delete users (except your own account)
- View user activity and last login times

### Page Access Control

Routes are protected based on permissions:
- `/invoices` - Requires 'view_invoices' permission
- `/cashflow` - Requires 'view_cashflow' permission
- `/users` - Requires 'master_admin' role
- `/audit` - Requires 'view_audit_log' permission
- Invoice metadata editing - Requires 'edit_invoice_metadata' permission
- Custom cash flows - Requires specific permissions based on flow type

## Troubleshooting

### QuickBooks OAuth Issues

If you encounter OAuth-related errors (such as "401 Unauthorized" when refreshing tokens):

1. **Check Credential Status**:
   ```bash
   python3 check_oauth_health.py
   ```
   This diagnostic script will check your OAuth configuration and provide recommendations.

2. **Common Error: "Failed to refresh access token: 401 Unauthorized"**
   - This means your OAuth credentials are invalid, expired, or not configured
   - **Solution**: Reconfigure credentials at `/qbo-settings` by connecting to QuickBooks
   - See `OAUTH_CREDENTIAL_SETUP_GUIDE.md` for detailed troubleshooting steps

3. **Credentials Not Configured**:
   - The application uses dummy placeholder values by default
   - **Solution**: Configure credentials via the admin UI at `/qbo-settings` or set environment variables
   - Priority: Database > Google Secret Manager > Environment Variables

4. **Token Expired (after 101 days)**:
   - Refresh tokens expire after 101 days
   - **Solution**: Reconnect to QuickBooks at `/qbo-settings`

For detailed OAuth troubleshooting, see `OAUTH_CREDENTIAL_SETUP_GUIDE.md`.

### Email Configuration Issues

If password reset emails are not working:
- Check SMTP configuration in environment variables
- See `EMAIL_CONFIGURATION.md` for setup instructions
- Verify SMTP credentials are correct

## Future Enhancements

- Full QuickBooks Online accounts payable integration
- Real-time sync with QuickBooks Online
- Advanced AI models for payment prediction
- Multi-currency support
- Export capabilities (PDF, Excel)
- Email notifications for cash flow alerts
- Two-factor authentication (2FA)
- Password reset functionality
- Session timeout configuration

## Security

- QuickBooks credentials stored securely in Google Cloud Secret Manager
- User passwords hashed using SHA-256 with salt
- Session-based authentication with secure cookies
- Role-based access control (RBAC) for all routes
- Comprehensive audit logging for compliance
- All sensitive data encrypted in transit
- Database stored locally with appropriate permissions
- No credentials stored in code or version control
