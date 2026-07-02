# Author: Member D — Evidently data drift detection
# Purpose: Compare reference baseline vs current production snapshot

"""Data drift detection using Evidently."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.preprocess import get_feature_columns
from src.utils.config import get_project_root, load_model_config


@dataclass
class DriftResult:
    """Result of a drift check run."""

    drift_detected: bool
    report_path: Path
    json_path: Path
    dataset_drift: bool
    column_drifts: dict[str, bool]
    summary: str


def get_default_drift_paths() -> tuple[Path, Path, Path]:
    """
    Return default paths for reference, current, and report output.

    Returns:
        Tuple of (reference_path, current_path, report_dir).
    """
    root = get_project_root()
    return (
        root / "data" / "reference" / "reference.csv",
        root / "data" / "processed" / "current.csv",
        root / "reports" / "drift",
    )


def load_drift_datasets(
    reference_path: Path | None = None,
    current_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Load reference and current datasets for drift analysis.

    Args:
        reference_path: Baseline CSV path.
        current_path: Current snapshot CSV path.

    Returns:
        Tuple of (reference_df, current_df, feature_columns).

    Raises:
        FileNotFoundError: If either dataset is missing.
    """
    default_ref, default_cur, _ = get_default_drift_paths()
    ref_path = reference_path or default_ref
    cur_path = current_path or default_cur

    if not ref_path.exists():
        raise FileNotFoundError(
            f"Reference data not found at {ref_path}. "
            "Run scripts/generate_sample_data.py first."
        )
    if not cur_path.exists():
        raise FileNotFoundError(
            f"Current snapshot not found at {cur_path}. "
            "Run scripts/generate_sample_data.py first."
        )

    reference_df = pd.read_csv(ref_path)
    current_df = pd.read_csv(cur_path)
    config = load_model_config()
    feature_cols = list(config.get("features", get_feature_columns()))

    for col in feature_cols:
        if col not in reference_df.columns or col not in current_df.columns:
            raise ValueError(f"Feature column '{col}' missing from drift datasets")

    return (
        reference_df[feature_cols],
        current_df[feature_cols],
        feature_cols,
    )


def run_drift_check(
    reference_path: Path | None = None,
    current_path: Path | None = None,
    output_dir: Path | None = None,
) -> DriftResult:
    """
    Run Evidently data drift report and test suite.

    Args:
        reference_path: Baseline CSV path.
        current_path: Current snapshot CSV path.
        output_dir: Directory for HTML and JSON reports.

    Returns:
        DriftResult with drift status and report paths.
    """
    try:
        from evidently.legacy.pipeline.column_mapping import ColumnMapping
        from evidently.legacy.metric_preset import DataDriftPreset
        from evidently.legacy.report import Report
        from evidently.legacy.test_preset import DataDriftTestPreset
        from evidently.legacy.test_suite import TestSuite
    except ImportError:
        from evidently import ColumnMapping
        from evidently.metric_preset import DataDriftPreset
        from evidently.report import Report
        from evidently.test_preset import DataDriftTestPreset
        from evidently.test_suite import TestSuite

    _, _, report_dir = get_default_drift_paths()
    out_dir = output_dir or report_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    reference_df, current_df, feature_cols = load_drift_datasets(
        reference_path, current_path
    )

    column_mapping = ColumnMapping(numerical_features=feature_cols)

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference_df, current_data=current_df, column_mapping=column_mapping)

    html_path = out_dir / "drift_report.html"
    json_path = out_dir / "drift_report.json"
    report.save_html(str(html_path))
    report.save_json(str(json_path))

    test_suite = TestSuite(tests=[DataDriftTestPreset()])
    test_suite.run(
        reference_data=reference_df,
        current_data=current_df,
        column_mapping=column_mapping,
    )
    test_json_path = out_dir / "drift_tests.json"
    test_suite.save_json(str(test_json_path))

    test_results = json.loads(test_json_path.read_text(encoding="utf-8"))
    tests = test_results.get("tests", [])
    failed_tests = [t for t in tests if t.get("status") == "FAIL"]
    drift_detected = len(failed_tests) > 0

    report_data = json.loads(json_path.read_text(encoding="utf-8"))
    dataset_drift = False
    column_drifts: dict[str, bool] = {}

    for metric in report_data.get("metrics", []):
        result = metric.get("result", {})
        metric_name = metric.get("metric", "")

        if metric_name == "DatasetDriftMetric":
            dataset_drift = dataset_drift or bool(result.get("dataset_drift"))
            drifted_count = result.get("number_of_drifted_columns")
            if drifted_count and int(drifted_count) > 0 and not column_drifts:
                dataset_drift = True

        if metric_name == "DataDriftTable":
            dataset_drift = dataset_drift or bool(result.get("dataset_drift"))
            for col, info in (result.get("drift_by_columns") or {}).items():
                column_drifts[col] = bool(info.get("drift_detected"))

        # Evidently <0.7 stored drift_by_columns on DatasetDriftMetric
        for col, info in (result.get("drift_by_columns") or {}).items():
            column_drifts[col] = bool(info.get("drift_detected"))

    drifted_columns = [col for col, drifted in column_drifts.items() if drifted]
    if drifted_columns and not dataset_drift:
        dataset_drift = True

    if not column_drifts and dataset_drift:
        column_drifts = {col: True for col in feature_cols}

    if drift_detected and not drifted_columns and column_drifts:
        drifted_columns = [col for col, drifted in column_drifts.items() if drifted]

    summary = (
        f"Dataset drift detected across {len(drifted_columns)} of "
        f"{len(feature_cols)} features"
        + (f": {', '.join(drifted_columns)}." if drifted_columns else ".")
        if drift_detected or dataset_drift
        else "No significant data drift detected."
    )

    return DriftResult(
        drift_detected=drift_detected or dataset_drift,
        report_path=html_path,
        json_path=json_path,
        dataset_drift=dataset_drift,
        column_drifts=column_drifts,
        summary=summary,
    )


def write_drift_summary(result: DriftResult, path: Path | None = None) -> Path:
    """
    Write a compact drift summary JSON for OpenRouter and alerting.

    Args:
        result: DriftResult from run_drift_check.
        path: Optional output path.

    Returns:
        Path to the summary JSON file.
    """
    _, _, report_dir = get_default_drift_paths()
    out_path = path or (report_dir / "drift_summary.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "drift_detected": result.drift_detected,
        "dataset_drift": result.dataset_drift,
        "column_drifts": result.column_drifts,
        "summary": result.summary,
        "report_path": str(result.report_path),
        "json_path": str(result.json_path),
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path
