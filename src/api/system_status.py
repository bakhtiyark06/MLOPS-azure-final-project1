# Author: Member D — dashboard system status
# Purpose: Aggregate health, artifacts, and evaluation state for the UI

"""System status helpers for the local demo dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.utils.config import get_project_root, load_yaml_config


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def get_system_status(
    *,
    model_loaded: bool,
    api_status: str,
    model_path: Path,
) -> dict[str, Any]:
    """
    Build a JSON snapshot of local demo system readiness.

    Args:
        model_loaded: Whether the in-memory model is loaded.
        api_status: Health endpoint status string.
        model_path: Expected model artifact path.

    Returns:
        Dict suitable for GET /system-status.
    """
    root = get_project_root()
    data_cfg = load_yaml_config("data_config.yaml")
    raw_name = data_cfg.get("raw_filename", "website_monitoring.csv")
    raw_path = root / "data" / "raw" / raw_name
    eval_path = root / "data" / "processed" / "eval_metrics.json"
    eval_data = _read_json(eval_path)

    gate_passed = eval_data.get("gate_passed") if eval_data else None
    if gate_passed is True:
        eval_status = "passed"
    elif gate_passed is False:
        eval_status = "failed"
    elif eval_data:
        eval_status = "unknown"
    else:
        eval_status = "not_run"

    return {
        "api_health": api_status,
        "model_loaded": model_loaded,
        "data_exists": raw_path.exists(),
        "model_file_exists": model_path.exists(),
        "eval_status": eval_status,
        "gate_passed": gate_passed,
        "eval_metrics": eval_data,
        "paths": {
            "raw_data": str(raw_path),
            "model": str(model_path),
            "eval_metrics": str(eval_path),
        },
    }
