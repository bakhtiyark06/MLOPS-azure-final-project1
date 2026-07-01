# Author: Member B — model registry stage
# Purpose: Register approved models in Azure ML Model Registry

"""Azure ML Model Registry registration with dataset lineage tags."""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models.evaluate import read_eval_metrics
from src.utils.config import (
    get_missing_azure_env_vars,
    get_project_root,
    is_azure_configured,
    load_azure_config,
    resolve_env_placeholder,
)


class QualityGateError(Exception):
    """Raised when registration is attempted without passing the quality gate."""


SKIP_MESSAGE = (
    "Azure configuration not found.\n"
    "Skipping Azure Model Registry registration."
)


def load_dataset_hash(root: Optional[Path] = None) -> str:
    """
    Load dataset hash from ingestion metadata or hash file.

    Args:
        root: Project root; defaults to get_project_root().

    Returns:
        SHA256 dataset hash string.

    Raises:
        FileNotFoundError: If neither metadata nor hash file exists.
    """
    root = root or get_project_root()
    meta_path = root / "data" / "raw" / "ingestion_metadata.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return str(meta["dataset_hash"])

    hash_path = root / "data" / "raw" / "dataset_hash.txt"
    if hash_path.exists():
        return hash_path.read_text(encoding="utf-8").strip()

    raise FileNotFoundError(
        "Dataset hash not found. Run scripts/ingest_data.py (Member A) first."
    )


def get_git_sha() -> str:
    """Return current git commit SHA, or 'unknown' when git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=get_project_root(),
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def assert_gate_passed(eval_metrics_path: Path) -> Dict[str, Any]:
    """
    Verify quality gate passed before registry registration.

    Args:
        eval_metrics_path: Path to eval_metrics.json.

    Returns:
        Parsed eval metrics dict.

    Raises:
        QualityGateError: If gate_passed is false or missing.
    """
    metrics = read_eval_metrics(eval_metrics_path)
    if not metrics.get("gate_passed"):
        raise QualityGateError(
            "Quality gate did not pass. Run evaluate_model.py and ensure "
            "gate_passed is true before registering."
        )
    return metrics


def get_azure_configuration_status() -> Dict[str, Any]:
    """
    Inspect Azure configuration availability for registration.

    Returns:
        Dict with configured flag, missing env vars, and loaded config (if any).
    """
    azure_cfg = load_azure_config()
    missing = get_missing_azure_env_vars()
    configured = is_azure_configured(azure_cfg)
    return {
        "configured": configured,
        "missing_env_vars": missing,
        "config": azure_cfg,
    }


def get_ml_client():
    """
    Create Azure ML MLClient using env-first config and DefaultAzureCredential.

    Returns:
        azure.ai.ml.MLClient instance.

    Raises:
        EnvironmentError: If Azure is not configured for registration.
    """
    from azure.ai.ml import MLClient
    from azure.identity import DefaultAzureCredential

    status = get_azure_configuration_status()
    if not status["configured"]:
        missing = status["missing_env_vars"]
        detail = (
            f"Missing environment variables: {', '.join(missing)}"
            if missing
            else "Azure configuration contains placeholder values only."
        )
        raise EnvironmentError(detail)

    azure_cfg = status["config"]
    subscription_id = resolve_env_placeholder(str(azure_cfg["subscription_id"]))

    return MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=azure_cfg["resource_group"],
        workspace_name=azure_cfg["workspace_name"],
    )


def _build_registry_tags(eval_metrics: Dict[str, Any], dataset_hash: str) -> Dict[str, str]:
    """Build Azure ML model tags from evaluation metrics and lineage."""
    accuracy = eval_metrics.get("accuracy", eval_metrics.get("test_accuracy", 0))
    f1_macro = eval_metrics.get(
        "f1_macro", eval_metrics.get("f1_score", eval_metrics.get("test_f1_macro", 0))
    )
    return {
        "accuracy": str(accuracy),
        "f1_macro": str(f1_macro),
        "dataset_hash": dataset_hash,
        "git_sha": get_git_sha(),
        "created_by": "Bakhtiyar Khan",
        "project": "MLOPS Azure Final Project",
        "stage": "approved",
    }


def register_model(
    model_path: Path,
    eval_metrics_path: Path,
    dataset_hash: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Register model in Azure ML Model Registry if quality gate passed.

    Args:
        model_path: Path to outage_model.joblib.
        eval_metrics_path: Path to eval_metrics.json.
        dataset_hash: Optional hash override; loaded from ingestion metadata if omitted.
        dry_run: If True, validate gate only without Azure API call.

    Returns:
        Dict with model name, version info, tags, or skip metadata.

    Raises:
        QualityGateError: If quality gate did not pass.
        FileNotFoundError: If model file is missing.
    """
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found at {model_path}.")

    eval_metrics = assert_gate_passed(eval_metrics_path)
    dataset_hash = dataset_hash or load_dataset_hash()
    tags = _build_registry_tags(eval_metrics, dataset_hash)

    azure_status = get_azure_configuration_status()
    azure_cfg = azure_status["config"] or {}
    model_name = azure_cfg.get("model_registry_name", "website-outage-model")

    result: Dict[str, Any] = {
        "model_name": model_name,
        "model_path": str(model_path),
        "tags": tags,
        "dry_run": dry_run,
        "skipped": False,
    }

    if dry_run:
        result["message"] = "Dry run - quality gate passed; Azure registration skipped."
        return result

    if not azure_status["configured"]:
        result["skipped"] = True
        result["message"] = SKIP_MESSAGE
        result["missing_env_vars"] = azure_status["missing_env_vars"]
        return result

    from azure.ai.ml.entities import Model

    ml_client = get_ml_client()
    model_entity = Model(
        path=str(model_path),
        name=model_name,
        description="Website outage prediction RandomForest classifier",
        tags=tags,
        type="custom_model",
    )
    registered = ml_client.models.create_or_update(model_entity)
    result["version"] = registered.version
    result["id"] = registered.id
    return result
