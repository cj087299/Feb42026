import os
import json
import logging
from typing import Optional
from google.cloud import secretmanager # Import SecretManagerServiceClient

logger = logging.getLogger(__name__)

# Local config file path for persisting credentials when Secret Manager is unavailable
_LOCAL_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'qbo_local_config.json')


def _read_local_config() -> dict:
    """Read local config JSON file, returning empty dict if not found."""
    try:
        if os.path.exists(_LOCAL_CONFIG_FILE):
            with open(_LOCAL_CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read local config file: {e}")
    return {}


def _write_local_config(data: dict) -> bool:
    """Write data to local config JSON file."""
    try:
        existing = _read_local_config()
        existing.update(data)
        with open(_LOCAL_CONFIG_FILE, 'w') as f:
            json.dump(existing, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to write local config file: {e}")
        return False


class SecretManager:
    """Manages access to Google Cloud Secret Manager for credentials."""

    def __init__(self):
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.client = None

        # Try to initialize Google Secret Manager client
        try:
            # Check if GOOGLE_CLOUD_PROJECT is set before attempting to import
            # and initialize the client.
            if self.project_id:
                self.client = secretmanager.SecretManagerServiceClient()
                logger.info("Google Secret Manager client initialized")
            else:
                logger.warning("GOOGLE_CLOUD_PROJECT not set, Secret Manager client will not be initialized. Using local config and environment variables.")
        except ImportError:
            logger.warning("google-cloud-secret-manager not installed, Secret Manager client will not be initialized. Using local config and environment variables.")
        except Exception as e:
            logger.warning(f"Failed to initialize Google Secret Manager client: {e}. Using local config and environment variables.")

    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieves a secret from Google Secret Manager.
        Falls back to local config file, then environment variables if Secret Manager is not available.

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

        # Fallback to local config file (runtime-updated credentials)
        local_config = _read_local_config()
        if secret_name in local_config:
            logger.info(f"Retrieved secret '{secret_name}' from local config file")
            return local_config[secret_name]

        # Fallback to environment variables
        env_value = os.environ.get(secret_name)
        if env_value:
            logger.info(f"Retrieved secret '{secret_name}' from environment variable")
            return env_value

        logger.warning(f"Secret '{secret_name}' not found in Secret Manager, local config, or environment")
        return None

    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """
        Sets or updates a secret in Google Secret Manager. Falls back to local config file
        if Secret Manager is not available.

        Args:
            secret_name: Name of the secret to set.
            secret_value: The value to set for the secret.

        Returns:
            True if the secret was set successfully, False otherwise.
        """
        # Try Google Secret Manager first
        if self.client and self.project_id:
            parent = f"projects/{self.project_id}"
            secret_path = f"{parent}/secrets/{secret_name}"

            try:
                # Check if the secret already exists
                self.client.get_secret(request={"name": secret_path})
                logger.info(f"Secret '{secret_name}' already exists. Adding a new version.")
            except Exception as e:
                # If the secret does not exist, create it
                if "NOT_FOUND" in str(e):
                    try:
                        self.client.create_secret(
                            request={
                                "parent": parent,
                                "secret_id": secret_name,
                                "secret": {"replication": {"automatic": {}}},
                            }
                        )
                        logger.info(f"Secret '{secret_name}' created successfully.")
                    except Exception as create_e:
                        logger.error(f"Failed to create secret '{secret_name}': {create_e}")
                        # Fall through to local config
                else:
                    logger.error(f"Failed to check existence of secret '{secret_name}': {e}")
                    # Fall through to local config

            # Add a new version to the secret
            try:
                self.client.add_secret_version(
                    request={"parent": secret_path, "payload": {"data": secret_value.encode("UTF-8")}}
                )
                logger.info(f"Secret '{secret_name}' updated with a new version.")
                return True
            except Exception as e:
                logger.error(f"Failed to add new version to secret '{secret_name}': {e}")
                # Fall through to local config

        # Fallback: write to local config file
        logger.info(f"Saving secret '{secret_name}' to local config file (Secret Manager unavailable).")
        return _write_local_config({secret_name: secret_value})

    def delete_secret_value(self, secret_name: str) -> bool:
        """
        Removes a secret value by setting it to empty string in local config and env.
        Used for disconnect operations.
        """
        # Write empty value to local config to override env vars
        result = _write_local_config({secret_name: ''})
        # Also clear from environment
        os.environ.pop(secret_name, None)
        logger.info(f"Cleared secret '{secret_name}' from local config and environment.")
        return result

    def get_qbo_credentials(self) -> dict:
        """
        Retrieves QuickBooks Online credentials from Google Secret Manager.

        Returns:
            Dictionary with QBO credentials
        """
        return {
            'client_id': self.get_secret('QBO_ID_2-3-26') or os.environ.get('QBO_CLIENT_ID', 'dummy_id'),
            'client_secret': self.get_secret('QBO_Secret_2-3-26') or os.environ.get('QBO_CLIENT_SECRET', 'dummy_secret'),
            'refresh_token': self.get_secret('QBO_Refresh_Token') or os.environ.get('QBO_REFRESH_TOKEN', 'dummy_refresh'),
            'realm_id': self.get_secret('QBO_Realm_Id') or os.environ.get('QBO_REALM_ID', 'dummy_realm')
        }
