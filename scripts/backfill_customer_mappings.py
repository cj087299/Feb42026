#!/usr/bin/env python3
import sys
import os
import logging
import argparse

# Add project root to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.common.database import Database
from src.auth.secret_manager import SecretManager
from src.auth.qbo_auth import QBOAuth
from src.invoices.qbo_connector import QBOConnector
from src.invoices.invoice_manager import InvoiceManager
from src.erp.customer_mapper import CustomerMapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for Dummy Credentials
DUMMY_QBO_CLIENT_ID = 'dummy_id'
DUMMY_QBO_CLIENT_SECRET = 'dummy_secret'
DUMMY_QBO_REFRESH_TOKEN = 'dummy_refresh'
DUMMY_QBO_REALM_ID = 'dummy_realm'

def backfill_invoices(dry_run=False):
    """
    Backfill invoice metadata based on customer mappings.
    Fetches all invoices from QBO and applies default mappings retroactively.
    """
    logger.info(f"Starting Customer Mapping Backfill... (Dry Run: {dry_run})")

    # 1. Initialize Database
    database = Database()

    # 2. Initialize QBO Connection
    secret_manager = SecretManager(database=database)
    qbo_creds = secret_manager.get_qbo_credentials()

    if not qbo_creds.get('is_valid'):
        logger.error("QBO credentials not configured. Cannot fetch invoices.")
        return

    auth = QBOAuth(
        qbo_creds['client_id'],
        qbo_creds['client_secret'],
        qbo_creds['refresh_token'],
        qbo_creds['realm_id'],
        database=database
    )
    if qbo_creds.get('access_token'):
        auth.access_token = qbo_creds['access_token']

    connector = QBOConnector(auth)

    # 3. Fetch Invoices
    logger.info("Fetching invoices from QBO...")
    # Using direct query to get all invoices
    query = "select * from Invoice"
    response = connector.make_request("query", params={"query": query})

    invoices = []
    if response and "QueryResponse" in response:
        invoices = response["QueryResponse"].get("Invoice", [])
    logger.info(f"Found {len(invoices)} invoices in QBO.")

    # 4. Initialize Mapper
    mapper = CustomerMapper(database)

    # 5. Process Invoices
    updated_count = 0
    mappings_applied = 0
    fallbacks_applied = 0

    # If not dry run, we use transactions (simple commit at end or batching)
    # The Database class commits on every save currently.
    # To implement batch transaction properly with the existing Database class would require modification.
    # Given the constraint to not drastically change Database class unless needed,
    # we will rely on individual updates but catch exceptions.
    # OR we can manually manage a transaction if we expose cursor.
    # Since existing Database class manages connections per method call, we can't easily wrap in one big transaction without modifying it.
    # However, individual saves are atomic.

    for inv in invoices:
        invoice_id = inv.get('Id')
        customer_id = inv.get('CustomerRef', {}).get('value')

        if not invoice_id:
            continue

        # Normalize invoice dict for mapper (simplified)
        normalized_inv = {
            'id': invoice_id,
            'doc_number': inv.get('DocNumber'),
            'customer_id': customer_id,
            'customer': inv.get('CustomerRef', {}).get('name'),
            'amount': inv.get('TotalAmt', 0),
            'due_date': inv.get('DueDate'),
            # ... other fields if needed by mapper
        }

        # Check if mapping exists
        mapping = database.get_customer_mapping(str(customer_id)) if customer_id else None

        # In dry-run, we just simulate
        if dry_run:
            # Check what would happen
            if mapping:
                logger.info(f"[DRY RUN] Invoice {invoice_id}: Would apply mapping for customer {customer_id}")
                mappings_applied += 1
                updated_count += 1
            else:
                logger.info(f"[DRY RUN] Invoice {invoice_id}: No mapping. Would apply System Default.")
                fallbacks_applied += 1
                updated_count += 1
        else:
            # Apply defaults (this saves to DB if needed)
            try:
                # Check before applying to know if it's an update
                before_meta = database.get_invoice_metadata(str(invoice_id))

                # Apply
                result_inv = mapper.apply_defaults(normalized_inv)

                # Check after
                after_meta = result_inv.get('metadata')

                if before_meta != after_meta:
                    updated_count += 1
                    if mapping:
                        mappings_applied += 1
                    else:
                        fallbacks_applied += 1
                    logger.info(f"Updated Invoice {invoice_id}")
            except Exception as e:
                logger.error(f"Failed to update invoice {invoice_id}: {e}")

    logger.info("-" * 40)
    logger.info("Backfill Summary:")
    logger.info(f"Total Invoices Processed: {len(invoices)}")
    if dry_run:
        logger.info(f"Invoices that WOULD be Updated: {updated_count}")
        logger.info(f"Mappings that WOULD be Applied: {mappings_applied}")
        logger.info(f"Fallbacks that WOULD be Applied: {fallbacks_applied}")
    else:
        logger.info(f"Invoices Updated: {updated_count}")
        logger.info(f"Mappings Applied: {mappings_applied}")
        logger.info(f"Fallbacks Applied: {fallbacks_applied}")
    logger.info("-" * 40)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backfill invoice customer mappings.')
    parser.add_argument('--dry-run', action='store_true', help='Simulate backfill without saving changes')
    args = parser.parse_args()

    backfill_invoices(dry_run=args.dry_run)
