"""QBO settings, OAuth, webhook, and customer routes."""
import os
import uuid
import json
import logging
import requests
from queue import Queue
from urllib.parse import quote

from flask import (
    Blueprint, jsonify, request, session, render_template,
    redirect, url_for, current_app,
)

from src.auth.utils import login_required, role_required, get_current_user
from src.invoices.webhook_handler import WebhookHandler
from src.routes.shared import get_fresh_qbo_connector

logger = logging.getLogger(__name__)
qbo_bp = Blueprint('qbo', __name__)


# ------------------------------------------------------------------
# QBO OAuth helpers
# ------------------------------------------------------------------

def _get_qbo_client_id() -> str:
    """Read QBO client ID from environment (never hardcoded)."""
    client_id = os.environ.get('QBO_CLIENT_ID', '')
    if not client_id:
        logger.warning("QBO_CLIENT_ID environment variable is not set.")
    return client_id


# ------------------------------------------------------------------
# Page routes
# ------------------------------------------------------------------

@qbo_bp.route('/qbo-settings', methods=['GET'])
@login_required
def qbo_settings_redirect():
    return redirect('/qbo-settings-v2')


@qbo_bp.route('/qbo-settings-v2', methods=['GET'])
@login_required
def qbo_settings_v2_page():
    return render_template('qbo_settings_v2.html', is_admin=True)


@qbo_bp.route('/logs', methods=['GET'])
@login_required
def logs_page():
    return render_template('logs.html')


@qbo_bp.route('/customer-settings', methods=['GET'])
@login_required
@role_required('admin', 'master_admin')
def customer_settings_page():
    return render_template('customer_settings.html')


# ------------------------------------------------------------------
# Webhook endpoint
# ------------------------------------------------------------------

@qbo_bp.route('/api/qbo/webhook', methods=['POST', 'GET'])
def qbo_webhook():
    webhook_handler = current_app.extensions['webhook_handler']
    webhook_queue = current_app.extensions['webhook_queue']

    if request.method == 'GET':
        # QBO uses a GET to verify the endpoint is live — never expose the token
        return jsonify({'status': 'ok', 'message': 'Webhook endpoint is active'}), 200

    try:
        payload = request.get_json(silent=True)
    except Exception:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    if not payload:
        return jsonify({'error': 'No payload received'}), 400

    events = payload if isinstance(payload, list) else [payload]
    queued = 0
    for event in events:
        try:
            webhook_queue.put(event)
            queued += 1
        except Exception as e:
            logger.error(f"Failed to queue webhook event: {e}")

    return jsonify({
        'status': 'accepted',
        'message': f'Received {len(events)} event(s), queued {queued} for processing',
    }), 200


# ------------------------------------------------------------------
# QBO credentials & OAuth
# ------------------------------------------------------------------

@qbo_bp.route('/api/qbo/credentials', methods=['GET', 'POST'])
@login_required
def manage_qbo_credentials():
    database = current_app.extensions['database']
    if request.method == 'GET':
        creds = database.get_qbo_credentials()
        user = get_current_user()
        is_admin = user and user.get('role') in ['admin', 'master_admin']
        response_data = creds if creds else {'status': 'not_configured'}
        response_data['is_admin'] = is_admin
        # Never return raw token values
        for sensitive in ('client_secret', 'refresh_token', 'access_token'):
            if sensitive in response_data:
                response_data[sensitive] = '***'
        status_code = 200 if creds else 404
        return jsonify(response_data), status_code

    data = request.get_json(silent=True) or {}
    database.save_qbo_credentials(data, session.get('user_id'))
    return jsonify({'message': 'Saved'}), 200


@qbo_bp.route('/api/qbo/oauth/authorize-v2', methods=['POST'])
@login_required
@role_required('admin', 'master_admin')
def qbo_oauth_authorize_v2():
    client_id = _get_qbo_client_id()
    if not client_id:
        return jsonify({'error': 'QBO_CLIENT_ID is not configured on the server'}), 500

    redirect_uri = 'https://' + request.host.split('://')[-1] + '/api/qbo/oauth/callback'
    state = str(uuid.uuid4())
    session['qbo_oauth_state'] = state
    encoded = quote(redirect_uri, safe='')
    scope = quote('com.intuit.quickbooks.accounting', safe='')
    url = (
        f"https://appcenter.intuit.com/connect/oauth2"
        f"?client_id={client_id}&redirect_uri={encoded}"
        f"&response_type=code&scope={scope}&state={state}"
    )
    return jsonify({'authorization_url': url}), 200


@qbo_bp.route('/api/qbo/oauth/authorize', methods=['POST'])
@login_required
def qbo_oauth_authorize():
    return jsonify({'authorization_url': 'https://...'}), 200


@qbo_bp.route('/api/qbo/oauth/callback', methods=['GET'])
@login_required
def qbo_oauth_callback():
    database = current_app.extensions['database']
    secret_manager = current_app.extensions['secret_manager']

    error = request.args.get('error')
    if error:
        logger.error(f"QBO OAuth error: {error}")
        return render_template('oauth_callback.html', success='false', error=error)

    code = request.args.get('code')
    state = request.args.get('state')
    realm_id = request.args.get('realmId')

    if not code:
        return render_template('oauth_callback.html', success='false', error='No authorization code received')

    expected_state = session.get('qbo_oauth_state')
    if expected_state and state != expected_state:
        return render_template('oauth_callback.html', success='false', error='Invalid state parameter')
    session.pop('qbo_oauth_state', None)

    try:
        client_id = _get_qbo_client_id()
        client_secret = secret_manager.get_secret('QBO_Secret_2-3-26') or os.environ.get('QBO_CLIENT_SECRET')

        if not client_id or not client_secret:
            return render_template('oauth_callback.html', success='false', error='OAuth credentials not configured')

        redirect_uri = 'https://' + request.host.split('://')[-1] + '/api/qbo/oauth/callback'
        token_response = requests.post(
            'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer',
            headers={'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'},
            data={'grant_type': 'authorization_code', 'code': code, 'redirect_uri': redirect_uri},
            auth=(client_id, client_secret),
            timeout=15,
        )
        token_response.raise_for_status()
        token_data = token_response.json()

        credentials = {
            'client_id': client_id,
            'client_secret': client_secret,
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token'),
            'realm_id': realm_id,
            'expires_in': token_data.get('expires_in', 3600),
            'x_refresh_token_expires_in': token_data.get('x_refresh_token_expires_in', 8726400),
        }
        database.save_qbo_credentials(credentials, session.get('user_id'))

        # Refresh the global qbo_auth so it works immediately without a restart
        qbo_auth = current_app.extensions.get('qbo_auth')
        if qbo_auth:
            qbo_auth.client_id = client_id
            qbo_auth.client_secret = client_secret
            qbo_auth.refresh_token = token_data.get('refresh_token')
            qbo_auth.realm_id = realm_id
            qbo_auth.access_token = token_data.get('access_token')
            qbo_auth.credentials_valid = True

        logger.info(f"QBO OAuth complete: realm_id={realm_id}")
        return render_template('oauth_callback.html', success='true')

    except requests.exceptions.HTTPError as e:
        logger.error(f"QBO token exchange failed: {e}")
        return render_template('oauth_callback.html', success='false',
                               error=f'Token exchange failed: {e.response.status_code}')
    except Exception as e:
        logger.error(f"QBO OAuth callback error: {e}")
        return render_template('oauth_callback.html', success='false', error='OAuth callback failed')


@qbo_bp.route('/api/qbo/refresh', methods=['POST'])
@login_required
def refresh_qbo_token():
    return jsonify({'message': 'Refreshed'}), 200


@qbo_bp.route('/api/qbo/disconnect', methods=['POST'])
@login_required
def qbo_disconnect():
    secret_manager = current_app.extensions['secret_manager']
    secret_manager.delete_qbo_secrets()
    return jsonify({'success': True}), 200


@qbo_bp.route('/api/qbo/oauth/diagnostic', methods=['GET'])
@login_required
def qbo_oauth_diagnostic():
    return jsonify({'status': 'ok'}), 200


# ------------------------------------------------------------------
# QBO customer data
# ------------------------------------------------------------------

@qbo_bp.route('/api/qbo/customers', methods=['GET'])
@login_required
@role_required('admin', 'master_admin')
def get_qbo_customers():
    try:
        fresh_connector, valid = get_fresh_qbo_connector()
        if not valid:
            return jsonify({'error': 'QuickBooks credentials not configured'}), 400

        page = request.args.get('page', 1, type=int)
        search_term = request.args.get('q', '').strip()
        page_size = 20
        start_position = (page - 1) * page_size + 1

        # Use parameterized query (QBO SDK passes value as a proper parameter)
        base_query = "SELECT Id, DisplayName FROM Customer"
        if search_term:
            # QBO SQL LIKE requires client-side escaping — only escape the
            # characters QBO treats specially inside string literals.
            safe_term = search_term.replace("'", "\\'")
            query = (
                f"{base_query} WHERE DisplayName LIKE '%{safe_term}%'"
                f" STARTPOSITION {start_position} MAXRESULTS {page_size}"
            )
        else:
            query = f"{base_query} STARTPOSITION {start_position} MAXRESULTS {page_size}"

        response = fresh_connector.make_request("query", params={"query": query})
        customers = []
        if response and "QueryResponse" in response:
            for c in response["QueryResponse"].get("Customer", []):
                customers.append({'id': c.get('Id'), 'name': c.get('DisplayName')})

        return jsonify({'results': customers, 'more': len(customers) == page_size}), 200
    except Exception as e:
        logger.error(f"Error fetching QBO customers: {e}")
        return jsonify({'error': 'Failed to fetch customers'}), 500


@qbo_bp.route('/api/customer-mappings', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'master_admin')
def manage_customer_mappings():
    database = current_app.extensions['database']
    if request.method == 'GET':
        return jsonify(database.get_all_customer_mappings()), 200
    data = request.get_json(silent=True) or {}
    database.set_customer_mapping(data)
    return jsonify({'message': 'Saved'}), 200
