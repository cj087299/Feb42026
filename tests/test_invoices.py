import unittest
from datetime import datetime
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
