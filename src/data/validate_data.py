# Author: Member A — data validation module
# Purpose: Validate raw monitoring CSV schema before training or ingestion

"""Schema validation for website monitoring dataset."""

from typing import List, Tuple  # Return type for validation errors

import pandas as pd  # DataFrame column checks

from src.utils.config import load_model_config  # Expected columns from YAML


def get_required_columns() -> List[str]:
    """
    Load feature columns plus target column required in raw CSV.

    Returns:
        Ordered list of required column name strings.
    """
    # Load shared model config used by training and API
    config = load_model_config()
    # Combine feature list and binary target column name
    features = list(config["features"])
    target = str(config["target_column"])
    # Return full schema for raw data validation
    return features + [target]


def validate_raw_dataframe(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Check that a DataFrame has all required columns and valid dtypes.

    Args:
        df: Raw monitoring DataFrame to validate.

    Returns:
        Tuple of (is_valid, list_of_error_messages).
    """
    # Collect human-readable validation errors
    errors: List[str] = []
    # Load expected column names from config
    required = get_required_columns()
    # Check for missing columns
    missing = [col for col in required if col not in df.columns]
    if missing:
        errors.append(f"Missing columns: {missing}")
    # Check dataframe is non-empty
    if len(df) == 0:
        errors.append("Dataset is empty (0 rows)")
    # Check target column is binary 0/1 when present
    target_col = load_model_config()["target_column"]
    if target_col in df.columns:
        unique_targets = set(df[target_col].dropna().unique())
        if not unique_targets.issubset({0, 1}):
            errors.append(f"Target '{target_col}' must contain only 0 and 1, got {unique_targets}")
    # Valid if no errors were found
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_raw_csv_path(csv_path) -> Tuple[bool, List[str]]:
    """
    Load a CSV file and run validate_raw_dataframe on it.

    Args:
        csv_path: Path object or string to CSV file.

    Returns:
        Tuple of (is_valid, list_of_error_messages).
    """
    # Read CSV from disk
    df = pd.read_csv(csv_path)
    # Delegate to DataFrame validator
    return validate_raw_dataframe(df)
