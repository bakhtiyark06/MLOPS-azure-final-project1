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

from src.monitoring.drift import get_default_drift_paths, run_drift_check, write_drift_summary


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
    args = parser.parse_args()

    default_ref, default_cur, default_out = get_default_drift_paths()
    reference_path = args.reference or default_ref
    current_path = args.current or default_cur
    output_dir = args.output_dir or default_out

    try:
        result = run_drift_check(reference_path, current_path, output_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Drift check failed: {exc}", file=sys.stderr)
        return 1

    summary_path = write_drift_summary(result)
    print(result.summary)
    print(f"HTML report: {result.report_path}")
    print(f"JSON report: {result.json_path}")
    print(f"Summary:     {summary_path}")

    if result.drift_detected:
        print("\nDRIFT DETECTED — alert condition met", file=sys.stderr)
        drifted = [col for col, drifted in result.column_drifts.items() if drifted]
        if drifted:
            print(f"Drifted features: {', '.join(drifted)}", file=sys.stderr)
        return 1

    print("\nNo drift detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
