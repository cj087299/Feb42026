"""Tests for QBO OAuth v2 authorization endpoint."""

import unittest
import json
from main import app
from tests.test_helpers import AuthenticatedTestCase


class TestQBOOAuthV2(AuthenticatedTestCase):
    """Tests for QBO OAuth v2 endpoints."""
    
    def setUp(self):
        """Set up test client and authenticated admin user."""
        self.app = app
        self.client = self.app.test_client()
        
        # Create and login a test admin user
        self.test_user_email = 'testoauth@example.com'
        self.test_user_password = 'testpass123'
        
        # Clean up any existing test user
        try:
            self.cleanup_test_user(self.test_user_email)
        except Exception:
            pass
        
        # Create and login test user
        self.create_and_login_user(
            self.client, 
            email=self.test_user_email, 
            password=self.test_user_password,
            role='admin'
        )
    
    def tearDown(self):
        """Clean up test data."""
        try:
            self.cleanup_test_user(self.test_user_email)
        except Exception:
            pass
    
    def test_oauth_authorize_v2_uses_https_redirect_uri(self):
        """Test that OAuth authorize v2 generates HTTPS redirect URI even with HTTP host."""
        # Call the authorize endpoint
        response = self.client.post('/api/qbo/oauth/authorize-v2')
        
        # Check response status
        self.assertEqual(response.status_code, 200)
        
        # Parse response data
        data = json.loads(response.data)
        
        # Verify authorization URL is returned
        self.assertIn('authorization_url', data)
        auth_url = data['authorization_url']
        
        # Verify the authorization URL contains HTTPS redirect URI
        self.assertIn('https%3A%2F%2F', auth_url, 
                     "Authorization URL should contain HTTPS redirect URI (URL-encoded)")
        
        # Verify HTTP redirect URI is NOT present
        self.assertNotIn('http%3A%2F%2F', auth_url,
                        "Authorization URL should NOT contain HTTP redirect URI")
        
        # Verify the redirect URI path is correct
        self.assertIn('%2Fapi%2Fqbo%2Foauth%2Fcallback', auth_url,
                     "Authorization URL should contain the correct callback path")
    
    def test_oauth_authorize_v2_requires_admin(self):
        """Test that OAuth authorize v2 requires admin role."""
        # Create and login a regular user (non-admin)
        regular_user_email = 'regular@example.com'
        try:
            self.cleanup_test_user(regular_user_email)
        except Exception:
            pass
        
        # Create regular user
        self.create_test_user(
            email=regular_user_email,
            password='testpass123',
            role='user'
        )
        
        # Login as regular user
        self.client.post('/api/login', json={
            'email': regular_user_email,
            'password': 'testpass123'
        })
        
        # Try to access OAuth authorize endpoint
        response = self.client.post('/api/qbo/oauth/authorize-v2')
        
        # Should get permission denied
        self.assertEqual(response.status_code, 403)
        
        # Cleanup
        try:
            self.cleanup_test_user(regular_user_email)
        except Exception:
            pass


if __name__ == '__main__':
    unittest.main()
