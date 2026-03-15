"""
Tests for QBO Token Management System

This module tests the centralized QBO token management functionality including:
- Database storage of credentials
- Token refresh mechanism
- Admin-only access controls
- Automatic token updates
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.common.database import Database
from src.auth.qbo_auth import QBOAuth
from src.auth.secret_manager import SecretManager


class TestQBOTokenManagement(unittest.TestCase):
    """Test QBO token management in database."""
    
    def setUp(self):
        """Set up test database."""
        self.test_db_path = 'test_token_mgmt.db'
        # Remove test database if it exists
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = Database(self.test_db_path)
        
        self.test_credentials = {
            'client_id': 'test_client_id_123',
            'client_secret': 'test_client_secret_456',
            'refresh_token': 'RT1-test-refresh-token',
            'realm_id': '9341453050298464'
        }
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'test_db_path') and os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    def test_save_qbo_credentials(self):
        """Test saving QBO credentials to database."""
        success = self.db.save_qbo_credentials(self.test_credentials, created_by_user_id=1)
        self.assertTrue(success)
        
        # Verify credentials were saved
        saved_creds = self.db.get_qbo_credentials()
        self.assertIsNotNone(saved_creds)
        self.assertEqual(saved_creds['client_id'], self.test_credentials['client_id'])
        self.assertEqual(saved_creds['realm_id'], self.test_credentials['realm_id'])
    
    def test_get_qbo_credentials_when_none_exist(self):
        """Test getting credentials when none are stored."""
        creds = self.db.get_qbo_credentials()
        self.assertIsNone(creds)
    
    def test_update_qbo_tokens(self):
        """Test updating access and refresh tokens."""
        # First save credentials
        self.db.save_qbo_credentials(self.test_credentials, created_by_user_id=1)
        
        # Update tokens
        new_access_token = 'new_access_token_xyz'
        new_refresh_token = 'new_refresh_token_abc'
        
        success = self.db.update_qbo_tokens(new_access_token, new_refresh_token)
        self.assertTrue(success)
        
        # Verify tokens were updated
        updated_creds = self.db.get_qbo_credentials()
        self.assertEqual(updated_creds['access_token'], new_access_token)
        self.assertEqual(updated_creds['refresh_token'], new_refresh_token)
    
    def test_update_only_access_token(self):
        """Test updating only the access token."""
        # First save credentials
        self.db.save_qbo_credentials(self.test_credentials, created_by_user_id=1)
        original_refresh = self.test_credentials['refresh_token']
        
        # Update only access token
        new_access_token = 'new_access_token_only'
        success = self.db.update_qbo_tokens(new_access_token)
        self.assertTrue(success)
        
        # Verify only access token changed
        updated_creds = self.db.get_qbo_credentials()
        self.assertEqual(updated_creds['access_token'], new_access_token)
        self.assertEqual(updated_creds['refresh_token'], original_refresh)
    
    def test_token_expiration_timestamps(self):
        """Test that expiration timestamps are set correctly."""
        self.db.save_qbo_credentials(self.test_credentials, created_by_user_id=1)
        
        creds = self.db.get_qbo_credentials()
        
        # Check that expiration times are set
        self.assertIsNotNone(creds['access_token_expires_at'])
        self.assertIsNotNone(creds['refresh_token_expires_at'])
        
        # Parse timestamps
        access_expires = datetime.fromisoformat(creds['access_token_expires_at'])
        refresh_expires = datetime.fromisoformat(creds['refresh_token_expires_at'])
        now = datetime.now()
        
        # Access token should expire in ~1 hour
        access_delta = (access_expires - now).total_seconds()
        self.assertGreater(access_delta, 3000)  # More than 50 minutes
        self.assertLess(access_delta, 4000)     # Less than 67 minutes
        
        # Refresh token should expire in ~101 days
        refresh_delta = (refresh_expires - now).days
        self.assertGreaterEqual(refresh_delta, 100)
        self.assertLess(refresh_delta, 102)
    
    def test_replace_existing_credentials(self):
        """Test that saving new credentials replaces old ones."""
        # Save first set of credentials
        self.db.save_qbo_credentials(self.test_credentials, created_by_user_id=1)
        
        # Save second set
        new_credentials = {
            'client_id': 'new_client_id',
            'client_secret': 'new_secret',
            'refresh_token': 'new_refresh',
            'realm_id': 'new_realm'
        }
        self.db.save_qbo_credentials(new_credentials, created_by_user_id=2)
        
        # Verify only new credentials exist
        creds = self.db.get_qbo_credentials()
        self.assertEqual(creds['client_id'], new_credentials['client_id'])
        self.assertEqual(creds['realm_id'], new_credentials['realm_id'])


class TestQBOAuthWithDatabase(unittest.TestCase):
    """Test QBO client with database integration."""
    
    def setUp(self):
        """Set up test client and database."""
        self.test_db_path = 'test_client_db.db'
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = Database(self.test_db_path)
        self.client = QBOAuth(
            'test_id',
            'test_secret',
            'test_refresh',
            'test_realm',
            database=self.db
        )
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'test_db_path') and os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    def test_client_has_database(self):
        """Test that client is initialized with database."""
        self.assertIsNotNone(self.client.database)
        self.assertIsInstance(self.client.database, Database)
    
    @patch('src.auth.qbo_auth.requests.post')
    def test_token_refresh_updates_database(self, mock_post):
        """Test that token refresh updates the database."""
        # Save initial credentials
        self.db.save_qbo_credentials({
            'client_id': 'test_id',
            'client_secret': 'test_secret',
            'refresh_token': 'test_refresh',
            'realm_id': 'test_realm'
        }, created_by_user_id=1)
        
        # Mock successful token refresh
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Refresh token
        self.client.refresh_access_token()
        
        # Verify database was updated
        creds = self.db.get_qbo_credentials()
        self.assertEqual(creds['access_token'], 'new_access_token')
        self.assertEqual(creds['refresh_token'], 'new_refresh_token')
    
    @patch('src.auth.qbo_auth.requests.post')
    def test_token_refresh_without_new_refresh_token(self, mock_post):
        """Test token refresh when QBO doesn't return new refresh token."""
        # Save initial credentials
        self.db.save_qbo_credentials({
            'client_id': 'test_id',
            'client_secret': 'test_secret',
            'refresh_token': 'original_refresh',
            'realm_id': 'test_realm'
        }, created_by_user_id=1)
        
        # Mock token refresh without new refresh token
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Refresh token
        self.client.refresh_access_token()
        
        # Verify only access token was updated
        creds = self.db.get_qbo_credentials()
        self.assertEqual(creds['access_token'], 'new_access_token')
        self.assertEqual(creds['refresh_token'], 'original_refresh')


class TestSecretManagerWithDatabase(unittest.TestCase):
    """Test Secret Manager with database priority."""
    
    def setUp(self):
        """Set up test database and secret manager."""
        self.test_db_path = 'test_sm_db.db'
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = Database(self.test_db_path)
        self.sm = SecretManager(database=self.db)
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'test_db_path') and os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    def test_database_credentials_take_priority(self):
        """Test that database credentials are used over environment variables."""
        # Save credentials to database
        db_credentials = {
            'client_id': 'db_client_id',
            'client_secret': 'db_secret',
            'refresh_token': 'db_refresh',
            'realm_id': 'db_realm'
        }
        self.db.save_qbo_credentials(db_credentials, created_by_user_id=1)
        
        # Get credentials (should come from database)
        creds = self.sm.get_qbo_credentials()
        
        self.assertEqual(creds['client_id'], 'db_client_id')
        self.assertEqual(creds['realm_id'], 'db_realm')
    
    @patch.dict(os.environ, {
        'QBO_CLIENT_ID': 'env_client_id',
        'QBO_REFRESH_TOKEN': 'env_refresh',
        'QBO_REALM_ID': 'env_realm'
    })
    def test_fallback_to_environment_variables(self):
        """Test fallback to environment variables when no database credentials."""
        # Don't save anything to database
        creds = self.sm.get_qbo_credentials()
        
        # Should fall back to environment variables
        self.assertEqual(creds['client_id'], 'env_client_id')
        self.assertEqual(creds['refresh_token'], 'env_refresh')
        self.assertEqual(creds['realm_id'], 'env_realm')
    
    def test_default_values_when_no_credentials(self):
        """Test that default dummy values are used when no credentials available."""
        # Clear environment variables
        for var in ['QBO_CLIENT_ID', 'QBO_CLIENT_SECRET', 'QBO_REFRESH_TOKEN', 'QBO_REALM_ID']:
            if var in os.environ:
                del os.environ[var]
        
        creds = self.sm.get_qbo_credentials()
        
        # Should use dummy values
        self.assertEqual(creds['client_id'], 'dummy_id')
        self.assertEqual(creds['client_secret'], 'dummy_secret')
        self.assertEqual(creds['refresh_token'], 'dummy_refresh')
        self.assertEqual(creds['realm_id'], 'dummy_realm')


if __name__ == '__main__':
    unittest.main()
