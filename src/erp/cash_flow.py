from datetime import datetime, timedelta
from typing import List, Dict, Optional
from src.erp.payment_predictor import PaymentPredictor

class CashFlowProjector:
    def __init__(self, invoices: List[Dict], expenses: List[Dict], predictor: Optional[PaymentPredictor] = None):
        self.invoices = invoices
        self.expenses = expenses
        self.predictor = predictor or PaymentPredictor()

        # Pre-calculate predictions
        self.invoice_predictions = {}
        self.expense_predictions = {}
        if self.predictor:
            # Predict for invoices
            self.invoice_predictions = self.predictor.predict_multiple(self.invoices)
            # Predict for expenses
            self.expense_predictions = self.predictor.predict_multiple(self.expenses)

    def calculate_projection(self, days: int = 30) -> List[Dict]:
        """
        Calculates projected cash flow for the next 'days' days.
        Returns a daily balance change list.
        """
        today = datetime.now().date()
        end_date = today + timedelta(days=days)

        daily_changes = {}

        # Process Invoices (Inflow)
        for invoice in self.invoices:
            # Determine expected payment date
            pay_date = self._determine_payment_date(invoice, self.invoice_predictions)

            if pay_date and today <= pay_date <= end_date:
                amount = float(invoice.get('amount', 0))
                self._add_to_daily(daily_changes, pay_date, amount, 'inflow')

        # Process Expenses (Outflow)
        for expense in self.expenses:
            # Determine expected payment date
            pay_date = self._determine_payment_date(expense, self.expense_predictions)

            if pay_date and today <= pay_date <= end_date:
                amount = float(expense.get('amount', 0))
                self._add_to_daily(daily_changes, pay_date, -amount, 'outflow')

        # Convert to sorted list
        projection = []
        current_date = today
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            change = daily_changes.get(current_date, {'inflow': 0, 'outflow': 0, 'net': 0})

            projection.append({
                'date': date_str,
                'inflow': change['inflow'],
                'outflow': change['outflow'],
                'net_change': change['net']
            })
            current_date += timedelta(days=1)

        return projection

    def _determine_payment_date(self, item: Dict, predictions: Dict[str, str] = None) -> Optional[datetime.date]:
        """Determines the likely payment date for an item."""
        # Check for specific override date first
        if item.get('metadata', {}).get('manual_override_pay_date'):
            try:
                return datetime.strptime(item['metadata']['manual_override_pay_date'], '%Y-%m-%d').date()
            except ValueError:
                pass

        # Try AI prediction if available (Cached)
        item_id = item.get('id') or item.get('doc_number')
        predicted_date = None

        if predictions and item_id:
            predicted_date = predictions.get(str(item_id))

        # Fallback to individual prediction if not in cache or no ID
        if not predicted_date and self.predictor:
            predicted_date = self.predictor.predict_expected_date(item)

        if predicted_date:
            try:
                return datetime.strptime(predicted_date, '%Y-%m-%d').date()
            except ValueError:
                pass

        # Fallback to due date
        if item.get('due_date'):
            try:
                return datetime.strptime(item.get('due_date'), '%Y-%m-%d').date()
            except ValueError:
                pass

        return None

    def _add_to_daily(self, daily_changes, date, amount, type_key):
        if date not in daily_changes:
            daily_changes[date] = {'inflow': 0, 'outflow': 0, 'net': 0}

        if type_key == 'inflow':
            daily_changes[date]['inflow'] += amount
        else:
            daily_changes[date]['outflow'] += abs(amount)

        daily_changes[date]['net'] += amount
