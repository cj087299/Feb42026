import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from src.erp.ai_service import AIService

class TestAIService(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.mock_db = Mock()
        self.ai_service = AIService(database=self.mock_db)

    def test_initialization(self):
        """Test AIService initialization."""
        self.assertEqual(self.ai_service.api_key, "dummy_key_for_simulation")
        self.assertEqual(self.ai_service.database, self.mock_db)
        self.assertEqual(self.ai_service.conversation_history, [])

    def test_chat_invoice_keyword(self):
        """Test chat with 'invoice' keyword."""
        message = "Can you help me with an invoice?"
        response = self.ai_service.chat(message, [], "admin")
        self.assertIn("invoice", response['message'].lower())
        self.assertEqual(response['role'], 'assistant')
        self.assertIsNotNone(response.get('timestamp'))

    def test_chat_cash_flow_keyword(self):
        """Test chat with 'cash flow' keyword."""
        message = "Show me cash flow."
        response = self.ai_service.chat(message, [], "admin")
        self.assertIn("cash flow", response['message'].lower())
        self.assertEqual(response['role'], 'assistant')

    def test_chat_customer_keyword(self):
        """Test chat with 'customer' keyword."""
        message = "Find customer details."
        response = self.ai_service.chat(message, [], "admin")
        self.assertIn("customer", response['message'].lower())
        self.assertEqual(response['role'], 'assistant')

    def test_chat_help_keyword(self):
        """Test chat with 'help' keyword."""
        message = "I need help."
        response = self.ai_service.chat(message, [], "admin")
        self.assertIn("vzt ai assistant", response['message'].lower())
        self.assertEqual(response['role'], 'assistant')

    def test_chat_unknown_keyword(self):
        """Test chat with unknown keyword."""
        message = "Tell me a joke."
        response = self.ai_service.chat(message, [], "admin")
        self.assertIn("i received your message", response['message'].lower())
        self.assertEqual(response['role'], 'assistant')

    def test_chat_error_handling(self):
        """Test chat error handling."""
        # Mock _generate_simulated_response to raise an exception
        with patch.object(self.ai_service, '_generate_simulated_response', side_effect=Exception("Test Error")):
            response = self.ai_service.chat("hello", [], "admin")
            self.assertIn("error processing your request", response['message'].lower())
            self.assertEqual(response['error'], "Test Error")

    def test_perform_action_generate_report(self):
        """Test perform_action 'generate_report' with master_admin."""
        result = self.ai_service.perform_action('generate_report', {}, 'master_admin')
        self.assertEqual(result['status'], 'success')
        self.assertIn('report_url', result)

    def test_perform_action_analyze_data(self):
        """Test perform_action 'analyze_data' with master_admin."""
        result = self.ai_service.perform_action('analyze_data', {}, 'master_admin')
        self.assertEqual(result['status'], 'success')
        self.assertIn('analysis', result)

    def test_perform_action_permission_denied(self):
        """Test perform_action with non-admin role."""
        result = self.ai_service.perform_action('generate_report', {}, 'view_only')
        self.assertEqual(result['error'], 'Permission denied')

    def test_perform_action_unknown(self):
        """Test perform_action with unknown action."""
        result = self.ai_service.perform_action('unknown_action', {}, 'master_admin')
        self.assertEqual(result['error'], 'Unknown action')

if __name__ == '__main__':
    unittest.main()
