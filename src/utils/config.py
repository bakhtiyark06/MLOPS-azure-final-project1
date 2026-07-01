# Author: Team — shared utility module
# Purpose: Load YAML configuration files for model and Azure settings

"""Configuration loading utilities for the MLOps pipeline."""

import os  # Used to resolve paths relative to the project root
from pathlib import Path  # Object-oriented filesystem paths
from typing import Any, Dict, List, Optional  # Type hints for config dictionaries

import yaml  # Parses YAML config files into Python dicts


def get_project_root() -> Path:
    """
    Return the absolute path to the project root directory.

    The project root is two levels above this file (src/utils/config.py).

    Returns:
        Path: Absolute path to MLOPS-azure-final-project1 root.
    """
    # __file__ is this module's path; .parent walks up the directory tree
    return Path(__file__).resolve().parent.parent.parent


def load_yaml_config(config_name: str) -> Dict[str, Any]:
    """
    Load a YAML configuration file from the configs/ directory.

    Args:
        config_name: Filename inside configs/, e.g. 'model_config.yaml'.

    Returns:
        Dict containing parsed YAML content.

    Raises:
        FileNotFoundError: If the config file does not exist.
    """
    # Build full path: project_root/configs/<config_name>
    config_path = get_project_root() / "configs" / config_name
    # Fail fast with a clear error if the file is missing
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    # Open the file in read mode with UTF-8 encoding
    with open(config_path, "r", encoding="utf-8") as config_file:
        # safe_load prevents arbitrary code execution from YAML
        return yaml.safe_load(config_file)


def load_model_config() -> Dict[str, Any]:
    """
    Load model hyperparameters and quality gate thresholds.

    Returns:
        Dict from configs/model_config.yaml.
    """
    # Delegate to the generic loader with the model config filename
    return load_yaml_config("model_config.yaml")


_AZURE_ENV_KEYS = (
    "AZURE_SUBSCRIPTION_ID",
    "AZURE_RESOURCE_GROUP",
    "AZURE_WORKSPACE_NAME",
)


def _load_azure_yaml(config_name: str) -> Dict[str, Any]:
    """Load an Azure YAML file from configs/ without raising if missing."""
    config_path = get_project_root() / "configs" / config_name
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file) or {}
    return dict(data)


def _is_placeholder_value(value: Any) -> bool:
    """Return True when a config value is an unfilled placeholder."""
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    if text.startswith("${") and text.endswith("}"):
        return True
    if text.startswith("<") and text.endswith(">"):
        return True
    return False


def get_missing_azure_env_vars() -> List[str]:
    """Return Azure env var names that are unset or empty."""
    return [key for key in _AZURE_ENV_KEYS if not os.environ.get(key)]


def is_azure_configured(config: Optional[Dict[str, Any]]) -> bool:
    """
    Return True when Azure settings are sufficient for Model Registry registration.

    Example YAML and placeholder values are never treated as configured.
    """
    if not config:
        return False
    if config.get("configured_for_registration") is False:
        return False
    if config.get("source") == "example":
        return False

    subscription_id = resolve_env_placeholder(str(config.get("subscription_id", "")))
    resource_group = str(config.get("resource_group", "")).strip()
    workspace_name = str(config.get("workspace_name", "")).strip()

    if _is_placeholder_value(subscription_id):
        return False
    if _is_placeholder_value(resource_group):
        return False
    if _is_placeholder_value(workspace_name):
        return False
    return True


def load_azure_config() -> Optional[Dict[str, Any]]:
    """
    Load Azure resource settings for optional Azure integrations.

    Priority:
    1. Environment variables (AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP,
       AZURE_WORKSPACE_NAME) when all are set.
    2. Local gitignored configs/azure_config.yaml when present.
    3. configs/azure_config.example.yaml for documentation defaults only.
    4. None when nothing is available (never raises FileNotFoundError).

    Returns:
        Config dict, or None if no Azure configuration source exists.
    """
    subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
    resource_group = os.environ.get("AZURE_RESOURCE_GROUP")
    workspace_name = os.environ.get("AZURE_WORKSPACE_NAME")

    if subscription_id and resource_group and workspace_name:
        cfg = _load_azure_yaml("azure_config.yaml")
        cfg.update(
            {
                "subscription_id": subscription_id,
                "resource_group": resource_group,
                "workspace_name": workspace_name,
                "source": "environment",
                "configured_for_registration": True,
            }
        )
        return cfg

    local_cfg = _load_azure_yaml("azure_config.yaml")
    if local_cfg:
        local_cfg = dict(local_cfg)
        local_cfg["source"] = "local_file"
        local_cfg["configured_for_registration"] = is_azure_configured(local_cfg)
        return local_cfg

    example_cfg = _load_azure_yaml("azure_config.example.yaml")
    if example_cfg:
        example_cfg = dict(example_cfg)
        example_cfg["source"] = "example"
        example_cfg["configured_for_registration"] = False
        return example_cfg

    return None


def resolve_env_placeholder(value: str) -> str:
    """
    Replace ${VAR_NAME} placeholders with environment variable values.

    Args:
        value: String that may contain ${ENV_VAR} syntax.

    Returns:
        Resolved string, or original if no placeholder or env var missing.
    """
    # Only process strings that look like our placeholder format
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        # Extract variable name between ${ and }
        env_key = value[2:-1]
        # os.environ.get returns None if unset; we fall back to original value
        return os.environ.get(env_key, value)
    # Non-placeholder values pass through unchanged
    return value
