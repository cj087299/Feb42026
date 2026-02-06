import pandas as pd
import logging
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

logger = logging.getLogger(__name__)

class PaymentPredictor:
    def __init__(self):
        # Pipeline: Encode categorical features (customer_id), impute missing values, run regression
        self.model = Pipeline(steps=[
            ('preprocessor', ColumnTransformer(
                transformers=[
                    ('num', SimpleImputer(strategy='mean'), ['amount']),
                    ('cat', OneHotEncoder(handle_unknown='ignore'), ['customer_id'])
                ]
            )),
            ('regressor', LinearRegression())
        ])
        self.is_trained = False

    def train(self, historical_invoices):
        """
        Trains the model on historical invoice data.

        historical_invoices: List of dicts with keys:
            - customer_id
            - amount
            - due_date (YYYY-MM-DD)
            - payment_date (YYYY-MM-DD)
        """
        try:
            df = pd.DataFrame(historical_invoices)

            if df.empty:
                logger.warning("No data provided to train on.")
                return

            required_cols = {'customer_id', 'amount', 'due_date', 'payment_date'}
            if not required_cols.issubset(df.columns):
                logger.error(f"Missing required columns in training data: {required_cols - set(df.columns)}")
                return

            # Calculate target: days delayed (payment_date - due_date)
            # If payment_date is missing, we can't use it for training
            df = df.dropna(subset=['payment_date', 'due_date'])

            if df.empty:
                logger.warning("No valid paid invoices (with payment_date and due_date) to train on.")
                return

            df['due_date_dt'] = pd.to_datetime(df['due_date'], errors='coerce')
            df['payment_date_dt'] = pd.to_datetime(df['payment_date'], errors='coerce')

            # Drop rows where date parsing failed
            df = df.dropna(subset=['due_date_dt', 'payment_date_dt'])

            if df.empty:
                logger.warning("All dates failed parsing.")
                return

            df['days_delayed'] = (df['payment_date_dt'] - df['due_date_dt']).dt.days

            # Features: customer_id, amount
            X = df[['customer_id', 'amount']]
            y = df['days_delayed']

            self.model.fit(X, y)
            self.is_trained = True
            logger.info("Model trained successfully.")

        except Exception as e:
            logger.error(f"Error during model training: {e}")
            self.is_trained = False

    def predict_expected_date(self, invoice):
        """
        Predicts the expected payment date for an open invoice.

        invoice: dict with keys:
            - customer_id
            - amount
            - due_date
        """
        try:
            if not self.is_trained:
                logger.debug("Model not trained, returning original due date.")
                return invoice.get('due_date')

            if not all(k in invoice for k in ['customer_id', 'amount', 'due_date']):
                logger.warning("Invoice missing keys for prediction, returning due date.")
                return invoice.get('due_date')

            # Create DataFrame for single prediction
            X_pred = pd.DataFrame([invoice])[['customer_id', 'amount']]

            predicted_delay = self.model.predict(X_pred)[0]

            due_date = datetime.strptime(invoice['due_date'], '%Y-%m-%d')
            predicted_date = due_date + timedelta(days=predicted_delay)

            return predicted_date.strftime('%Y-%m-%d')

        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            return invoice.get('due_date')
