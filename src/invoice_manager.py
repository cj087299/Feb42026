from datetime import datetime, timedelta
from src.qbo_client import QBOClient
import logging

logger = logging.getLogger(__name__)


class InvoiceManager:
    def __init__(self, qbo_client: QBOClient, database=None, predictor=None):
        self.client = qbo_client
        self.database = database
        self.predictor = predictor

    def fetch_invoices(self, qbo_filters=None):
        """
        Fetches a list of invoices from QBO with optional server-side filtering.
        
        Args:
            qbo_filters (dict): Optional filters to apply in QBO query
                - status: 'paid' or 'pending' or 'overdue'
                
        Returns:
            list: Normalized invoice data
        """
        try:
            # Build WHERE clause based on filters
            where_clauses = []
            
            if qbo_filters:
                status = qbo_filters.get('status')
                if status == 'paid':
                    where_clauses.append("Balance = '0'")
                elif status == 'pending':
                    where_clauses.append("Balance > '0'")
                elif status == 'overdue':
                    # For overdue, we need to filter paid out and check due date client-side
                    where_clauses.append("Balance > '0'")
            
            # Build final query
            if where_clauses:
                query = f"select * from Invoice WHERE {' AND '.join(where_clauses)}"
            else:
                query = "select * from Invoice"
            
            logger.info(f"Fetching invoices from QBO with query: {query}")
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
        - invoice_start_date (str): Filter by txn_date >= invoice_start_date (YYYY-MM-DD)
        - invoice_end_date (str): Filter by txn_date <= invoice_end_date (YYYY-MM-DD)
        - customer_id (str): Filter by customer ID
        - invoice_number (str): Filter by document number
        - region (str): Filter by custom field 'Region'
        - status (str): Filter by payment status (e.g., 'Paid', 'Unpaid')
        - min_amount (float): Filter by amount >= min_amount (only if not empty string)
        - max_amount (float): Filter by amount <= max_amount (only if not empty string)
        - vzt_rep (str): Filter by VZT Rep metadata
        - customer_portal (str): Filter by Customer Portal metadata
        - missing_portal_submission (bool): Filter invoices missing portal submission date
        - search_query (str): Search by invoice number or customer name
        """
        filtered = list(invoices)

        # Due date filters
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

        # Invoice date (TxnDate) filters
        invoice_start_date = kwargs.get('invoice_start_date')
        if invoice_start_date:
            s_date = self._parse_date(invoice_start_date)
            if s_date:
                filtered = [
                    inv for inv in filtered
                    if (d := self._parse_date(inv.get('txn_date'))) and d >= s_date
                ]
            else:
                logger.warning(f"Invalid invoice_start_date provided: {invoice_start_date}")

        invoice_end_date = kwargs.get('invoice_end_date')
        if invoice_end_date:
            e_date = self._parse_date(invoice_end_date)
            if e_date:
                filtered = [
                    inv for inv in filtered
                    if (d := self._parse_date(inv.get('txn_date'))) and d <= e_date
                ]
            else:
                logger.warning(f"Invalid invoice_end_date provided: {invoice_end_date}")

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
            # Map frontend status values to backend values
            if status.lower() == 'paid':
                filtered = [inv for inv in filtered if inv.get('status', '').lower() == 'paid']
            elif status.lower() == 'pending':
                filtered = [inv for inv in filtered if inv.get('status', '').lower() != 'paid']
            elif status.lower() == 'overdue':
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                filtered = [
                    inv for inv in filtered 
                    if inv.get('status', '').lower() != 'paid' and 
                    (d := self._parse_date(inv.get('due_date'))) and d < today
                ]

        # Amount filters - only apply if value is not empty string
        min_amount = kwargs.get('min_amount')
        if min_amount and min_amount != '':
            try:
                min_val = float(min_amount)
                filtered = [inv for inv in filtered if float(inv.get('amount', 0)) >= min_val]
            except ValueError:
                logger.warning(f"Invalid min_amount: {min_amount}")

        max_amount = kwargs.get('max_amount')
        if max_amount and max_amount != '':
            try:
                max_val = float(max_amount)
                filtered = [inv for inv in filtered if float(inv.get('amount', 0)) <= max_val]
            except ValueError:
                logger.warning(f"Invalid max_amount: {max_amount}")

        # VZT metadata filters
        vzt_rep = kwargs.get('vzt_rep')
        if vzt_rep:
            filtered = [
                inv for inv in filtered
                if inv.get('metadata', {}).get('vzt_rep') == vzt_rep
            ]

        customer_portal = kwargs.get('customer_portal')
        if customer_portal:
            filtered = [
                inv for inv in filtered
                if inv.get('metadata', {}).get('customer_portal_name') == customer_portal
            ]

        missing_portal_submission = kwargs.get('missing_portal_submission')
        if missing_portal_submission and missing_portal_submission.lower() in ['true', '1', 'yes']:
            filtered = [
                inv for inv in filtered
                if not inv.get('metadata', {}).get('portal_submission_date')
            ]

        # Search query - filter by invoice number or customer name
        search_query = kwargs.get('search_query')
        if search_query:
            search_lower = search_query.lower()
            filtered = [
                inv for inv in filtered
                if search_lower in str(inv.get('doc_number', '')).lower() or
                   search_lower in str(inv.get('customer', '')).lower() or
                   search_lower in str(inv.get('id', '')).lower()
            ]

        return filtered

    def sort_invoices(self, invoices, sort_by='due_date', reverse=False):
        """
        Sorts invoices by a key. Handles missing keys gracefully.
        Supports sorting by: due_date, invoice_date, amount, customer, status
        """
        def get_sort_key(inv):
            # Map sort_by to actual field names
            field_map = {
                'invoice_date': 'txn_date',
                'due_date': 'due_date',
                'amount': 'amount',
                'customer': 'customer',
                'status': 'status'
            }
            
            field = field_map.get(sort_by, sort_by)
            val = inv.get(field)
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

    def calculate_projected_pay_date(self, invoice):
        """
        Calculate the projected pay date for an invoice using priority logic:
        1. manual_override_pay_date if exists
        2. portal_submission_date + Net Terms (30/45/60 days) if portal_submission_date exists
        3. AI Predictor date if available and trained
        4. QBO Due Date as absolute fallback
        
        Args:
            invoice: Invoice dict with invoice data
            
        Returns:
            datetime or None: The projected payment date
        """
        invoice_id = invoice.get('id') or invoice.get('doc_number')
        
        # Priority 1: Check for manual override
        if self.database and invoice_id:
            metadata = self.database.get_invoice_metadata(str(invoice_id))
            
            if metadata:
                # Priority 1: Manual override
                manual_override = metadata.get('manual_override_pay_date')
                if manual_override:
                    try:
                        return datetime.strptime(manual_override, '%Y-%m-%d')
                    except ValueError:
                        logger.warning(f"Invalid manual_override_pay_date for invoice {invoice_id}: {manual_override}")
                
                # Priority 2: Portal submission date + Net Terms
                portal_submission = metadata.get('portal_submission_date')
                if portal_submission:
                    try:
                        submission_date = datetime.strptime(portal_submission, '%Y-%m-%d')
                        terms_days = invoice.get('terms_days', 30)
                        return submission_date + timedelta(days=terms_days)
                    except ValueError:
                        logger.warning(f"Invalid portal_submission_date for invoice {invoice_id}: {portal_submission}")
        
        # Priority 3: AI Predictor
        if self.predictor and self.predictor.is_trained:
            try:
                predicted_date_str = self.predictor.predict_expected_date(invoice)
                if predicted_date_str:
                    return datetime.strptime(predicted_date_str, '%Y-%m-%d')
            except Exception as e:
                logger.debug(f"Prediction failed for invoice {invoice_id}: {e}")
        
        # Priority 4: QBO Due Date (fallback)
        due_date_str = invoice.get('due_date')
        if due_date_str:
            try:
                return datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                logger.warning(f"Invalid due_date for invoice {invoice_id}: {due_date_str}")
        
        return None
