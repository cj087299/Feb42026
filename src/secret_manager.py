import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SecretManager:
    """Manages access to Google Cloud Secret Manager for credentials."""
    
    def __init__(self, database=None):
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.client = None
        self.database = database  # Database instance for QBO token storage
        
        # Try to initialize Google Secret Manager client
        try:
            from google.cloud import secretmanager
            if self.project_id:
                self.client = secretmanager.SecretManagerServiceClient()
                logger.info("Google Secret Manager client initialized")
            else:
                logger.warning("GOOGLE_CLOUD_PROJECT not set, using environment variables")
        except ImportError:
            logger.warning("google-cloud-secret-manager not installed, using environment variables")
        except Exception as e:
            logger.warning(f"Failed to initialize Google Secret Manager: {e}")
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieves a secret from Google Secret Manager.
        Falls back to environment variables if Secret Manager is not available.
        
        Args:
            secret_name: Name of the secret to retrieve
            
        Returns:
            Secret value as string, or None if not found
        """
        # First try Google Secret Manager
        if self.client and self.project_id:
            try:
                name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                response = self.client.access_secret_version(request={"name": name})
                secret_value = response.payload.data.decode('UTF-8')
                logger.info(f"Retrieved secret '{secret_name}' from Google Secret Manager")
                return secret_value
            except Exception as e:
                logger.warning(f"Failed to retrieve secret '{secret_name}' from Google Secret Manager: {e}")
        
        # Fallback to environment variables
        env_value = os.environ.get(secret_name)
        if env_value:
            logger.info(f"Retrieved secret '{secret_name}' from environment variable")
            return env_value
        
        logger.warning(f"Secret '{secret_name}' not found in Secret Manager or environment")
        return None
    
    def get_qbo_credentials(self) -> dict:
        """
        Retrieves QuickBooks Online credentials.
        Priority order:
        1. Database (if available) - credentials set by admin
        2. Google Secret Manager
        3. Environment variables
        4. Default dummy values (with warning)
        
        Returns:
            Dictionary with QBO credentials and validity flag
        """
        # First, try to get credentials from database (highest priority)
        if self.database:
            try:
                db_creds = self.database.get_qbo_credentials()
                if db_creds:
                    logger.info("Retrieved QBO credentials from database")
                    return {
                        'client_id': db_creds['client_id'],
                        'client_secret': db_creds['client_secret'],
                        'refresh_token': db_creds['refresh_token'],
                        'realm_id': db_creds['realm_id'],
                        'access_token': db_creds.get('access_token'),
                        'access_token_expires_at': db_creds.get('access_token_expires_at'),
                        'refresh_token_expires_at': db_creds.get('refresh_token_expires_at'),
                        'is_valid': True
                    }
            except Exception as e:
                logger.warning(f"Failed to get QBO credentials from database: {e}")
        
        # Fallback to Secret Manager and environment variables
        client_id = self.get_secret('QBO_ID_2-3-26') or os.environ.get('QBO_CLIENT_ID', 'dummy_id')
        client_secret = self.get_secret('QBO_Secret_2-3-26') or os.environ.get('QBO_CLIENT_SECRET', 'dummy_secret')
        refresh_token = os.environ.get('QBO_REFRESH_TOKEN', 'dummy_refresh')
        realm_id = os.environ.get('QBO_REALM_ID', 'dummy_realm')
        
        # Check if we're using dummy values
        is_valid = not (client_id == 'dummy_id' or client_secret == 'dummy_secret' or 
                       refresh_token == 'dummy_refresh' or realm_id == 'dummy_realm')
        
        if not is_valid:
            logger.error("QBO credentials are not configured. Please set up credentials via the admin UI at /qbo-settings or configure environment variables.")
        
        return {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'realm_id': realm_id,
            'is_valid': is_valid
        }
