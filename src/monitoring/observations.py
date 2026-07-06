# Author: Member D — demo production observation log
# Purpose: Append prediction/URL-check activity for activity-triggered drift

"""
Append-only observation log for demo-triggered drift monitoring.

Production systems usually run drift checks on schedules or batch windows,
not after every single API request. This module simulates a rolling
production snapshot for the MLOps demo.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.preprocess import get_feature_columns
from src.utils.config import get_project_root, load_yaml_config

META_COLUMNS = ["observed_at", "outage_predicted", "outage_probability", "source", "url"]


def get_activity_drift_config() -> dict[str, Any]:
    """Load activity drift paths from monitoring_config.yaml."""
    cfg = load_yaml_config("monitoring_config.yaml")
    drift_cfg = cfg.get("drift", {})
    root = get_project_root()
    activity_dir = root / drift_cfg.get("activity_report_dir", "artifacts/reports")
    observations_rel = drift_cfg.get(
        "observations_file", "artifacts/reports/current_observations.csv"
    )
    return {
        "activity_report_dir": activity_dir,
        "observations_path": root / observations_rel,
        "current_snapshot_path": activity_dir / "current_snapshot.csv",
        "min_observations": int(drift_cfg.get("min_observations", 5)),
        "reference_path": root / drift_cfg.get("reference_path", "data/reference/reference.csv"),
    }


def _ensure_observations_header(path: Path) -> None:
    """Create observations CSV with header if it does not exist."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    feature_cols = get_feature_columns()
    columns = feature_cols + META_COLUMNS
    pd.DataFrame(columns=columns).to_csv(path, index=False)


def append_observation(
    features: dict[str, float],
    *,
    outage_predicted: bool,
    outage_probability: float,
    source: str,
    url: str | None = None,
) -> Path:
    """
    Append one demo production observation row.

    Args:
        features: Model feature dict (7 monitoring metrics).
        outage_predicted: Model prediction flag.
        outage_probability: Model confidence / probability.
        source: ``predict`` or ``url_check``.
        url: Optional URL for URL-check observations.

    Returns:
        Path to the observations CSV.
    """
    cfg = get_activity_drift_config()
    path = cfg["observations_path"]
    _ensure_observations_header(path)

    feature_cols = get_feature_columns()
    row: dict[str, Any] = {col: features.get(col) for col in feature_cols}
    row["observed_at"] = datetime.now(UTC).isoformat()
    row["outage_predicted"] = outage_predicted
    row["outage_probability"] = outage_probability
    row["source"] = source
    row["url"] = url or ""

    df = pd.DataFrame([row])
    df.to_csv(path, mode="a", header=False, index=False)
    return path


def observation_count() -> int:
    """Return number of logged observations (excluding header)."""
    cfg = get_activity_drift_config()
    path = cfg["observations_path"]
    if not path.exists():
        return 0
    try:
        df = pd.read_csv(path)
        return len(df)
    except (pd.errors.EmptyDataError, OSError):
        return 0


def build_current_snapshot() -> Path:
    """
    Build feature-only current snapshot CSV from all observations.

    Returns:
        Path to current_snapshot.csv for drift comparison.
    """
    cfg = get_activity_drift_config()
    obs_path = cfg["observations_path"]
    snapshot_path = cfg["current_snapshot_path"]
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    feature_cols = get_feature_columns()
    if not obs_path.exists():
        pd.DataFrame(columns=feature_cols).to_csv(snapshot_path, index=False)
        return snapshot_path

    df = pd.read_csv(obs_path)
    if df.empty:
        pd.DataFrame(columns=feature_cols).to_csv(snapshot_path, index=False)
        return snapshot_path

    snapshot = df[feature_cols].copy()
    snapshot.to_csv(snapshot_path, index=False)
    return snapshot_path
