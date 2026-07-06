# Author: TODO - Team Member Name
# Responsibility: TODO - API / Inference
# Last Reviewed: TODO

"""Model loading and prediction helpers for the API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from src.data.preprocess import get_feature_columns


def load_model(model_path: Path) -> Any:
    """Load a serialized scikit-learn model from disk."""
    if not model_path.is_file():
        raise FileNotFoundError(f"Model not found at {model_path}")
    return joblib.load(model_path)


def features_from_request(payload: dict[str, float]) -> pd.DataFrame:
    """Build a single-row feature matrix in training column order."""
    columns = get_feature_columns()
    row = {col: float(payload[col]) for col in columns}
    return pd.DataFrame([row], columns=columns)


def predict_outage(model: Any, features: pd.DataFrame) -> dict[str, bool | float]:
    """Return outage label and probability from model predictions."""
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(features)[0]
        outage_probability = float(proba[1]) if len(proba) > 1 else float(proba[0])
    else:
        label = int(model.predict(features)[0])
        outage_probability = float(label)

    return {
        "outage_predicted": outage_probability >= 0.5,
        "outage_probability": outage_probability,
    }
