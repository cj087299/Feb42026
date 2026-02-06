import unittest
from datetime import datetime, timedelta
from src.cash_flow import CashFlowProjector

class TestCashFlowProjector(unittest.TestCase):
    def test_projection(self):
        today = datetime.now().strftime('%Y-%m-%d')
        invoices = [{'amount': 100, 'due_date': today}]
        expenses = [{'amount': 30, 'due_date': today}]

        projector = CashFlowProjector(invoices, expenses)
        projection = projector.calculate_projection(days=30)
        self.assertEqual(projection, 70.0)

if __name__ == '__main__':
    unittest.main()
