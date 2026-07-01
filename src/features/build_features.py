# Author: Member B — feature preparation stage
# Purpose: Prepare training features from raw monitoring data

"""Feature preparation pipeline delegating to Member A preprocessing."""

from typing import Tuple

import pandas as pd

from src.data.preprocess import preprocess_dataframe, train_test_split_data


def prepare_training_data(
    df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Clean raw data and split into train/test sets.

    Args:
        df: Raw monitoring DataFrame from load_raw_data().
        test_size: Fraction held out for testing.
        random_state: Seed for reproducible splits.

    Returns:
        Tuple of (X_train, X_test, y_train, y_test).
    """
    cleaned = preprocess_dataframe(df)
    return train_test_split_data(cleaned, test_size=test_size, random_state=random_state)
