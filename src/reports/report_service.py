import logging
from src.invoices.qbo_connector import QBOConnector

logger = logging.getLogger(__name__)

class ReportService:
    def __init__(self, qbo_connector: QBOConnector):
        self.qbo = qbo_connector

    def get_report(self, report_name, params=None):
        """
        Fetches a generic report from QBO API.
        Endpoint: /reports/<report_name>
        """
        endpoint = f"reports/{report_name}"
        # Filter None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        logger.info(f"Fetching report: {report_name} with params: {params}")
        return self.qbo.make_request(endpoint, params=params)

    def get_balance_sheet(self, start_date=None, end_date=None, accounting_method="Accrual", summarize_column_by="Total"):
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "accounting_method": accounting_method,
            "summarize_column_by": summarize_column_by
        }
        return self.get_report("BalanceSheet", params)

    def get_profit_and_loss(self, start_date=None, end_date=None, accounting_method="Accrual", summarize_column_by="Total"):
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "accounting_method": accounting_method,
            "summarize_column_by": summarize_column_by
        }
        return self.get_report("ProfitAndLoss", params)

    def get_ap_aging(self, date=None, report_type="AgedPayables"):
        # For aging reports, 'end_date' is the 'As Of' date.
        params = {}
        if date:
            params["end_date"] = date
        return self.get_report(report_type, params)

    def get_ar_aging(self, date=None, report_type="AgedReceivables"):
         params = {}
         if date:
             params["end_date"] = date
         return self.get_report(report_type, params)

    def get_transaction_list(self, start_date=None, end_date=None,
                             sort_by="date", sort_order="desc",
                             account=None, customer=None, vendor=None,
                             transaction_type=None, **kwargs):
        """
        Fetches a Transaction List report.
        Useful for drill-down.
        """
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "sort_by": sort_by,
            "sort_order": sort_order
        }

        if account:
            params["account"] = account
        if customer:
            params["customer"] = customer
        if vendor:
            params["vendor"] = vendor
        if transaction_type:
             params["transaction_type"] = transaction_type

        params.update(kwargs)

        return self.get_report("TransactionList", params)

    def get_comparison_report(self, report_type, params_a, params_b):
        """
        Fetches two reports for side-by-side comparison.
        Returns a dictionary with both reports.
        """
        logger.info(f"Fetching comparison report: {report_type}")
        report_a = self.get_report(report_type, params_a)
        report_b = self.get_report(report_type, params_b)

        return {
            "report_a": report_a,
            "report_b": report_b
        }
