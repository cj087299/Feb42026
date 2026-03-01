"""Shared utilities for all route blueprints."""
import os
import logging
from flask import current_app

from src.auth.qbo_auth import QBOAuth
from src.invoices.qbo_connector import QBOConnector

logger = logging.getLogger(__name__)

DUMMY_QBO_CLIENT_ID = 'dummy_id'
DUMMY_QBO_CLIENT_SECRET = 'dummy_secret'
DUMMY_QBO_REFRESH_TOKEN = 'dummy_refresh'
DUMMY_QBO_REALM_ID = 'dummy_realm'


def get_fresh_qbo_connector():
    """Create a fresh QBOConnector from the latest stored credentials.

    Returns:
        (QBOConnector, credentials_valid: bool)
    """
    database = current_app.extensions['database']
    secret_manager = current_app.extensions['secret_manager']
    try:
        qbo_creds = secret_manager.get_qbo_credentials()
        required_fields = ['client_id', 'client_secret', 'refresh_token', 'realm_id']
        missing = [f for f in required_fields if not qbo_creds.get(f)]

        if missing:
            logger.error(f"Missing required QBO credential fields: {missing}")
            auth = QBOAuth(
                DUMMY_QBO_CLIENT_ID, DUMMY_QBO_CLIENT_SECRET,
                DUMMY_QBO_REFRESH_TOKEN, DUMMY_QBO_REALM_ID,
                database=database,
            )
            return QBOConnector(auth), False

        auth = QBOAuth(
            qbo_creds['client_id'], qbo_creds['client_secret'],
            qbo_creds['refresh_token'], qbo_creds['realm_id'],
            database=database,
        )
        if qbo_creds.get('access_token'):
            auth.access_token = qbo_creds['access_token']
        return QBOConnector(auth), qbo_creds.get('is_valid', False)
    except Exception as e:
        logger.error(f"Error creating fresh QBO connector: {e}")
        auth = QBOAuth(
            DUMMY_QBO_CLIENT_ID, DUMMY_QBO_CLIENT_SECRET,
            DUMMY_QBO_REFRESH_TOKEN, DUMMY_QBO_REALM_ID,
            database=database,
        )
        return QBOConnector(auth), False
