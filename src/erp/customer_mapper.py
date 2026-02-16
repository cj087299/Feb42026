import logging
from typing import Dict, Optional, Any
from src.common.database import Database

logger = logging.getLogger(__name__)

class CustomerMapper:
    """Handles mapping of QBO customers to VZT defaults."""

    def __init__(self, database: Database):
        self.database = database

    def apply_defaults(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply default mappings to an invoice if they exist.
        Updates the invoice metadata in the database.

        Args:
            invoice: Invoice dictionary from QBO.

        Returns:
            The updated invoice dictionary (with potential metadata attached).
        """
        invoice_id = invoice.get('id') or invoice.get('doc_number')
        customer_id = invoice.get('customer_id')

        if not invoice_id:
            logger.warning(f"Invoice missing ID, skipping mapping.")
            return invoice

        # Check if metadata already exists for this invoice
        current_metadata = self.database.get_invoice_metadata(str(invoice_id))

        if current_metadata:
            new_metadata = current_metadata.copy()
        else:
            new_metadata = {}

        updated = False

        # Get mapping if customer_id exists
        mapping = None
        if customer_id:
            mapping = self.database.get_customer_mapping(str(customer_id))

        # Determine Default Rep
        default_rep_id = None
        default_rep_name = None

        if mapping and mapping.get('default_vzt_rep_id'):
            # Validate rep exists
            user = self.database.get_user_by_id(mapping['default_vzt_rep_id'])
            if user:
                default_rep_id = mapping['default_vzt_rep_id']
                default_rep_name = user['full_name'] or user['email']
            else:
                logger.warning(f"Mapped rep ID {mapping['default_vzt_rep_id']} for customer {customer_id} not found.")

        # Fallback to System Default if no valid mapped rep found
        if not default_rep_id:
             # Find system default (e.g. first admin)
             users = self.database.get_all_users()
             admin = None
             if users:
                 # Try to find an admin, or fallback to first user
                 admin = next((u for u in users if u['role'] in ['admin', 'master_admin']), users[0])

             if admin:
                 default_rep_id = admin['id']
                 default_rep_name = admin['full_name'] or admin['email']
             else:
                 # Last resort if no users exist
                 default_rep_name = "System Default"

        # Apply Rep if not set in metadata
        if not new_metadata.get('vzt_rep'):
             if default_rep_name:
                 new_metadata['vzt_rep'] = default_rep_name
                 updated = True

        # Apply Portal Name from Mapping
        if mapping and mapping.get('default_portal_name'):
            if not new_metadata.get('customer_portal_name'):
                new_metadata['customer_portal_name'] = mapping['default_portal_name']
                updated = True

        # Apply Net Terms override in memory if mapping exists
        if mapping and mapping.get('default_net_terms'):
             invoice['terms_days'] = mapping['default_net_terms']

        if updated:
            self.database.save_invoice_metadata(str(invoice_id), new_metadata)
            # Update the invoice object with new metadata
            invoice['metadata'] = new_metadata
            logger.info(f"Applied customer mapping defaults to invoice {invoice_id}")
        elif current_metadata:
             invoice['metadata'] = current_metadata

        return invoice
