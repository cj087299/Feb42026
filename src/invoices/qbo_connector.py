import os
import requests
import logging
from src.auth.qbo_auth import QBOAuth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        if not self.auth.access_token:
            try:
                self.auth.refresh_access_token()
            except Exception as e:
                logger.error(f"Failed to refresh token before request: {e}")
                return {}

        url = f"{self.base_url}/{self.auth.realm_id}/{endpoint}"

        logger.info(f"Making {method} request to {url}")

        try:
            headers = self.auth.get_headers()
            response = requests.request(method, url, headers=headers, params=params, json=data)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e}")

            # Handle 401 (Unauthorized) - token expired
            if e.response.status_code == 401:
                logger.info("Received 401, attempting to refresh token and retry...")
                try:
                    self.auth.refresh_access_token()
                    headers = self.auth.get_headers()
                    response = requests.request(method, url, headers=headers, params=params, json=data)
                    response.raise_for_status()
                    return response.json()
                except Exception as retry_error:
                    logger.error(f"Retry after token refresh failed: {retry_error}")
                    return {}

            # Handle 403 (Forbidden)
            elif e.response.status_code == 403:
                error_msg = (
                    f"403 Forbidden error when accessing QuickBooks API at {url}. "
                    f"Please reconnect to QuickBooks via /qbo-settings"
                )
                logger.error(error_msg)

                # Attempt token refresh as a last resort
                try:
                    self.auth.refresh_access_token()
                    headers = self.auth.get_headers()
                    response = requests.request(method, url, headers=headers, params=params, json=data)
                    response.raise_for_status()
                    logger.info("Token refresh resolved the 403 error")
                    return response.json()
                except Exception as retry_error:
                    logger.error(f"Token refresh did not resolve the 403 error: {retry_error}")
                return {}

            return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {}
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return {}

    def fetch_bank_accounts(self):
        """
        Fetches bank accounts from QBO to get current balances.

        Returns:
            List of bank accounts with their current balances
        """
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
