"""Authentication and user-management routes."""
import logging
from flask import Blueprint, jsonify, request, session, redirect, url_for, render_template, current_app

from src.auth.utils import (
    hash_password, verify_password, login_required, role_required,
    get_current_user, audit_log, ROLES,
)

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


# ------------------------------------------------------------------
# Page routes
# ------------------------------------------------------------------

@auth_bp.route('/login', methods=['GET'])
def login_page():
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    return render_template('login.html')


@auth_bp.route('/forgot-password', methods=['GET'])
def forgot_password_page():
    return render_template('forgot-password.html')


@auth_bp.route('/forgot-username', methods=['GET'])
def forgot_username_page():
    return render_template('forgot-username.html')


@auth_bp.route('/reset-password', methods=['GET'])
def reset_password_page():
    return render_template('reset-password.html')


@auth_bp.route('/users', methods=['GET'])
@login_required
@role_required('master_admin')
def users_page():
    return render_template('users.html')


@auth_bp.route('/audit', methods=['GET'])
@login_required
def audit_page():
    return render_template('audit.html')


# ------------------------------------------------------------------
# API routes
# ------------------------------------------------------------------

@auth_bp.route('/api/login', methods=['POST'])
@audit_log('user_login')
def login():
    try:
        database = current_app.extensions['database']
        limiter = current_app.extensions.get('limiter')
        data = request.get_json(silent=True) or {}
        email = data.get('email', '').strip()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        user = database.get_user_by_email(email)
        if not user or not user['is_active'] or not verify_password(password, user['password_hash']):
            return jsonify({'error': 'Invalid email or password'}), 401

        session['user_id'] = user['id']
        session['user_email'] = user['email']
        session['user_full_name'] = user['full_name']
        session['user_role'] = user['role']
        database.update_last_login(user['id'])

        safe_user = {k: v for k, v in user.items() if k != 'password_hash'}
        return jsonify({'message': 'Login successful', 'user': safe_user}), 200
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/api/logout', methods=['POST'])
@audit_log('user_logout')
def logout():
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200


@auth_bp.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    return jsonify({'message': 'If the email exists, a password reset link has been sent'}), 200


@auth_bp.route('/api/reset-password', methods=['POST'])
def reset_password():
    return jsonify({'message': 'Password reset successful'}), 200


@auth_bp.route('/api/forgot-username', methods=['POST'])
def forgot_username():
    return jsonify({'message': 'If the email exists, a username reminder has been sent'}), 200


@auth_bp.route('/api/me', methods=['GET'])
@login_required
def get_current_user_info():
    user = get_current_user()
    if user:
        return jsonify(user), 200
    return jsonify({'error': 'Not logged in'}), 401


@auth_bp.route('/api/roles', methods=['GET'])
@login_required
def get_roles():
    return jsonify(ROLES), 200


@auth_bp.route('/api/users', methods=['GET', 'POST'])
@login_required
@role_required('master_admin')
def manage_users():
    database = current_app.extensions['database']
    if request.method == 'GET':
        return jsonify(database.get_all_users()), 200

    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    role = data.get('role', '')

    if not email or not password or role not in ROLES:
        return jsonify({'error': 'email, password, and a valid role are required'}), 400

    password_hash = hash_password(password)
    user_id = database.create_user(email, password_hash, full_name, role)
    if user_id:
        return jsonify({'id': user_id, 'message': 'User created'}), 201
    return jsonify({'error': 'Failed to create user (email may already exist)'}), 500


@auth_bp.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@role_required('master_admin')
def manage_user_detail(user_id):
    database = current_app.extensions['database']
    if request.method == 'GET':
        user = database.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        safe_user = {k: v for k, v in user.items() if k != 'password_hash'}
        return jsonify(safe_user), 200

    if request.method == 'PUT':
        data = request.get_json(silent=True) or {}
        if 'password' in data:
            data['password_hash'] = hash_password(data.pop('password'))
        if database.update_user(user_id, data):
            return jsonify({'message': 'Updated'}), 200
        return jsonify({'error': 'Update failed'}), 500

    if request.method == 'DELETE':
        if database.delete_user(user_id):
            return jsonify({'message': 'Deleted'}), 200
        return jsonify({'error': 'Delete failed'}), 500


@auth_bp.route('/api/users/<int:user_id>/force-reset-password', methods=['POST'])
@login_required
@role_required('master_admin')
def force_reset_password(user_id):
    database = current_app.extensions['database']
    data = request.get_json(silent=True) or {}
    new_password = data.get('password', '')
    if not new_password:
        return jsonify({'error': 'New password required'}), 400
    if database.update_user(user_id, {'password_hash': hash_password(new_password)}):
        return jsonify({'message': 'Password reset'}), 200
    return jsonify({'error': 'Reset failed'}), 500


@auth_bp.route('/api/audit-log', methods=['GET'])
@login_required
def get_audit_log():
    database = current_app.extensions['database']
    return jsonify(database.get_audit_logs()), 200
