import unittest
from unittest.mock import patch, Mock
from src.qbo_client import QBOClient


class TestQBOClient(unittest.TestCase):
    def setUp(self):
        self.client = QBOClient("id", "secret", "refresh", "realm")

    def test_init(self):
        self.assertEqual(self.client.client_id, "id")
        self.assertEqual(self.client.realm_id, "realm")

    @patch('src.qbo_client.requests.post')
    @patch('src.qbo_client.requests.request')
    def test_make_request(self, mock_request, mock_post):
        # Mock token refresh
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"access_token": "test_token"}
        )
        
        # Mock API request
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {"QueryResponse": {}},
            raise_for_status=lambda: None
        )
        
        response = self.client.make_request("query")
        self.assertIsInstance(response, dict)
    
    @patch('src.qbo_client.requests.post')
    def test_fetch_bank_accounts(self, mock_post):
        # Mock token refresh
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"access_token": "test_token"}
        )
        
        with patch('src.qbo_client.requests.request') as mock_request:
            # Mock API request for bank accounts with realistic balances
            mock_request.return_value = Mock(
                status_code=200,
                json=lambda: {
                    "QueryResponse": {
                        "Account": [
                            {
                                "Id": "35",
                                "Name": "Business Checking Account",
                                "AcctNum": "****4567",
                                "CurrentBalance": 45789.32,
                                "AccountType": "Bank",
                                "AccountSubType": "Checking",
                                "CurrencyRef": {"value": "USD", "name": "United States Dollar"}
                            },
                            {
                                "Id": "42",
                                "Name": "Savings Account",
                                "AcctNum": "****8901",
                                "CurrentBalance": 125000.00,
                                "AccountType": "Bank",
                                "AccountSubType": "Savings",
                                "CurrencyRef": {"value": "USD", "name": "United States Dollar"}
                            },
                            {
                                "Id": "58",
                                "Name": "Payroll Account",
                                "AcctNum": "****2345",
                                "CurrentBalance": 28456.78,
                                "AccountType": "Bank",
                                "AccountSubType": "Checking",
                                "CurrencyRef": {"value": "USD", "name": "United States Dollar"}
                            }
                        ]
                    }
                },
                raise_for_status=lambda: None
            )
            
            accounts = self.client.fetch_bank_accounts()
            self.assertIsInstance(accounts, list)
            self.assertEqual(len(accounts), 3)
            self.assertEqual(accounts[0]['Name'], "Business Checking Account")
            self.assertEqual(accounts[0]['CurrentBalance'], 45789.32)
            self.assertEqual(accounts[1]['CurrentBalance'], 125000.00)
            self.assertEqual(accounts[2]['CurrentBalance'], 28456.78)
            # Verify total balance across all accounts
            total_balance = sum(acc['CurrentBalance'] for acc in accounts)
            self.assertEqual(total_balance, 199246.10)


if __name__ == '__main__':
    unittest.main()
