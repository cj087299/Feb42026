from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CashFlowProjector:
    def __init__(self, invoices, expenses, predictor=None):
        """
        invoices: List of dicts, e.g., [{'amount': 100, 'due_date': '2023-10-01', 'customer_id': 'C1'}]
        expenses: List of dicts, e.g., [{'amount': 50, 'due_date': '2023-10-05'}]
        predictor: Optional PaymentPredictor instance.
        """
        self.invoices = invoices
        self.expenses = expenses
        self.predictor = predictor

    def calculate_projection(self, days=30):
        """
        Calculates cash flow projection for the next 'days' days.
        If a predictor is available and trained, it uses predicted payment dates.
        """
        projected_balance = 0.0
        cutoff_date = datetime.now() + timedelta(days=days)

        for invoice in self.invoices:
            # Determine effective date (predicted or due date)
            effective_date_str = invoice.get('due_date', '2999-01-01')

            if self.predictor and self.predictor.is_trained:
                try:
                    predicted_date = self.predictor.predict_expected_date(invoice)
                    if predicted_date:
                        effective_date_str = predicted_date
                except Exception as e:
                    logger.error(f"Prediction failed for invoice {invoice.get('doc_number')}: {e}")

            effective_date = datetime.strptime(effective_date_str, '%Y-%m-%d')

            if effective_date <= cutoff_date:
                projected_balance += float(invoice.get('amount', 0))

        for expense in self.expenses:
            effective_date = datetime.strptime(expense.get('due_date', '2999-01-01'), '%Y-%m-%d')
            if effective_date <= cutoff_date:
                projected_balance -= float(expense.get('amount', 0))

        return projected_balance
