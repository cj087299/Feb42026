import unittest
from unittest.mock import MagicMock, patch
from flask import session
from main import app, get_fresh_qbo_connector

class TestLiquidity(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('main.get_fresh_qbo_connector')
    @patch('main.InvoiceManager')
    def test_get_liquidity_metrics(self, mock_invoice_manager, mock_get_connector):
        # Mock QBO Connector
        mock_connector = MagicMock()
        mock_get_connector.return_value = (mock_connector, True)

        # Mock Invoice Manager instance
        mock_inv_mgr_instance = mock_invoice_manager.return_value

        # Mock Data
        # AR: 2 invoices, 500 each = 1000
        mock_inv_mgr_instance.fetch_invoices.return_value = [
            {'balance': 500}, {'balance': 500}
        ]

        # AP: 2 bills, 200 each = 400
        mock_connector.fetch_bills.return_value = [
            {'Balance': 200}, {'Balance': 200}
        ]

        # Bank: 1 account, 2000
        mock_connector.fetch_bank_accounts.return_value = [
            {'CurrentBalance': 2000}
        ]

        with self.app.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_role'] = 'admin'

        response = self.app.get('/api/liquidity')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertEqual(data['total_ar'], 1000.0)
        self.assertEqual(data['total_ap'], 400.0)
        self.assertEqual(data['total_bank_balance'], 2000.0)

        # Quick Ratio = (Cash + AR) / AP = (2000 + 1000) / 400 = 3000 / 400 = 7.5
        self.assertEqual(data['quick_ratio'], 7.5)

    @patch('main.get_fresh_qbo_connector')
    @patch('main.InvoiceManager')
    def test_liquidity_zero_ap(self, mock_invoice_manager, mock_get_connector):
        mock_connector = MagicMock()
        mock_get_connector.return_value = (mock_connector, True)
        mock_inv_mgr_instance = mock_invoice_manager.return_value

        mock_inv_mgr_instance.fetch_invoices.return_value = [{'balance': 100}]
        mock_connector.fetch_bills.return_value = [] # 0 AP
        mock_connector.fetch_bank_accounts.return_value = [{'CurrentBalance': 100}]

        with self.app.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_role'] = 'admin'

        response = self.app.get('/api/liquidity')
        data = response.get_json()

        self.assertEqual(data['total_ap'], 0.0)
        self.assertIsNone(data['quick_ratio'])

    @patch('main.get_fresh_qbo_connector')
    def test_liquidity_invalid_credentials(self, mock_get_connector):
        mock_get_connector.return_value = (MagicMock(), False)

        with self.app.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_role'] = 'admin'

        response = self.app.get('/api/liquidity')
        data = response.get_json()

        self.assertEqual(data['total_ar'], 0.0)
        self.assertEqual(data['total_ap'], 0.0)
        self.assertEqual(data['total_bank_balance'], 0.0)
        self.assertIsNone(data['quick_ratio'])

if __name__ == '__main__':
    unittest.main()
