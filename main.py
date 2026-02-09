import os
import logging
from flask import Flask, jsonify, request, render_template
from src.qbo_client import QBOClient
from src.invoice_manager import InvoiceManager
from src.cash_flow_calendar import CashFlowCalendar
from src.cash_flow import CashFlowProjector
from src.ai_predictor import PaymentPredictor
from src.secret_manager import SecretManager
from src.database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize Secret Manager and Database
secret_manager = SecretManager()
database = Database()

# Initialize QBO client with credentials from Secret Manager
qbo_credentials = secret_manager.get_qbo_credentials()
qbo_client = QBOClient(
    qbo_credentials['client_id'],
    qbo_credentials['client_secret'],
    qbo_credentials['refresh_token'],
    qbo_credentials['realm_id']
)
invoice_manager = InvoiceManager(qbo_client)
# Train predictor with dummy data initially or load a saved model
predictor = PaymentPredictor()
# Ideally, we would load training data from a persistent source here
# For now, we leave it untrained or train on demand if data is available


@app.route('/', methods=['GET'])
def index():
    # Check if request is from browser (HTML) or API client (JSON)
    # Browsers typically have HTML with higher quality than JSON
    if request.accept_mimetypes.best == 'text/html' or \
       (request.accept_mimetypes.accept_html and 
        request.accept_mimetypes['text/html'] > request.accept_mimetypes['application/json']):
        return render_template('index.html')
    return jsonify({
        "service": "VZT Accounting API",
        "version": "1.0",
        "endpoints": {
            "health": "/health",
            "invoices": "/api/invoices",
            "cashflow": "/api/cashflow"
        }
    }), 200


@app.route('/invoices', methods=['GET'])
def invoices_page():
    return render_template('invoices.html')


@app.route('/cashflow', methods=['GET'])
def cashflow_page():
    return render_template('cashflow.html')


@app.route('/health', methods=['GET'])
def health_check():
    # Check if request is from browser (HTML) or API client (JSON)
    if request.accept_mimetypes.best == 'text/html' or \
       (request.accept_mimetypes.accept_html and 
        request.accept_mimetypes['text/html'] > request.accept_mimetypes['application/json']):
        return render_template('health.html')
    return jsonify({"status": "healthy"}), 200


@app.route('/api/invoices', methods=['GET'])
def get_invoices():
    try:
        # Extract query parameters for filtering
        filters = {
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'customer_id': request.args.get('customer_id'),
            'status': request.args.get('status'),
            'min_amount': request.args.get('min_amount'),
            'max_amount': request.args.get('max_amount'),
            'region': request.args.get('region')
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}

        invoices = invoice_manager.fetch_invoices()
        filtered_invoices = invoice_manager.filter_invoices(invoices, **filters)

        sort_by = request.args.get('sort_by', 'due_date')
        reverse = request.args.get('reverse', 'false').lower() == 'true'

        sorted_invoices = invoice_manager.sort_invoices(filtered_invoices, sort_by=sort_by, reverse=reverse)
        
        # Enrich invoices with metadata from database
        all_metadata = database.get_all_invoice_metadata()
        metadata_map = {m['invoice_id']: m for m in all_metadata}
        
        for invoice in sorted_invoices:
            invoice_id = invoice.get('id') or invoice.get('doc_number')
            if invoice_id and invoice_id in metadata_map:
                invoice['metadata'] = metadata_map[invoice_id]

        return jsonify(sorted_invoices), 200
    except Exception as e:
        logger.error(f"Error fetching invoices: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/invoices/<invoice_id>/metadata', methods=['GET', 'POST'])
def invoice_metadata(invoice_id):
    """Get or update invoice metadata."""
    if request.method == 'GET':
        try:
            metadata = database.get_invoice_metadata(invoice_id)
            if metadata:
                return jsonify(metadata), 200
            else:
                return jsonify({}), 200
        except Exception as e:
            logger.error(f"Error fetching invoice metadata: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            success = database.save_invoice_metadata(invoice_id, data)
            if success:
                return jsonify({"message": "Metadata saved successfully"}), 200
            else:
                return jsonify({"error": "Failed to save metadata"}), 500
        except Exception as e:
            logger.error(f"Error saving invoice metadata: {e}")
            return jsonify({"error": str(e)}), 500


@app.route('/api/cashflow', methods=['GET'])
def get_cashflow():
    try:
        days = int(request.args.get('days', 30))
        invoices = invoice_manager.fetch_invoices()
        # Mock expenses for now, or fetch from another source if available
        expenses = []

        projector = CashFlowProjector(invoices, expenses, predictor=predictor)
        projection = projector.calculate_projection(days=days)

        return jsonify({
            "days": days,
            "projected_balance_change": projection
        }), 200
    except Exception as e:
        logger.error(f"Error calculating cashflow: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/cashflow/calendar', methods=['GET'])
def get_cashflow_calendar():
    """Get calendar-style cash flow projection with daily breakdown."""
    try:
        from datetime import datetime, timedelta
        
        # Get parameters
        days = int(request.args.get('days', 90))
        initial_balance_param = request.args.get('initial_balance')
        start_date_param = request.args.get('start_date')
        end_date_param = request.args.get('end_date')
        
        # Get initial balance from QBO if not provided
        if initial_balance_param:
            initial_balance = float(initial_balance_param)
        else:
            # Fetch from QBO
            bank_accounts = qbo_client.fetch_bank_accounts()
            initial_balance = 0.0
            for account in bank_accounts:
                balance = account.get('CurrentBalance', 0)
                initial_balance += float(balance) if balance else 0
            logger.info(f"Using QBO bank balance: {initial_balance}")
        
        # Toggle parameters
        show_projected_inflows = request.args.get('show_projected_inflows', 'true').lower() == 'true'
        show_projected_outflows = request.args.get('show_projected_outflows', 'true').lower() == 'true'
        show_custom_inflows = request.args.get('show_custom_inflows', 'true').lower() == 'true'
        show_custom_outflows = request.args.get('show_custom_outflows', 'true').lower() == 'true'
        
        # Calculate date range
        if start_date_param and end_date_param:
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = datetime.strptime(end_date_param, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=days)
        
        # Fetch data
        invoices = invoice_manager.fetch_invoices()
        accounts_payable = []  # TODO: Fetch from QBO when available
        custom_flows = database.get_custom_cash_flows()
        
        # Create calendar projector
        calendar = CashFlowCalendar(
            invoices=invoices,
            accounts_payable=accounts_payable,
            custom_flows=custom_flows,
            predictor=predictor,
            database=database
        )
        
        # Calculate projection
        projection = calendar.calculate_daily_projection(
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance,
            show_projected_inflows=show_projected_inflows,
            show_projected_outflows=show_projected_outflows,
            show_custom_inflows=show_custom_inflows,
            show_custom_outflows=show_custom_outflows
        )
        
        return jsonify({
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "initial_balance": initial_balance,
            "daily_projection": projection
        }), 200
    except Exception as e:
        logger.error(f"Error calculating calendar cashflow: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/bank-accounts', methods=['GET'])
def get_bank_accounts():
    """Get bank accounts and their current balances from QBO."""
    try:
        bank_accounts = qbo_client.fetch_bank_accounts()
        
        # Format the response
        accounts_data = []
        total_balance = 0.0
        
        for account in bank_accounts:
            balance = float(account.get('CurrentBalance', 0))
            total_balance += balance
            
            accounts_data.append({
                'id': account.get('Id'),
                'name': account.get('Name'),
                'account_number': account.get('AcctNum', 'N/A'),
                'balance': balance,
                'currency': account.get('CurrencyRef', {}).get('value', 'USD')
            })
        
        return jsonify({
            'accounts': accounts_data,
            'total_balance': total_balance,
            'as_of': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error fetching bank accounts: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/custom-cash-flows', methods=['GET', 'POST'])
def custom_cash_flows():
    """Get all custom cash flows or add a new one."""
    if request.method == 'GET':
        try:
            flow_type = request.args.get('flow_type')  # 'inflow' or 'outflow'
            flows = database.get_custom_cash_flows(flow_type)
            return jsonify(flows), 200
        except Exception as e:
            logger.error(f"Error fetching custom cash flows: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            flow_id = database.add_custom_cash_flow(data)
            if flow_id:
                return jsonify({"message": "Custom cash flow added", "id": flow_id}), 201
            else:
                return jsonify({"error": "Failed to add custom cash flow"}), 500
        except Exception as e:
            logger.error(f"Error adding custom cash flow: {e}")
            return jsonify({"error": str(e)}), 500


@app.route('/api/custom-cash-flows/<int:flow_id>', methods=['GET', 'PUT', 'DELETE'])
def custom_cash_flow_detail(flow_id):
    """Get, update, or delete a specific custom cash flow."""
    if request.method == 'GET':
        try:
            flows = database.get_custom_cash_flows()
            flow = next((f for f in flows if f['id'] == flow_id), None)
            if flow:
                return jsonify(flow), 200
            else:
                return jsonify({"error": "Cash flow not found"}), 404
        except Exception as e:
            logger.error(f"Error fetching custom cash flow: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            success = database.update_custom_cash_flow(flow_id, data)
            if success:
                return jsonify({"message": "Custom cash flow updated"}), 200
            else:
                return jsonify({"error": "Failed to update custom cash flow"}), 500
        except Exception as e:
            logger.error(f"Error updating custom cash flow: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            success = database.delete_custom_cash_flow(flow_id)
            if success:
                return jsonify({"message": "Custom cash flow deleted"}), 200
            else:
                return jsonify({"error": "Failed to delete custom cash flow"}), 500
        except Exception as e:
            logger.error(f"Error deleting custom cash flow: {e}")
            return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
