"""Tests for QBO OAuth v2 authorization endpoint."""

import unittest
import json
from main import app
from tests.test_helpers import AuthenticatedTestCase
from src.auth.utils import hash_password

class TestQBOOAuthV2(AuthenticatedTestCase):
    """Tests for QBO OAuth v2 endpoints."""
    
    def setUp(self):
        """Set up test client and authenticated admin user."""
        self.app = app
        self.client = self.app.test_client()
        
        # Create and login a test admin user
        self.test_user_email = 'testoauth@example.com'
        self.test_user_password = 'testpass123'
        
        try:
            self.cleanup_test_user(self.test_user_email)
        except Exception:
            pass
        
        self.create_and_login_user(
            self.client, 
            email=self.test_user_email, 
            password=self.test_user_password,
            role='admin'
        )
    
    def tearDown(self):
        try:
            self.cleanup_test_user(self.test_user_email)
        except Exception:
            pass
    
    def test_oauth_authorize_v2_uses_https_redirect_uri(self):
        response = self.client.post('/api/qbo/oauth/authorize-v2')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        auth_url = data['authorization_url']
        self.assertIn('https%3A%2F%2F', auth_url)
        self.assertIn('%2Fapi%2Fqbo%2Foauth%2Fcallback', auth_url)
    
    def test_oauth_authorize_v2_requires_admin(self):
        regular_user_email = 'regular@example.com'
        try:
            self.cleanup_test_user(regular_user_email)
        except Exception:
            pass
        
        from main import database
        pw_hash = hash_password('testpass123')
        database.create_user(regular_user_email, pw_hash, 'Regular', 'view_only')
        
        self.client.post('/api/logout')
        self.client.post('/api/login', json={
            'email': regular_user_email,
            'password': 'testpass123'
        })
        
        response = self.client.post('/api/qbo/oauth/authorize-v2')
        self.assertEqual(response.status_code, 403)
        
        try:
            self.cleanup_test_user(regular_user_email)
        except Exception:
            pass

if __name__ == '__main__':
    unittest.main()
