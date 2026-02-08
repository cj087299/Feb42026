import os
import logging
from flask import Flask, jsonify, request, render_template
from src.qbo_client import QBOClient
from src.invoice_manager import InvoiceManager
from src.cash_flow import CashFlowProjector
from src.ai_predictor import PaymentPredictor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize components
# In a real app, you would load these from environment variables or a secret manager
CLIENT_ID = os.environ.get('QBO_CLIENT_ID', 'dummy_id')
CLIENT_SECRET = os.environ.get('QBO_CLIENT_SECRET', 'dummy_secret')
REFRESH_TOKEN = os.environ.get('QBO_REFRESH_TOKEN', 'dummy_refresh')
REALM_ID = os.environ.get('QBO_REALM_ID', 'dummy_realm')

qbo_client = QBOClient(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, REALM_ID)
invoice_manager = InvoiceManager(qbo_client)
# Train predictor with dummy data initially or load a saved model
predictor = PaymentPredictor()
# Ideally, we would load training data from a persistent source here
# For now, we leave it untrained or train on demand if data is available


@app.route('/', methods=['GET'])
def index():
    # Check if request is from browser (HTML) or API client (JSON)
    if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
        return render_template('index.html')
    return jsonify({
        "service": "QBO Cash Flow Projection API",
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
    if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
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

        return jsonify(sorted_invoices), 200
    except Exception as e:
        logger.error(f"Error fetching invoices: {e}")
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
