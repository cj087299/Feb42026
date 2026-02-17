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
        for i, inv in enumerate(invoices):
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
                '_index': i,
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

    def predict_multiple(self, invoices: List[Dict]) -> Dict[str, str]:
        """
        Predict expected payment dates for a list of invoices.

        Args:
            invoices: List of invoice dictionaries

        Returns:
            Dictionary mapping invoice ID (or doc_number) to predicted date string
        """
        results = {}

        # If not trained, use heuristics for all
        if not self.is_trained or not self.model:
            return self._apply_heuristics_batch(invoices)

        try:
            # Prepare DataFrame for all invoices
            df = self.prepare_features(invoices, training=False)

            if df.empty:
                return self._apply_heuristics_batch(invoices)

            # Predict for the batch
            # Note: prepare_features includes _index to map back to original list
            predicted_days_batch = self.model.predict(df[self.feature_columns])

            # Map predictions back to invoices using _index
            indices = df['_index'].values

            for i, predicted_days in enumerate(predicted_days_batch):
                original_idx = int(indices[i])
                if original_idx >= len(invoices):
                    continue

                inv = invoices[original_idx]
                inv_id = inv.get('id') or inv.get('doc_number')
                if not inv_id:
                    continue

                predicted_days = max(1, round(predicted_days))

                if inv.get('txn_date'):
                    try:
                        txn_date = datetime.strptime(inv.get('txn_date'), '%Y-%m-%d')
                        predicted_date = txn_date + timedelta(days=predicted_days)
                        results[str(inv_id)] = predicted_date.strftime('%Y-%m-%d')
                    except ValueError:
                        # Fallback
                        pred = self._heuristic_prediction(inv)
                        if pred: results[str(inv_id)] = pred
                else:
                    # Fallback
                    pred = self._heuristic_prediction(inv)
                    if pred: results[str(inv_id)] = pred

            # Fill in missing predictions with heuristics (for rows dropped by prepare_features if any)
            # Or for invoices that failed date parsing above but heuristics might succeed?
            # Actually, _heuristic_prediction also depends on date parsing, but it uses due_date mostly.
            # Let's run a pass for any missing IDs that we expected.
            for inv in invoices:
                inv_id = inv.get('id') or inv.get('doc_number')
                if inv_id and str(inv_id) not in results:
                    pred = self._heuristic_prediction(inv)
                    if pred:
                        results[str(inv_id)] = pred

            return results

        except Exception as e:
            logger.error(f"Batch prediction failed: {e}")
            return self._apply_heuristics_batch(invoices)

    def _apply_heuristics_batch(self, invoices: List[Dict]) -> Dict[str, str]:
        """Apply heuristics to a batch of invoices."""
        results = {}
        for inv in invoices:
            inv_id = inv.get('id') or inv.get('doc_number')
            pred = self._heuristic_prediction(inv)
            if inv_id and pred:
                results[str(inv_id)] = pred
        return results

    def _heuristic_prediction(self, invoice: Dict) -> Optional[str]:
        """Fallback prediction using simple heuristics (Terms + Average Delay)."""
        if not invoice.get('due_date'):
            return None

        # Simple rule: Assume mostly on time, maybe 5 days late average
        due_date = datetime.strptime(invoice.get('due_date'), '%Y-%m-%d')
        predicted_date = due_date + timedelta(days=5)

        return predicted_date.strftime('%Y-%m-%d')
