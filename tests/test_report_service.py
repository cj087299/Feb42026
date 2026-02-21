import unittest
from unittest.mock import MagicMock
from src.reports.report_service import ReportService
from src.invoices.qbo_connector import QBOConnector

class TestReportService(unittest.TestCase):
    def setUp(self):
        self.mock_qbo = MagicMock(spec=QBOConnector)
        self.service = ReportService(self.mock_qbo)

    def test_get_report_generic(self):
        self.mock_qbo.make_request.return_value = {"Header": {"ReportName": "Generic"}}
        result = self.service.get_report("Generic", {"param": "value"})

        self.mock_qbo.make_request.assert_called_with("reports/Generic", params={"param": "value"})
        self.assertEqual(result["Header"]["ReportName"], "Generic")

    def test_get_balance_sheet(self):
        self.service.get_balance_sheet(start_date="2023-01-01", end_date="2023-01-31")
        self.mock_qbo.make_request.assert_called_with(
            "reports/BalanceSheet",
            params={
                "start_date": "2023-01-01",
                "end_date": "2023-01-31",
                "accounting_method": "Accrual",
                "summarize_column_by": "Total"
            }
        )

    def test_get_ap_aging(self):
        self.service.get_ap_aging(date="2023-01-31")
        self.mock_qbo.make_request.assert_called_with(
            "reports/AgedPayables",
            params={"end_date": "2023-01-31"}
        )

    def test_get_transaction_list(self):
        self.service.get_transaction_list(start_date="2023-01-01", end_date="2023-01-31", account="123")
        self.mock_qbo.make_request.assert_called_with(
            "reports/TransactionList",
            params={
                "start_date": "2023-01-01",
                "end_date": "2023-01-31",
                "sort_by": "date",
                "sort_order": "desc",
                "account": "123"
            }
        )

    def test_get_comparison_report(self):
        self.mock_qbo.make_request.side_effect = [{"Report": "A"}, {"Report": "B"}]

        result = self.service.get_comparison_report(
            "BalanceSheet",
            {"start_date": "2023-01-01"},
            {"start_date": "2022-01-01"}
        )

        self.assertEqual(result["report_a"], {"Report": "A"})
        self.assertEqual(result["report_b"], {"Report": "B"})
        self.assertEqual(self.mock_qbo.make_request.call_count, 2)

if __name__ == '__main__':
    unittest.main()
