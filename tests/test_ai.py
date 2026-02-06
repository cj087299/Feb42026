import unittest
from datetime import datetime, timedelta
from src.ai_predictor import PaymentPredictor

class TestPaymentPredictor(unittest.TestCase):
    def test_training_and_prediction(self):
        predictor = PaymentPredictor()

        # Training data: Customer C1 always pays 5 days late
        history = [
            {'customer_id': 'C1', 'amount': 100, 'due_date': '2023-01-01', 'payment_date': '2023-01-06'},
            {'customer_id': 'C1', 'amount': 200, 'due_date': '2023-02-01', 'payment_date': '2023-02-06'},
            {'customer_id': 'C2', 'amount': 100, 'due_date': '2023-01-01', 'payment_date': '2023-01-01'}, # On time
        ]

        predictor.train(history)
        self.assertTrue(predictor.is_trained)

        # Prediction for C1: Should be approx 5 days after due date
        invoice_c1 = {'customer_id': 'C1', 'amount': 150, 'due_date': '2023-10-01'}
        predicted_date_str = predictor.predict_expected_date(invoice_c1)
        predicted_date = datetime.strptime(predicted_date_str, '%Y-%m-%d')
        due_date = datetime.strptime('2023-10-01', '%Y-%m-%d')

        diff = (predicted_date - due_date).days
        self.assertAlmostEqual(diff, 5, delta=1) # Allow slight floating point error

        # Prediction for C2: Should be approx 0 days delay
        invoice_c2 = {'customer_id': 'C2', 'amount': 150, 'due_date': '2023-10-01'}
        predicted_date_str_2 = predictor.predict_expected_date(invoice_c2)
        predicted_date_2 = datetime.strptime(predicted_date_str_2, '%Y-%m-%d')
        diff_2 = (predicted_date_2 - due_date).days
        self.assertAlmostEqual(diff_2, 0, delta=1)

    def test_predict_untrained(self):
        predictor = PaymentPredictor()
        invoice = {'customer_id': 'C1', 'amount': 100, 'due_date': '2023-10-01'}
        # Should return due date if untrained
        self.assertEqual(predictor.predict_expected_date(invoice), '2023-10-01')

if __name__ == '__main__':
    unittest.main()
