# Author: Member B — model training stage
# Purpose: Build, train, and serialize scikit-learn outage prediction model

"""Training utilities for RandomForest outage classifier."""

from pathlib import Path
from typing import Any, Dict, Tuple

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

from src.data.preprocess import get_feature_columns, get_target_column


def build_model(config: Dict[str, Any]) -> RandomForestClassifier:
    """
    Instantiate a RandomForestClassifier from model config.

    Args:
        config: Parsed model_config.yaml dict.

    Returns:
        Unfitted RandomForestClassifier.
    """
    model_cfg = config["model"]
    return RandomForestClassifier(
        n_estimators=model_cfg["n_estimators"],
        max_depth=model_cfg["max_depth"],
        random_state=model_cfg["random_state"],
    )


def train_model(
    X_train: pd.DataFrame, y_train: pd.Series, config: Dict[str, Any]
) -> RandomForestClassifier:
    """
    Fit a RandomForest classifier on training data.

    Args:
        X_train: Training feature matrix.
        y_train: Training target vector.
        config: Model configuration dict.

    Returns:
        Fitted classifier.
    """
    model = build_model(config)
    model.fit(X_train, y_train)
    return model


def compute_train_metrics(
    model: RandomForestClassifier, X_train: pd.DataFrame, y_train: pd.Series
) -> Dict[str, float]:
    """
    Compute training-set metrics for MLflow logging.

    Args:
        model: Fitted classifier.
        X_train: Training features.
        y_train: Training targets.

    Returns:
        Dict with f1_score and accuracy.
    """
    y_pred = model.predict(X_train)
    return {
        "train_f1_score": float(f1_score(y_train, y_pred, average="binary", zero_division=0)),
        "train_accuracy": float(accuracy_score(y_train, y_pred)),
    }


def save_artifacts(
    model: RandomForestClassifier,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    model_path: Path,
    test_set_path: Path,
) -> None:
    """
    Persist trained model and holdout test set to disk.

    Args:
        model: Fitted classifier.
        X_test: Test feature matrix.
        y_test: Test target vector.
        model_path: Destination for joblib model file.
        test_set_path: Destination for test CSV (features + target).
    """
    model_path.parent.mkdir(parents=True, exist_ok=True)
    test_set_path.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, model_path)

    target_col = get_target_column()
    test_df = X_test.copy()
    test_df[target_col] = y_test.values
    test_df.to_csv(test_set_path, index=False)


def get_default_artifact_paths() -> Tuple[Path, Path]:
    """
    Return default paths for model and test set artifacts.

    Returns:
        Tuple of (model_path, test_set_path).
    """
    from src.utils.config import get_project_root

    root = get_project_root()
    return (
        root / "models" / "outage_model.joblib",
        root / "data" / "processed" / "test_set.csv",
    )
