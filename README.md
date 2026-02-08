# VZT Accounting

## QuickBooks Online Cash Flow Projection and Invoice Management

This project provides tools for managing QuickBooks Online invoices and projecting cash flow with a user-friendly web interface.

## Features

### Web Interface
- **Navigation Landing Page**: Easy-to-use home page with quick access to all features
- **Invoice Management**: Interactive page to view, filter, and sort invoices
- **Cash Flow Projections**: AI-powered forecasting with customizable time periods
- **System Status**: Health check and API documentation page

### Core Modules

- `qbo_client`: Handles authentication and API requests to QuickBooks Online.
- `invoice_manager`: Fetches and manages invoices.
- `cash_flow`: Projects cash flow based on invoice due dates.
- `ai_predictor`: Machine learning model for payment date prediction.

## Getting Started

### Installation

```bash
pip install -r requirements.txt
```

### Running the Application

```bash
python main.py
```

The application will start on `http://localhost:8080`

### Using the Web Interface

1. **Home Page** (`/`): Landing page with navigation to all features
2. **Invoices** (`/invoices`): View and filter invoices with advanced options:
   - Filter by date range, status, customer, amount, and region
   - Sort by due date, amount, customer, or status
3. **Cash Flow** (`/cashflow`): Generate AI-powered cash flow projections:
   - Select projection period (30, 60, 90, or 180 days)
   - View projected balance changes
4. **Status** (`/health`): Check system health and view API documentation

### API Endpoints

The application also provides REST API endpoints:

- `GET /api/invoices` - Fetch and filter invoices
- `GET /api/cashflow?days=30` - Get cash flow projections
- `GET /health` - Health check

For API usage examples, visit the Status page in the web interface.
