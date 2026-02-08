import unittest
from datetime import datetime
from src.cash_flow import CashFlowProjector
from src.ai_predictor import PaymentPredictor


class TestCashFlowProjector(unittest.TestCase):
    def test_projection_without_ai(self):
        today = datetime.now().strftime('%Y-%m-%d')
        invoices = [{'amount': 100, 'due_date': today, 'customer_id': 'C1'}]
        expenses = [{'amount': 30, 'due_date': today}]

        projector = CashFlowProjector(invoices, expenses)
        projection = projector.calculate_projection(days=30)
        self.assertEqual(projection, 70.0)

    def test_projection_with_ai(self):
        # Scenario: Customer C1 pays 10 days late.
        # Invoice due today, but won't be paid for 10 days.
        # If projection window is 5 days, it should NOT be included.

        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')

        # Training data: C1 pays 10 days late
        history = [
            {'customer_id': 'C1', 'amount': 100, 'due_date': '2023-01-01', 'payment_date': '2023-01-11'},
            {'customer_id': 'C1', 'amount': 100, 'due_date': '2023-02-01', 'payment_date': '2023-02-11'},
        ]

        predictor = PaymentPredictor()
        predictor.train(history)

        invoices = [{'amount': 100, 'due_date': today_str, 'customer_id': 'C1'}]
        expenses = []

        projector = CashFlowProjector(invoices, expenses, predictor=predictor)

        # Window: 5 days. Predicted payment (day 10) is OUTSIDE. Balance should be 0.
        projection_short = projector.calculate_projection(days=5)
        self.assertEqual(projection_short, 0.0)

        # Window: 15 days. Predicted payment (day 10) is INSIDE. Balance should be 100.
        projection_long = projector.calculate_projection(days=15)
        self.assertEqual(projection_long, 100.0)


if __name__ == '__main__':
    unittest.main()
