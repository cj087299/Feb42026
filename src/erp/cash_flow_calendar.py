from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from src.common.database import Database
from src.erp.payment_predictor import PaymentPredictor
import logging

logger = logging.getLogger(__name__)

class CashFlowCalendar:
    """
    Generates a daily cash flow calendar projection.
    Aggregates inflows (invoices, custom) and outflows (expenses, custom)
    to show projected daily balances.
    """

    def __init__(self,
                 invoices: List[Dict],
                 accounts_payable: List[Dict],
                 custom_flows: List[Dict],
                 predictor: Optional[PaymentPredictor] = None,
                 database: Optional[Database] = None):
        """
        Initialize the calendar projector.

        Args:
            invoices: List of receivable invoices (inflows)
            accounts_payable: List of bills/expenses (outflows)
            custom_flows: List of manual cash flow entries
            predictor: AI predictor for payment dates
            database: Database connection for metadata
        """
        self.invoices = invoices
        self.accounts_payable = accounts_payable
        self.custom_flows = custom_flows
        self.predictor = predictor
        self.database = database

        # Pre-fetch metadata to avoid N+1 queries
        self.invoice_metadata = {}
        if self.database:
            all_meta = self.database.get_all_invoice_metadata()
            self.invoice_metadata = {m['invoice_id']: m for m in all_meta}

        # Pre-calculate predictions to avoid N+1 model inference
        self.predictions = {}
        if self.predictor:
            self.predictions = self.predictor.predict_multiple(self.invoices)

    def _get_invoice_date(self, invoice: Dict) -> datetime.date:
        """
        Determine the projected payment date for an invoice.
        Priority:
        1. Manual override from database
        2. AI Prediction
        3. Portal submission date + Terms
        4. Due Date
        """
        inv_id = invoice.get('id') or invoice.get('doc_number')
        metadata = self.invoice_metadata.get(str(inv_id), {})

        # 1. Manual override
        if metadata.get('manual_override_pay_date'):
            try:
                return datetime.strptime(metadata['manual_override_pay_date'], '%Y-%m-%d').date()
            except ValueError:
                pass

        # 2. Portal submission + Terms (if available in metadata)
        if metadata.get('portal_submission_date'):
            try:
                submission_date = datetime.strptime(metadata['portal_submission_date'], '%Y-%m-%d').date()
                terms = int(invoice.get('terms_days', 30))
                return submission_date + timedelta(days=terms)
            except (ValueError, TypeError):
                pass

        # 3. AI Prediction (Cached)
        if self.predictor and inv_id:
            predicted = self.predictions.get(str(inv_id))
            if predicted:
                try:
                    return datetime.strptime(predicted, '%Y-%m-%d').date()
                except ValueError:
                    pass

        # 4. Due Date (Fallback)
        if invoice.get('due_date'):
            try:
                return datetime.strptime(invoice['due_date'], '%Y-%m-%d').date()
            except ValueError:
                pass

        # Absolute fallback: today
        return datetime.now().date()

    def calculate_daily_projection(self,
                                 start_date: datetime,
                                 end_date: datetime,
                                 initial_balance: float = 0.0,
                                 show_projected_inflows: bool = True,
                                 show_projected_outflows: bool = True,
                                 show_custom_inflows: bool = True,
                                 show_custom_outflows: bool = True) -> List[Dict]:
        """
        Calculate daily cash flow projection.

        Args:
            start_date: Start of projection period
            end_date: End of projection period
            initial_balance: Starting bank balance
            show_*: Toggles for different flow types

        Returns:
            List of daily summaries
        """
        # Initialize daily map
        days_map = {}
        curr_date = start_date.date()
        end_date_date = end_date.date()

        while curr_date <= end_date_date:
            days_map[curr_date] = {
                'date': curr_date.strftime('%Y-%m-%d'),
                'opening_balance': 0.0,
                'inflows': [],
                'outflows': [],
                'net_change': 0.0,
                'closing_balance': 0.0
            }
            curr_date += timedelta(days=1)

        # Process Invoices (Projected Inflows)
        if show_projected_inflows:
            for inv in self.invoices:
                # Skip paid invoices (balance = 0)
                if float(inv.get('balance', 0)) <= 0:
                    continue

                pay_date = self._get_invoice_date(inv)
                if start_date.date() <= pay_date <= end_date_date:
                    amount = float(inv.get('balance', 0))
                    days_map[pay_date]['inflows'].append({
                        'type': 'invoice',
                        'id': inv.get('id'),
                        'description': f"Invoice #{inv.get('doc_number')} - {inv.get('customer')}",
                        'amount': amount,
                        'is_projected': True
                    })

        # Process Custom Flows
        for flow in self.custom_flows:
            try:
                flow_date = datetime.strptime(flow['date'], '%Y-%m-%d').date()

                # Handle recurring flows
                # TODO: specific logic for recurrence expansion

                if start_date.date() <= flow_date <= end_date_date:
                    amount = float(flow['amount'])
                    flow_type = flow['flow_type'] # 'inflow' or 'outflow'

                    if flow_type == 'inflow' and show_custom_inflows:
                        days_map[flow_date]['inflows'].append({
                            'type': 'custom_inflow',
                            'id': flow.get('id'),
                            'description': flow.get('description', 'Custom Inflow'),
                            'amount': amount,
                            'is_projected': False # Manual entries are considered "certain"
                        })
                    elif flow_type == 'outflow' and show_custom_outflows:
                        days_map[flow_date]['outflows'].append({
                            'type': 'custom_outflow',
                            'id': flow.get('id'),
                            'description': flow.get('description', 'Custom Outflow'),
                            'amount': amount,
                            'is_projected': False
                        })
            except ValueError:
                continue

        # Calculate Balances
        running_balance = initial_balance
        sorted_dates = sorted(days_map.keys())
        result = []

        for date_key in sorted_dates:
            day_data = days_map[date_key]
            day_data['opening_balance'] = running_balance

            total_inflow = sum(i['amount'] for i in day_data['inflows'])
            total_outflow = sum(o['amount'] for o in day_data['outflows'])

            net_change = total_inflow - total_outflow
            day_data['net_change'] = net_change

            running_balance += net_change
            day_data['closing_balance'] = running_balance

            result.append(day_data)

        return result
