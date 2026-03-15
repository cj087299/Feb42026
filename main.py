import os
import logging

# Load .env file before anything else so credentials are available
try:
    from dotenv import load_dotenv
    import pathlib
    load_dotenv(pathlib.Path(__file__).parent / '.env')
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables

from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from src.qbo_client import QBOClient, InvalidQBORefreshTokenError # Import the new exception
from src.invoice_manager import InvoiceManager
from src.cash_flow_calendar import CashFlowCalendar
from src.cash_flow import CashFlowProjector
from src.ai_predictor import PaymentPredictor
from src.secret_manager import SecretManager
from src.database import Database
from src.auth import (
    hash_password, verify_password, login_required, permission_required, 
    role_required, get_current_user, audit_log, ROLES, has_permission
)
import json # New import
import requests # New import
import base64 # New import
from datetime import datetime, timedelta # New import

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Initialize Secret Manager and Database
secret_manager = SecretManager()
database = Database()

# Determine QBO environment and base URL
QBO_PRODUCTION_BASE_URL = "https://quickbooks.api.intuit.com/v3/company"
qbo_environment = os.environ.get('QBO_ENVIRONMENT', 'sandbox').lower()
qbo_base_url = QBO_PRODUCTION_BASE_URL if qbo_environment == 'production' else None # QBOClient will default to sandbox if None

# Initialize QBO client with credentials from Secret Manager
qbo_credentials = secret_manager.get_qbo_credentials()
qbo_client = QBOClient(
    qbo_credentials['client_id'],
    qbo_credentials['client_secret'],
    qbo_credentials['refresh_token'],
    qbo_credentials['realm_id'],
    base_url=qbo_base_url # Pass the determined base URL
)
invoice_manager = InvoiceManager(qbo_client)
# Train predictor with dummy data initially or load a saved model
predictor = PaymentPredictor()
# Ideally, we would load training data from a persistent source here
# For now, we leave it untrained or train on demand if data is available


@app.route('/', methods=['GET'])
def index():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    # Check if request is from browser (HTML) or API client (JSON)
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


@app.route('/login', methods=['GET'])
def login_page():
    """Display login page."""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/api/login', methods=['POST'])
@audit_log('user_login')
def login():
    """Handle user login."""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Get user from database
        user = database.get_user_by_email(email)
        
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not user['is_active']:
            return jsonify({'error': 'Account is inactive'}), 401
        
        # Verify password
        if not verify_password(password, user['password_hash']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Set session
        session['user_id'] = user['id']
        session['user_email'] = user['email']
        session['user_full_name'] = user['full_name']
        session['user_role'] = user['role']
        
        # Update last login
        database.update_last_login(user['id'])
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user['full_name'],
                'role': user['role']
            }
        }), 200
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/logout', methods=['POST'])
@audit_log('user_logout')
def logout():
    """Handle user logout."""
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200


@app.route('/api/me', methods=['GET'])
@login_required
def get_current_user_info():
    """Get current user information."""
    user = get_current_user()
    if user:
        return jsonify(user), 200
    return jsonify({'error': 'Not logged in'}), 401


@app.route('/invoices', methods=['GET'])
@login_required
@permission_required('view_invoices')
def invoices_page():
    return render_template('invoices.html')


@app.route('/cashflow', methods=['GET'])
@login_required
@permission_required('view_cashflow')
def cashflow_page():
    return render_template('cashflow.html')


@app.route('/users', methods=['GET'])
@login_required
@role_required('master_admin')
def users_page():
    """User management page (master admin only)."""
    return render_template('users.html')


@app.route('/audit', methods=['GET'])
@login_required
@permission_required('view_audit_log')
def audit_page():
    """Audit log page (admin and master admin only)."""
    return render_template('audit.html')


@app.route('/health', methods=['GET'])
def health_check():
    # Check if request is from browser (HTML) or API client (JSON)
    if request.accept_mimetypes.best == 'text/html' or \
       (request.accept_mimetypes.accept_html and 
        request.accept_mimetypes['text/html'] > request.accept_mimetypes['application/json']):
        return render_template('health.html')
    return jsonify({"status": "healthy"}), 200

# Constants for QBO OAuth
QBO_BASE_URL = "https://appcenter.intuit.com"
QBO_AUTHORIZE_URL = f"{QBO_BASE_URL}/connect/oauth2"
QBO_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

# Helper function to URL encode parameters
def url_encode(params):
    return '&'.join([f"{key}={value}" for key, value in params.items()])

@app.route('/qbo/auth', methods=['GET'])
@login_required
@permission_required('manage_qbo_credentials') # Assuming a new permission for this
@audit_log('initiate_qbo_oauth', 'qbo')
def qbo_auth():
    """Initiates the QBO OAuth 2.0 authorization flow."""
    # Dynamically build QBO_REDIRECT_URI
    qbo_redirect_uri = url_for('qbo_oauth_callback', _external=True)

    params = {
        "client_id": qbo_client.client_id,
        "scope": "com.intuit.quickbooks.accounting openid profile email phone address",
        "redirect_uri": qbo_redirect_uri,
        "response_type": "code",
        "state": "security_token_" + os.urandom(16).hex() # CSRF protection
    }
    logger.info(f"Initiating QBO OAuth flow to: {QBO_AUTHORIZE_URL}")
    return redirect(f"{QBO_AUTHORIZE_URL}?{url_encode(params)}")


@app.route('/qbo/oauth-callback', methods=['GET'])
@audit_log('complete_qbo_oauth', 'qbo')
def qbo_oauth_callback():
    """Handles the redirect from QBO after authorization."""
    global qbo_client, invoice_manager # Declare as global to re-initialize

    error = request.args.get('error')
    state = request.args.get('state')
    code = request.args.get('code')
    realm_id = request.args.get('realmId')

    if error:
        logger.error(f"QBO OAuth callback error: {error}")
        return jsonify({"error": f"OAuth Error: {error}"}), 400

    # Validate state for CSRF protection
    # In a real app, you'd store the state in session and compare
    # if state != session.get('oauth_state'):
    #     return jsonify({"error": "Invalid state parameter"}), 400

    qbo_redirect_uri = url_for('qbo_oauth_callback', _external=True)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + base64.b64encode(f"{qbo_client.client_id}:{qbo_client.client_secret}".encode()).decode()
    }
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": qbo_redirect_uri
    }

    try:
        response = requests.post(QBO_TOKEN_URL, headers=headers, data=payload)
        response.raise_for_status() # Raise an exception for HTTP errors
        token_data = response.json()

        new_refresh_token = token_data.get('refresh_token')
        new_access_token = token_data.get('access_token')

        if new_refresh_token:
            # Store the new refresh token securely using Secret Manager
            secret_manager.set_secret('QBO_Refresh_Token', new_refresh_token) # Changed from QBO_REFRESH_TOKEN to QBO_Refresh_Token
            os.environ['QBO_REFRESH_TOKEN'] = new_refresh_token # Also update env var for consistency
            logger.info("New QBO refresh token successfully stored in Secret Manager and environment.")
            
        if realm_id:
            # For this app, realm_id is an env var, so we update the Secret Manager and env var
            secret_manager.set_secret('QBO_Realm_Id', realm_id) # Changed from QBO_REALM_ID to QBO_Realm_Id
            os.environ['QBO_REALM_ID'] = realm_id # Update env var for current runtime
            logger.info(f"QBO Realm ID updated to: {realm_id} in Secret Manager and environment.")

        # Re-initialize qbo_client and invoice_manager with updated credentials
        updated_qbo_credentials = secret_manager.get_qbo_credentials()
        
        # Determine QBO environment and base URL for re-initialization
        qbo_environment_callback = os.environ.get('QBO_ENVIRONMENT', 'sandbox').lower()
        qbo_base_url_callback = QBO_PRODUCTION_BASE_URL if qbo_environment_callback == 'production' else None

        qbo_client = QBOClient(
            updated_qbo_credentials['client_id'],
            updated_qbo_credentials['client_secret'],
            new_refresh_token, # Use the new refresh token directly
            updated_qbo_credentials['realm_id'],
            base_url=qbo_base_url_callback # Pass the determined base URL
        )
        # Manually set access token for immediate use as the client would re-fetch it
        qbo_client.access_token = new_access_token
        qbo_client.access_token_expires_at = datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
        invoice_manager = InvoiceManager(qbo_client) # Re-initialize invoice manager with new client

        logger.info("QBO OAuth flow completed successfully. Tokens updated and client re-initialized.")
        return redirect(url_for('index') + '?qbo_connected=1')

    except requests.exceptions.RequestException as e:
        logger.error(f"Error exchanging QBO authorization code for tokens: {e}")
        return jsonify({"error": f"Failed to exchange code for tokens: {e}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error during QBO OAuth callback: {e}")
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/qbo/status', methods=['GET'])
@login_required
def qbo_status():
    """Returns the current QBO connection status."""
    refresh_token = qbo_client.refresh_token
    is_connected = bool(refresh_token and refresh_token not in ('dummy_refresh', '', None))
    return jsonify({
        'connected': is_connected,
        'realm_id': qbo_client.realm_id if is_connected else None
    }), 200


@app.route('/qbo/disconnect', methods=['POST'])
@login_required
@permission_required('manage_qbo_credentials')
@audit_log('disconnect_qbo', 'qbo')
def qbo_disconnect():
    """Disconnects QBO by revoking the token and clearing stored credentials."""
    global qbo_client, invoice_manager

    current_refresh_token = qbo_client.refresh_token
    current_access_token = qbo_client.access_token

    # Attempt to revoke the token with Intuit
    revoke_url = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
    token_to_revoke = current_refresh_token or current_access_token
    if token_to_revoke and token_to_revoke not in ('dummy_refresh', ''):
        try:
            revoke_headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": "Basic " + base64.b64encode(
                    f"{qbo_client.client_id}:{qbo_client.client_secret}".encode()
                ).decode()
            }
            requests.post(revoke_url, headers=revoke_headers, data={"token": token_to_revoke}, timeout=10)
            logger.info("QBO token revoked with Intuit.")
        except Exception as e:
            logger.warning(f"Failed to revoke QBO token with Intuit (continuing disconnect): {e}")

    # Clear stored credentials
    secret_manager.delete_secret_value('QBO_Refresh_Token')
    secret_manager.set_secret('QBO_Refresh_Token', '')

    # Re-initialize client with dummy credentials (keeps client_id/secret for reconnect)
    client_id = qbo_client.client_id
    client_secret = qbo_client.client_secret
    qbo_environment_dc = os.environ.get('QBO_ENVIRONMENT', 'production').lower()
    qbo_base_url_dc = QBO_PRODUCTION_BASE_URL if qbo_environment_dc == 'production' else None
    qbo_client = QBOClient(client_id, client_secret, '', '', base_url=qbo_base_url_dc)
    invoice_manager = InvoiceManager(qbo_client)

    logger.info("QBO disconnected successfully.")
    return jsonify({"message": "QBO disconnected successfully."}), 200


@app.route('/api/invoices', methods=['GET'])
@login_required
@permission_required('view_invoices')
@audit_log('view_invoices', 'invoice')
def get_invoices():
    try:
        # Extract query parameters for filtering
        filters = {
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'date_type': request.args.get('date_type', 'TxnDate'), # Default to TxnDate
            'customer_id': request.args.get('customer_id'),
            'customer_name': request.args.get('customer_name'),
            'invoice_number': request.args.get('invoice_number'),
            'status': request.args.get('status'),
            'min_amount': request.args.get('min_amount'),
            'max_amount': request.args.get('max_amount'),
            'payment_terms': request.args.get('payment_terms'),
            'region': request.args.get('region')
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}

        invoices = invoice_manager.fetch_invoices(**filters) # Pass filters directly
        # The in-memory filter_invoices is no longer needed here
        # filtered_invoices = invoice_manager.filter_invoices(invoices, **filters) 
        filtered_invoices = invoices # Already filtered by fetch_invoices

        sort_by = request.args.get('sort_by', 'due_date')
        reverse = request.args.get('reverse', 'false').lower() == 'true'

        sorted_invoices = invoice_manager.sort_invoices(filtered_invoices, sort_by=sort_by, reverse=reverse)
        
        # Enrich invoices with metadata from database more efficiently
        invoice_ids = [inv.get('id') for inv in sorted_invoices if inv.get('id')]
        if invoice_ids:
            metadata_map = database.get_invoice_metadata_for_ids(invoice_ids)
            for invoice in sorted_invoices:
                invoice_id = invoice.get('id')
                if invoice_id in metadata_map:
                    invoice['metadata'] = metadata_map[invoice_id]

        return jsonify(sorted_invoices), 200
    except InvalidQBORefreshTokenError:
        logger.warning("QBO Refresh Token invalid for invoices. Redirecting to OAuth.")
        return redirect(url_for('qbo_auth'))
    except Exception as e:
        logger.error(f"Error fetching invoices: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/invoices/<invoice_id>/metadata', methods=['GET', 'POST'])
@login_required
def invoice_metadata(invoice_id):
    """Get or update invoice metadata."""
    if request.method == 'GET':
        if not has_permission(session.get('user_role'), 'view_invoices'):
            return jsonify({'error': 'Permission denied'}), 403
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
        if not has_permission(session.get('user_role'), 'edit_invoice_metadata'):
            return jsonify({'error': 'Permission denied'}), 403
        try:
            data = request.get_json()
            success = database.save_invoice_metadata(invoice_id, data)
            if success:
                # Log the action
                database.log_audit(
                    user_id=session.get('user_id'),
                    user_email=session.get('user_email'),
                    action='update_invoice_metadata',
                    resource_type='invoice',
                    resource_id=invoice_id,
                    details=str(data),
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string if request.user_agent else None
                )
                return jsonify({"message": "Metadata saved successfully"}), 200
            else:
                return jsonify({"error": "Failed to save metadata"}), 500
        except Exception as e:
            logger.error(f"Error saving invoice metadata: {e}")
            return jsonify({"error": str(e)}), 500


@app.route('/api/cashflow', methods=['GET'])
@login_required
@permission_required('view_cashflow')
@audit_log('view_cashflow', 'cashflow')
def get_cashflow():
    try:
        days = int(request.args.get('days', 30))
        # Pass filters to fetch_invoices
        filters = {
            'end_date': (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        }
        invoices = invoice_manager.fetch_invoices(**filters)
        # Mock expenses for now, or fetch from another source if available
        expenses = []

        projector = CashFlowProjector(invoices, expenses, predictor=predictor)
        projection = projector.calculate_projection(days=days)

        return jsonify({
            "days": days,
            "projected_balance_change": projection
        }), 200
    except InvalidQBORefreshTokenError:
        logger.warning("QBO Refresh Token invalid for cashflow. Redirecting to OAuth.")
        return redirect(url_for('qbo_auth'))
    except Exception as e:
        logger.error(f"Error calculating cashflow: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/cashflow/calendar', methods=['GET'])
@login_required
@permission_required('view_cashflow')
@audit_log('view_cashflow_calendar', 'cashflow')
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
        
        # Fetch data - Pass filters to fetch_invoices
        invoice_filters = {}
        if start_date_param:
            invoice_filters['start_date'] = start_date_param
        if end_date_param:
            invoice_filters['end_date'] = end_date_param

        invoices = invoice_manager.fetch_invoices(**invoice_filters) # Pass filters
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
    except InvalidQBORefreshTokenError:
        logger.warning("QBO Refresh Token invalid for cashflow calendar. Redirecting to OAuth.")
        return redirect(url_for('qbo_auth'))
    except Exception as e:
        logger.error(f"Error calculating calendar cashflow: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/bank-accounts', methods=['GET'])
@login_required
@permission_required('view_cashflow')
@audit_log('view_bank_accounts', 'qbo_bank_accounts') # Updated audit log action
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
    except InvalidQBORefreshTokenError:
        logger.warning("QBO Refresh Token invalid for bank accounts. Redirecting to OAuth.")
        return redirect(url_for('qbo_auth'))
    except Exception as e:
        logger.error(f"Error fetching bank accounts: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/custom-cash-flows', methods=['GET', 'POST'])
@login_required
def custom_cash_flows():
    """Get all custom cash flows or add a new one."""
    if request.method == 'GET':
        if not has_permission(session.get('user_role'), 'view_cashflow'):
            return jsonify({'error': 'Permission denied'}), 403
        try:
            flow_type = request.args.get('flow_type')  # 'inflow' or 'outflow'
            flows = database.get_custom_cash_flows(flow_type)
            return jsonify(flows), 200
        except Exception as e:
            logger.error(f"Error fetching custom cash flows: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'POST':
        # Check permissions based on flow type
        data = request.get_json()
        flow_type = data.get('flow_type')
        if flow_type == 'inflow' and not has_permission(session.get('user_role'), 'add_custom_inflows'):
            return jsonify({'error': 'Permission denied'}), 403
        if flow_type == 'outflow' and not has_permission(session.get('user_role'), 'add_custom_outflows'):
            return jsonify({'error': 'Permission denied'}), 403
        
        try:
            flow_id = database.add_custom_cash_flow(data)
            if flow_id:
                # Log the action
                database.log_audit(
                    user_id=session.get('user_id'),
                    user_email=session.get('user_email'),
                    action='add_custom_cash_flow',
                    resource_type='custom_cash_flow',
                    resource_id=str(flow_id),
                    details=str(data),
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string if request.user_agent else None
                )
                return jsonify({"message": "Custom cash flow added", "id": flow_id}), 201
            else:
                return jsonify({"error": "Failed to add custom cash flow"}), 500
        except Exception as e:
            logger.error(f"Error adding custom cash flow: {e}")
            return jsonify({"error": str(e)}), 500


@app.route('/api/custom-cash-flows/<int:flow_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def custom_cash_flow_detail(flow_id):
    """Get, update, or delete a specific custom cash flow."""
    if request.method == 'GET':
        if not has_permission(session.get('user_role'), 'view_cashflow'):
            return jsonify({'error': 'Permission denied'}), 403
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
        if not has_permission(session.get('user_role'), 'edit_custom_flows'):
            return jsonify({'error': 'Permission denied'}), 403
        try:
            data = request.get_json()
            success = database.update_custom_cash_flow(flow_id, data)
            if success:
                # Log the action
                database.log_audit(
                    user_id=session.get('user_id'),
                    user_email=session.get('user_email'),
                    action='update_custom_cash_flow',
                    resource_type='custom_cash_flow',
                    resource_id=str(flow_id),
                    details=str(data),
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string if request.user_agent else None
                )
                return jsonify({"message": "Custom cash flow updated"}), 200
            else:
                return jsonify({"error": "Failed to update custom cash flow"}), 500
        except Exception as e:
            logger.error(f"Error updating custom cash flow: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'DELETE':
        if not has_permission(session.get('user_role'), 'delete_custom_flows'):
            return jsonify({'error': 'Permission denied'}), 403
        try:
            success = database.delete_custom_cash_flow(flow_id)
            if success:
                # Log the action
                database.log_audit(
                    user_id=session.get('user_id'),
                    user_email=session.get('user_email'),
                    action='delete_custom_cash_flow',
                    resource_type='custom_cash_flow',
                    resource_id=str(flow_id),
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string if request.user_agent else None
                )
                return jsonify({"message": "Custom cash flow deleted"}), 200
            else:
                return jsonify({"error": "Failed to delete custom cash flow"}), 500
        except Exception as e:
            logger.error(f"Error deleting custom cash flow: {e}")
            return jsonify({"error": str(e)}), 500


# User management API routes

@app.route('/api/users', methods=['GET', 'POST'])
@login_required
@role_required('master_admin')
def manage_users():
    """Get all users or create a new user (master admin only)."""
    if request.method == 'GET':
        try:
            users = database.get_all_users()
            return jsonify(users), 200
        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
            full_name = data.get('full_name')
            role = data.get('role')
            
            if not email or not password or not role:
                return jsonify({'error': 'Email and password are required'}), 400
            
            if role not in ROLES:
                return jsonify({'error': f'Invalid role. Must be one of: {", ".join(ROLES.keys())}'}), 400
            
            # Check if user already exists
            existing_user = database.get_user_by_email(email)
            if existing_user:
                return jsonify({'error': 'User with this email already exists'}), 400
            
            # Hash password
            password_hash = hash_password(password)
            
            # Create user
            user_id = database.create_user(email, password_hash, full_name, role)
            
            if user_id:
                # Log the action
                database.log_audit(
                    user_id=session.get('user_id'),
                    user_email=session.get('user_email'),
                    action='create_user',
                    resource_type='user',
                    resource_id=str(user_id),
                    details=f"Created user {email} with role {role}",
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string if request.user_agent else None
                )
                return jsonify({"message": "User created successfully", "id": user_id}), 201
            else:
                return jsonify({"error": "Failed to create user"}), 500
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return jsonify({"error": str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@role_required('master_admin')
def manage_user_detail(user_id):
    """Get, update, or delete a specific user (master admin only)."""
    if request.method == 'GET':
        try:
            user = database.get_user_by_id(user_id)
            if user:
                # Remove password hash from response
                user.pop('password_hash', None)
                return jsonify(user), 200
            else:
                return jsonify({"error": "User not found"}), 404
        except Exception as e:
            logger.error(f"Error fetching user: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            
            # Validate role if provided
            if 'role' in data and data['role'] not in ROLES:
                return jsonify({'error': f'Invalid role. Must be one of: {", ".join(ROLES.keys())}'}), 400
            
            # Hash new password if provided
            if 'password' in data:
                data['password_hash'] = hash_password(data.pop('password'))
            
            success = database.update_user(user_id, data)
            
            if success:
                # Log the action
                database.log_audit(
                    user_id=session.get('user_id'),
                    user_email=session.get('user_email'),
                    action='update_user',
                    resource_type='user',
                    resource_id=str(user_id),
                    details=str(data),
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string if request.user_agent else None
                )
                return jsonify({"message": "User updated successfully"}), 200
            else:
                return jsonify({"error": "Failed to update user"}), 500
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            # Prevent deleting yourself
            if user_id == session.get('user_id'):
                return jsonify({"error": "Cannot delete your own account"}), 400
            
            success = database.delete_user(user_id)
            
            if success:
                # Log the action
                database.log_audit(
                    user_id=session.get('user_id'),
                    user_email=session.get('user_email'),
                    action='delete_user',
                    resource_type='user',
                    resource_id=str(user_id),
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string if request.user_agent else None
                )
                return jsonify({"message": "User deleted successfully"}), 200
            else:
                return jsonify({"error": "Failed to delete user"}), 500
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return jsonify({"error": str(e)}), 500


@app.route('/api/roles', methods=['GET'])
@login_required
@role_required('master_admin')
def get_roles():
    """Get all available roles and their permissions."""
    return jsonify(ROLES), 200


# Audit log API routes

@app.route('/api/audit-log', methods=['GET'])
@login_required
@permission_required('view_audit_log')
def get_audit_log():
    """Get audit log entries (admin and master admin only)."""
    try:
        user_id = request.args.get('user_id', type=int)
        action = request.args.get('action')
        resource_type = request.args.get('resource_type')
        limit = request.args.get('limit', default=100, type=int)
        
        logs = database.get_audit_logs(user_id, action, resource_type, limit)
        return jsonify(logs), 200
    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)