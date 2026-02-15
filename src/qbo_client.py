import requests
import logging
from datetime import datetime, timedelta
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QBOClient:
    def __init__(self, client_id, client_secret, refresh_token, realm_id, database=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.realm_id = realm_id
        self.access_token = None
        self.base_url = "https://sandbox-quickbooks.api.intuit.com/v3/company"
        self.database = database  # Optional database for persistent token storage
        
        # Check if credentials are valid
        self._validate_credentials()
    
    def _validate_credentials(self):
        """Validate that credentials are not dummy values."""
        if (self.client_id == 'dummy_id' or 
            self.client_secret == 'dummy_secret' or 
            self.refresh_token == 'dummy_refresh' or 
            self.realm_id == 'dummy_realm'):
            logger.warning(
                "QBO credentials are not configured properly. "
                "Please configure OAuth credentials at /qbo-settings or set environment variables. "
                "Current operations will fail until valid credentials are provided."
            )
            self.credentials_valid = False
        else:
            self.credentials_valid = True

    def refresh_access_token(self):
        """
        Refreshes the access token using the refresh token.
        Updates the database if available.
        
        Raises:
            ValueError: If credentials are not valid
            Exception: If token refresh fails
        """
        # Check if credentials are valid before attempting refresh
        if not self.credentials_valid:
            error_msg = (
                "Cannot refresh access token: QBO credentials are not configured. "
                "Please configure OAuth credentials at /qbo-settings or set environment variables "
                "(QBO_CLIENT_ID, QBO_CLIENT_SECRET, QBO_REFRESH_TOKEN, QBO_REALM_ID)."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("Refreshing access token...")
        try:
            token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }
            
            response = requests.post(
                token_url, 
                headers=headers, 
                data=data,
                auth=(self.client_id, self.client_secret)
            )
            response.raise_for_status()
            
            token_data = response.json()
            # Handle both camelCase (accessToken) and snake_case (access_token) from QBO
            self.access_token = token_data.get("access_token") or token_data.get("accessToken")
            
            # Update refresh token if provided (QBO returns a new refresh token)
            new_refresh_token = token_data.get("refresh_token") or token_data.get("refreshToken")
            if new_refresh_token:
                self.refresh_token = new_refresh_token
            
            # Update tokens in database if available
            if self.database:
                try:
                    # Get expiration times from QBO response
                    expires_in = token_data.get("expires_in", 3600)
                    x_refresh_token_expires_in = token_data.get("x_refresh_token_expires_in", 8726400)
                    
                    self.database.update_qbo_tokens(
                        access_token=self.access_token,
                        refresh_token=new_refresh_token if new_refresh_token else None,
                        expires_in=expires_in,
                        x_refresh_token_expires_in=x_refresh_token_expires_in
                    )
                    logger.info("Updated tokens in database")
                except Exception as db_error:
                    logger.warning(f"Failed to update tokens in database: {db_error}")
                
            logger.info("Access token refreshed successfully")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                error_msg = (
                    f"Failed to refresh access token: 401 Unauthorized. "
                    f"The refresh token or client credentials are invalid or expired. "
                    f"Please reconfigure OAuth credentials at /qbo-settings by connecting to QuickBooks again."
                )
                logger.error(error_msg)
                raise Exception(error_msg) from e
            logger.error(f"Failed to refresh access token: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise

    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }

    def make_request(self, endpoint, method="GET", params=None, data=None):
        if not self.access_token:
            self.refresh_access_token()

        url = f"{self.base_url}/{self.realm_id}/{endpoint}"

        logger.info(f"Making {method} request to {url}")

        try:
            headers = self.get_headers()
            response = requests.request(method, url, headers=headers, params=params, json=data)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e}")
            
            # Handle 401 (Unauthorized) - token expired
            if e.response.status_code == 401 and self.access_token:
                logger.info("Received 401, attempting to refresh token and retry...")
                try:
                    self.refresh_access_token()
                    headers = self.get_headers()
                    response = requests.request(method, url, headers=headers, params=params, json=data)
                    response.raise_for_status()
                    return response.json()
                except Exception as retry_error:
                    logger.error(f"Retry after token refresh failed: {retry_error}")
                    return {}
            
            # Handle 403 (Forbidden) - invalid credentials or insufficient permissions
            elif e.response.status_code == 403:
                error_msg = (
                    f"403 Forbidden error when accessing QuickBooks API at {url}. "
                    f"This typically indicates one of the following issues:\n"
                    f"1. OAuth credentials are invalid or have been revoked\n"
                    f"2. The refresh token has expired (refresh tokens expire after 101 days)\n"
                    f"3. Insufficient permissions/scopes for this operation\n"
                    f"4. The company (realm_id) is not accessible with these credentials\n\n"
                    f"To resolve this issue:\n"
                    f"→ Log in to the application and navigate to /qbo-settings\n"
                    f"→ Click 'Disconnect from QuickBooks' if connected\n"
                    f"→ Click 'Connect to QuickBooks' to re-authorize the application\n"
                    f"→ Make sure to authorize with an account that has access to company ID: {self.realm_id}"
                )
                logger.error(error_msg)
                
                # Attempt token refresh as a last resort (might help in some edge cases)
                if self.access_token:
                    logger.info("Attempting token refresh for 403 error as a troubleshooting step...")
                    try:
                        self.refresh_access_token()
                        headers = self.get_headers()
                        response = requests.request(method, url, headers=headers, params=params, json=data)
                        response.raise_for_status()
                        logger.info("Token refresh resolved the 403 error")
                        return response.json()
                    except Exception as retry_error:
                        logger.error(
                            f"Token refresh did not resolve the 403 error: {retry_error}. "
                            f"Please reconnect to QuickBooks via /qbo-settings"
                        )
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
    
    def disconnect(self):
        """
        Disconnect from QuickBooks by removing all stored tokens and credentials.
        This deletes access tokens, refresh tokens, and realm_id from the database.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Disconnecting from QuickBooks Online...")
            
            # Delete tokens from database if available
            if self.database:
                success = self.database.delete_qbo_credentials()
                if success:
                    logger.info("Successfully disconnected from QuickBooks - all credentials removed")
                    # Clear local instance variables
                    self.access_token = None
                    self.refresh_token = None
                    self.realm_id = None
                    return True
                else:
                    logger.error("Failed to disconnect - database operation failed")
                    return False
            else:
                logger.warning("No database available for disconnect operation")
                return False
        except Exception as e:
            logger.error(f"Error during QuickBooks disconnect: {e}")
            return False
