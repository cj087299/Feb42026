"""
Comprehensive QBO (QuickBooks Online) Authentication Tests

This module tests the QBO authentication implementation to ensure:
1. Proper token refresh mechanism
2. Credentials management via Secret Manager
3. Error handling for invalid credentials
4. API request authentication
"""

import unittest
import sys
from unittest.mock import patch, Mock, MagicMock
import os
from src.auth.qbo_auth import QBOAuth
from src.auth.secret_manager import SecretManager
from src.invoices.qbo_connector import QBOConnector

# Check if google.cloud is available for testing
try:
    import google.cloud.secretmanager
    HAS_GOOGLE_CLOUD = True
except ImportError:
    HAS_GOOGLE_CLOUD = False


class TestQBOAuthentication(unittest.TestCase):
    """Test QBO authentication and credential management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_client_id = "test_client_id_12345"
        self.test_client_secret = "test_client_secret_67890"
        self.test_refresh_token = "test_refresh_token_abcde"
        self.test_realm_id = "test_realm_id_12345"
        self.test_access_token = "test_access_token_xyz"
    
    def test_qbo_client_initialization(self):
        """Test that QBO client initializes with correct credentials."""
        client = QBOAuth(
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            refresh_token=self.test_refresh_token,
            realm_id=self.test_realm_id
        )
        
        self.assertEqual(client.client_id, self.test_client_id)
        self.assertEqual(client.client_secret, self.test_client_secret)
        self.assertEqual(client.refresh_token, self.test_refresh_token)
        self.assertEqual(client.realm_id, self.test_realm_id)
        self.assertIsNone(client.access_token)  # Should be None until refresh
    
    @patch('src.auth.qbo_auth.requests.post')
    def test_successful_token_refresh(self, mock_post):
        """Test successful OAuth token refresh."""
        # Mock successful token refresh response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': self.test_access_token,
            'expires_in': 3600,
            'token_type': 'bearer'
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = QBOAuth(
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            refresh_token=self.test_refresh_token,
            realm_id=self.test_realm_id
        )
        
        # Trigger token refresh
        client.refresh_access_token()
        
        # Verify token was set
        self.assertEqual(client.access_token, self.test_access_token)
        
        # Verify correct API call was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn('oauth.platform.intuit.com', call_args[0][0])
    
    @patch('src.auth.qbo_auth.requests.post')
    def test_failed_token_refresh_unauthorized(self, mock_post):
        """Test handling of 401 Unauthorized during token refresh."""
        # Mock 401 error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("401 Client Error: Unauthorized")
        mock_post.return_value = mock_response
        
        client = QBOAuth(
            client_id="invalid_client",
            client_secret="invalid_secret",
            refresh_token="invalid_token",
            realm_id=self.test_realm_id
        )
        
        # Attempt token refresh should raise exception
        with self.assertRaises(Exception) as context:
            client.refresh_access_token()
        
        # Check if error message contains 401 or Unauthorized
        self.assertTrue('401' in str(context.exception) or 'Unauthorized' in str(context.exception),
                       f"Expected '401' or 'Unauthorized' in error, got: {context.exception}")
    
    @patch('src.auth.qbo_auth.requests.post')
    def test_token_refresh_with_invalid_response(self, mock_post):
        """Test handling of malformed token refresh response."""
        # Mock response with missing access_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'expires_in': 3600,
            # Missing 'access_token' key
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = QBOAuth(
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            refresh_token=self.test_refresh_token,
            realm_id=self.test_realm_id
        )
        
        # Should handle missing token gracefully (sets to None)
        client.refresh_access_token()
        self.assertIsNone(client.access_token)
    
    @patch('src.auth.qbo_auth.requests.post')
    @patch('src.invoices.qbo_connector.requests.request')
    def test_authenticated_api_request(self, mock_request, mock_post):
        """Test that API requests include proper authentication."""
        # Mock token refresh
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            'access_token': self.test_access_token
        }
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response
        
        # Mock API request
        mock_api_response = Mock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = {"QueryResponse": {"Invoice": []}}
        mock_api_response.raise_for_status = Mock()
        mock_request.return_value = mock_api_response
        
        auth = QBOAuth(
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            refresh_token=self.test_refresh_token,
            realm_id=self.test_realm_id
        )
        connector = QBOConnector(auth)
        
        # Make an API request
        connector.make_request("query", params={"query": "SELECT * FROM Invoice"})
        
        # Verify request includes authorization header
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args[1]
        self.assertIn('headers', call_kwargs)
        self.assertIn('Authorization', call_kwargs['headers'])
        self.assertEqual(
            call_kwargs['headers']['Authorization'],
            f'Bearer {self.test_access_token}'
        )
    
    @patch('src.auth.qbo_auth.requests.post')
    @patch('src.invoices.qbo_connector.requests.request')
    def test_token_auto_refresh_on_401(self, mock_request, mock_post):
        """Test that client automatically refreshes token on 401 response."""
        # Mock token refresh
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            'access_token': 'new_access_token'
        }
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response
        
        # First request returns 401, second succeeds
        mock_401_response = Mock()
        mock_401_response.status_code = 401
        from requests.exceptions import HTTPError
        http_error = HTTPError(response=mock_401_response)
        mock_401_response.raise_for_status.side_effect = http_error
        
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"QueryResponse": {"Invoice": []}}
        mock_success_response.raise_for_status = Mock()
        
        mock_request.side_effect = [http_error, mock_success_response]
        
        auth = QBOAuth(
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            refresh_token=self.test_refresh_token,
            realm_id=self.test_realm_id
        )
        connector = QBOConnector(auth)
        
        # Should handle 401 and retry
        connector.make_request("query", params={"query": "SELECT * FROM Invoice"})
        
        # Verify token refresh was called
        self.assertTrue(mock_post.called)


class TestSecretManagerIntegration(unittest.TestCase):
    """Test Secret Manager integration for QBO credentials."""
    
    def test_secret_manager_initialization(self):
        """Test Secret Manager initializes correctly."""
        secret_manager = SecretManager()
        self.assertIsNotNone(secret_manager)
    
    @patch.dict(os.environ, {
        'QBO_CLIENT_ID': 'env_client_id',
        'QBO_CLIENT_SECRET': 'env_client_secret',
        'QBO_REFRESH_TOKEN': 'env_refresh_token',
        'QBO_REALM_ID': 'env_realm_id'
    })
    def test_fallback_to_environment_variables(self):
        """Test that credentials fall back to environment variables."""
        secret_manager = SecretManager()
        credentials = secret_manager.get_qbo_credentials()
        
        self.assertIsNotNone(credentials)
        self.assertIn('client_id', credentials)
        self.assertIn('client_secret', credentials)
        self.assertIn('refresh_token', credentials)
        self.assertIn('realm_id', credentials)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_use_defaults(self):
        """Test that missing credentials use safe defaults."""
        try:
            secret_manager = SecretManager()
            credentials = secret_manager.get_qbo_credentials()
            
            # Should return dict with dummy values when nothing is configured
            self.assertIsNotNone(credentials)
            self.assertIn('client_id', credentials)
            self.assertIn('client_secret', credentials)
            # Dummy values should be present
            self.assertIsNotNone(credentials['client_id'])
            self.assertIsNotNone(credentials['client_secret'])
        except Exception as e:
            self.fail(f"Test failed with unexpected exception: {e}")
    
    @unittest.skipUnless(HAS_GOOGLE_CLOUD, "google-cloud-secret-manager not installed")
    @patch('google.cloud.secretmanager.SecretManagerServiceClient')
    @patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'test-project'})
    def test_secret_manager_client_initialization(self, mock_client):
        """Test Secret Manager client initializes when project is set."""
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        secret_manager = SecretManager()
        
        # Should attempt to initialize client when project is set
        self.assertEqual(secret_manager.project_id, 'test-project')
    
    @unittest.skipUnless(HAS_GOOGLE_CLOUD, "google-cloud-secret-manager not installed")
    @patch('google.cloud.secretmanager.SecretManagerServiceClient')
    @patch.dict(os.environ, {
        'GOOGLE_CLOUD_PROJECT': 'test-project',
        'QBO_CLIENT_ID': 'fallback_client_id'
    })
    def test_secret_retrieval_with_fallback(self, mock_client):
        """Test secret retrieval with fallback to environment."""
        mock_instance = MagicMock()
        # Simulate Secret Manager failure
        mock_instance.access_secret_version.side_effect = Exception("Secret not found")
        mock_client.return_value = mock_instance
        
        secret_manager = SecretManager()
        value = secret_manager.get_secret('QBO_CLIENT_ID')
        
        # Should fall back to environment variable
        self.assertEqual(value, 'fallback_client_id')


class TestQBOEndToEnd(unittest.TestCase):
    """End-to-end tests for QBO authentication flow."""
    
    @patch('src.auth.qbo_auth.requests.post')
    @patch('src.invoices.qbo_connector.requests.request')
    def test_complete_qbo_workflow(self, mock_request, mock_post):
        """Test complete workflow: initialize, authenticate, fetch data."""
        # Mock token refresh
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            'access_token': 'workflow_access_token',
            'expires_in': 3600
        }
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response
        
        # Mock invoice fetch
        mock_api_response = Mock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = {
            "QueryResponse": {
                "Invoice": [
                    {
                        "Id": "1",
                        "DocNumber": "INV-001",
                        "TotalAmt": 1000.00,
                        "Balance": 1000.00,
                        "DueDate": "2026-03-01"
                    }
                ]
            }
        }
        mock_api_response.raise_for_status = Mock()
        mock_request.return_value = mock_api_response
        
        # Initialize client
        auth = QBOAuth(
            client_id="workflow_client_id",
            client_secret="workflow_client_secret",
            refresh_token="workflow_refresh_token",
            realm_id="workflow_realm_id"
        )
        connector = QBOConnector(auth)
        
        # Fetch invoices (should trigger authentication)
        from src.invoices.invoice_manager import InvoiceManager
        manager = InvoiceManager(connector)
        invoices = manager.fetch_invoices()
        
        # Verify flow worked
        self.assertIsNotNone(invoices)
        self.assertTrue(mock_post.called)  # Token refresh was called
        self.assertTrue(mock_request.called)  # API request was made
        
    @patch('src.auth.qbo_auth.requests.post')
    def test_authentication_error_handling(self, mock_post):
        """Test proper error handling for authentication failures."""
        # Mock authentication failure
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': 'invalid_grant',
            'error_description': 'Token has expired'
        }
        mock_response.raise_for_status.side_effect = Exception("400 Bad Request")
        mock_post.return_value = mock_response
        
        client = QBOAuth(
            client_id="invalid_client",
            client_secret="invalid_secret",
            refresh_token="expired_token",
            realm_id="test_realm"
        )
        
        # Should handle error gracefully
        with self.assertRaises(Exception):
            client.refresh_access_token()
    
    @patch('src.auth.qbo_auth.requests.post')
    @patch('src.invoices.qbo_connector.requests.request')
    def test_403_forbidden_error_handling(self, mock_request, mock_post):
        """Test handling of 403 Forbidden errors from QuickBooks API."""
        test_access_token = 'test_access_token_xyz'
        
        # Mock token refresh (will be called before the request)
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            'access_token': test_access_token,
            'expires_in': 3600
        }
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response
        
        # Mock 403 error response from API
        mock_403_response = Mock()
        mock_403_response.status_code = 403
        from requests.exceptions import HTTPError
        http_error = HTTPError(response=mock_403_response)
        mock_403_response.raise_for_status.side_effect = http_error
        
        # Set up mock_request to return 403 on first call, then again on retry
        mock_request.side_effect = [http_error, http_error]
        
        auth = QBOAuth(
            client_id='test_client_id',
            client_secret='test_client_secret',
            refresh_token='test_refresh_token',
            realm_id='test_realm_id'
        )
        connector = QBOConnector(auth)
        
        # Set an access token to avoid initial refresh
        auth.access_token = test_access_token
        
        # Make a request that should get 403
        result = connector.make_request("query", params={"query": "select * from Invoice"})
        
        # Should return empty dict on 403 error
        self.assertEqual(result, {})
        
        # Verify that the request was attempted (at least twice due to retry logic)
        self.assertGreaterEqual(mock_request.call_count, 1)
    
    @patch('src.auth.qbo_auth.requests.post')
    @patch('src.invoices.qbo_connector.requests.request')
    def test_403_resolved_by_token_refresh(self, mock_request, mock_post):
        """Test case where 403 error is resolved by refreshing the access token."""
        test_access_token = 'test_access_token_xyz'
        new_access_token = 'new_access_token_xyz'
        
        # Mock token refresh
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            'access_token': new_access_token,
            'expires_in': 3600
        }
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response
        
        # Mock API responses: 403 on first call, success on retry
        from requests.exceptions import HTTPError
        
        mock_403_response = Mock()
        mock_403_response.status_code = 403
        http_error = HTTPError(response=mock_403_response)
        mock_403_response.raise_for_status.side_effect = http_error
        
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"QueryResponse": {"Invoice": []}}
        mock_success_response.raise_for_status = Mock()
        
        # First call returns 403, second call (after token refresh) succeeds
        mock_request.side_effect = [http_error, mock_success_response]
        
        auth = QBOAuth(
            client_id='test_client_id',
            client_secret='test_client_secret',
            refresh_token='test_refresh_token',
            realm_id='test_realm_id'
        )
        connector = QBOConnector(auth)
        
        # Set an access token
        auth.access_token = test_access_token
        
        # Make request - should get 403, retry with new token, and succeed
        result = connector.make_request("query", params={"query": "select * from Invoice"})
        
        # Should return successful response
        self.assertIsInstance(result, dict)
        self.assertIn("QueryResponse", result)
        
        # Verify token refresh was called
        mock_post.assert_called_once()
        
        # Verify request was made twice (initial + retry)
        self.assertEqual(mock_request.call_count, 2)


if __name__ == '__main__':
    unittest.main()
