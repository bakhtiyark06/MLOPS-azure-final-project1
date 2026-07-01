# Author: Member B — model evaluation stage
# Purpose: Compute metrics and enforce quality gate thresholds

"""Evaluation and quality gate utilities for trained models."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

from src.data.preprocess import get_feature_columns, get_target_column
from src.utils.config import load_model_config


def load_model_and_test_set(
    model_path: Path, test_set_path: Path
) -> Tuple[Any, pd.DataFrame, pd.Series]:
    """
    Load serialized model and test holdout CSV.

    Args:
        model_path: Path to joblib model file.
        test_set_path: Path to test_set.csv.

    Returns:
        Tuple of (model, X_test, y_test).
    """
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. Run scripts/train_model.py first."
        )
    if not test_set_path.exists():
        raise FileNotFoundError(
            f"Test set not found at {test_set_path}. Run scripts/train_model.py first."
        )

    model = joblib.load(model_path)
    test_df = pd.read_csv(test_set_path)
    feature_cols = get_feature_columns()
    target_col = get_target_column()
    X_test = test_df[feature_cols]
    y_test = test_df[target_col]
    return model, X_test, y_test


def compute_metrics(y_true: pd.Series, y_pred: pd.Series) -> Dict[str, float]:
    """
    Compute classification metrics on holdout predictions.

    Uses binary F1 for the positive outage class.

    Args:
        y_true: Ground truth labels.
        y_pred: Model predictions.

    Returns:
        Dict with f1_score and accuracy.
    """
    return {
        "f1_score": float(f1_score(y_true, y_pred, average="binary", zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }


def run_quality_gate(
    metrics: Dict[str, float], config: Dict[str, Any] | None = None
) -> Tuple[bool, List[str]]:
    """
    Compare metrics against quality gate thresholds from config.

    Args:
        metrics: Dict with f1_score and accuracy.
        config: Optional model config; loads from YAML if omitted.

    Returns:
        Tuple of (passed, list of failure reasons).
    """
    if config is None:
        config = load_model_config()
    gate = config["quality_gate"]
    reasons: List[str] = []

    if metrics["f1_score"] < gate["min_f1_score"]:
        reasons.append(
            f"f1_score {metrics['f1_score']:.4f} < min {gate['min_f1_score']}"
        )
    if metrics["accuracy"] < gate["min_accuracy"]:
        reasons.append(
            f"accuracy {metrics['accuracy']:.4f} < min {gate['min_accuracy']}"
        )

    return len(reasons) == 0, reasons


def write_eval_metrics(
    path: Path,
    metrics: Dict[str, float],
    gate_passed: bool,
    gate_reasons: List[str] | None = None,
    force_fail: bool = False,
) -> Dict[str, Any]:
    """
    Write evaluation metrics JSON for DVC and registry gating.

    Args:
        path: Output JSON path.
        metrics: Computed f1_score and accuracy.
        gate_passed: Whether the quality gate passed.
        gate_reasons: Optional list of failure reasons.
        force_fail: If True, record demo failure in output.

    Returns:
        The metrics dict that was written.
    """
    config = load_model_config()
    payload: Dict[str, Any] = {
        "f1_score": metrics["f1_score"],
        "accuracy": metrics["accuracy"],
        "gate_passed": gate_passed,
        "thresholds": dict(config["quality_gate"]),
    }
    if gate_reasons:
        payload["gate_failure_reasons"] = gate_reasons
    if force_fail:
        payload["force_fail_demo"] = True

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return payload


def get_default_eval_paths() -> Tuple[Path, Path, Path]:
    """
    Return default paths for model, test set, and eval metrics.

    Returns:
        Tuple of (model_path, test_set_path, eval_metrics_path).
    """
    from src.utils.config import get_project_root

    root = get_project_root()
    return (
        root / "models" / "outage_model.joblib",
        root / "data" / "processed" / "test_set.csv",
        root / "data" / "processed" / "eval_metrics.json",
    )


def read_eval_metrics(eval_metrics_path: Path) -> Dict[str, Any]:
    """
    Load eval_metrics.json written by evaluation stage.

    Args:
        eval_metrics_path: Path to eval metrics JSON.

    Returns:
        Parsed metrics dict.

    Raises:
        FileNotFoundError: If file does not exist.
    """
    if not eval_metrics_path.exists():
        raise FileNotFoundError(
            f"Eval metrics not found at {eval_metrics_path}. "
            "Run scripts/evaluate_model.py first."
        )
    with open(eval_metrics_path, "r", encoding="utf-8") as f:
        return json.load(f)
