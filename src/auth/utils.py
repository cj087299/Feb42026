"""Authentication and authorization module for VZT Accounting."""

import hashlib
import secrets
import logging
from functools import wraps
from flask import session, request, jsonify, redirect, url_for, current_app
from typing import Optional, Dict, List, Callable

logger = logging.getLogger(__name__)

# Role definitions
ROLES = {
    'view_only': {
        'name': 'View Only',
        'description': 'Can view all pages but cannot make changes',
        'permissions': ['view_invoices', 'view_cashflow', 'view_reports']
    },
    'ap': {
        'name': 'Accounts Payable',
        'description': 'Can manage accounts payable',
        'permissions': ['view_invoices', 'view_cashflow', 'view_reports', 'manage_ap', 'add_custom_outflows']
    },
    'ar': {
        'name': 'Accounts Receivable',
        'description': 'Can manage accounts receivable',
        'permissions': ['view_invoices', 'view_cashflow', 'view_reports', 'manage_ar', 'edit_invoice_metadata', 'add_custom_inflows']
    },
    'admin': {
        'name': 'Admin',
        'description': 'Can manage all accounting functions and view audit logs',
        'permissions': ['view_invoices', 'view_cashflow', 'view_reports', 'manage_ar', 'manage_ap', 
                       'edit_invoice_metadata', 'add_custom_inflows', 'add_custom_outflows', 
                       'edit_custom_flows', 'delete_custom_flows', 'view_audit_log']
    },
    'master_admin': {
        'name': 'Master Admin',
        'description': 'Full system access including user management',
        'permissions': ['*']  # All permissions
    }
}


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with a salt."""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash."""
    try:
        salt, pwd_hash = password_hash.split('$')
        new_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return new_hash == pwd_hash
    except Exception as e:
        logger.error(f"Failed to verify password: {e}")
        return False


def has_permission(user_role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    if user_role not in ROLES:
        return False
    
    role_perms = ROLES[user_role]['permissions']
    
    # Master admin has all permissions
    if '*' in role_perms:
        return True
    
    return permission in role_perms


def get_role_permissions(role: str) -> List[str]:
    """Get all permissions for a role."""
    if role not in ROLES:
        return []
    return ROLES[role]['permissions']


def get_current_user() -> Optional[Dict]:
    """Get the current logged-in user from session."""
    if 'user_id' in session:
        return {
            'id': session['user_id'],
            'email': session.get('user_email'),
            'full_name': session.get('user_full_name'),
            'role': session.get('user_role')
        }
    return None


def login_required(f: Callable) -> Callable:
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


def permission_required(permission: str) -> Callable:
    """Decorator to require a specific permission for a route."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('login_page'))
            
            user_role = session.get('user_role')
            if not has_permission(user_role, permission):
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Permission denied'}), 403
                return jsonify({'error': 'You do not have permission to access this resource'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def role_required(*roles: str) -> Callable:
    """Decorator to require one of the specified roles for a route."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('login_page'))
            
            user_role = session.get('user_role')
            if user_role not in roles:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Permission denied'}), 403
                return jsonify({'error': 'You do not have permission to access this resource'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def audit_log(action: str, resource_type: Optional[str] = None):
    """Decorator to automatically log actions to audit log."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Execute the function first
            result = f(*args, **kwargs)
            
            # Log the action
            try:
                # Use current_app.config or a similar mechanism to access database
                # Assuming 'database' is available in current_app extensions or config
                # For now, we'll try to get it from current_app.extensions if we register it there
                # OR we will need to change how this is called.
                
                # In main.py, we should do: app.extensions['database'] = database
                database = None
                if current_app and hasattr(current_app, 'extensions'):
                    database = current_app.extensions.get('database')
                
                if database:
                    user = get_current_user()
                    user_id = user['id'] if user else None
                    user_email = user['email'] if user else None

                    # Get resource_id from kwargs if available
                    resource_id = kwargs.get('invoice_id') or kwargs.get('flow_id') or kwargs.get('user_id')
                    if not resource_id and args:
                        resource_id = str(args[0]) if args else None

                    # Get details from request if available
                    details = None
                    if request.is_json:
                        details = str(request.get_json())

                    database.log_audit(
                        user_id=user_id,
                        user_email=user_email,
                        action=action,
                        resource_type=resource_type,
                        resource_id=str(resource_id) if resource_id else None,
                        details=details,
                        ip_address=request.remote_addr,
                        user_agent=request.user_agent.string if request.user_agent else None
                    )
                else:
                    logger.warning("Database extension not found in current_app")

            except Exception as e:
                logger.error(f"Failed to log audit entry: {e}")
            
            return result
        return decorated_function
    return decorator
