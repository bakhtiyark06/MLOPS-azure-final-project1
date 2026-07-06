# Author: Member D — Evidently data drift detection
# Purpose: Compare reference baseline vs current production snapshot

"""Data drift detection using Evidently with scipy statistical fallback."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
from scipy import stats

from scripts.generate_sample_data import generate_monitoring_data
from src.data.preprocess import get_feature_columns
from src.data.validate_data import validate_raw_dataframe
from src.utils.config import get_project_root, load_model_config, load_yaml_config


@dataclass
class DriftResult:
    """Result of a drift check run."""

    drift_detected: bool
    report_path: Path
    json_path: Path
    dataset_drift: bool
    column_drifts: dict[str, bool]
    summary: str
    reference_rows: int = 0
    current_rows: int = 0
    drift_score: float = 0.0
    method: str = "evidently"
    column_pvalues: dict[str, float] = field(default_factory=dict)


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


def get_drift_config() -> dict[str, Any]:
    """Load drift thresholds from monitoring_config.yaml."""
    cfg = load_yaml_config("monitoring_config.yaml")
    drift_cfg = cfg.get("drift", {})
    return {
        "ks_pvalue_threshold": float(drift_cfg.get("ks_pvalue_threshold", 0.05)),
        "moderate_drift_score": float(drift_cfg.get("moderate_drift_score", 0.5)),
    }


def ensure_drift_inputs(
    reference_path: Path | None = None,
    current_path: Path | None = None,
) -> tuple[Path, Path]:
    """
    Ensure reference and current CSVs exist, generating sample data if needed.

    Returns:
        Tuple of (reference_path, current_path).

    Raises:
        FileNotFoundError: If data generation fails.
    """
    default_ref, default_cur, _ = get_default_drift_paths()
    ref_path = reference_path or default_ref
    cur_path = current_path or default_cur

    if ref_path.exists() and cur_path.exists():
        return ref_path, cur_path

    root = get_project_root()
    data_cfg = load_yaml_config("data_config.yaml")
    n_samples = int(data_cfg.get("default_sample_count", 2000))
    raw_name = data_cfg.get("raw_filename", "website_monitoring.csv")
    output_path = root / "data" / "raw" / raw_name

    df = generate_monitoring_data(n_samples=n_samples)
    is_valid, errors = validate_raw_dataframe(df)
    if not is_valid:
        raise FileNotFoundError(
            f"Could not generate drift inputs: {'; '.join(errors)}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    ref_rows = int(data_cfg.get("reference_rows", 500))
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    df.head(ref_rows).to_csv(ref_path, index=False)

    cur_rows = int(data_cfg.get("current_snapshot_rows", 300))
    cur_path.parent.mkdir(parents=True, exist_ok=True)
    df.tail(cur_rows).to_csv(cur_path, index=False)

    return ref_path, cur_path


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


def recommendation_from_drift(drift_score: float, dataset_drift: bool) -> str:
    """Return a human-readable recommendation based on drift severity."""
    if not dataset_drift:
        return "Continue monitoring — no significant drift detected."
    if drift_score < 0.5:
        return "Investigate drifted features and compare recent production changes."
    return "Retraining recommended."


def _compute_drift_score(column_drifts: dict[str, bool]) -> float:
    if not column_drifts:
        return 0.0
    drifted = sum(1 for v in column_drifts.values() if v)
    return round(drifted / len(column_drifts), 4)


def _build_summary_text(
    drift_detected: bool,
    dataset_drift: bool,
    drifted_columns: list[str],
    feature_count: int,
) -> str:
    if drift_detected or dataset_drift:
        severity = "Moderate" if len(drifted_columns) < feature_count / 2 else "Significant"
        cols = f": {', '.join(drifted_columns)}." if drifted_columns else "."
        return (
            f"{severity} drift detected across {len(drifted_columns)} of "
            f"{feature_count} features{cols}"
        )
    return "No significant data drift detected."


def build_fallback_html_report(
    result: DriftResult,
    feature_cols: list[str],
    *,
    generated_at: str,
    recommendation: str,
) -> str:
    """Build a professional HTML drift report when Evidently is unavailable."""
    drifted = [c for c, d in result.column_drifts.items() if d]
    drift_pct = round(result.drift_score * 100, 1)
    status_label = "Drift Detected" if result.drift_detected else "No Drift"
    status_class = "warn" if result.drift_detected else "ok"

    rows_html = []
    for col in feature_cols:
        drifted_flag = result.column_drifts.get(col, False)
        pval = result.column_pvalues.get(col)
        pval_str = f"{pval:.4f}" if pval is not None else "—"
        badge = "Drifted" if drifted_flag else "Stable"
        row_class = "drifted" if drifted_flag else ""
        rows_html.append(
            f"<tr class='{row_class}'>"
            f"<td>{escape(col)}</td>"
            f"<td>{escape(badge)}</td>"
            f"<td>{escape(pval_str)}</td>"
            f"</tr>"
        )

    drifted_list = ", ".join(escape(c) for c in drifted) if drifted else "None"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Data Drift Report</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1a1a2e; background: #f8f9fc; }}
    h1 {{ margin-bottom: 0.25rem; }}
    .meta {{ color: #555; margin-bottom: 1.5rem; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
    .card {{ background: #fff; border-radius: 8px; padding: 1rem; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    .card .label {{ font-size: 0.8rem; color: #666; text-transform: uppercase; }}
    .card .value {{ font-size: 1.4rem; font-weight: 600; margin-top: 0.25rem; }}
    .value.ok {{ color: #0d7a4a; }}
    .value.warn {{ color: #b45309; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; }}
    th, td {{ padding: 0.6rem 1rem; text-align: left; border-bottom: 1px solid #eee; }}
    th {{ background: #eef1f8; }}
    tr.drifted td {{ background: #fff8f0; }}
    .recommendation {{ background: #fff; padding: 1rem; border-radius: 8px; margin-top: 1.5rem; border-left: 4px solid #3b5bdb; }}
  </style>
</head>
<body>
  <h1>Data Drift Report</h1>
  <p class="meta">Generated {escape(generated_at)} · Method: {escape(result.method)}</p>
  <div class="cards">
    <div class="card"><div class="label">Overall Status</div><div class="value {status_class}">{escape(status_label)}</div></div>
    <div class="card"><div class="label">Dataset Drift</div><div class="value">{escape(str(result.dataset_drift))}</div></div>
    <div class="card"><div class="label">Drift Score</div><div class="value">{drift_pct}%</div></div>
    <div class="card"><div class="label">Drifted Features</div><div class="value">{len(drifted)} / {len(feature_cols)}</div></div>
    <div class="card"><div class="label">Reference Rows</div><div class="value">{result.reference_rows}</div></div>
    <div class="card"><div class="label">Current Rows</div><div class="value">{result.current_rows}</div></div>
  </div>
  <h2>Affected Features</h2>
  <p>Drifted columns: {drifted_list}</p>
  <table>
    <thead><tr><th>Feature</th><th>Status</th><th>KS p-value</th></tr></thead>
    <tbody>{"".join(rows_html)}</tbody>
  </table>
  <div class="recommendation">
    <strong>Recommendation:</strong> {escape(recommendation)}
  </div>
  <p class="meta" style="margin-top:2rem">{escape(result.summary)}</p>
</body>
</html>
"""


def run_statistical_drift_check(
    reference_path: Path | None = None,
    current_path: Path | None = None,
    output_dir: Path | None = None,
) -> DriftResult:
    """
    Run Kolmogorov-Smirnov drift detection per feature (scipy fallback).

    Args:
        reference_path: Baseline CSV path.
        current_path: Current snapshot CSV path.
        output_dir: Directory for HTML and JSON reports.

    Returns:
        DriftResult with drift status and report paths.
    """
    _, _, report_dir = get_default_drift_paths()
    out_dir = output_dir or report_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    reference_df, current_df, feature_cols = load_drift_datasets(
        reference_path, current_path
    )
    reference_rows = len(reference_df)
    current_rows = len(current_df)

    drift_cfg = get_drift_config()
    p_threshold = drift_cfg["ks_pvalue_threshold"]

    column_drifts: dict[str, bool] = {}
    column_pvalues: dict[str, float] = {}

    for col in feature_cols:
        ref_vals = reference_df[col].dropna().astype(float)
        cur_vals = current_df[col].dropna().astype(float)
        if len(ref_vals) < 2 or len(cur_vals) < 2:
            column_drifts[col] = False
            continue
        stat_result = stats.ks_2samp(ref_vals, cur_vals)
        p_value = float(stat_result.pvalue)
        column_pvalues[col] = round(p_value, 6)
        column_drifts[col] = p_value < p_threshold

    drifted_columns = [col for col, drifted in column_drifts.items() if drifted]
    dataset_drift = len(drifted_columns) > 0
    drift_score = _compute_drift_score(column_drifts)
    drift_detected = dataset_drift
    summary = _build_summary_text(
        drift_detected, dataset_drift, drifted_columns, len(feature_cols)
    )

    generated_at = datetime.now(UTC).isoformat()
    recommendation = recommendation_from_drift(drift_score, dataset_drift)

    result = DriftResult(
        drift_detected=drift_detected,
        report_path=out_dir / "drift_report.html",
        json_path=out_dir / "drift_report.json",
        dataset_drift=dataset_drift,
        column_drifts=column_drifts,
        summary=summary,
        reference_rows=reference_rows,
        current_rows=current_rows,
        drift_score=drift_score,
        method="scipy_ks",
        column_pvalues=column_pvalues,
    )

    json_payload = {
        "generated_at": generated_at,
        "method": result.method,
        "dataset_drift": dataset_drift,
        "drift_detected": drift_detected,
        "drift_score": drift_score,
        "drifted_columns": drifted_columns,
        "column_drifts": column_drifts,
        "column_pvalues": column_pvalues,
        "reference_rows": reference_rows,
        "current_rows": current_rows,
        "summary": summary,
        "recommendation": recommendation,
    }
    result.json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    result.report_path.write_text(
        build_fallback_html_report(
            result, feature_cols, generated_at=generated_at, recommendation=recommendation
        ),
        encoding="utf-8",
    )
    return result


def _run_evidently_drift_check(
    reference_path: Path | None,
    current_path: Path | None,
    output_dir: Path,
) -> DriftResult:
    """Run Evidently data drift report and test suite."""
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

    output_dir.mkdir(parents=True, exist_ok=True)

    reference_df, current_df, feature_cols = load_drift_datasets(
        reference_path, current_path
    )
    reference_rows = len(reference_df)
    current_rows = len(current_df)

    column_mapping = ColumnMapping(numerical_features=feature_cols)

    report = Report(metrics=[DataDriftPreset()])
    report.run(
        reference_data=reference_df,
        current_data=current_df,
        column_mapping=column_mapping,
    )

    html_path = output_dir / "drift_report.html"
    json_path = output_dir / "drift_report.json"
    report.save_html(str(html_path))
    report.save_json(str(json_path))

    test_suite = TestSuite(tests=[DataDriftTestPreset()])
    test_suite.run(
        reference_data=reference_df,
        current_data=current_df,
        column_mapping=column_mapping,
    )
    test_json_path = output_dir / "drift_tests.json"
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

        for col, info in (result.get("drift_by_columns") or {}).items():
            column_drifts[col] = bool(info.get("drift_detected"))

    drifted_columns = [col for col, drifted in column_drifts.items() if drifted]
    if drifted_columns and not dataset_drift:
        dataset_drift = True

    if not column_drifts and dataset_drift:
        column_drifts = {col: True for col in feature_cols}

    if drift_detected and not drifted_columns and column_drifts:
        drifted_columns = [col for col, drifted in column_drifts.items() if drifted]

    drift_score = _compute_drift_score(column_drifts)
    summary = _build_summary_text(
        drift_detected, dataset_drift, drifted_columns, len(feature_cols)
    )

    return DriftResult(
        drift_detected=drift_detected or dataset_drift,
        report_path=html_path,
        json_path=json_path,
        dataset_drift=dataset_drift,
        column_drifts=column_drifts,
        summary=summary,
        reference_rows=reference_rows,
        current_rows=current_rows,
        drift_score=drift_score,
        method="evidently",
    )


def run_drift_check(
    reference_path: Path | None = None,
    current_path: Path | None = None,
    output_dir: Path | None = None,
) -> DriftResult:
    """
    Run data drift analysis (Evidently preferred, scipy KS fallback).

    Args:
        reference_path: Baseline CSV path.
        current_path: Current snapshot CSV path.
        output_dir: Directory for HTML and JSON reports.

    Returns:
        DriftResult with drift status and report paths.
    """
    _, _, report_dir = get_default_drift_paths()
    out_dir = output_dir or report_dir

    try:
        return _run_evidently_drift_check(reference_path, current_path, out_dir)
    except ImportError:
        return run_statistical_drift_check(reference_path, current_path, out_dir)
    except Exception:
        return run_statistical_drift_check(reference_path, current_path, out_dir)


def build_drift_summary_payload(result: DriftResult) -> dict[str, Any]:
    """Build the enriched drift summary dict from a DriftResult."""
    drifted_columns = [col for col, drifted in result.column_drifts.items() if drifted]
    recommendation = recommendation_from_drift(result.drift_score, result.dataset_drift)
    root = get_project_root()

    def _rel(path: Path) -> str:
        try:
            return str(path.relative_to(root))
        except ValueError:
            return str(path)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_drift": result.dataset_drift,
        "drift_detected": result.drift_detected,
        "drift_score": result.drift_score,
        "drifted_columns": drifted_columns,
        "column_drifts": result.column_drifts,
        "reference_rows": result.reference_rows,
        "current_rows": result.current_rows,
        "summary": result.summary,
        "recommendation": recommendation,
        "method": result.method,
        "report_path": _rel(result.report_path),
        "json_path": _rel(result.json_path),
    }


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

    payload = build_drift_summary_payload(result)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def read_drift_summary_file(path: Path | None = None) -> dict[str, Any] | None:
    """Read drift summary JSON if it exists."""
    _, _, report_dir = get_default_drift_paths()
    summary_path = path or (report_dir / "drift_summary.json")
    if not summary_path.exists():
        return None
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def execute_drift_pipeline(
    reference_path: Path | None = None,
    current_path: Path | None = None,
    output_dir: Path | None = None,
    *,
    ensure_inputs: bool = True,
) -> tuple[DriftResult, dict[str, Any]]:
    """
    Run the full drift pipeline: ensure inputs, analyze, write summary.

    Returns:
        Tuple of (DriftResult, summary dict).
    """
    if ensure_inputs:
        ref_path, cur_path = ensure_drift_inputs(reference_path, current_path)
    else:
        default_ref, default_cur, _ = get_default_drift_paths()
        ref_path = reference_path or default_ref
        cur_path = current_path or default_cur

    _, _, report_dir = get_default_drift_paths()
    out_dir = output_dir or report_dir

    result = run_drift_check(ref_path, cur_path, out_dir)
    summary_path = write_drift_summary(result, out_dir / "drift_summary.json")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    return result, payload
