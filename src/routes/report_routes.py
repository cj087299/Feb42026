"""Report-related routes."""
import logging
from flask import Blueprint, jsonify, request, session, render_template, current_app

from src.auth.utils import login_required
from src.reports.report_service import ReportService
from src.routes.shared import get_fresh_qbo_connector

logger = logging.getLogger(__name__)
report_bp = Blueprint('reports', __name__)


@report_bp.route('/reports', methods=['GET'])
@login_required
def reports_page():
    return render_template('reports.html')


@report_bp.route('/api/reports/<report_type>', methods=['GET'])
@login_required
def get_report(report_type):
    try:
        fresh_connector, credentials_valid = get_fresh_qbo_connector()
        if not credentials_valid:
            return jsonify({'error': 'QuickBooks credentials not configured'}), 400

        report_service = ReportService(fresh_connector)
        compare = request.args.get('compare') == 'true'

        if compare:
            params_a = {k.replace('_a', ''): v for k, v in request.args.items() if k.endswith('_a')}
            params_b = {k.replace('_b', ''): v for k, v in request.args.items() if k.endswith('_b')}
            common = {k: v for k, v in request.args.items()
                      if not k.endswith('_a') and not k.endswith('_b') and k != 'compare'}
            params_a.update(common)
            params_b.update(common)
            result = report_service.get_comparison_report(report_type, params_a, params_b)
        else:
            result = report_service.get_report(report_type, request.args)

        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error fetching report {report_type}: {e}")
        return jsonify({'error': 'Failed to fetch report'}), 500


@report_bp.route('/api/reports/drilldown', methods=['GET'])
@login_required
def get_report_drilldown():
    try:
        fresh_connector, credentials_valid = get_fresh_qbo_connector()
        if not credentials_valid:
            return jsonify({'error': 'QuickBooks credentials not configured'}), 400

        report_service = ReportService(fresh_connector)
        result = report_service.get_transaction_list(**dict(request.args))
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error fetching drilldown: {e}")
        return jsonify({'error': 'Failed to fetch drilldown'}), 500


@report_bp.route('/api/reports/saved', methods=['GET', 'POST'])
@login_required
def saved_reports():
    database = current_app.extensions['database']
    user_id = session.get('user_id')

    if request.method == 'GET':
        return jsonify(database.get_saved_reports(user_id)), 200

    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    report_type = data.get('report_type', '').strip()
    params = data.get('params', {})

    if not name or not report_type:
        return jsonify({'error': 'name and report_type are required'}), 400

    report_id = database.save_report_view(user_id, name, report_type, params)
    if report_id:
        return jsonify({'id': report_id, 'message': 'Report view saved'}), 201
    return jsonify({'error': 'Failed to save report'}), 500


@report_bp.route('/api/reports/saved/<int:report_id>', methods=['DELETE'])
@login_required
def delete_saved_report(report_id):
    database = current_app.extensions['database']
    user_id = session.get('user_id')
    if database.delete_saved_report(report_id, user_id):
        return jsonify({'message': 'Deleted'}), 200
    return jsonify({'error': 'Not found or not owned by user'}), 404
