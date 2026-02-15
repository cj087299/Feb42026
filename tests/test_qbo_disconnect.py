"""
Tests for QBO disconnect functionality
"""

import unittest
from unittest.mock import patch, Mock, MagicMock
from src.qbo_client import QBOClient
from src.secret_manager import SecretManager
from src.database import Database


class TestQBODisconnect(unittest.TestCase):
    """Test QBO disconnect functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_client_id = "test_client_id_12345"
        self.test_client_secret = "test_client_secret_67890"
        self.test_refresh_token = "test_refresh_token_abcde"
        self.test_realm_id = "test_realm_id_12345"
        self.test_access_token = "test_access_token_xyz"
    
    def test_qbo_client_disconnect_with_database(self):
        """Test QBOClient disconnect method with database."""
        # Create mock database
        mock_db = Mock(spec=Database)
        mock_db.delete_qbo_credentials.return_value = True
        
        # Create client with mock database
        client = QBOClient(
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            refresh_token=self.test_refresh_token,
            realm_id=self.test_realm_id,
            database=mock_db
        )
        
        # Set access token
        client.access_token = self.test_access_token
        
        # Call disconnect
        result = client.disconnect()
        
        # Verify disconnect was successful
        self.assertTrue(result)
        
        # Verify database delete was called
        mock_db.delete_qbo_credentials.assert_called_once()
        
        # Verify tokens were cleared
        self.assertIsNone(client.access_token)
        self.assertIsNone(client.refresh_token)
        self.assertIsNone(client.realm_id)
    
    def test_qbo_client_disconnect_without_database(self):
        """Test QBOClient disconnect method without database."""
        # Create client without database
        client = QBOClient(
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            refresh_token=self.test_refresh_token,
            realm_id=self.test_realm_id
        )
        
        # Call disconnect
        result = client.disconnect()
        
        # Verify disconnect failed without database
        self.assertFalse(result)
    
    def test_secret_manager_delete_qbo_secrets(self):
        """Test SecretManager delete_qbo_secrets method."""
        # Create mock database
        mock_db = Mock(spec=Database)
        mock_db.delete_qbo_credentials.return_value = True
        
        # Create SecretManager with mock database
        secret_manager = SecretManager(database=mock_db)
        
        # Call delete_qbo_secrets
        result = secret_manager.delete_qbo_secrets()
        
        # Verify success
        self.assertTrue(result)
        
        # Verify database delete was called
        mock_db.delete_qbo_credentials.assert_called_once()
    
    def test_secret_manager_delete_qbo_secrets_with_db_error(self):
        """Test SecretManager delete_qbo_secrets with database error."""
        # Create mock database that raises an exception
        mock_db = Mock(spec=Database)
        mock_db.delete_qbo_credentials.side_effect = Exception("Database error")
        
        # Create SecretManager with mock database
        secret_manager = SecretManager(database=mock_db)
        
        # Call delete_qbo_secrets - should still return True
        # (because it catches and logs the database error)
        result = secret_manager.delete_qbo_secrets()
        
        # Verify it still returns True (graceful handling)
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
