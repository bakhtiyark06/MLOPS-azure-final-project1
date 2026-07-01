# Author: Member A — data generation script
# Purpose: Generate synthetic website monitoring dataset for local dev and demos

"""Generate synthetic website monitoring CSV for outage prediction training."""

import argparse  # CLI argument parsing
import sys  # Exit codes for quality gate integration
from pathlib import Path  # Output file paths

# Add project root to Python path when running as a script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np  # Random number generation for synthetic data
import pandas as pd  # DataFrame and CSV export

from src.data.validate_data import validate_raw_dataframe  # Validate schema after generation
from src.utils.config import get_project_root, load_yaml_config


def generate_monitoring_data(n_samples: int = 2000, random_state: int = 42) -> pd.DataFrame:
    """
    Create synthetic monitoring records with realistic outage labels.

    Outage label (outage_within_1h) is correlated with high error_rate,
    high latency, non-200 status codes, and high resource usage.

    Args:
        n_samples: Number of rows to generate.
        random_state: RNG seed for reproducibility.

    Returns:
        DataFrame with features and outage_within_1h target column.
    """
    # Seeded RNG for reproducible dataset across team members
    rng = np.random.default_rng(random_state)
    # Simulate HTTP response times (ms) — log-normal distribution
    response_time_ms = rng.lognormal(mean=4.5, sigma=0.5, size=n_samples)
    # Clip to realistic range 50ms – 10000ms
    response_time_ms = np.clip(response_time_ms, 50, 10000)
    # Base error rate before outage correlation
    error_rate = rng.beta(2, 20, size=n_samples)
    # P95 latency typically higher than mean response time
    latency_p95_ms = response_time_ms * rng.uniform(1.2, 3.0, size=n_samples)
    # Request volume per measurement window
    request_count = rng.integers(100, 10000, size=n_samples)
    # CPU and memory utilization percentages
    cpu_usage_percent = rng.uniform(10, 95, size=n_samples)
    memory_usage_percent = rng.uniform(20, 90, size=n_samples)
    # Mostly 200 OK; occasional 4xx/5xx
    status_code = np.where(
        rng.random(n_samples) < 0.85,
        200,
        rng.choice([500, 502, 503, 404], size=n_samples),
    )
    # Compute outage risk score from monitoring signals
    risk_score = (
        (error_rate * 5)
        + (response_time_ms / 2000)
        + (latency_p95_ms / 3000)
        + ((status_code != 200).astype(float) * 2)
        + (cpu_usage_percent / 100)
        + (memory_usage_percent / 100)
    )
    # Binary target: outage likely within 1 hour if risk exceeds threshold
    outage_within_1h = (risk_score > rng.uniform(1.5, 2.5, size=n_samples)).astype(int)
    # For rows labeled outage, push metrics into unhealthy ranges
    mask = outage_within_1h == 1
    error_rate[mask] = np.clip(error_rate[mask] + 0.15, 0, 1)
    response_time_ms[mask] *= 1.5
    status_code[mask] = np.where(rng.random(mask.sum()) < 0.6, 500, status_code[mask])
    # Assemble DataFrame with config-aligned column names
    df = pd.DataFrame(
        {
            "response_time_ms": response_time_ms,
            "status_code": status_code,
            "error_rate": error_rate,
            "latency_p95_ms": latency_p95_ms,
            "request_count": request_count,
            "cpu_usage_percent": cpu_usage_percent,
            "memory_usage_percent": memory_usage_percent,
            "outage_within_1h": outage_within_1h,
        }
    )
    return df


def main() -> int:
    """
    CLI entrypoint: write synthetic CSV to data/raw/ and data/reference/.

    Returns:
        0 on success.
    """
    # Parse optional sample count from command line
    parser = argparse.ArgumentParser(description="Generate synthetic monitoring data")
    parser.add_argument("--n-samples", type=int, default=2000, help="Number of rows")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV path (default: data/raw/website_monitoring.csv)",
    )
    args = parser.parse_args()
    # Load data config for default sample count and output paths
    data_cfg = load_yaml_config("data_config.yaml")
    n_samples = args.n_samples or int(data_cfg.get("default_sample_count", 2000))
    # Generate synthetic dataset
    df = generate_monitoring_data(n_samples=n_samples)
    # Validate generated data matches expected schema before writing
    is_valid, errors = validate_raw_dataframe(df)
    if not is_valid:
        print("Generated data failed validation:")
        for err in errors:
            print(f"  - {err}")
        return 1
    # Resolve output path
    root = get_project_root()
    raw_name = data_cfg.get("raw_filename", "website_monitoring.csv")
    output_path = Path(args.output) if args.output else root / "data" / "raw" / raw_name
    # Ensure parent directory exists (gitignored data/raw/)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Write main training dataset
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} rows -> {output_path}")
    # Save reference rows as baseline for Evidently drift (Member D uses this)
    ref_rows = int(data_cfg.get("reference_rows", 500))
    ref_path = root / "data" / "reference" / "reference.csv"
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    df.head(ref_rows).to_csv(ref_path, index=False)
    print(f"Reference baseline ({ref_rows} rows) -> {ref_path}")
    # Save tail as current snapshot for drift demo
    cur_rows = int(data_cfg.get("current_snapshot_rows", 300))
    cur_path = root / "data" / "processed" / "current.csv"
    cur_path.parent.mkdir(parents=True, exist_ok=True)
    df.tail(cur_rows).to_csv(cur_path, index=False)
    print(f"Current snapshot ({cur_rows} rows) -> {cur_path}")
    return 0


if __name__ == "__main__":
  # Run main when executed as python scripts/generate_sample_data.py
    sys.exit(main())
