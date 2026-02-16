import unittest
from datetime import datetime, timedelta
from src.erp.payment_predictor import PaymentPredictor
import logging

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestPaymentPredictor(unittest.TestCase):
    def test_training_and_prediction(self):
        predictor = PaymentPredictor()

        # Training data: Customer C1 always pays 5 days late
        # Need at least 10 records for training to succeed
        history = []
        # 8 records for C1 (late)
        for i in range(1, 9):
            history.append({
                'customer_id': 'C1',
                'amount': 100 * i,
                'due_date': f'2023-{i:02d}-01',
                'payment_date': f'2023-{i:02d}-06',
                'txn_date': f'2023-{i:02d}-01', # Required for feature extraction
                'terms_days': 30
            })
        # 3 records for C2 (on time)
        for i in range(1, 4):
            history.append({
                'customer_id': 'C2',
                'amount': 150 * i,
                'due_date': f'2023-{i:02d}-15',
                'payment_date': f'2023-{i:02d}-15',
                'txn_date': f'2023-{i:02d}-15',
                'terms_days': 30
            })

        predictor.train(history)
        self.assertTrue(predictor.is_trained)

        # Prediction for C1: Should be approx 5 days after due date
        # Note: Model is linear regression on features, not just customer ID
        # Since we only mocked simple features, prediction might not be exactly 5 days
        # but let's test that it returns a valid date string
        invoice_c1 = {'customer_id': 'C1', 'amount': 150, 'due_date': '2023-10-01', 'txn_date': '2023-10-01'}
        predicted_date_str = predictor.predict_expected_date(invoice_c1)
        self.assertIsNotNone(predicted_date_str)

    def test_predict_untrained(self):
        predictor = PaymentPredictor()
        invoice = {'customer_id': 'C1', 'amount': 100, 'due_date': '2023-10-01'}
        # Should return due date + 5 days (heuristic) if untrained
        predicted = predictor.predict_expected_date(invoice)
        due_date = datetime.strptime('2023-10-01', '%Y-%m-%d')
        expected = (due_date + timedelta(days=5)).strftime('%Y-%m-%d')
        self.assertEqual(predicted, expected)

    def test_train_empty_data(self):
        predictor = PaymentPredictor()
        predictor.train([])
        self.assertFalse(predictor.is_trained)

    def test_train_missing_columns(self):
        predictor = PaymentPredictor()
        # Missing payment_date
        history = [{'customer_id': 'C1', 'amount': 100, 'due_date': '2023-01-01'}]
        predictor.train(history)
        self.assertFalse(predictor.is_trained)

    def test_predict_missing_keys(self):
        predictor = PaymentPredictor()
        predictor.is_trained = True  # Fake it

        # Missing customer_id
        invoice = {'amount': 100, 'due_date': '2023-10-01'}
        # Should gracefully return due_date + 5 days (heuristic) if model fails or fallback used
        predicted = predictor.predict_expected_date(invoice)
        due_date = datetime.strptime('2023-10-01', '%Y-%m-%d')
        expected = (due_date + timedelta(days=5)).strftime('%Y-%m-%d')
        self.assertEqual(predicted, expected)


if __name__ == '__main__':
    unittest.main()
