import os
import logging
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from src.qbo_client import QBOClient
from src.invoice_manager import InvoiceManager
from src.cash_flow_calendar import CashFlowCalendar
from src.cash_flow import CashFlowProjector
from src.ai_predictor import PaymentPredictor
from src.secret_manager import SecretManager
from src.database import Database
from src.ai_service import AIService
from src.error_handler import ErrorLogger, handle_errors, log_ai_action
from src.auth import (
    hash_password, verify_password, login_required, permission_required, 
    role_required, get_current_user, audit_log, ROLES, has_permission
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Initialize Secret Manager and Database
secret_manager = SecretManager()
database = Database()

# Initialize Error Logger
error_logger = ErrorLogger()

# Initialize AI Service
ai_service = AIService()

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


@app.route('/forgot-password', methods=['GET'])
def forgot_password_page():
    """Display forgot password page."""
    return render_template('forgot-password.html')


@app.route('/forgot-username', methods=['GET'])
def forgot_username_page():
    """Display forgot username page."""
    return render_template('forgot-username.html')


@app.route('/reset-password', methods=['GET'])
def reset_password_page():
    """Display reset password page."""
    return render_template('reset-password.html')


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


@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset."""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Get user from database
        user = database.get_user_by_email(email)
        
        if not user:
            # Don't reveal if user exists or not for security
            return jsonify({'message': 'If the email exists, a password reset link has been sent'}), 200
        
        # Generate reset token
        import secrets
        token = secrets.token_urlsafe(32)
        
        # Token expires in 1 hour
        from datetime import datetime, timedelta
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        
        # Save token to database
        database.create_password_reset_token(user['id'], token, expires_at)
        
        # In a real application, you would send an email with the reset link
        # For now, we'll just log it (without the full token for security)
        logger.info(f"Password reset requested for user ID {user['id']}")
        
        return jsonify({'message': 'If the email exists, a password reset link has been sent'}), 200
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    """Reset password using token."""
    try:
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('password')
        
        if not token or not new_password:
            return jsonify({'error': 'Token and new password are required'}), 400
        
        # Get token from database
        token_data = database.get_password_reset_token(token)
        
        if not token_data:
            return jsonify({'error': 'Invalid or expired token'}), 400
        
        if token_data['used']:
            return jsonify({'error': 'Token has already been used'}), 400
        
        # Check if token is expired
        from datetime import datetime
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            return jsonify({'error': 'Token has expired'}), 400
        
        # Update password
        password_hash = hash_password(new_password)
        success = database.update_user(token_data['user_id'], {'password_hash': password_hash})
        
        if success:
            # Mark token as used
            database.mark_token_as_used(token)
            
            # Log the action
            user = database.get_user_by_id(token_data['user_id'])
            database.log_audit(
                user_id=token_data['user_id'],
                user_email=user['email'] if user else None,
                action='password_reset',
                resource_type='user',
                resource_id=str(token_data['user_id']),
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string if request.user_agent else None
            )
            
            return jsonify({'message': 'Password reset successful'}), 200
        else:
            return jsonify({'error': 'Failed to reset password'}), 500
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/forgot-username', methods=['POST'])
def forgot_username():
    """Request username reminder (email lookup)."""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Get user from database
        user = database.get_user_by_email(email)
        
        if not user:
            # Don't reveal if user exists or not for security
            return jsonify({'message': 'If the email exists, a username reminder has been sent'}), 200
        
        # In a real application, you would send an email with the username
        # For now, we'll just log the request
        logger.info(f"Username reminder requested")
        
        return jsonify({'message': 'If the email exists, a username reminder has been sent'}), 200
    except Exception as e:
        logger.error(f"Forgot username error: {e}")
        return jsonify({'error': str(e)}), 500


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
@login_required
@permission_required('view_cashflow')
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
                return jsonify({'error': 'Email, password, and role are required'}), 400
            
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


# AI Chat API routes

@app.route('/api/ai/chat', methods=['POST'])
@login_required
@audit_log('ai_chat')
@handle_errors('ai_chat')
def ai_chat():
    """Handle AI chat messages (available to all authenticated users)."""
    try:
        data = request.get_json()
        message = data.get('message')
        conversation_history = data.get('history', [])
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        user_role = session.get('user_role')
        
        # Get AI response
        response = ai_service.chat(message, conversation_history, user_role)
        
        return jsonify(response), 200
    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        error_details = error_logger.log_error(
            e,
            context={'message': message, 'user_role': user_role},
            user_id=session.get('user_id'),
            user_email=session.get('user_email')
        )
        return jsonify({"error": "An error occurred processing your request. Please try again."}), 500


@app.route('/api/ai/action', methods=['POST'])
@login_required
@role_required('master_admin')
@audit_log('ai_action')
@log_ai_action('advanced_ai_action')
@handle_errors('ai_action')
def ai_action():
    """Perform AI action (master admin only)."""
    try:
        data = request.get_json()
        action = data.get('action')
        parameters = data.get('parameters', {})
        
        if not action:
            return jsonify({'error': 'Action is required'}), 400
        
        user_role = session.get('user_role')
        
        # Perform action
        result = ai_service.perform_action(action, parameters, user_role)
        
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error performing AI action: {e}")
        error_details = error_logger.log_error(
            e,
            context={'action': action, 'parameters': parameters},
            user_id=session.get('user_id'),
            user_email=session.get('user_email')
        )
        return jsonify({"error": "An error occurred performing the action. Please check the error logs."}), 500


# Error and log viewing endpoints (master admin only)

@app.route('/api/errors/recent', methods=['GET'])
@login_required
@role_required('master_admin')
def get_recent_errors():
    """Get recent error logs (master admin only)."""
    try:
        limit = request.args.get('limit', default=100, type=int)
        errors = error_logger.get_recent_errors(limit)
        return jsonify({'errors': errors, 'count': len(errors)}), 200
    except Exception as e:
        logger.error(f"Error fetching error logs: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/ai/operation-logs', methods=['GET'])
@login_required
@role_required('master_admin')
def get_ai_operation_logs():
    """Get AI operation logs (master admin only)."""
    try:
        limit = request.args.get('limit', default=100, type=int)
        logs = error_logger.get_ai_operation_logs(limit)
        return jsonify({'logs': logs, 'count': len(logs)}), 200
    except Exception as e:
        logger.error(f"Error fetching AI operation logs: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/logs', methods=['GET'])
@login_required
@role_required('master_admin')
def logs_page():
    """Error and operation logs page (master admin only)."""
    return render_template('logs.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
