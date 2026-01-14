"""Secure credential storage using libsecret/keyring."""

from typing import Optional

import keyring


KEYRING_SERVICE = "nanochat-desktop"


class SecretsManager:
    """Manages secure storage of credentials."""

    @staticmethod
    def get_api_key() -> Optional[str]:
        """Get stored API key."""
        return keyring.get_password(KEYRING_SERVICE, "api_key")

    @staticmethod
    def set_api_key(api_key: str) -> None:
        """Store API key securely."""
        keyring.set_password(KEYRING_SERVICE, "api_key", api_key)

    @staticmethod
    def delete_api_key() -> None:
        """Delete stored API key."""
        try:
            keyring.delete_password(KEYRING_SERVICE, "api_key")
        except keyring.errors.PasswordDeleteError:
            pass

    @staticmethod
    def has_api_key() -> bool:
        """Check if API key is stored."""
        return SecretsManager.get_api_key() is not None
