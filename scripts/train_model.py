# Author: Member B — training script
# Purpose: Train outage model, log to MLflow, save artifacts

"""CLI entrypoint for Stage 02 — model training with MLflow logging."""

import argparse
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import mlflow

from src.data.load_data import load_raw_data
from src.features.build_features import prepare_training_data
from src.models.train import (
    compute_train_metrics,
    get_default_artifact_paths,
    save_artifacts,
    train_model,
)
from src.models.registry import load_dataset_hash
from src.utils.config import get_project_root, load_azure_config, load_model_config


def _read_dataset_hash_safe() -> str:
    """Return dataset hash if ingestion completed, else 'unknown'."""
    try:
        return load_dataset_hash()
    except FileNotFoundError:
        return "unknown"


def _setup_mlflow() -> str:
    """Configure MLflow tracking URI and experiment from env or azure config."""
    azure_cfg = load_azure_config() or {}
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
        print(f"  MLflow tracking URI: {tracking_uri}")
    experiment_name = azure_cfg.get("mlflow_experiment_name", "website-outage-prediction")
    mlflow.set_experiment(experiment_name)
    return experiment_name


def main() -> int:
    """Train model, log to MLflow, and write artifacts."""
    parser = argparse.ArgumentParser(description="Train website outage prediction model")
    parser.add_argument(
        "--data-path",
        type=Path,
        default=None,
        help="Optional override for raw CSV path",
    )
    args = parser.parse_args()

    config = load_model_config()
    model_cfg = config["model"]

    print("Loading raw data...")
    df = load_raw_data(args.data_path)
    print(f"  Rows: {len(df)}")

    print("Preparing features and train/test split...")
    X_train, X_test, y_train, y_test = prepare_training_data(
        df, random_state=model_cfg["random_state"]
    )
    print(f"  Train: {len(X_train)}, Test: {len(X_test)}")

    print("Training RandomForestClassifier...")
    model = train_model(X_train, y_train, config)
    train_metrics = compute_train_metrics(model, X_train, y_train)

    model_path, test_set_path = get_default_artifact_paths()
    save_artifacts(model, X_test, y_test, model_path, test_set_path)
    print(f"  Model saved: {model_path}")
    print(f"  Test set saved: {test_set_path}")

    dataset_hash = _read_dataset_hash_safe()
    experiment_name = _setup_mlflow()

    with mlflow.start_run(run_name="outage-rf-train"):
        mlflow.log_params(
            {
                "model_type": model_cfg["type"],
                "n_estimators": model_cfg["n_estimators"],
                "max_depth": model_cfg["max_depth"],
                "random_state": model_cfg["random_state"],
                "feature_count": len(config["features"]),
                "dataset_hash": dataset_hash,
            }
        )
        mlflow.log_param("features", ",".join(config["features"]))
        mlflow.log_metrics(train_metrics)
        mlflow.log_artifact(str(model_path), artifact_path="model")

    print("\nTraining metrics (train set):")
    print(f"  F1 score:  {train_metrics['train_f1_score']:.4f}")
    print(f"  Accuracy:  {train_metrics['train_accuracy']:.4f}")
    print(f"  MLflow experiment: {experiment_name}")
    print(f"  MLflow runs dir: {get_project_root() / 'mlruns'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
