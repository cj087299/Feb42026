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


if __name__ == '__main__':
    unittest.main()
