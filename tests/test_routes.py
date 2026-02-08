import unittest
import json
from main import app


class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_root_route(self):
        """Test that the root route returns API information"""
        response = self.client.get('/')
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

    def test_health_route(self):
        """Test that the health route returns healthy status"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')


if __name__ == '__main__':
    unittest.main()
