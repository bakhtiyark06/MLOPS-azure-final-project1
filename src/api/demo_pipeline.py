# Author: Member D — local demo pipeline runner
# Purpose: Run generate → ingest → train → evaluate from the dashboard

"""Local MLOps demo pipeline for browser-triggered runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from scripts.generate_sample_data import generate_monitoring_data
from scripts.ingest_data import compute_file_hash, write_ingestion_metadata
from src.data.load_data import load_raw_data
from src.data.validate_data import validate_raw_csv_path, validate_raw_dataframe
from src.features.build_features import prepare_training_data
from src.models.evaluate import (
    compute_metrics,
    get_default_eval_paths,
    load_model_and_test_set,
    run_quality_gate,
    write_eval_metrics,
)
from src.models.train import compute_train_metrics, get_default_artifact_paths, save_artifacts, train_model
from src.utils.config import get_project_root, load_model_config, load_yaml_config
from src.utils.secrets import get_env_optional


class PipelineStepError(Exception):
    """Raised when a pipeline step fails."""

    def __init__(self, step: str, message: str) -> None:
        super().__init__(message)
        self.step = step
        self.message = message


@dataclass
class PipelineRun:
    steps: list[dict[str, str]] = field(default_factory=list)
    azure_skipped: bool = False
    azure_message: str = ""

    def add(self, name: str, status: str, detail: str = "") -> None:
        step = {"name": name, "status": status}
        if detail:
            step["detail"] = detail
        self.steps.append(step)


def _azure_credentials_present() -> bool:
    return bool(get_env_optional("AZURE_STORAGE_CONNECTION_STRING"))


def _step_generate_data(root: Path, run: PipelineRun) -> Path:
    data_cfg = load_yaml_config("data_config.yaml")
    n_samples = int(data_cfg.get("default_sample_count", 2000))
    raw_name = data_cfg.get("raw_filename", "website_monitoring.csv")
    output_path = root / "data" / "raw" / raw_name

    df = generate_monitoring_data(n_samples=n_samples)
    is_valid, errors = validate_raw_dataframe(df)
    if not is_valid:
        raise PipelineStepError("Generate data", "; ".join(errors))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    ref_rows = int(data_cfg.get("reference_rows", 500))
    ref_path = root / "data" / "reference" / "reference.csv"
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    df.head(ref_rows).to_csv(ref_path, index=False)

    cur_rows = int(data_cfg.get("current_snapshot_rows", 300))
    cur_path = root / "data" / "processed" / "current.csv"
    cur_path.parent.mkdir(parents=True, exist_ok=True)
    df.tail(cur_rows).to_csv(cur_path, index=False)

    run.add("Generate data", "passed", f"{len(df)} rows written")
    return output_path


def _step_ingest_data(root: Path, data_path: Path, run: PipelineRun) -> None:
    data_cfg = load_yaml_config("data_config.yaml")
    is_valid, errors = validate_raw_csv_path(data_path)
    if not is_valid:
        raise PipelineStepError("Ingest data", "; ".join(errors))

    dataset_hash = compute_file_hash(data_path)
    hash_path = root / "data" / "raw" / "dataset_hash.txt"
    hash_path.write_text(dataset_hash, encoding="utf-8")
    row_count = len(pd.read_csv(data_path))

    blob_url = None
    run.azure_skipped = True
    if _azure_credentials_present():
        run.azure_message = (
            "Azure credentials detected; local dashboard pipeline completed "
            "without Azure upload/registry."
        )
        detail = "Validated locally; run scripts/ingest_data.py for Azure blob upload."
    else:
        run.azure_message = (
            "Azure credentials not found, local demo pipeline completed "
            "without Azure upload/registry."
        )
        detail = "Validated locally without Azure upload"

    meta_path = root / data_cfg.get("ingestion_metadata_file", "data/raw/ingestion_metadata.json")
    write_ingestion_metadata(meta_path, dataset_hash, row_count, blob_url, dvc_tracked=False)
    run.add("Ingest data", "passed", detail)


def _step_train_model(root: Path, run: PipelineRun) -> Path:
    config = load_model_config()
    df = load_raw_data()
    X_train, X_test, y_train, y_test = prepare_training_data(
        df, random_state=config["model"]["random_state"]
    )
    model = train_model(X_train, y_train, config)
    compute_train_metrics(model, X_train, y_train)

    model_path, test_set_path = get_default_artifact_paths()
    save_artifacts(model, X_test, y_test, model_path, test_set_path)
    run.add("Train model", "passed", f"Model saved to {model_path.name}")
    return model_path


def _step_evaluate_model(run: PipelineRun) -> dict[str, Any]:
    config = load_model_config()
    model_path, test_set_path, eval_metrics_path = get_default_eval_paths()
    model, X_test, y_test = load_model_and_test_set(model_path, test_set_path)
    metrics = compute_metrics(y_test, model.predict(X_test))
    passed, reasons = run_quality_gate(metrics, config)
    write_eval_metrics(eval_metrics_path, metrics, gate_passed=passed, gate_reasons=reasons)

    status = "passed" if passed else "failed"
    detail = (
        f"F1={metrics['f1_score']:.4f}, accuracy={metrics['accuracy']:.4f}"
        if passed
        else "; ".join(reasons)
    )
    run.add("Evaluate model", status, detail)
    if not passed:
        raise PipelineStepError("Evaluate model", detail)
    return metrics


def run_local_pipeline(reload_model: Callable[[], None] | None = None) -> dict[str, Any]:
    """
    Execute the safe local demo pipeline steps.

    Args:
        reload_model: Optional callback to reload the in-memory model after training.

    Returns:
        JSON-serializable pipeline result for the dashboard.
    """
    root = get_project_root()
    run = PipelineRun()

    try:
        data_path = _step_generate_data(root, run)
        _step_ingest_data(root, data_path, run)
        _step_train_model(root, run)
        metrics = _step_evaluate_model(run)

        if reload_model is not None:
            reload_model()

        message = "Local pipeline completed successfully."
        if run.azure_skipped:
            message += f" {run.azure_message}"

        return {
            "status": "success",
            "steps": run.steps,
            "message": message,
            "azure_skipped": run.azure_skipped,
            "eval_metrics": metrics,
        }
    except PipelineStepError as exc:
        return {
            "status": "failed",
            "steps": run.steps,
            "failed_step": exc.step,
            "error": exc.message,
            "azure_skipped": run.azure_skipped,
            "message": run.azure_message or None,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "steps": run.steps,
            "failed_step": run.steps[-1]["name"] if run.steps else "Unknown",
            "error": f"Pipeline failed: {exc}",
            "azure_skipped": run.azure_skipped,
        }
