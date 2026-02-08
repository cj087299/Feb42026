from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CashFlowCalendar:
    """Enhanced cash flow projector with calendar-style daily breakdown."""
    
    def __init__(self, invoices, accounts_payable, custom_flows, predictor=None, database=None):
        """
        Initialize the cash flow calendar.
        
        Args:
            invoices: List of invoices from QBO
            accounts_payable: List of accounts payable from QBO
            custom_flows: List of custom cash flows from database
            predictor: Optional AI predictor for payment dates
            database: Database instance for fetching invoice metadata
        """
        self.invoices = invoices
        self.accounts_payable = accounts_payable
        self.custom_flows = custom_flows
        self.predictor = predictor
        self.database = database
    
    def calculate_daily_projection(self, start_date: datetime, end_date: datetime, 
                                   initial_balance: float = 0.0,
                                   show_projected_inflows: bool = True,
                                   show_projected_outflows: bool = True,
                                   show_custom_inflows: bool = True,
                                   show_custom_outflows: bool = True) -> Dict:
        """
        Calculate daily cash flow projection with calendar view.
        
        Returns a dictionary with dates as keys and cash flow details as values.
        """
        projection = {}
        current_balance = initial_balance
        
        # Initialize all dates in range
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            projection[date_str] = {
                'date': date_str,
                'projected_inflows': [],
                'projected_outflows': [],
                'custom_inflows': [],
                'custom_outflows': [],
                'total_inflow': 0.0,
                'total_outflow': 0.0,
                'net_change': 0.0,
                'balance': current_balance
            }
            current_date += timedelta(days=1)
        
        # Process projected inflows from invoices
        if show_projected_inflows:
            for invoice in self.invoices:
                if invoice.get('status') == 'Paid':
                    continue  # Skip paid invoices
                
                # Get effective payment date
                payment_date = self._get_invoice_payment_date(invoice)
                if not payment_date:
                    continue
                
                payment_date_str = payment_date.strftime('%Y-%m-%d')
                
                if payment_date_str in projection:
                    amount = float(invoice.get('amount', 0))
                    projection[payment_date_str]['projected_inflows'].append({
                        'type': 'invoice',
                        'id': invoice.get('id') or invoice.get('doc_number'),
                        'customer': invoice.get('customer') or invoice.get('customer_id'),
                        'amount': amount,
                        'description': f"Invoice {invoice.get('doc_number', 'N/A')}"
                    })
                    projection[payment_date_str]['total_inflow'] += amount
        
        # Process projected outflows from accounts payable
        if show_projected_outflows:
            for bill in self.accounts_payable:
                due_date_str = bill.get('due_date')
                if not due_date_str:
                    continue
                
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                    due_date_str = due_date.strftime('%Y-%m-%d')
                    
                    if due_date_str in projection:
                        amount = float(bill.get('amount', 0))
                        projection[due_date_str]['projected_outflows'].append({
                            'type': 'bill',
                            'id': bill.get('id') or bill.get('doc_number'),
                            'vendor': bill.get('vendor') or bill.get('vendor_id'),
                            'amount': amount,
                            'description': f"Bill {bill.get('doc_number', 'N/A')}"
                        })
                        projection[due_date_str]['total_outflow'] += amount
                except ValueError:
                    logger.warning(f"Invalid due date for bill: {due_date_str}")
        
        # Process custom cash flows
        for flow in self.custom_flows:
            flow_type = flow.get('flow_type')
            is_recurring = flow.get('is_recurring', False)
            
            if is_recurring:
                # Handle recurring flows
                dates = self._get_recurring_dates(
                    flow,
                    start_date,
                    end_date
                )
            else:
                # Single occurrence
                flow_date_str = flow.get('date')
                if flow_date_str:
                    try:
                        flow_date = datetime.strptime(flow_date_str, '%Y-%m-%d')
                        dates = [flow_date] if start_date <= flow_date <= end_date else []
                    except ValueError:
                        dates = []
                else:
                    dates = []
            
            # Add flow to projection
            for flow_date in dates:
                date_str = flow_date.strftime('%Y-%m-%d')
                if date_str in projection:
                    amount = float(flow.get('amount', 0))
                    flow_entry = {
                        'type': 'custom',
                        'id': flow.get('id'),
                        'amount': amount,
                        'description': flow.get('description', 'Custom flow')
                    }
                    
                    if flow_type == 'inflow' and show_custom_inflows:
                        projection[date_str]['custom_inflows'].append(flow_entry)
                        projection[date_str]['total_inflow'] += amount
                    elif flow_type == 'outflow' and show_custom_outflows:
                        projection[date_str]['custom_outflows'].append(flow_entry)
                        projection[date_str]['total_outflow'] += amount
        
        # Calculate net changes and running balances
        current_balance = initial_balance
        for date_str in sorted(projection.keys()):
            day_data = projection[date_str]
            day_data['net_change'] = day_data['total_inflow'] - day_data['total_outflow']
            current_balance += day_data['net_change']
            day_data['balance'] = current_balance
        
        return projection
    
    def _get_invoice_payment_date(self, invoice: Dict) -> Optional[datetime]:
        """Get the expected payment date for an invoice."""
        # First, check if we have customer portal submission date from metadata
        if self.database:
            invoice_id = invoice.get('id') or invoice.get('doc_number')
            metadata = self.database.get_invoice_metadata(str(invoice_id))
            
            if metadata and metadata.get('customer_portal_submission_date'):
                try:
                    submission_date = datetime.strptime(
                        metadata['customer_portal_submission_date'], 
                        '%Y-%m-%d'
                    )
                    
                    # Add payment terms to submission date
                    terms_days = invoice.get('terms_days', 30)  # Default 30 days
                    payment_date = submission_date + timedelta(days=terms_days)
                    return payment_date
                except ValueError:
                    pass
        
        # Use AI predictor if available
        if self.predictor and self.predictor.is_trained:
            try:
                predicted_date_str = self.predictor.predict_expected_date(invoice)
                if predicted_date_str:
                    return datetime.strptime(predicted_date_str, '%Y-%m-%d')
            except Exception as e:
                logger.error(f"Prediction failed: {e}")
        
        # Fall back to due date
        due_date_str = invoice.get('due_date')
        if due_date_str:
            try:
                return datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                pass
        
        return None
    
    def _get_recurring_dates(self, flow: Dict, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Calculate all dates for a recurring flow within the date range."""
        dates = []
        
        recurrence_type = flow.get('recurrence_type')
        recurrence_interval = flow.get('recurrence_interval', 1)
        
        # Get recurrence range
        rec_start_str = flow.get('recurrence_start_date')
        rec_end_str = flow.get('recurrence_end_date')
        
        if not rec_start_str:
            return dates
        
        try:
            rec_start = datetime.strptime(rec_start_str, '%Y-%m-%d')
            rec_end = datetime.strptime(rec_end_str, '%Y-%m-%d') if rec_end_str else end_date
        except ValueError:
            return dates
        
        # Limit to requested range
        effective_start = max(start_date, rec_start)
        effective_end = min(end_date, rec_end)
        
        current = effective_start
        
        if recurrence_type == 'weekly':
            # Weekly recurrence
            while current <= effective_end:
                dates.append(current)
                current += timedelta(weeks=recurrence_interval)
        
        elif recurrence_type == 'monthly':
            # Monthly recurrence (same day of month)
            while current <= effective_end:
                dates.append(current)
                # Add months
                month = current.month + recurrence_interval
                year = current.year + (month - 1) // 12
                month = ((month - 1) % 12) + 1
                try:
                    current = current.replace(year=year, month=month)
                except ValueError:
                    # Handle day overflow (e.g., Jan 31 -> Feb 28)
                    # Use last day of month
                    if month == 12:
                        next_month = 1
                        next_year = year + 1
                    else:
                        next_month = month + 1
                        next_year = year
                    current = datetime(next_year, next_month, 1) - timedelta(days=1)
        
        elif recurrence_type == 'custom_days':
            # Every X days
            while current <= effective_end:
                dates.append(current)
                current += timedelta(days=recurrence_interval)
        
        return dates
