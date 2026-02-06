from datetime import datetime, timedelta

class CashFlowProjector:
    def __init__(self, invoices, expenses):
        """
        invoices: List of dicts, e.g., [{'amount': 100, 'due_date': '2023-10-01'}]
        expenses: List of dicts, e.g., [{'amount': 50, 'due_date': '2023-10-05'}]
        """
        self.invoices = invoices
        self.expenses = expenses

    def calculate_projection(self, days=30):
        """
        Calculates cash flow projection for the next 'days' days.
        """
        projected_balance = 0.0
        cutoff_date = datetime.now() + timedelta(days=days)

        for invoice in self.invoices:
            due_date = datetime.strptime(invoice.get('due_date', '2999-01-01'), '%Y-%m-%d')
            if due_date <= cutoff_date:
                projected_balance += float(invoice.get('amount', 0))

        for expense in self.expenses:
            due_date = datetime.strptime(expense.get('due_date', '2999-01-01'), '%Y-%m-%d')
            if due_date <= cutoff_date:
                projected_balance -= float(expense.get('amount', 0))

        return projected_balance
