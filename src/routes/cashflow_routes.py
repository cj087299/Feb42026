"""Cash flow, liquidity, and custom-flow routes."""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template, current_app

from src.auth.utils import login_required, permission_required
from src.erp.cash_flow_calendar import CashFlowCalendar
from src.erp.payment_predictor import PaymentPredictor
from src.invoices.invoice_manager import InvoiceManager
from src.routes.shared import get_fresh_qbo_connector

logger = logging.getLogger(__name__)
cashflow_bp = Blueprint('cashflow', __name__)


@cashflow_bp.route('/cashflow', methods=['GET'])
@login_required
@permission_required('view_cashflow')
def cashflow_page():
    return render_template('cashflow.html')


@cashflow_bp.route('/liquidity', methods=['GET'])
@login_required
@permission_required('view_cashflow')
def liquidity_page():
    return render_template('liquidity.html')


@cashflow_bp.route('/api/cashflow', methods=['GET'])
@login_required
def get_cashflow():
    return jsonify({'days': 30, 'projected_balance_change': []}), 200


@cashflow_bp.route('/api/cashflow/calendar', methods=['GET'])
@login_required
def get_cashflow_calendar():
    try:
        database = current_app.extensions['database']
        ai_service = current_app.extensions['ai_service']
        fresh_connector, credentials_valid = get_fresh_qbo_connector()

        days = int(request.args.get('days', 90))
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)
        initial_balance = 0.0

        if credentials_valid:
            for account in fresh_connector.fetch_bank_accounts():
                initial_balance += float(account.get('CurrentBalance', 0))

        local_predictor = PaymentPredictor(
            ai_service=ai_service,
            qbo_client=fresh_connector if credentials_valid else None,
        )
        invoice_mgr = InvoiceManager(fresh_connector, database=database, predictor=local_predictor)
        invoices = invoice_mgr.fetch_invoices() if credentials_valid else []
        custom_flows = database.get_custom_cash_flows()

        calendar = CashFlowCalendar(
            invoices, [], custom_flows,
            predictor=local_predictor, database=database,
        )
        projection = calendar.calculate_daily_projection(start_date, end_date, initial_balance)

        return jsonify({
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'initial_balance': initial_balance,
            'daily_projection': projection,
        }), 200
    except Exception as e:
        logger.error(f"Error computing cashflow calendar: {e}")
        return jsonify({'error': 'Failed to compute cashflow calendar'}), 500


@cashflow_bp.route('/api/liquidity', methods=['GET'])
@login_required
@permission_required('view_cashflow')
def get_liquidity_metrics():
    try:
        database = current_app.extensions['database']
        predictor = current_app.extensions['predictor']
        fresh_connector, credentials_valid = get_fresh_qbo_connector()

        metrics = {
            'total_ar': 0.0,
            'total_ap': 0.0,
            'total_bank_balance': 0.0,
            'quick_ratio': None,
        }

        if credentials_valid:
            invoice_mgr = InvoiceManager(fresh_connector, database=database, predictor=predictor)
            invoices = invoice_mgr.fetch_invoices(qbo_filters={'status': 'pending'})
            metrics['total_ar'] = sum(float(inv.get('balance', 0)) for inv in invoices)

            bills = fresh_connector.fetch_bills()
            metrics['total_ap'] = sum(float(b.get('Balance', 0)) for b in bills)

            bank_accounts = fresh_connector.fetch_bank_accounts()
            metrics['total_bank_balance'] = sum(float(a.get('CurrentBalance', 0)) for a in bank_accounts)

            if metrics['total_ap'] > 0:
                metrics['quick_ratio'] = (
                    (metrics['total_bank_balance'] + metrics['total_ar']) / metrics['total_ap']
                )

        return jsonify(metrics), 200
    except Exception as e:
        logger.error(f"Error fetching liquidity metrics: {e}")
        return jsonify({'error': 'Failed to fetch liquidity metrics'}), 500


@cashflow_bp.route('/api/bank-accounts', methods=['GET'])
@login_required
def get_bank_accounts():
    return jsonify({'accounts': []}), 200


@cashflow_bp.route('/api/custom-cash-flows', methods=['GET', 'POST'])
@login_required
def custom_cash_flows():
    database = current_app.extensions['database']
    if request.method == 'GET':
        return jsonify(database.get_custom_cash_flows(request.args.get('flow_type'))), 200
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid or missing JSON body'}), 400
    flow_id = database.add_custom_cash_flow(data)
    return jsonify({'id': flow_id}), 201


@cashflow_bp.route('/api/custom-cash-flows/<int:flow_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def custom_cash_flow_detail(flow_id):
    database = current_app.extensions['database']
    if request.method == 'GET':
        flows = database.get_custom_cash_flows()
        match = next((f for f in flows if f['id'] == flow_id), None)
        return (jsonify(match), 200) if match else (jsonify({'error': 'Not found'}), 404)
    if request.method == 'PUT':
        data = request.get_json(silent=True) or {}
        database.update_custom_cash_flow(flow_id, data)
        return jsonify({'message': 'Updated'}), 200
    if request.method == 'DELETE':
        database.delete_custom_cash_flow(flow_id)
        return jsonify({'message': 'Deleted'}), 200
