# Changes Summary

## Modular Architecture Refactor
The application has been refactored from a monolithic `src` directory into a modular structure:
- **`src/auth`**: Handles authentication logic, including QBO OAuth (`qbo_auth.py`), user session utilities (`utils.py`), and secret management (`secret_manager.py`).
- **`src/invoices`**: Manages invoice processing (`invoice_manager.py`), QBO data fetching (`qbo_connector.py`), and webhook handling (`webhook_handler.py`).
- **`src/erp`**: Contains the "intelligence" layer, including the AI Payment Predictor (`payment_predictor.py`), Cash Flow logic (`cash_flow.py`, `cash_flow_calendar.py`), AI Service (`ai_service.py`), and the new **Customer Mapping** logic (`customer_mapper.py`).
- **`src/common`**: Shared utilities like `database.py`, `error_handler.py`, and `email_service.py` to prevent circular dependencies.

## Customer Mapping System
A new persistent mapping system allows admins to define default settings for QBO Customers.
- **Database Table**: `customer_mappings` stores `default_portal_name`, `default_net_terms`, and `default_vzt_rep_id` linked to a QBO Customer ID.
- **Logic**: `CustomerMapper` automatically applies these defaults to invoices when fetched from QBO if the invoice metadata is missing.
- **Fallback**: If a mapped user is invalid or no mapping exists, a "System Default" rep (e.g., first admin) is assigned.
- **UI**: A new "Customer Settings" page (`/customer-settings`) allows admins to search for customers (via server-side pagination) and configure these mappings.

## Backfill Script
A script `scripts/backfill_customer_mappings.py` is provided to retroactively apply mappings to all historical invoices in QBO.
- Supports `--dry-run` to preview changes.
- Iterates all invoices, looks up mappings by Customer ID, and updates local metadata.

## Server-Side Pagination
The `/api/qbo/customers` endpoint now supports server-side pagination and search to handle large customer lists efficiently.
- Accepts `page` and `q` parameters.
- Uses QBO `STARTPOSITION` and `MAXRESULTS` for efficient data retrieval.
- Integrated with Select2 in the frontend.

## Testing & Stability
- Unit tests updated to reflect new directory structure.
- New tests added for `CustomerMapper` logic and fallback mechanisms.
- Circular imports resolved by introducing `src/common` and refactoring `src/auth`.
