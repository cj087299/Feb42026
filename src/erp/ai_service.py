import logging
import json
import requests
from datetime import datetime
import numpy as np
from typing import Dict, List, Optional
from src.common.database import Database

logger = logging.getLogger(__name__)

class AIService:
    """
    AI Service for VZT Accounting.
    Handles AI interactions, including chat, report generation, and data analysis.
    """

    def __init__(self, database: Optional[Database] = None):
        """Initialize AI Service."""
        self.database = database
        self.conversation_history = []

        # Check for OpenAI API Key (simulated for now)
        self.api_key = "dummy_key_for_simulation"

    def chat(self, message: str, history: List[Dict], user_role: str) -> Dict:
        """
        Process a chat message and return a response.

        Args:
            message: User's message
            history: Conversation history
            user_role: Role of the user (e.g., 'admin', 'view_only')

        Returns:
            Dictionary containing the AI response
        """
        try:
            # Simulate AI response logic
            # In a real implementation, this would call OpenAI or another LLM

            response_text = self._generate_simulated_response(message, user_role)

            return {
                'message': response_text,
                'role': 'assistant',
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error in AI chat: {e}")
            return {
                'message': "I apologize, but I encountered an error processing your request.",
                'role': 'assistant',
                'error': str(e)
            }

    def _generate_simulated_response(self, message: str, user_role: str) -> str:
        """Generate a simulated AI response based on keywords."""
        message_lower = message.lower()

        if "invoice" in message_lower:
            return "I can help you with invoices. You can ask me to list overdue invoices, find a specific invoice, or analyze payment trends."
        elif "cash flow" in message_lower or "cashflow" in message_lower:
            return "Cash flow analysis is available in the Cash Flow tab. I can also generate a projection report for you."
        elif "customer" in message_lower:
            return "I can provide customer details. Which customer are you interested in?"
        elif "help" in message_lower:
            return "I am the VZT AI Assistant. I can help you navigate the system, analyze data, and answer questions about your accounting data."
        else:
            return f"I received your message: '{message}'. How can I assist you with your accounting tasks today?"

    def perform_action(self, action: str, parameters: Dict, user_role: str) -> Dict:
        """
        Perform a specific AI action.

        Args:
            action: Action identifier
            parameters: Action parameters
            user_role: User role

        Returns:
            Result dictionary
        """
        if user_role != 'master_admin':
            return {'error': 'Permission denied'}

        if action == 'generate_report':
            return {'status': 'success', 'report_url': '/reports/generated/123'}
        elif action == 'analyze_data':
            return {'status': 'success', 'analysis': 'Data analysis complete. Trends detected...'}
        else:
            return {'error': 'Unknown action'}

    def analyze_customer_payment_behavior(self, customer_id: str, qbo_client) -> Dict:
        """
        Analyzes the last 20 paid invoices for a customer to determine average delay and confidence.

        Args:
            customer_id: QBO Customer ID
            qbo_client: Authenticated QBOConnector instance

        Returns:
            Dict containing 'average_delay' (float days) and 'confidence_score' (0.0 - 1.0)
        """
        try:
            # 1. Fetch last 20 payments for this customer
            query_payments = f"SELECT * FROM Payment WHERE CustomerRef = '{customer_id}' ORDERBY TxnDate DESC MAXRESULTS 20"
            response_payments = qbo_client.make_request("query", params={"query": query_payments})

            payments = response_payments.get('QueryResponse', {}).get('Payment', [])

            if not payments:
                return {'average_delay': 0.0, 'confidence_score': 0.0}

            # 2. Extract Invoice IDs and map to Payment Date
            invoice_payment_map = {} # invoice_id -> payment_date (datetime)
            invoice_ids = set()

            for payment in payments:
                payment_date_str = payment.get('TxnDate')
                if not payment_date_str: continue

                try:
                    payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d')
                except ValueError:
                    continue

                for line in payment.get('Line', []):
                    for linked_txn in line.get('LinkedTxn', []):
                        if linked_txn.get('TxnType') == 'Invoice':
                            inv_id = linked_txn.get('TxnId')
                            if inv_id:
                                # Map invoice to this payment date
                                invoice_payment_map[inv_id] = payment_date
                                invoice_ids.add(inv_id)

            if not invoice_ids:
                return {'average_delay': 0.0, 'confidence_score': 0.0}

            # 3. Fetch Invoices to get Due Dates
            ids_formatted = ", ".join([f"'{id}'" for id in invoice_ids])
            query_invoices = f"SELECT Id, DueDate FROM Invoice WHERE Id IN ({ids_formatted})"
            response_invoices = qbo_client.make_request("query", params={"query": query_invoices})

            invoices = response_invoices.get('QueryResponse', {}).get('Invoice', [])

            delays = []
            for invoice in invoices:
                inv_id = invoice.get('Id')
                due_date_str = invoice.get('DueDate')

                if inv_id and due_date_str and inv_id in invoice_payment_map:
                    try:
                        due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                        payment_date = invoice_payment_map[inv_id]

                        # Calculate delay
                        delay = (payment_date - due_date).days
                        delays.append(delay)
                    except ValueError:
                        continue

            if not delays:
                return {'average_delay': 0.0, 'confidence_score': 0.0}

            # 4. Calculate Stats
            average_delay = float(np.mean(delays))
            std_dev = float(np.std(delays))

            # 5. Calculate Confidence
            # Heuristic: 1.0 / (1.0 + (std_dev / 5.0))
            # If std_dev is 0 (always same delay), confidence is 1.0
            # If std_dev is 5 days, confidence is 0.5
            confidence_score = 1.0 / (1.0 + (std_dev / 5.0))

            return {
                'average_delay': average_delay,
                'confidence_score': confidence_score,
                'sample_size': len(delays)
            }

        except Exception as e:
            logger.error(f"Error analyzing customer payment behavior: {e}")
            return {'average_delay': 0.0, 'confidence_score': 0.0}
