import os
import time
import requests
import logging
from src.auth.qbo_auth import QBOAuth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BACKOFF_BASE = 2  # seconds


def _backoff_delay(attempt: int) -> None:
    """Sleep for exponential backoff: 2s, 4s, 8s."""
    time.sleep(_BACKOFF_BASE ** attempt)


class QBOConnector:
    def __init__(self, auth: QBOAuth):
        self.auth = auth

        # Set base URL based on QBO_ENVIRONMENT variable
        qbo_environment = os.environ.get('QBO_ENVIRONMENT', 'production').lower()
        if qbo_environment == 'production':
            self.base_url = "https://quickbooks.api.intuit.com/v3/company"
            logger.info("QBOConnector initialized for PRODUCTION environment")
        else:
            self.base_url = "https://sandbox-quickbooks.api.intuit.com/v3/company"
            logger.info("QBOConnector initialized for SANDBOX environment")

    def make_request(self, endpoint, method="GET", params=None, data=None):
        """Make a QBO API request with retry logic.

        Retries on:
          - 401: refresh token once, then retry
          - 429 / 5xx: exponential backoff up to _MAX_RETRIES attempts
          - Network errors: exponential backoff up to _MAX_RETRIES attempts
        """
        if not self.auth.access_token:
            try:
                self.auth.refresh_access_token()
            except Exception as e:
                logger.error(f"Failed to refresh token before request: {e}")
                return {}

        url = f"{self.base_url}/{self.auth.realm_id}/{endpoint}"
        logger.info(f"Making {method} request to {url}")

        last_exception = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                headers = self.auth.get_headers()
                response = requests.request(
                    method, url, headers=headers, params=params, json=data, timeout=30
                )

                if response.status_code == 401:
                    logger.info("Received 401 — refreshing token and retrying once...")
                    self.auth.refresh_access_token()
                    headers = self.auth.get_headers()
                    response = requests.request(
                        method, url, headers=headers, params=params, json=data, timeout=30
                    )
                    response.raise_for_status()
                    return response.json()

                if response.status_code == 403:
                    logger.error(
                        f"403 Forbidden at {url}. Attempting token refresh as last resort."
                    )
                    try:
                        self.auth.refresh_access_token()
                        headers = self.auth.get_headers()
                        response = requests.request(
                            method, url, headers=headers, params=params, json=data, timeout=30
                        )
                        response.raise_for_status()
                        return response.json()
                    except Exception as retry_error:
                        logger.error(f"Token refresh did not resolve the 403: {retry_error}")
                    return {}

                if response.status_code in _RETRYABLE_STATUS_CODES:
                    if attempt < _MAX_RETRIES:
                        logger.warning(
                            f"Received {response.status_code} on attempt {attempt + 1}/"
                            f"{_MAX_RETRIES + 1} — retrying after backoff."
                        )
                        _backoff_delay(attempt)
                        continue
                    logger.error(f"HTTP {response.status_code} after {_MAX_RETRIES} retries: {url}")
                    return {}

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        f"Network error on attempt {attempt + 1}/{_MAX_RETRIES + 1}: {e} — retrying."
                    )
                    _backoff_delay(attempt)
                else:
                    logger.error(f"Request failed after {_MAX_RETRIES} retries: {e}")

        return {}

    def fetch_bank_accounts(self):
        """Fetch bank accounts from QBO to get current balances."""
        try:
            query = "select * from Account where AccountType = 'Bank' and AccountSubType = 'Checking'"
            response = self.make_request("query", params={"query": query})

            if response and "QueryResponse" in response:
                accounts = response["QueryResponse"].get("Account", [])
                logger.info(f"Fetched {len(accounts)} bank accounts from QBO")
                return accounts

            logger.warning("No bank accounts found in QBO response")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch bank accounts: {e}")
            return []

    def fetch_bills(self):
        """Fetch unpaid bills from QBO (Accounts Payable)."""
        try:
            query = "select * from Bill where Balance > '0'"
            response = self.make_request("query", params={"query": query})

            if response and "QueryResponse" in response:
                bills = response["QueryResponse"].get("Bill", [])
                logger.info(f"Fetched {len(bills)} unpaid bills from QBO")
                return bills

            logger.warning("No bills found in QBO response")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch bills: {e}")
            return []
