# Author: Team — shared utility module
# Purpose: Read credentials from environment variables only (never hardcode)

"""Secure secret retrieval from environment variables and GitHub Secrets."""

import os  # Access process environment variables at runtime
from typing import Optional  # Optional return type for missing secrets


def get_env_or_raise(key: str) -> str:
    """
    Read a required environment variable or raise a clear error.

    Args:
        key: Environment variable name, e.g. 'AZURE_CLIENT_ID'.

    Returns:
        The non-empty string value of the variable.

    Raises:
        EnvironmentError: If the variable is missing or empty.
    """
    # os.environ.get returns None when the key is not set
    value = os.environ.get(key)
    # Reject missing or blank values to avoid silent auth failures
    if not value:
        raise EnvironmentError(
            f"Required secret '{key}' is not set. "
            f"Add it to GitHub Secrets or your local .env file (never commit .env)."
        )
    # Return the validated secret string
    return value


def get_env_optional(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Read an optional environment variable with a default fallback.

    Args:
        key: Environment variable name.
        default: Value to return if the variable is unset.

    Returns:
        Environment value or default.
    """
    # get with default avoids raising when the secret is optional
    return os.environ.get(key, default)


def get_azure_credentials() -> dict:
    """
    Collect Azure service principal credentials from environment.

    Used by Azure SDK DefaultAzureCredential and explicit client auth.

    Returns:
        Dict with client_id, client_secret, tenant_id keys when all are set.
    """
    # Build a dict of standard service principal env var names
    return {
        "client_id": get_env_optional("AZURE_CLIENT_ID"),
        "client_secret": get_env_optional("AZURE_CLIENT_SECRET"),
        "tenant_id": get_env_optional("AZURE_TENANT_ID"),
        "subscription_id": get_env_optional("AZURE_SUBSCRIPTION_ID"),
    }


def get_openrouter_api_key() -> str:
    """
    Return the OpenRouter API key from environment.

    Returns:
        API key string for OpenRouter HTTP requests.

    Raises:
        EnvironmentError: If OPENROUTER_API_KEY is not configured.
    """
    # OpenRouter key must never appear in source code — env only
    return get_env_or_raise("OPENROUTER_API_KEY")


def get_storage_connection_string() -> str:
    """
    Return Azure Blob Storage connection string from environment.

    Returns:
        Connection string for azure-storage-blob client.

    Raises:
        EnvironmentError: If AZURE_STORAGE_CONNECTION_STRING is missing.
    """
    # Connection string is a secret — loaded at runtime from GitHub Secrets
    return get_env_or_raise("AZURE_STORAGE_CONNECTION_STRING")
