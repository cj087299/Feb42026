import unittest
import json
from main import app, database
from tests.test_helpers import AuthenticatedTestCase


class TestNewFeatures(AuthenticatedTestCase):
    """Test new VZT Accounting features."""
    
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.db = database
        
        # Create and login a test user with admin role for testing
        self.test_user_email = 'testfeatures@example.com'
        self.test_user_password = 'testpass123'
        
        # Clean up any existing test user
        try:
            self.cleanup_test_user(self.test_user_email)
        except Exception:
            pass
        
        # Create and login test user with admin role (has all permissions)
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
    
    def test_invoice_metadata_api(self):
        """Test invoice metadata endpoints."""
        # Test saving metadata
        test_invoice_id = "TEST001"
        metadata = {
            "vzt_rep": "John Doe",
            "sent_to_vzt_rep_date": "2026-02-01",
            "customer_portal_name": "Portal A",
            "portal_submission_date": "2026-02-05"
        }
        
        response = self.client.post(
            f'/api/invoices/{test_invoice_id}/metadata',
            data=json.dumps(metadata),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Test retrieving metadata
        response = self.client.get(f'/api/invoices/{test_invoice_id}/metadata')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['vzt_rep'], "John Doe")
        self.assertEqual(data['customer_portal_name'], "Portal A")
    
    def test_custom_cash_flows_api(self):
        """Test custom cash flow endpoints."""
        # Test adding a custom inflow
        custom_flow = {
            "flow_type": "inflow",
            "amount": 5000.00,
            "date": "2026-03-01",
            "description": "Test inflow",
            "is_recurring": False
        }
        
        response = self.client.post(
            '/api/custom-cash-flows',
            data=json.dumps(custom_flow),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('id', data)
        flow_id = data['id']
        
        # Test retrieving custom flows
        response = self.client.get('/api/custom-cash-flows')
        self.assertEqual(response.status_code, 200)
        flows = json.loads(response.data)
        self.assertIsInstance(flows, list)
        self.assertTrue(any(f['id'] == flow_id for f in flows))
        
        # Test updating custom flow
        updated_flow = {
            "flow_type": "inflow",
            "amount": 6000.00,
            "date": "2026-03-01",
            "description": "Updated test inflow",
            "is_recurring": False
        }
        response = self.client.put(
            f'/api/custom-cash-flows/{flow_id}',
            data=json.dumps(updated_flow),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Test deleting custom flow
        response = self.client.delete(f'/api/custom-cash-flows/{flow_id}')
        self.assertEqual(response.status_code, 200)
    
    def test_calendar_cashflow_api(self):
        """Test calendar cash flow endpoint."""
        response = self.client.get('/api/cashflow/calendar?days=30&initial_balance=10000')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify response structure
        self.assertIn('start_date', data)
        self.assertIn('end_date', data)
        self.assertIn('initial_balance', data)
        self.assertIn('daily_projection', data)
        
        # Verify daily projection is a dictionary
        self.assertIsInstance(data['daily_projection'], dict)
        
        # Check if at least one day exists
        self.assertGreater(len(data['daily_projection']), 0)
        
        # Verify structure of a daily entry
        first_day = list(data['daily_projection'].values())[0]
        self.assertIn('date', first_day)
        self.assertIn('balance', first_day)
        self.assertIn('total_inflow', first_day)
        self.assertIn('total_outflow', first_day)
        self.assertIn('net_change', first_day)
    
    def test_recurring_cash_flow(self):
        """Test recurring cash flow functionality."""
        # Add a recurring weekly inflow
        recurring_flow = {
            "flow_type": "inflow",
            "amount": 1000.00,
            "description": "Weekly recurring test",
            "is_recurring": True,
            "recurrence_type": "weekly",
            "recurrence_interval": 1,
            "recurrence_start_date": "2026-02-10",
            "recurrence_end_date": "2026-03-10"
        }
        
        response = self.client.post(
            '/api/custom-cash-flows',
            data=json.dumps(recurring_flow),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        flow_id = data['id']
        
        # Verify it was created
        response = self.client.get(f'/api/custom-cash-flows/{flow_id}')
        self.assertEqual(response.status_code, 200)
        flow_data = json.loads(response.data)
        self.assertTrue(flow_data['is_recurring'])
        self.assertEqual(flow_data['recurrence_type'], 'weekly')
        
        # Clean up
        self.client.delete(f'/api/custom-cash-flows/{flow_id}')
    
    def test_service_name_update(self):
        """Test that service name has been updated to VZT Accounting."""
        response = self.client.get('/', headers={'Accept': 'application/json'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('VZT Accounting', data['service'])


if __name__ == '__main__':
    unittest.main()
