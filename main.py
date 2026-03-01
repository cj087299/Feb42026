"""VZT Accounting — Flask application entry point."""
import os
import json
import logging
import secrets
import threading
from queue import Queue, Empty

from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.common.database import Database
from src.common.error_handler import ErrorLogger, handle_errors, log_ai_action
from src.common.email_service import EmailService

from src.auth.utils import (
    hash_password, login_required, role_required, get_current_user, ROLES,
)
from src.auth.secret_manager import SecretManager
from src.auth.qbo_auth import QBOAuth

from src.invoices.qbo_connector import QBOConnector
from src.invoices.invoice_manager import InvoiceManager
from src.invoices.webhook_handler import WebhookHandler

from src.erp.payment_predictor import PaymentPredictor
from src.erp.ai_service import AIService
from src.reports.report_service import ReportService

# Blueprints
from src.routes.auth_routes import auth_bp
from src.routes.invoice_routes import invoice_bp
from src.routes.cashflow_routes import cashflow_bp
from src.routes.report_routes import report_bp
from src.routes.qbo_routes import qbo_bp

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dummy credential sentinels
# ---------------------------------------------------------------------------

DUMMY_QBO_CLIENT_ID = 'dummy_id'
DUMMY_QBO_CLIENT_SECRET = 'dummy_secret'
DUMMY_QBO_REFRESH_TOKEN = 'dummy_refresh'
DUMMY_QBO_REALM_ID = 'dummy_realm'

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> Flask:
    app = Flask(__name__)

    # ---- Secret key -------------------------------------------------------
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        logger.warning(
            "SECRET_KEY env var is not set — generating a random key. "
            "Sessions will be invalidated on every restart. Set SECRET_KEY in production."
        )
        secret_key = secrets.token_hex(32)
    app.secret_key = secret_key

    # ---- Database ---------------------------------------------------------
    database = Database()
    app.extensions['database'] = database

    # ---- Rate limiter -----------------------------------------------------
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["200 per minute"],
        storage_uri="memory://",
    )
    app.extensions['limiter'] = limiter
    # Tighten the login endpoint specifically
    limiter.limit("10 per minute")(auth_bp.view_functions.get('auth.login', lambda: None))

    # ---- Other services ---------------------------------------------------
    secret_manager = SecretManager(database=database)
    app.extensions['secret_manager'] = secret_manager

    error_logger = ErrorLogger()
    ai_service = AIService(database=database)
    app.extensions['ai_service'] = ai_service

    email_service = EmailService()
    app.extensions['email_service'] = email_service

    webhook_handler = WebhookHandler(database=database)
    app.extensions['webhook_handler'] = webhook_handler

    # ---- QBO client -------------------------------------------------------
    qbo_credentials = secret_manager.get_qbo_credentials()
    qbo_auth = QBOAuth(
        qbo_credentials.get('client_id', DUMMY_QBO_CLIENT_ID),
        qbo_credentials.get('client_secret', DUMMY_QBO_CLIENT_SECRET),
        qbo_credentials.get('refresh_token', DUMMY_QBO_REFRESH_TOKEN),
        qbo_credentials.get('realm_id', DUMMY_QBO_REALM_ID),
        database=database,
    )
    if qbo_credentials.get('access_token'):
        qbo_auth.access_token = qbo_credentials['access_token']
    app.extensions['qbo_auth'] = qbo_auth

    qbo_client = QBOConnector(qbo_auth)
    predictor = PaymentPredictor()
    app.extensions['predictor'] = predictor
    invoice_manager = InvoiceManager(qbo_client, database=database, predictor=predictor)

    if not qbo_auth.credentials_valid:
        logger.warning("QuickBooks credentials are NOT configured.")
    else:
        logger.info("QuickBooks credentials are configured.")

    # ---- Webhook queue (with DB persistence for failed events) -----------
    webhook_queue: Queue = Queue()
    app.extensions['webhook_queue'] = webhook_queue
    _start_webhook_processor(app, webhook_queue, webhook_handler, database)

    # ---- Register blueprints ---------------------------------------------
    app.register_blueprint(auth_bp)
    app.register_blueprint(invoice_bp)
    app.register_blueprint(cashflow_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(qbo_bp)

    # ---- Core routes (kept in main for simplicity) -----------------------
    _register_core_routes(app, database)

    # ---- Admin bootstrap --------------------------------------------------
    with app.app_context():
        _ensure_admin_users(database)

    return app


# ---------------------------------------------------------------------------
# Webhook processor
# ---------------------------------------------------------------------------


def _start_webhook_processor(app, webhook_queue: Queue, webhook_handler, database):
    """Start a background thread that drains the webhook queue.

    Failed events are persisted to the audit log (dead-letter record) so they
    are not silently lost if the queue empties on restart.
    """

    def _run():
        while True:
            try:
                event_data = webhook_queue.get(timeout=5)
            except Empty:
                continue

            if event_data is None:
                break  # Graceful shutdown signal

            event_id = event_data.get('id', 'unknown')
            try:
                with app.app_context():
                    parsed = webhook_handler.parse_cloudevents(event_data)
                    if not parsed:
                        logger.error(f"Webhook {event_id}: failed to parse CloudEvents payload")
                        _dead_letter(database, event_data, "parse_failed")
                    else:
                        result = webhook_handler.process_webhook_event(parsed)
                        logger.info(f"Webhook {event_id} processed: {result}")
            except Exception as e:
                logger.error(f"Webhook {event_id} processing error: {e}")
                _dead_letter(database, event_data, str(e))
            finally:
                webhook_queue.task_done()

    thread = threading.Thread(target=_run, daemon=True, name="webhook-processor")
    thread.start()
    logger.info("Webhook background processor started")


def _dead_letter(database, event_data: dict, reason: str):
    """Persist a failed webhook event to the audit log for later investigation."""
    try:
        database.log_audit(
            user_id=None,
            user_email=None,
            action='webhook_dead_letter',
            resource_type='webhook',
            resource_id=event_data.get('id'),
            details=json.dumps({'event': event_data, 'reason': reason}, default=str)[:4000],
        )
    except Exception as e:
        logger.error(f"Failed to write dead-letter record: {e}")


# ---------------------------------------------------------------------------
# Admin bootstrap
# ---------------------------------------------------------------------------


def _ensure_admin_users(database):
    """Create initial admin accounts if they do not already exist.

    Passwords are sourced from environment variables.  If an env var is not
    set a cryptographically random password is generated and logged ONCE so
    the operator can retrieve it.  We never ship a hardcoded default password.
    """
    bootstrap_accounts = [
        {
            'email': os.environ.get('ADMIN_EMAIL', 'cjones@vztsolutions.com'),
            'password_env': 'ADMIN_PASSWORD',
            'full_name': 'CJones',
            'role': 'master_admin',
        },
    ]

    for account in bootstrap_accounts:
        email = account['email']
        if database.get_user_by_email(email):
            continue

        password = os.environ.get(account['password_env'])
        if not password:
            password = secrets.token_urlsafe(16)
            logger.warning(
                f"Bootstrap admin '{email}' created with generated password: {password} "
                f"— set {account['password_env']} env var to control this."
            )
        else:
            logger.info(f"Bootstrap admin '{email}' created from {account['password_env']}.")

        password_hash = hash_password(password)
        database.create_user(email, password_hash, account['full_name'], account['role'])


# ---------------------------------------------------------------------------
# Core routes (index, health, AI stubs — not worth a separate blueprint)
# ---------------------------------------------------------------------------


def _register_core_routes(app: Flask, database):

    @app.route('/', methods=['GET'])
    def index():
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        best = request.accept_mimetypes.best_match(['text/html', 'application/json'])
        if best == 'text/html':
            return render_template('index.html')
        return jsonify({
            "service": "VZT Accounting API",
            "version": "1.0",
            "endpoints": {"health": "/health", "invoices": "/api/invoices", "cashflow": "/api/cashflow"},
        }), 200

    @app.route('/health', methods=['GET'])
    def health_check():
        if request.accept_mimetypes.best == 'text/html':
            return render_template('health.html')
        return jsonify({"status": "healthy"}), 200

    @app.route('/api/ai/chat', methods=['POST'])
    @login_required
    def ai_chat():
        return jsonify({'message': 'AI Chat'}), 200

    @app.route('/api/ai/action', methods=['POST'])
    @login_required
    def ai_action():
        return jsonify({'status': 'success'}), 200

    @app.route('/api/errors/recent', methods=['GET'])
    @login_required
    def get_recent_errors():
        return jsonify({'errors': []}), 200

    @app.route('/api/ai/operation-logs', methods=['GET'])
    @login_required
    def get_ai_operation_logs():
        return jsonify({'logs': []}), 200

    # ---- Consistent JSON error handlers -----------------------------------

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Bad request', 'detail': str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'error': 'Authentication required'}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'error': 'Permission denied'}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({'error': 'Too many requests — please slow down'}), 429

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Unhandled 500: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
