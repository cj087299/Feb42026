from datetime import datetime
from src.qbo_client import QBOClient
import logging

logger = logging.getLogger(__name__)


class InvoiceManager:
    def __init__(self, qbo_client: QBOClient):
        self.client = qbo_client

    def fetch_invoices(self):
        """
        Fetches a list of invoices from QBO.
        """
        try:
            query = "select * from Invoice"
            logger.info("Fetching invoices from QBO.")
            response = self.client.make_request("query", params={"query": query})
            
            if response and "QueryResponse" in response:
                invoices = response["QueryResponse"].get("Invoice", [])
                logger.info(f"Fetched {len(invoices)} invoices from QBO")
                
                # Parse and normalize invoice data
                normalized_invoices = []
                for invoice in invoices:
                    normalized_invoices.append({
                        'id': invoice.get('Id'),
                        'doc_number': invoice.get('DocNumber'),
                        'customer_id': invoice.get('CustomerRef', {}).get('value') if invoice.get('CustomerRef') else None,
                        'customer': invoice.get('CustomerRef', {}).get('name') if invoice.get('CustomerRef') else None,
                        'amount': invoice.get('TotalAmt', 0),
                        'balance': invoice.get('Balance', 0),
                        'due_date': invoice.get('DueDate'),
                        'txn_date': invoice.get('TxnDate'),
                        'status': 'Paid' if invoice.get('Balance', 0) == 0 else 'Unpaid',
                        'CustomField': invoice.get('CustomField', []),
                        'terms_days': self._get_terms_days(invoice)
                    })
                
                return normalized_invoices
            
            logger.warning("No invoices found in QBO response")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch invoices: {e}")
            return []
    
    def _get_terms_days(self, invoice):
        """Extract payment terms in days from invoice.
        
        Returns:
            int: Number of days for payment terms. Defaults to 30 if not specified.
        """
        sales_term_ref = invoice.get('SalesTermRef')
        if sales_term_ref:
            # Common term mappings
            term_name = sales_term_ref.get('name', '').lower()
            if 'net 30' in term_name:
                return 30
            elif 'net 15' in term_name:
                return 15
            elif 'net 60' in term_name:
                return 60
            elif 'net 90' in term_name:
                return 90
            elif 'due on receipt' in term_name:
                return 0
        return 30  # Default to 30 days

    def _parse_date(self, date_str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            logger.debug(f"Failed to parse date: {date_str}")
            return None

    def filter_invoices(self, invoices, **kwargs):
        """
        Filters a list of invoices based on criteria.

        Supported kwargs:
        - start_date (str): Filter by due_date >= start_date (YYYY-MM-DD)
        - end_date (str): Filter by due_date <= end_date (YYYY-MM-DD)
        - customer_id (str): Filter by customer ID
        - invoice_number (str): Filter by document number
        - region (str): Filter by custom field 'Region'
        - status (str): Filter by payment status (e.g., 'Paid')
        - min_amount (float): Filter by amount >= min_amount
        - max_amount (float): Filter by amount <= max_amount
        """
        filtered = list(invoices)

        start_date = kwargs.get('start_date')
        if start_date:
            s_date = self._parse_date(start_date)
            if s_date:
                filtered = [
                    inv for inv in filtered
                    if (d := self._parse_date(inv.get('due_date'))) and d >= s_date
                ]
            else:
                logger.warning(f"Invalid start_date provided: {start_date}")

        end_date = kwargs.get('end_date')
        if end_date:
            e_date = self._parse_date(end_date)
            if e_date:
                filtered = [
                    inv for inv in filtered
                    if (d := self._parse_date(inv.get('due_date'))) and d <= e_date
                ]
            else:
                logger.warning(f"Invalid end_date provided: {end_date}")

        customer_id = kwargs.get('customer_id')
        if customer_id:
            filtered = [inv for inv in filtered if inv.get('customer_id') == customer_id]

        invoice_number = kwargs.get('invoice_number')
        if invoice_number:
            filtered = [inv for inv in filtered if inv.get('doc_number') == invoice_number]

        region = kwargs.get('region')
        if region:
            # Assuming custom fields are a list of dicts: [{'Name': 'Region', 'StringValue': 'North'}]
            filtered = [
                inv for inv in filtered
                if any(cf.get('Name') == 'Region' and cf.get('StringValue') == region for cf in inv.get('CustomField', []))
            ]

        status = kwargs.get('status')
        if status:
            filtered = [inv for inv in filtered if inv.get('status') == status]

        min_amount = kwargs.get('min_amount')
        if min_amount is not None:
            try:
                min_val = float(min_amount)
                filtered = [inv for inv in filtered if float(inv.get('amount', 0)) >= min_val]
            except ValueError:
                logger.warning(f"Invalid min_amount: {min_amount}")

        max_amount = kwargs.get('max_amount')
        if max_amount is not None:
            try:
                max_val = float(max_amount)
                filtered = [inv for inv in filtered if float(inv.get('amount', 0)) <= max_val]
            except ValueError:
                logger.warning(f"Invalid max_amount: {max_amount}")

        return filtered

    def sort_invoices(self, invoices, sort_by='due_date', reverse=False):
        """
        Sorts invoices by a key. Handles missing keys gracefully.
        """
        def get_sort_key(inv):
            val = inv.get(sort_by)
            if val is None:
                return ""
            return val

        return sorted(invoices, key=get_sort_key, reverse=reverse)

    def get_overdue_invoices(self):
        """
        Filters invoices to find overdue ones.
        """
        invoices = self.fetch_invoices()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        overdue = [
            inv for inv in invoices
            if inv.get('status') != 'Paid' and (d := self._parse_date(inv.get('due_date'))) and d < today
        ]
        return overdue
