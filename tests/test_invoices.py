import unittest
from unittest.mock import patch, Mock
from src.qbo_client import QBOClient
from src.invoice_manager import InvoiceManager


class TestInvoiceManager(unittest.TestCase):
    def setUp(self):
        client = QBOClient("id", "secret", "refresh", "realm")
        self.manager = InvoiceManager(client)
        self.invoices = [
            {
                'doc_number': '1001',
                'customer_id': 'C1',
                'due_date': '2023-10-01',
                'amount': 100.0,
                'status': 'Unpaid',
                'CustomField': [{'Name': 'Region', 'StringValue': 'North'}]
            },
            {
                'doc_number': '1002',
                'customer_id': 'C2',
                'due_date': '2023-10-05',
                'amount': 200.0,
                'status': 'Paid',
                'CustomField': [{'Name': 'Region', 'StringValue': 'South'}]
            },
            {
                'doc_number': '1003',
                'customer_id': 'C1',
                'due_date': '2023-10-10',
                'amount': 150.0,
                'status': 'Unpaid',
                'CustomField': [{'Name': 'Region', 'StringValue': 'North'}]
            },
            {
                'doc_number': '1004',
                'customer_id': 'C3',
                'due_date': '2023-10-15',
                'amount': 50.0,
                'status': 'Unpaid'
            }
        ]

    def test_fetch_invoices(self):
        invoices = self.manager.fetch_invoices()
        self.assertIsInstance(invoices, list)
    
    @patch('src.qbo_client.requests.post')
    @patch('src.qbo_client.requests.request')
    def test_fetch_invoices_normalization(self, mock_request, mock_post):
        # Mock token refresh
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"access_token": "test_token"}
        )
        
        # Mock API request with QBO-format data
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                "QueryResponse": {
                    "Invoice": [
                        {
                            "Id": "1",
                            "DocNumber": "INV-001",
                            "CustomerRef": {"value": "C1", "name": "Customer One"},
                            "TotalAmt": 500.0,
                            "Balance": 500.0,
                            "DueDate": "2024-02-01",
                            "TxnDate": "2024-01-01",
                            "SalesTermRef": {"name": "Net 30"}
                        }
                    ]
                }
            },
            raise_for_status=lambda: None
        )
        
        invoices = self.manager.fetch_invoices()
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices[0]['id'], '1')
        self.assertEqual(invoices[0]['doc_number'], 'INV-001')
        self.assertEqual(invoices[0]['customer'], 'Customer One')
        self.assertEqual(invoices[0]['amount'], 500.0)
        self.assertEqual(invoices[0]['status'], 'Unpaid')
        self.assertEqual(invoices[0]['terms_days'], 30)

    def test_filter_date_range(self):
        filtered = self.manager.filter_invoices(
            self.invoices,
            start_date='2023-10-02',
            end_date='2023-10-12'
        )
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]['doc_number'], '1002')
        self.assertEqual(filtered[1]['doc_number'], '1003')

    def test_filter_customer(self):
        filtered = self.manager.filter_invoices(self.invoices, customer_id='C1')
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(inv['customer_id'] == 'C1' for inv in filtered))

    def test_filter_invoice_number(self):
        filtered = self.manager.filter_invoices(self.invoices, invoice_number='1002')
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['doc_number'], '1002')

    def test_filter_region(self):
        filtered = self.manager.filter_invoices(self.invoices, region='North')
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(inv['doc_number'] in ['1001', '1003'] for inv in filtered))

    def test_filter_status(self):
        filtered = self.manager.filter_invoices(self.invoices, status='Paid')
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['status'], 'Paid')

    def test_filter_amount(self):
        filtered = self.manager.filter_invoices(self.invoices, min_amount=100, max_amount=150)
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(100 <= inv['amount'] <= 150 for inv in filtered))

    def test_sort_invoices(self):
        sorted_inv = self.manager.sort_invoices(self.invoices, sort_by='amount', reverse=True)
        self.assertEqual(sorted_inv[0]['amount'], 200.0)
        self.assertEqual(sorted_inv[-1]['amount'], 50.0)

    def test_filter_invoice_date_range(self):
        """Test filtering by invoice date (txn_date)"""
        invoices_with_txn = [
            {'doc_number': '1001', 'txn_date': '2023-09-01', 'due_date': '2023-10-01', 'amount': 100.0},
            {'doc_number': '1002', 'txn_date': '2023-09-15', 'due_date': '2023-10-15', 'amount': 200.0},
            {'doc_number': '1003', 'txn_date': '2023-10-01', 'due_date': '2023-11-01', 'amount': 150.0}
        ]
        filtered = self.manager.filter_invoices(
            invoices_with_txn,
            invoice_start_date='2023-09-10',
            invoice_end_date='2023-09-20'
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['doc_number'], '1002')

    def test_filter_blank_amount(self):
        """Test that blank/empty amount filters don't affect results"""
        # Should return all invoices when amount filters are empty strings
        filtered = self.manager.filter_invoices(self.invoices, min_amount='', max_amount='')
        self.assertEqual(len(filtered), 4)
        
        # Should only apply min_amount when max_amount is blank
        filtered = self.manager.filter_invoices(self.invoices, min_amount=100, max_amount='')
        self.assertEqual(len(filtered), 3)

    def test_filter_vzt_metadata(self):
        """Test filtering by VZT Rep metadata"""
        invoices_with_metadata = [
            {'doc_number': '1001', 'metadata': {'vzt_rep': 'John Doe'}},
            {'doc_number': '1002', 'metadata': {'vzt_rep': 'Jane Smith'}},
            {'doc_number': '1003', 'metadata': {'vzt_rep': 'John Doe'}},
            {'doc_number': '1004', 'metadata': {}}
        ]
        filtered = self.manager.filter_invoices(invoices_with_metadata, vzt_rep='John Doe')
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(inv['metadata'].get('vzt_rep') == 'John Doe' for inv in filtered))

    def test_filter_customer_portal(self):
        """Test filtering by Customer Portal metadata"""
        invoices_with_portal = [
            {'doc_number': '1001', 'metadata': {'customer_portal_name': 'OpenInvoice'}},
            {'doc_number': '1002', 'metadata': {'customer_portal_name': 'Cortex'}},
            {'doc_number': '1003', 'metadata': {'customer_portal_name': 'OpenInvoice'}},
            {'doc_number': '1004', 'metadata': {}}
        ]
        filtered = self.manager.filter_invoices(invoices_with_portal, customer_portal='OpenInvoice')
        self.assertEqual(len(filtered), 2)

    def test_filter_missing_portal_submission(self):
        """Test filtering for missing portal submission dates"""
        invoices_with_submission = [
            {'doc_number': '1001', 'metadata': {'portal_submission_date': '2023-10-01'}},
            {'doc_number': '1002', 'metadata': {}},
            {'doc_number': '1003', 'metadata': {'portal_submission_date': '2023-10-05'}},
            {'doc_number': '1004', 'metadata': {}}
        ]
        filtered = self.manager.filter_invoices(invoices_with_submission, missing_portal_submission='true')
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(not inv['metadata'].get('portal_submission_date') for inv in filtered))

    def test_search_query(self):
        """Test search by invoice number or customer name"""
        invoices_with_customer = [
            {'doc_number': 'INV-1001', 'customer': 'Acme Corp', 'id': '1'},
            {'doc_number': 'INV-1002', 'customer': 'Beta LLC', 'id': '2'},
            {'doc_number': 'INV-2001', 'customer': 'Acme Industries', 'id': '3'}
        ]
        # Search by invoice number
        filtered = self.manager.filter_invoices(invoices_with_customer, search_query='1001')
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['doc_number'], 'INV-1001')
        
        # Search by customer name (case insensitive)
        filtered = self.manager.filter_invoices(invoices_with_customer, search_query='acme')
        self.assertEqual(len(filtered), 2)

    def test_sort_by_invoice_date(self):
        """Test sorting by invoice date"""
        invoices_with_txn = [
            {'doc_number': '1001', 'txn_date': '2023-10-15', 'amount': 100.0},
            {'doc_number': '1002', 'txn_date': '2023-10-01', 'amount': 200.0},
            {'doc_number': '1003', 'txn_date': '2023-10-10', 'amount': 150.0}
        ]
        sorted_inv = self.manager.sort_invoices(invoices_with_txn, sort_by='invoice_date', reverse=False)
        self.assertEqual(sorted_inv[0]['doc_number'], '1002')
        self.assertEqual(sorted_inv[-1]['doc_number'], '1001')

    @patch('src.qbo_client.requests.post')
    @patch('src.qbo_client.requests.request')
    def test_fetch_invoices_with_server_side_filters(self, mock_request, mock_post):
        """Test fetching invoices with server-side filtering"""
        # Mock token refresh
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"access_token": "test_token"}
        )
        
        # Mock API request
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                "QueryResponse": {
                    "Invoice": [
                        {
                            "Id": "1",
                            "DocNumber": "INV-001",
                            "CustomerRef": {"value": "C1", "name": "Customer One"},
                            "TotalAmt": 500.0,
                            "Balance": 500.0,
                            "DueDate": "2024-02-01",
                            "TxnDate": "2024-01-01"
                        }
                    ]
                }
            },
            raise_for_status=lambda: None
        )
        
        # Test with status filter for pending invoices
        invoices = self.manager.fetch_invoices(qbo_filters={'status': 'pending'})
        self.assertEqual(len(invoices), 1)
        
        # Verify the WHERE clause was used in the query
        call_args = mock_request.call_args
        query_params = call_args[1]['params']
        self.assertIn("WHERE", query_params['query'])
        self.assertIn("Balance > '0'", query_params['query'])


if __name__ == '__main__':
    unittest.main()
