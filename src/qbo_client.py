import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QBOClient:
    def __init__(self, client_id, client_secret, refresh_token, realm_id):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.realm_id = realm_id
        self.access_token = None
        self.base_url = "https://sandbox-quickbooks.api.intuit.com/v3/company"

    def refresh_access_token(self):
        """
        Refreshes the access token using the refresh token.
        """
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
            self.access_token = token_data.get("access_token")
            
            # Update refresh token if provided
            if "refresh_token" in token_data:
                self.refresh_token = token_data["refresh_token"]
                
            logger.info("Access token refreshed successfully")
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
            # If 401, try to refresh token once and retry
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
