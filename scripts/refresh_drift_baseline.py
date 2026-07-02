#!/usr/bin/env python3
# Author: Member D — baseline refresh after retrain
# Purpose: Align reference and current snapshots from the same post-retrain corpus

"""Refresh drift reference baseline from the latest training dataset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils.config import get_project_root, load_yaml_config


def refresh_baseline(
    raw_path: Path | None = None,
    reference_rows: int | None = None,
    current_rows: int | None = None,
    reference_seed: int = 42,
    current_seed: int = 43,
) -> tuple[Path, Path]:
    """
    Write reference and current CSVs from independent samples of the same raw file.

    Both snapshots come from the post-retrain corpus so Evidently compares
    like-for-like distributions after remediation.
    """
    root = get_project_root()
    data_cfg = load_yaml_config("data_config.yaml")
    raw_name = data_cfg.get("raw_filename", "website_monitoring.csv")
    raw_path = raw_path or root / "data" / "raw" / raw_name
    if not raw_path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at {raw_path}. Run scripts/generate_sample_data.py first."
        )

    ref_rows = reference_rows or int(data_cfg.get("reference_rows", 500))
    cur_rows = current_rows or int(data_cfg.get("current_snapshot_rows", 300))

    df = pd.read_csv(raw_path)
    if len(df) < ref_rows + cur_rows:
        raise ValueError(
            f"Need at least {ref_rows + cur_rows} rows in {raw_path}, found {len(df)}"
        )

    ref_path = root / "data" / "reference" / "reference.csv"
    cur_path = root / "data" / "processed" / "current.csv"
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    cur_path.parent.mkdir(parents=True, exist_ok=True)

    ref_df = df.sample(n=ref_rows, random_state=reference_seed)
    cur_df = df.sample(n=cur_rows, random_state=current_seed)
    ref_df.to_csv(ref_path, index=False)
    cur_df.to_csv(cur_path, index=False)
    return ref_path, cur_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh drift baseline from raw training data")
    parser.add_argument("--raw", type=Path, default=None)
    args = parser.parse_args()
    try:
        ref_path, cur_path = refresh_baseline(raw_path=args.raw)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Reference baseline -> {ref_path}")
    print(f"Current snapshot   -> {cur_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
