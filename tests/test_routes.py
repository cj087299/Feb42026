import unittest
import json
from main import app
from src.common.database import Database
database = Database()
from tests.test_helpers import AuthenticatedTestCase


class TestRoutes(AuthenticatedTestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        # Create and login a test user for authenticated requests
        self.test_user_email = 'testroutes@example.com'
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

    def test_root_route(self):
        """Test that the root route returns API information"""
        # Test API JSON response
        response = self.client.get('/', headers={'Accept': 'application/json'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify response structure
        self.assertIn('service', data)
        self.assertIn('version', data)
        self.assertIn('endpoints', data)
        
        # Verify endpoints are listed
        self.assertIn('health', data['endpoints'])
        self.assertIn('invoices', data['endpoints'])
        self.assertIn('cashflow', data['endpoints'])
        
        # Test HTML response
        response_html = self.client.get('/', headers={'Accept': 'text/html'})
        self.assertEqual(response_html.status_code, 200)
        self.assertIn(b'VZT Accounting', response_html.data)

    def test_health_route(self):
        """Test that the health route returns healthy status"""
        # Test API JSON response
        response = self.client.get('/health', headers={'Accept': 'application/json'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        
        # Test HTML response
        response_html = self.client.get('/health', headers={'Accept': 'text/html'})
        self.assertEqual(response_html.status_code, 200)
        self.assertIn(b'System Status', response_html.data)
    
    def test_invoices_page(self):
        """Test that the invoices page is accessible"""
        response = self.client.get('/invoices')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invoice Management', response.data)
    
    def test_cashflow_page(self):
        """Test that the cashflow page is accessible"""
        response = self.client.get('/cashflow')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cash Flow Projection', response.data)
    
    def test_qbo_settings_v2_page_accessible_for_admin(self):
        """Test that the QBO settings v2 page is accessible for admin users"""
        response = self.client.get('/qbo-settings-v2')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'QuickBooks Settings', response.data)
        self.assertIn(b'v2', response.data)
    
    def test_qbo_settings_v2_page_has_last_revised(self):
        """Test that the QBO settings v2 page has last revised date/time"""
        response = self.client.get('/qbo-settings-v2')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Last Revised:', response.data)
        self.assertIn(b'lastRevised', response.data)


if __name__ == '__main__':
    unittest.main()
