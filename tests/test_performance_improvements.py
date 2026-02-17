import unittest
from unittest.mock import MagicMock
import pandas as pd
from datetime import datetime, timedelta
from src.erp.payment_predictor import PaymentPredictor
from src.erp.cash_flow_calendar import CashFlowCalendar
from src.erp.cash_flow import CashFlowProjector

class TestPerformanceImprovements(unittest.TestCase):
    def setUp(self):
        self.predictor = PaymentPredictor()

        # Sample invoices
        self.invoices = [
            {
                'id': '1',
                'doc_number': '1001',
                'amount': 1000,
                'terms_days': 30,
                'txn_date': '2023-01-01',
                'due_date': '2023-01-31',
                'customer': 'Customer A'
            },
            {
                'id': '2',
                'doc_number': '1002',
                'amount': 2000,
                'terms_days': 15,
                'txn_date': '2023-01-10',
                'due_date': '2023-01-25',
                'customer': 'Customer B'
            },
            {
                'id': '3', # No doc_number
                'amount': 500,
                'terms_days': 0,
                'txn_date': '2023-01-15',
                'due_date': '2023-01-15',
                'customer': 'Customer C'
            },
            {
                # Missing ID
                'doc_number': '1004',
                'amount': 100,
                'terms_days': 30,
                'txn_date': '2023-02-01',
                'due_date': '2023-03-03',
                'customer': 'Customer D'
            }
        ]

        # Sample expenses with colliding ID
        self.expenses = [
            {
                'id': '1', # Collision with Invoice 1
                'doc_number': 'EXP-1',
                'amount': 50,
                'terms_days': 0,
                'txn_date': '2023-01-05',
                'due_date': '2023-01-05', # Heuristic would be +5 days = 2023-01-10
                'customer': 'Vendor X'
            }
        ]

    def test_predict_multiple_untrained(self):
        """Test predict_multiple when model is not trained (should use heuristics)."""
        results = self.predictor.predict_multiple(self.invoices)

        # Verify results size
        # Invoice 3 has id '3', Invoice 4 has doc_number '1004' (as fallback ID if logic supports it, but my logic uses id OR doc_number)
        # In predict_multiple: inv_id = inv.get('id') or inv.get('doc_number')
        # So all 4 should be present
        self.assertEqual(len(results), 4)

        # Verify heuristic calculation: due_date + 5 days
        # Invoice 1: 2023-01-31 + 5 = 2023-02-05
        self.assertEqual(results['1'], '2023-02-05')

        # Invoice 4 (ID 1004): 2023-03-03 + 5 = 2023-03-08
        self.assertEqual(results['1004'], '2023-03-08')

    def test_predict_multiple_trained_with_missing_id(self):
        """Test prediction alignment when an invoice is missing ID."""
        # Mock trained state
        self.predictor.is_trained = True
        self.predictor.model = MagicMock()

        # Mock prediction output:
        # Returns days_to_pay.
        # Invoice 1 (txn 2023-01-01): 10 days -> 2023-01-11
        # Invoice 2 (missing ID completely): 20 days -> Should be skipped in results but consume prediction
        # Invoice 3 (txn 2023-01-15): 5 days -> 2023-01-20

        # We need a list of invoices where one is completely missing ID
        test_invoices = [
            {
                'id': '1',
                'amount': 100,
                'terms_days': 30,
                'txn_date': '2023-01-01',
                'due_date': '2023-01-31'
            },
            {
                # Missing ID and doc_number
                'amount': 200,
                'terms_days': 30,
                'txn_date': '2023-01-05'
            },
            {
                'id': '3',
                'amount': 300,
                'terms_days': 30,
                'txn_date': '2023-01-15',
                'due_date': '2023-02-15'
            }
        ]

        # Mock model.predict to return [10, 20, 5]
        # 10 for Invoice 1
        # 20 for Invoice 2 (missing ID)
        # 5 for Invoice 3
        self.predictor.model.predict.return_value = [10, 20, 5]

        results = self.predictor.predict_multiple(test_invoices)

        # Verify Invoice 1
        # 2023-01-01 + 10 days = 2023-01-11
        self.assertIn('1', results)
        self.assertEqual(results['1'], '2023-01-11')

        # Verify Invoice 3
        # 2023-01-15 + 5 days = 2023-01-20
        # If alignment was broken (Invoice 2 skipped without consuming prediction),
        # Invoice 3 would get 20 days -> 2023-01-15 + 20 = 2023-02-04
        self.assertIn('3', results)
        self.assertEqual(results['3'], '2023-01-20')

    def test_cash_flow_calendar_uses_batch_predictions(self):
        """Test that CashFlowCalendar uses pre-calculated predictions."""
        # Create a mock predictor that tracks calls
        class MockPredictor(PaymentPredictor):
            def __init__(self):
                super().__init__()
                self.predict_multiple_called = False
                self.predict_expected_date_called = False

            def predict_multiple(self, invoices):
                self.predict_multiple_called = True
                return super().predict_multiple(invoices)

            def predict_expected_date(self, invoice):
                self.predict_expected_date_called = True
                return super().predict_expected_date(invoice)

        mock_predictor = MockPredictor()

        # Initialize calendar
        calendar = CashFlowCalendar(
            invoices=self.invoices,
            accounts_payable=[],
            custom_flows=[],
            predictor=mock_predictor
        )

        # Verify predict_multiple was called in __init__
        self.assertTrue(mock_predictor.predict_multiple_called)

        # Run projection
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 3, 30)
        calendar.calculate_daily_projection(start_date, end_date)

        # Verify predict_expected_date was NOT called
        self.assertFalse(mock_predictor.predict_expected_date_called)

    def test_cash_flow_projector_uses_batch_predictions(self):
        """Test that CashFlowProjector uses pre-calculated predictions."""
         # Create a mock predictor that tracks calls
        class MockPredictor(PaymentPredictor):
            def __init__(self):
                super().__init__()
                self.predict_multiple_called = False
                self.predict_expected_date_called = False

            def predict_multiple(self, invoices):
                self.predict_multiple_called = True
                return super().predict_multiple(invoices)

            def predict_expected_date(self, invoice):
                self.predict_expected_date_called = True
                return super().predict_expected_date(invoice)

        mock_predictor = MockPredictor()

        projector = CashFlowProjector(
            invoices=self.invoices,
            expenses=self.expenses,
            predictor=mock_predictor
        )

        self.assertTrue(mock_predictor.predict_multiple_called)

        projector.calculate_projection(days=30)
        self.assertFalse(mock_predictor.predict_expected_date_called)

    def test_cash_flow_projector_id_collision_handling(self):
        """Test that Invoice ID 1 and Expense ID 1 do not collide."""
        projector = CashFlowProjector(
            invoices=self.invoices,
            expenses=self.expenses,
            predictor=self.predictor
        )

        # Check cached predictions
        # Invoice 1 due date 2023-01-31 -> Predicted 2023-02-05
        # Expense 1 due date 2023-01-05 -> Predicted 2023-01-10

        self.assertIn('1', projector.invoice_predictions)
        self.assertIn('1', projector.expense_predictions)

        self.assertEqual(projector.invoice_predictions['1'], '2023-02-05')
        self.assertEqual(projector.expense_predictions['1'], '2023-01-10')

        # Ensure they are distinct
        self.assertNotEqual(projector.invoice_predictions['1'], projector.expense_predictions['1'])

if __name__ == '__main__':
    unittest.main()
