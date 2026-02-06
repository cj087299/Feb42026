import unittest
from src.qbo_client import QBOClient
from src.invoice_manager import InvoiceManager

class TestInvoiceManager(unittest.TestCase):
    def setUp(self):
        client = QBOClient("id", "secret", "refresh", "realm")
        self.manager = InvoiceManager(client)

    def test_fetch_invoices(self):
        invoices = self.manager.fetch_invoices()
        self.assertIsInstance(invoices, list)

if __name__ == '__main__':
    unittest.main()
