#!/usr/bin/env python3
# Author: Member D — drift investigation
# Purpose: Deep-dive analysis when Evidently flags feature drift

"""Investigate drifted features with statistical comparison and recommendations."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.monitoring.drift import get_default_drift_paths, load_drift_datasets, run_drift_check


def analyze_feature(
    reference: pd.Series, current: pd.Series, feature: str
) -> dict:
    """Compute descriptive stats and shift metrics for one feature."""
    ref = reference.dropna()
    cur = current.dropna()
    ref_mean = float(ref.mean())
    cur_mean = float(cur.mean())
    ref_std = float(ref.std())
    cur_std = float(cur.std())
    mean_shift_pct = (
        ((cur_mean - ref_mean) / ref_mean * 100.0) if ref_mean else 0.0
    )
    return {
        "feature": feature,
        "reference_mean": round(ref_mean, 4),
        "current_mean": round(cur_mean, 4),
        "reference_std": round(ref_std, 4),
        "current_std": round(cur_std, 4),
        "mean_shift_percent": round(mean_shift_pct, 2),
        "reference_median": round(float(ref.median()), 4),
        "current_median": round(float(cur.median()), 4),
        "reference_min": round(float(ref.min()), 4),
        "reference_max": round(float(ref.max()), 4),
        "current_min": round(float(cur.min()), 4),
        "current_max": round(float(cur.max()), 4),
    }


def build_investigation_report(
    drifted_features: list[str],
    feature_stats: list[dict],
    drift_summary_path: Path,
) -> dict:
    """Build structured investigation payload."""
    recommendations = []
    if "latency_p95_ms" in drifted_features:
        latency = next(s for s in feature_stats if s["feature"] == "latency_p95_ms")
        if latency["current_mean"] < latency["reference_mean"]:
            recommendations.append(
                "Current P95 latency is lower than the training baseline — "
                "traffic may be healthier than reference window, but model was "
                "trained on higher-latency patterns."
            )
        else:
            recommendations.append(
                "Current P95 latency exceeds reference baseline — "
                "investigate upstream services and consider retraining."
            )
        recommendations.append(
            "Compare reports/drift/drift_report.html for latency_p95_ms distribution plots."
        )
        recommendations.append(
            "Retrain on recent data and refresh data/reference/reference.csv baseline."
        )

    return {
        "investigated_at_utc": datetime.now(timezone.utc).isoformat(),
        "drift_summary_path": str(drift_summary_path),
        "drifted_features": drifted_features,
        "feature_statistics": feature_stats,
        "recommendations": recommendations,
        "action_required": len(drifted_features) > 0,
        "suggested_actions": [
            "Retrain model on updated dataset",
            "Refresh reference baseline after retrain",
            "Re-run scripts/run_drift_check.py",
            "Monitor latency_p95_ms in Application Insights",
            "Document findings in reports/drift/drift_investigation.md",
        ],
    }


def write_markdown_report(payload: dict, path: Path) -> None:
    """Write human-readable investigation markdown."""
    lines = [
        "# Drift Investigation Report",
        "",
        f"**Generated:** {payload['investigated_at_utc']}",
        "",
        "## Drifted features",
        "",
    ]
    for feat in payload["drifted_features"]:
        lines.append(f"- `{feat}`")
    if not payload["drifted_features"]:
        lines.append("- None (no drift detected)")

    lines.extend(["", "## Feature statistics", ""])
    for stat in payload["feature_statistics"]:
        lines.extend(
            [
                f"### {stat['feature']}",
                "",
                f"| Metric | Reference | Current |",
                f"|--------|-----------|---------|",
                f"| Mean | {stat['reference_mean']} | {stat['current_mean']} |",
                f"| Std | {stat['reference_std']} | {stat['current_std']} |",
                f"| Median | {stat['reference_median']} | {stat['current_median']} |",
                f"| Min / Max | {stat['reference_min']} / {stat['reference_max']} | "
                f"{stat['current_min']} / {stat['current_max']} |",
                f"| Mean shift | {stat['mean_shift_percent']}% | |",
                "",
            ]
        )

    lines.extend(["## Recommendations", ""])
    for rec in payload["recommendations"]:
        lines.append(f"- {rec}")

    lines.extend(["", "## Suggested MLOps actions", ""])
    for action in payload["suggested_actions"]:
        lines.append(f"- {action}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Investigate Evidently drift findings")
    parser.add_argument(
        "--drift-summary",
        type=Path,
        default=_PROJECT_ROOT / "reports" / "drift" / "drift_summary.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_PROJECT_ROOT / "reports" / "drift",
    )
    parser.add_argument(
        "--run-drift-first",
        action="store_true",
        help="Run Evidently drift check before investigation",
    )
    args = parser.parse_args()

    if args.run_drift_first:
        run_drift_check()

    if not args.drift_summary.exists():
        print(f"ERROR: Drift summary not found at {args.drift_summary}", file=sys.stderr)
        print("Run: python scripts/run_drift_check.py", file=sys.stderr)
        return 1

    summary = json.loads(args.drift_summary.read_text(encoding="utf-8"))
    drifted = [k for k, v in summary.get("column_drifts", {}).items() if v]

    ref_df, cur_df, feature_cols = load_drift_datasets()
    targets = drifted if drifted else feature_cols
    feature_stats = [
        analyze_feature(ref_df[feat], cur_df[feat], feat) for feat in targets
    ]

    payload = build_investigation_report(drifted, feature_stats, args.drift_summary)
    out_dir = args.output_dir
    json_path = out_dir / "drift_investigation.json"
    md_path = out_dir / "drift_investigation.md"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(payload, md_path)

    print(f"Drifted features: {', '.join(drifted) if drifted else 'none'}")
    print(f"Investigation JSON: {json_path}")
    print(f"Investigation report: {md_path}")
    for stat in feature_stats:
        print(
            f"  {stat['feature']}: reference_mean={stat['reference_mean']} "
            f"current_mean={stat['current_mean']} shift={stat['mean_shift_percent']}%"
        )
    return 0 if not payload["action_required"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
