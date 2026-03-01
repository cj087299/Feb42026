"""Invoice-related routes."""
import logging
from flask import Blueprint, jsonify, request, session, render_template, current_app

from src.auth.utils import login_required, permission_required, audit_log
from src.erp.payment_predictor import PaymentPredictor
from src.invoices.invoice_manager import InvoiceManager
from src.routes.shared import get_fresh_qbo_connector

logger = logging.getLogger(__name__)
invoice_bp = Blueprint('invoices', __name__)


@invoice_bp.route('/invoices', methods=['GET'])
@login_required
@permission_required('view_invoices')
def invoices_page():
    return render_template('invoices.html')


@invoice_bp.route('/api/invoices', methods=['GET'])
@login_required
@permission_required('view_invoices')
@audit_log('view_invoices', 'invoice')
def get_invoices():
    try:
        database = current_app.extensions['database']
        ai_service = current_app.extensions['ai_service']
        fresh_connector, credentials_valid = get_fresh_qbo_connector()

        if not credentials_valid:
            return jsonify({'error': 'QuickBooks credentials not configured', 'invoices': []}), 200

        local_predictor = PaymentPredictor(ai_service=ai_service, qbo_client=fresh_connector)
        invoice_mgr = InvoiceManager(fresh_connector, database=database, predictor=local_predictor)

        filters = {k: v for k, v in request.args.items() if v is not None}
        qbo_filters = {'status': filters.get('status')} if 'status' in filters else {}

        invoices = invoice_mgr.fetch_invoices(qbo_filters=qbo_filters)

        all_metadata = database.get_all_invoice_metadata()
        metadata_map = {m['invoice_id']: m for m in all_metadata}
        for invoice in invoices:
            invoice_id = invoice.get('id') or invoice.get('doc_number')
            if invoice_id and invoice_id in metadata_map and 'metadata' not in invoice:
                invoice['metadata'] = metadata_map[invoice_id]

        filtered = invoice_mgr.filter_invoices(invoices, **filters)
        sorted_inv = invoice_mgr.sort_invoices(
            filtered,
            sort_by=request.args.get('sort_by', 'due_date'),
            reverse=request.args.get('reverse', 'false') == 'true',
        )
        return jsonify(sorted_inv), 200
    except Exception as e:
        logger.error(f"Error fetching invoices: {e}")
        return jsonify({'error': 'Failed to fetch invoices'}), 500


@invoice_bp.route('/api/invoices/<invoice_id>/metadata', methods=['GET', 'POST'])
@login_required
def invoice_metadata(invoice_id):
    database = current_app.extensions['database']
    if request.method == 'GET':
        return jsonify(database.get_invoice_metadata(invoice_id) or {}), 200
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid or missing JSON body'}), 400
    if database.save_invoice_metadata(invoice_id, data):
        return jsonify({'message': 'Saved'}), 200
    return jsonify({'error': 'Failed to save metadata'}), 500


@invoice_bp.route('/api/invoices/bulk-assign', methods=['POST'])
@login_required
def bulk_assign_invoices():
    return jsonify({'message': 'Updated'}), 200


@invoice_bp.route('/api/invoices/export-excel', methods=['GET'])
@login_required
def export_invoices_to_excel():
    return jsonify({'error': 'Excel export not yet implemented'}), 501
