# Author: Member A — data preprocessing stage
# Purpose: Clean raw monitoring data and prepare train-ready features

"""Preprocessing pipeline for website monitoring data."""

from typing import List, Tuple  # Type hints for feature lists and splits

import numpy as np  # Numerical operations for imputation
import pandas as pd  # DataFrame operations
from sklearn.model_selection import train_test_split  # Holdout split for training

from src.utils.config import load_model_config  # Load feature list and target from YAML


def get_feature_columns() -> List[str]:
    """
    Load the list of input feature column names from model config.

    Returns:
        List of feature column name strings.
    """
    # Parse model_config.yaml for the features section
    config = load_model_config()
    # Return the ordered feature list used by training and API
    return list(config["features"])


def get_target_column() -> str:
    """
    Load the target column name from model config.

    Returns:
        Name of the binary outage prediction target column.
    """
    # Target is defined once in config for consistency across pipeline
    config = load_model_config()
    return str(config["target_column"])


def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and validate the raw monitoring DataFrame.

    Steps: drop duplicates, handle missing values, clip outliers.

    Args:
        df: Raw monitoring DataFrame from load_data.

    Returns:
        Cleaned DataFrame ready for feature extraction.
    """
    # Work on a copy so we do not mutate the caller's dataframe
    cleaned = df.copy()
    # Remove exact duplicate rows that could bias the model
    cleaned = cleaned.drop_duplicates()
    # Load expected feature and target names from config
    feature_cols = get_feature_columns()
    target_col = get_target_column()
    # Keep only columns we need plus the target
    required_cols = feature_cols + [target_col]
    # Subset to required columns; raises KeyError if columns missing (caught in tests)
    cleaned = cleaned[required_cols]
    # Fill numeric NaNs with column median — simple robust imputation
    for col in feature_cols:
        median_val = cleaned[col].median()
        cleaned[col] = cleaned[col].fillna(median_val)
    # Clip extreme values to 1st–99th percentile per feature to reduce outlier impact
    for col in feature_cols:
        lower = cleaned[col].quantile(0.01)
        upper = cleaned[col].quantile(0.99)
        cleaned[col] = cleaned[col].clip(lower=lower, upper=upper)
    # Ensure target is integer 0/1 for classification
    cleaned[target_col] = cleaned[target_col].astype(int)
    # Return cleaned data for splitting and training
    return cleaned


def train_test_split_data(
    df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Split preprocessed data into train and test sets.

    Args:
        df: Preprocessed DataFrame.
        test_size: Fraction held out for testing (default 0.2).
        random_state: Seed for reproducible splits.

    Returns:
        Tuple of (X_train, X_test, y_train, y_test).
    """
    # Resolve feature and target column names from config
    feature_cols = get_feature_columns()
    target_col = get_target_column()
    # Separate features (X) and target (y)
    X = df[feature_cols]
    y = df[target_col]
    # sklearn train_test_split with stratify keeps class balance in both sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    # Return four objects for training and evaluation scripts
    return X_train, X_test, y_train, y_test
