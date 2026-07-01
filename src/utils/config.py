# Author: Team — shared utility module
# Purpose: Load YAML configuration files for model and Azure settings

"""Configuration loading utilities for the MLOps pipeline."""

import os  # Used to resolve paths relative to the project root
from pathlib import Path  # Object-oriented filesystem paths
from typing import Any, Dict  # Type hints for config dictionaries

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


def load_azure_config() -> Dict[str, Any]:
    """
    Load non-secret Azure resource names and locations.

    Returns:
        Dict from configs/azure_config.yaml.
    """
    # Delegate to the generic loader with the Azure config filename
    return load_yaml_config("azure_config.yaml")


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
