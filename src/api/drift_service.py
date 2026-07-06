# Author: Member D — drift API service
# Purpose: Auto-generate drift reports on API request and after demo activity

"""API-facing drift report orchestration."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from src.monitoring.drift import (
    execute_drift_pipeline,
    get_default_drift_paths,
    read_drift_summary_file,
)
from src.monitoring.observations import (
    build_current_snapshot,
    get_activity_drift_config,
    observation_count,
)

logger = logging.getLogger(__name__)

_drift_lock = threading.Lock()


def get_activity_report_dir() -> Path:
    """Return artifacts/reports directory for activity-triggered drift."""
    return get_activity_drift_config()["activity_report_dir"]


def get_drift_summary_path() -> Path:
    """Return activity drift_summary.json path (API/dashboard)."""
    return get_activity_report_dir() / "drift_summary.json"


def read_drift_summary() -> dict[str, Any] | None:
    """Read existing activity drift summary from disk."""
    return read_drift_summary_file(get_drift_summary_path())


def _activity_status_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Build compact drift status for predict/URL-check responses."""
    return {
        "updated": True,
        "insufficient_data": False,
        "dataset_drift": payload.get("dataset_drift"),
        "drift_score": payload.get("drift_score"),
        "drifted_columns": payload.get("drifted_columns", []),
        "message": "Drift report updated.",
        "observation_count": observation_count(),
    }


def try_update_drift_after_activity() -> dict[str, Any]:
    """
    Regenerate drift report from demo observation log when enough data exists.

    Demo-triggered drift: production systems usually run drift on schedules
    or batch windows, not after every request. Never raises — safe for predict hook.
    """
    cfg = get_activity_drift_config()
    count = observation_count()
    min_obs = cfg["min_observations"]

    if count < min_obs:
        return {
            "updated": False,
            "insufficient_data": True,
            "dataset_drift": None,
            "drift_score": None,
            "drifted_columns": [],
            "message": "At least 5 observations are required for drift analysis.",
            "observation_count": count,
        }

    try:
        with _drift_lock:
            snapshot_path = build_current_snapshot()
            ref_path = cfg["reference_path"]
            out_dir = cfg["activity_report_dir"]
            out_dir.mkdir(parents=True, exist_ok=True)

            if not ref_path.exists():
                return {
                    "updated": False,
                    "insufficient_data": False,
                    "message": (
                        f"Reference baseline missing at {ref_path}. "
                        "Run generate_sample_data or the local pipeline first."
                    ),
                    "observation_count": count,
                }

            _, payload = execute_drift_pipeline(
                reference_path=ref_path,
                current_path=snapshot_path,
                output_dir=out_dir,
                ensure_inputs=False,
            )
            return _activity_status_from_payload(payload)
    except Exception as exc:
        logger.warning("Activity-triggered drift update failed: %s", exc)
        return {
            "updated": False,
            "insufficient_data": False,
            "message": f"Drift update failed: {exc}",
            "observation_count": count,
        }


def ensure_drift_report(*, force: bool = False) -> dict[str, Any]:
    """
    Return drift summary JSON for API/dashboard.

    Prefers activity-generated summary; falls back to running activity drift
    when observations exist, otherwise legacy batch pipeline.
    """
    if not force:
        existing = read_drift_summary()
        if existing is not None:
            return existing

    with _drift_lock:
        if not force:
            existing = read_drift_summary()
            if existing is not None:
                return existing

        count = observation_count()
        cfg = get_activity_drift_config()

        if count > 0 and count < cfg["min_observations"]:
            return {
                "insufficient_data": True,
                "message": "At least 5 observations are required for drift analysis.",
                "observation_count": count,
            }

        if count >= cfg["min_observations"]:
            status = try_update_drift_after_activity()
            if status.get("updated"):
                summary = read_drift_summary()
                if summary is not None:
                    return summary
            if status.get("insufficient_data"):
                return {
                    "insufficient_data": True,
                    "message": status.get("message", ""),
                    "observation_count": status.get("observation_count", count),
                }

        if count > 0:
            # Observations exist but drift update failed — surface last status without batch fallback.
            status = try_update_drift_after_activity()
            if status.get("updated"):
                summary = read_drift_summary()
                if summary is not None:
                    return summary
            return {
                "insufficient_data": status.get("insufficient_data", False),
                "message": status.get("message", "Drift update did not complete."),
                "observation_count": count,
            }

        try:
            out_dir = cfg["activity_report_dir"]
            out_dir.mkdir(parents=True, exist_ok=True)
            _, payload = execute_drift_pipeline(output_dir=out_dir)
            return payload
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=503,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Drift analysis failed: {exc}",
            ) from exc
