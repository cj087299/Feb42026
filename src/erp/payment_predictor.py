import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Optional, Tuple, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentPredictor:
    """
    AI-powered predictor for invoice payment dates.
    Uses historical payment data to forecast when an invoice will be paid.
    """

    def __init__(self):
        """Initialize the payment predictor."""
        self.model = None
        self.is_trained = False
        self.last_trained_at = None
        self.feature_columns = ['amount', 'customer_avg_days', 'terms_days', 'day_of_week', 'month']

        # In a real scenario, we would load a saved model here
        # self.load_model()

    def prepare_features(self, invoices: List[Dict], training: bool = True) -> pd.DataFrame:
        """
        Extract features from invoices for model training or prediction.

        Args:
            invoices: List of invoice dictionaries
            training: Whether this is for training (requires 'days_to_pay' target)

        Returns:
            DataFrame with features
        """
        if not invoices:
            return pd.DataFrame()

        data = []
        for inv in invoices:
            # Basic features
            amount = float(inv.get('amount', 0))
            terms = int(inv.get('terms_days', 30))

            # Date features
            if inv.get('txn_date'):
                txn_date = datetime.strptime(inv.get('txn_date'), '%Y-%m-%d')
                day_of_week = txn_date.weekday()
                month = txn_date.month
            else:
                day_of_week = 0
                month = 1

            # Customer behavior (simplified)
            # In a real system, we'd look up historical avg for this specific customer
            customer_avg = 35 # Default placeholder

            row = {
                'amount': amount,
                'customer_avg_days': customer_avg,
                'terms_days': terms,
                'day_of_week': day_of_week,
                'month': month
            }

            # Target variable for training
            if training and inv.get('payment_date') and inv.get('txn_date'):
                pay_date = datetime.strptime(inv.get('payment_date'), '%Y-%m-%d')
                txn_date = datetime.strptime(inv.get('txn_date'), '%Y-%m-%d')
                days_to_pay = (pay_date - txn_date).days
                row['days_to_pay'] = days_to_pay

                # Only include valid training rows
                if days_to_pay >= 0:
                    data.append(row)
            elif not training:
                data.append(row)

        return pd.DataFrame(data)

    def train(self, historical_invoices: List[Dict]) -> Dict:
        """
        Train the model on historical invoice data.

        Args:
            historical_invoices: List of paid invoices with payment dates

        Returns:
            Dictionary with training metrics
        """
        if not historical_invoices:
            logger.warning("No data provided for training")
            return {'success': False, 'message': 'No data'}

        try:
            df = self.prepare_features(historical_invoices, training=True)

            if df.empty or len(df) < 10:
                logger.warning("Insufficient data for training (need at least 10 records)")
                return {'success': False, 'message': 'Insufficient data'}

            X = df[self.feature_columns]
            y = df['days_to_pay']

            # Create and train pipeline
            self.model = make_pipeline(StandardScaler(), LinearRegression())
            self.model.fit(X, y)

            self.is_trained = True
            self.last_trained_at = datetime.now()

            # Calculate basic metrics
            score = self.model.score(X, y)

            logger.info(f"Model trained successfully. R² score: {score:.4f}")

            return {
                'success': True,
                'r2_score': score,
                'samples': len(df),
                'trained_at': self.last_trained_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {'success': False, 'message': str(e)}

    def predict_expected_date(self, invoice: Dict) -> Optional[str]:
        """
        Predict the expected payment date for a single invoice.

        Args:
            invoice: Invoice dictionary

        Returns:
            Predicted payment date string (YYYY-MM-DD) or None
        """
        if not self.is_trained or not self.model:
            # Fallback to simple logic if model not trained
            return self._heuristic_prediction(invoice)

        try:
            # Prepare single row DataFrame
            df = self.prepare_features([invoice], training=False)

            if df.empty:
                return self._heuristic_prediction(invoice)

            # Predict days to pay
            predicted_days = self.model.predict(df[self.feature_columns])[0]

            # Ensure prediction is reasonable (e.g., non-negative)
            predicted_days = max(1, round(predicted_days))

            # Calculate date
            if invoice.get('txn_date'):
                txn_date = datetime.strptime(invoice.get('txn_date'), '%Y-%m-%d')
                predicted_date = txn_date + timedelta(days=predicted_days)
                return predicted_date.strftime('%Y-%m-%d')

            return None

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return self._heuristic_prediction(invoice)

    def _heuristic_prediction(self, invoice: Dict) -> Optional[str]:
        """Fallback prediction using simple heuristics (Terms + Average Delay)."""
        if not invoice.get('due_date'):
            return None

        # Simple rule: Assume mostly on time, maybe 5 days late average
        due_date = datetime.strptime(invoice.get('due_date'), '%Y-%m-%d')
        predicted_date = due_date + timedelta(days=5)

        return predicted_date.strftime('%Y-%m-%d')
