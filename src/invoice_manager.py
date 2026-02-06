from src.qbo_client import QBOClient

class InvoiceManager:
    def __init__(self, qbo_client: QBOClient):
        self.client = qbo_client

    def fetch_invoices(self):
        """
        Fetches a list of invoices from QBO.
        """
        query = "select * from Invoice"
        response = self.client.make_request("query", params={"query": query})
        # Placeholder for parsing response
        return []

    def get_overdue_invoices(self):
        """
        Filters invoices to find overdue ones.
        """
        invoices = self.fetch_invoices()
        # Logic to filter overdue invoices would go here
        return []
