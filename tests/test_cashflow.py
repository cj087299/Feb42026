import unittest
from datetime import datetime, timedelta
from src.erp.cash_flow import CashFlowProjector
from src.erp.payment_predictor import PaymentPredictor


class TestCashFlowProjector(unittest.TestCase):
    def test_projection_without_ai(self):
        today = datetime.now().strftime('%Y-%m-%d')
        invoices = [{'amount': 100, 'due_date': today, 'customer_id': 'C1'}]
        expenses = [{'amount': 30, 'due_date': today}]

        projector = CashFlowProjector(invoices, expenses)
        projection = projector.calculate_projection(days=30)

        if isinstance(projection, list):
            total_change = sum(day['net_change'] for day in projection)
        else:
            total_change = projection

        self.assertEqual(total_change, 70.0)

    def test_projection_with_ai(self):
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')

        # Training data: C1 pays 10 days late. Need >10 records.
        history = []
        for i in range(12):
            due = datetime(2023, 1, 1) + timedelta(days=i*30)
            pay = due + timedelta(days=10)
            history.append({
                'customer_id': 'C1',
                'amount': 100,
                'due_date': due.strftime('%Y-%m-%d'),
                'payment_date': pay.strftime('%Y-%m-%d'),
                'txn_date': (due - timedelta(days=30)).strftime('%Y-%m-%d'),
                'terms_days': 30
            })

        predictor = PaymentPredictor()
        predictor.train(history)

        # Invoice created 30 days ago (standard net 30), due today.
        txn_date_str = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        invoices = [{'amount': 100, 'due_date': today_str, 'txn_date': txn_date_str, 'customer_id': 'C1', 'terms_days': 30}]
        expenses = []

        projector = CashFlowProjector(invoices, expenses, predictor=predictor)

        # AI should predict payment ~10 days AFTER due date (total 40 days from txn).
        # Due today. Payment ~ today + 10.

        # Window: 5 days. Payment (today+10) is OUTSIDE.
        projection_short = projector.calculate_projection(days=5)
        if isinstance(projection_short, list):
            total_short = sum(day['net_change'] for day in projection_short)
        else:
            total_short = projection_short

        # Verify excluded (0.0)
        # Note: Linear regression might not be exact 10.0, but should be close.
        # If it predicts 9.9, and round() makes it 10.
        # If it predicts < 5, it fails test.
        self.assertEqual(total_short, 0.0)

        # Window: 15 days. Payment (today+10) is INSIDE.
        projection_long = projector.calculate_projection(days=15)
        if isinstance(projection_long, list):
            total_long = sum(day['net_change'] for day in projection_long)
        else:
            total_long = projection_long
        self.assertEqual(total_long, 100.0)


if __name__ == '__main__':
    unittest.main()
