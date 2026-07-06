#!/usr/bin/env python3
# Author: Member D — drift check CLI
# Purpose: Run Evidently drift detection and exit non-zero when drift is detected

"""CLI entrypoint for data drift detection (Evidently)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.monitoring.drift import execute_drift_pipeline, get_default_drift_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Evidently data drift check")
    parser.add_argument(
        "--reference",
        type=Path,
        default=None,
        help="Reference baseline CSV (default: data/reference/reference.csv)",
    )
    parser.add_argument(
        "--current",
        type=Path,
        default=None,
        help="Current snapshot CSV (default: data/processed/current.csv)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Report output directory (default: reports/drift)",
    )
    parser.add_argument(
        "--no-ensure-inputs",
        action="store_true",
        help="Do not auto-generate reference/current CSVs if missing",
    )
    args = parser.parse_args()

    default_ref, default_cur, default_out = get_default_drift_paths()
    reference_path = args.reference or default_ref
    current_path = args.current or default_cur
    output_dir = args.output_dir or default_out

    try:
        result, payload = execute_drift_pipeline(
            reference_path,
            current_path,
            output_dir,
            ensure_inputs=not args.no_ensure_inputs,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Drift check failed: {exc}", file=sys.stderr)
        return 1

    print(result.summary)
    print(f"HTML report: {result.report_path}")
    print(f"JSON report: {result.json_path}")
    print(f"Summary:     {output_dir / 'drift_summary.json'}")
    print(f"Drift score: {payload.get('drift_score')}")
    print(f"Method:      {payload.get('method')}")

    if result.drift_detected:
        print("\nDRIFT DETECTED — alert condition met", file=sys.stderr)
        drifted = payload.get("drifted_columns", [])
        if drifted:
            print(f"Drifted features: {', '.join(drifted)}", file=sys.stderr)
        return 1

    print("\nNo drift detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
