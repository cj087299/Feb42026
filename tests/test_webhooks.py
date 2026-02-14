import unittest
from unittest.mock import patch, Mock
from src.webhook_handler import WebhookHandler


class TestWebhookHandler(unittest.TestCase):
    """Test cases for WebhookHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = WebhookHandler()
    
    def test_verifier_token_constant(self):
        """Test that verifier token constant is set correctly."""
        self.assertEqual(
            WebhookHandler.VERIFIER_TOKEN, 
            "eb566143-7dcf-46a0-a51b-dc42962e461d"
        )
    
    def test_validate_verifier_token_valid(self):
        """Test validation with correct verifier token."""
        result = WebhookHandler.validate_verifier_token(
            "eb566143-7dcf-46a0-a51b-dc42962e461d"
        )
        self.assertTrue(result)
    
    def test_validate_verifier_token_invalid(self):
        """Test validation with incorrect verifier token."""
        result = WebhookHandler.validate_verifier_token("wrong-token")
        self.assertFalse(result)
    
    def test_validate_verifier_token_empty(self):
        """Test validation with empty token."""
        result = WebhookHandler.validate_verifier_token("")
        self.assertFalse(result)
    
    def test_parse_cloudevents_valid_invoice_update(self):
        """Test parsing valid CloudEvents payload for invoice update."""
        payload = {
            "specversion": "1.0",
            "type": "com.intuit.quickbooks.entity.update",
            "source": "//quickbooks.api.intuit.com",
            "id": "evt-inv-20240213-154732",
            "time": "2024-02-13T15:47:32Z",
            "datacontenttype": "application/json",
            "data": {
                "realm": "4620816365314298765",
                "name": "Invoice",
                "id": "1047",
                "operation": "Update",
                "lastUpdated": "2024-02-13T15:47:30Z"
            }
        }
        
        result = WebhookHandler.parse_cloudevents(payload)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['spec_version'], "1.0")
        self.assertEqual(result['event_type'], "com.intuit.quickbooks.entity.update")
        self.assertEqual(result['source'], "//quickbooks.api.intuit.com")
        self.assertEqual(result['event_id'], "evt-inv-20240213-154732")
        self.assertEqual(result['realm_id'], "4620816365314298765")
        self.assertEqual(result['entity_name'], "Invoice")
        self.assertEqual(result['entity_id'], "1047")
        self.assertEqual(result['operation'], "Update")
    
    def test_parse_cloudevents_valid_customer_create(self):
        """Test parsing valid CloudEvents payload for customer creation."""
        payload = {
            "specversion": "1.0",
            "type": "com.intuit.quickbooks.entity.create",
            "source": "//quickbooks.api.intuit.com",
            "id": "evt-cust-20240213-163045",
            "time": "2024-02-13T16:30:45Z",
            "data": {
                "realm": "4620816365314298765",
                "name": "Customer",
                "id": "2456",
                "operation": "Create"
            }
        }
        
        result = WebhookHandler.parse_cloudevents(payload)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['entity_name'], "Customer")
        self.assertEqual(result['operation'], "Create")
        self.assertEqual(result['entity_id'], "2456")
    
    def test_parse_cloudevents_valid_payment(self):
        """Test parsing valid CloudEvents payload for payment."""
        payload = {
            "specversion": "1.0",
            "type": "com.intuit.quickbooks.entity.update",
            "source": "//quickbooks.api.intuit.com",
            "id": "evt-pmt-20240213-171523",
            "data": {
                "realm": "4620816365314298765",
                "name": "Payment",
                "id": "3789",
                "operation": "Create",
                "lastUpdated": "2024-02-13T17:15:20Z"
            }
        }
        
        result = WebhookHandler.parse_cloudevents(payload)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['entity_name'], "Payment")
        self.assertEqual(result['operation'], "Create")
        self.assertEqual(result['entity_id'], "3789")
    
    def test_parse_cloudevents_valid_account_update(self):
        """Test parsing valid CloudEvents payload for account (bank balance) update."""
        payload = {
            "specversion": "1.0",
            "type": "com.intuit.quickbooks.entity.update",
            "source": "//quickbooks.api.intuit.com",
            "id": "evt-acc-20240213-182345",
            "data": {
                "realm": "4620816365314298765",
                "name": "Account",
                "id": "35",
                "operation": "Update",
                "lastUpdated": "2024-02-13T18:23:40Z"
            }
        }
        
        result = WebhookHandler.parse_cloudevents(payload)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['entity_name'], "Account")
        self.assertEqual(result['operation'], "Update")
        self.assertEqual(result['entity_id'], "35")
    
    def test_parse_cloudevents_missing_required_fields(self):
        """Test parsing CloudEvents with missing required fields."""
        payload = {
            "specversion": "1.0",
            "type": "com.intuit.quickbooks.entity.update",
            # Missing 'source' and 'id'
            "data": {
                "realm": "test-realm",
                "name": "Invoice",
                "id": "123"
            }
        }
        
        result = WebhookHandler.parse_cloudevents(payload)
        
        self.assertIsNone(result)
    
    def test_parse_cloudevents_invalid_type(self):
        """Test parsing invalid payload type (not a dict)."""
        result = WebhookHandler.parse_cloudevents("not a dict")
        self.assertIsNone(result)
        
        result = WebhookHandler.parse_cloudevents(None)
        self.assertIsNone(result)
        
        result = WebhookHandler.parse_cloudevents([])
        self.assertIsNone(result)
    
    def test_parse_cloudevents_empty_data(self):
        """Test parsing CloudEvents with empty data section."""
        payload = {
            "specversion": "1.0",
            "type": "com.intuit.quickbooks.entity.update",
            "source": "//quickbooks.api.intuit.com",
            "id": "test-event-789",
            "data": {}
        }
        
        result = WebhookHandler.parse_cloudevents(payload)
        
        # Should parse but with None values for entity data
        self.assertIsNotNone(result)
        self.assertIsNone(result['entity_name'])
        self.assertIsNone(result['entity_id'])
    
    def test_process_webhook_event_customer(self):
        """Test processing customer webhook event."""
        parsed_data = {
            'entity_name': 'Customer',
            'operation': 'Update',
            'entity_id': '2456',
            'realm_id': '4620816365314298765',
            'last_updated': '2024-02-13T16:30:45Z'
        }
        
        result = WebhookHandler.process_webhook_event(parsed_data)
        
        self.assertEqual(result['status'], 'processed')
        self.assertEqual(result['entity'], 'Customer')
        self.assertEqual(result['operation'], 'Update')
        self.assertEqual(result['entity_id'], '2456')
    
    def test_process_webhook_event_invoice(self):
        """Test processing invoice webhook event."""
        parsed_data = {
            'entity_name': 'Invoice',
            'operation': 'Create',
            'entity_id': '1047',
            'realm_id': '4620816365314298765'
        }
        
        result = WebhookHandler.process_webhook_event(parsed_data)
        
        self.assertEqual(result['status'], 'processed')
        self.assertEqual(result['entity'], 'Invoice')
        self.assertEqual(result['operation'], 'Create')
    
    def test_process_webhook_event_payment(self):
        """Test processing payment webhook event."""
        parsed_data = {
            'entity_name': 'Payment',
            'operation': 'Update',
            'entity_id': '3789',
            'realm_id': '4620816365314298765'
        }
        
        result = WebhookHandler.process_webhook_event(parsed_data)
        
        self.assertEqual(result['status'], 'processed')
        self.assertEqual(result['entity'], 'Payment')
    
    def test_process_webhook_event_account(self):
        """Test processing account webhook event."""
        parsed_data = {
            'entity_name': 'Account',
            'operation': 'Update',
            'entity_id': '35',
            'realm_id': '4620816365314298765'
        }
        
        result = WebhookHandler.process_webhook_event(parsed_data)
        
        self.assertEqual(result['status'], 'processed')
        self.assertEqual(result['entity'], 'Account')
        self.assertIn('note', result)
        self.assertIn('bank balance', result['note'])
    
    def test_process_webhook_event_unknown_entity(self):
        """Test processing webhook event with unknown entity type."""
        parsed_data = {
            'entity_name': 'UnknownEntity',
            'operation': 'Update',
            'entity_id': '999'
        }
        
        result = WebhookHandler.process_webhook_event(parsed_data)
        
        self.assertEqual(result['status'], 'ignored')
        self.assertIn('Unhandled entity type', result['reason'])


class TestWebhookEndpoint(unittest.TestCase):
    """Test cases for webhook endpoint integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Import here to avoid circular imports
        from main import app
        self.app = app
        self.client = self.app.test_client()
    
    def test_webhook_endpoint_get(self):
        """Test GET request to webhook endpoint (verification)."""
        response = self.client.get('/api/qbo/webhook')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('verifier_token', data)
        self.assertEqual(
            data['verifier_token'], 
            "eb566143-7dcf-46a0-a51b-dc42962e461d"
        )
    
    def test_webhook_endpoint_post_valid_single_event(self):
        """Test POST request with valid single CloudEvents payload."""
        payload = {
            "specversion": "1.0",
            "type": "com.intuit.quickbooks.entity.update",
            "source": "//quickbooks.api.intuit.com",
            "id": "evt-inv-20240213-154732",
            "time": "2024-02-13T15:47:32Z",
            "data": {
                "realm": "4620816365314298765",
                "name": "Invoice",
                "id": "1047",
                "operation": "Update",
                "lastUpdated": "2024-02-13T15:47:30Z"
            }
        }
        
        response = self.client.post(
            '/api/qbo/webhook',
            json=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        # Webhook now queues events asynchronously and returns 'accepted'
        self.assertEqual(data['status'], 'accepted')
        self.assertEqual(data['queued'], 1)
        self.assertIn('message', data)
    
    def test_webhook_endpoint_post_valid_multiple_events(self):
        """Test POST request with multiple CloudEvents payloads."""
        payload = [
            {
                "specversion": "1.0",
                "type": "com.intuit.quickbooks.entity.update",
                "source": "//quickbooks.api.intuit.com",
                "id": "evt-inv-20240213-154732",
                "data": {
                    "realm": "4620816365314298765",
                    "name": "Invoice",
                    "id": "1047",
                    "operation": "Update"
                }
            },
            {
                "specversion": "1.0",
                "type": "com.intuit.quickbooks.entity.create",
                "source": "//quickbooks.api.intuit.com",
                "id": "evt-pmt-20240213-171523",
                "data": {
                    "realm": "4620816365314298765",
                    "name": "Payment",
                    "id": "3789",
                    "operation": "Create"
                }
            },
            {
                "specversion": "1.0",
                "type": "com.intuit.quickbooks.entity.update",
                "source": "//quickbooks.api.intuit.com",
                "id": "evt-acc-20240213-182345",
                "data": {
                    "realm": "4620816365314298765",
                    "name": "Account",
                    "id": "35",
                    "operation": "Update"
                }
            }
        ]
        
        response = self.client.post(
            '/api/qbo/webhook',
            json=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        # Webhook now queues events asynchronously and returns 'accepted'
        self.assertEqual(data['status'], 'accepted')
        self.assertEqual(data['queued'], 3)
        self.assertIn('message', data)
    
    def test_webhook_endpoint_post_no_payload(self):
        """Test POST request with no payload."""
        response = self.client.post(
            '/api/qbo/webhook',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_webhook_endpoint_post_invalid_cloudevents(self):
        """Test POST request with invalid CloudEvents format."""
        payload = {
            "invalid": "data",
            "missing": "required_fields"
        }
        
        response = self.client.post(
            '/api/qbo/webhook',
            json=payload,
            content_type='application/json'
        )
        
        # Should still return 200 (accepted) even with invalid CloudEvents
        # Invalid events are queued and errors are logged during processing
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'accepted')
        self.assertEqual(data['queued'], 1)


if __name__ == '__main__':
    unittest.main()
