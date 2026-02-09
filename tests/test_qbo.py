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
            # Mock API request for bank accounts
            mock_request.return_value = Mock(
                status_code=200,
                json=lambda: {
                    "QueryResponse": {
                        "Account": [
                            {
                                "Id": "1",
                                "Name": "Checking Account",
                                "CurrentBalance": 5000.0
                            }
                        ]
                    }
                },
                raise_for_status=lambda: None
            )
            
            accounts = self.client.fetch_bank_accounts()
            self.assertIsInstance(accounts, list)
            self.assertEqual(len(accounts), 1)
            self.assertEqual(accounts[0]['Name'], "Checking Account")


if __name__ == '__main__':
    unittest.main()
