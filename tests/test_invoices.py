import unittest
from unittest.mock import MagicMock, patch
from src.invoices.invoice_manager import InvoiceManager
from src.erp.customer_mapper import CustomerMapper

class TestInvoiceManager(unittest.TestCase):
    def setUp(self):
        self.mock_connector = MagicMock()
        self.mock_database = MagicMock()
        self.mock_predictor = MagicMock()
        self.invoice_manager = InvoiceManager(
            self.mock_connector,
            self.mock_database,
            self.mock_predictor
        )

    def test_fetch_invoices_applies_defaults(self):
        """Test that fetch_invoices calls CustomerMapper.apply_defaults."""
        # Mock QBO response
        self.mock_connector.make_request.return_value = {
            "QueryResponse": {
                "Invoice": [
                    {"Id": "1", "DocNumber": "1001", "TotalAmt": 100.0, "Balance": 100.0}
                ]
            }
        }
        
        # Mock CustomerMapper
        self.invoice_manager.customer_mapper = MagicMock()
        self.invoice_manager.customer_mapper.apply_defaults.return_value = {
            "id": "1",
            "doc_number": "1001",
            "amount": 100.0,
            "metadata": {"vzt_rep": "Test Rep"}
        }

        invoices = self.invoice_manager.fetch_invoices()
        
        self.assertEqual(len(invoices), 1)
        self.invoice_manager.customer_mapper.apply_defaults.assert_called_once()
        self.assertEqual(invoices[0]['metadata']['vzt_rep'], "Test Rep")

    def test_system_default_fallback_integration(self):
        """
        Test that InvoiceManager -> CustomerMapper falls back to System Default
        when no mapping exists and no rep is assigned.
        """
        # Setup Mapper with real logic but mock DB
        mapper = CustomerMapper(self.mock_database)
        self.invoice_manager.customer_mapper = mapper
        
        # Mock DB: No mapping for customer
        self.mock_database.get_invoice_metadata.return_value = {} # No existing metadata
        self.mock_database.get_customer_mapping.return_value = None # No mapping
        
        # Mock DB: Users exist, find admin
        self.mock_database.get_all_users.return_value = [
            {'id': 1, 'email': 'admin@example.com', 'full_name': 'Admin User', 'role': 'admin'}
        ]
        
        # Input invoice
        invoice = {
            'id': '123',
            'customer_id': 'CUST1',
            'amount': 500
        }
        
        # Execute
        result = mapper.apply_defaults(invoice)
        
        # Verify
        # Should have applied System Default (Admin User)
        self.assertIn('metadata', result)
        self.assertEqual(result['metadata']['vzt_rep'], 'Admin User')

        # Should have saved to DB
        self.mock_database.save_invoice_metadata.assert_called_with('123', result['metadata'])

if __name__ == '__main__':
    unittest.main()
