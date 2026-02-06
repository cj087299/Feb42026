import pandas as pd
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

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
        df = pd.DataFrame(historical_invoices)

        if df.empty:
            print("No data to train on.")
            return

        # Calculate target: days delayed (payment_date - due_date)
        # If payment_date is missing, we can't use it for training (or assume today/overdue logic, but let's stick to paid ones)
        df = df.dropna(subset=['payment_date', 'due_date'])

        if df.empty:
            print("No valid paid invoices to train on.")
            return

        df['due_date_dt'] = pd.to_datetime(df['due_date'])
        df['payment_date_dt'] = pd.to_datetime(df['payment_date'])

        df['days_delayed'] = (df['payment_date_dt'] - df['due_date_dt']).dt.days

        # Features: customer_id, amount
        X = df[['customer_id', 'amount']]
        y = df['days_delayed']

        self.model.fit(X, y)
        self.is_trained = True
        print("Model trained successfully.")

    def predict_expected_date(self, invoice):
        """
        Predicts the expected payment date for an open invoice.

        invoice: dict with keys:
            - customer_id
            - amount
            - due_date
        """
        if not self.is_trained:
            # Fallback if model isn't trained
            return invoice.get('due_date')

        # Create DataFrame for single prediction
        X_pred = pd.DataFrame([invoice])[['customer_id', 'amount']]

        predicted_delay = self.model.predict(X_pred)[0]

        due_date = datetime.strptime(invoice['due_date'], '%Y-%m-%d')
        predicted_date = due_date + timedelta(days=predicted_delay)

        return predicted_date.strftime('%Y-%m-%d')
