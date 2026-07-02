#!/usr/bin/env python3
# Author: Member D — verification helper
# Purpose: Quick checklist that all Member D deliverables exist and core flows work

"""Verify Member D deliverables: files, drift check, and quality gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "infra/deploy_aks.py",
    "infra/k8s/deployment.yaml",
    "infra/k8s/service.yaml",
    "infra/setup_alerts.py",
    "src/monitoring/telemetry.py",
    "src/monitoring/drift.py",
    "src/monitoring/llm_prompts.py",
    "scripts/run_drift_check.py",
    "scripts/openrouter_report.py",
    ".github/workflows/deploy.yml",
    ".github/workflows/train.yml",
    ".github/workflows/drift-check.yml",
    "docs/architecture/README.md",
    "docs/stages/stage-09-monitoring.md",
    "docs/stages/stage-10-openrouter.md",
    "docs/azure-setup.md",
    "docs/demo-day.md",
    "configs/monitoring_config.yaml",
    "tests/test_monitoring.py",
]


def check_files() -> list[str]:
    """Return list of missing required files."""
    missing = []
    for rel in REQUIRED_FILES:
        if not (PROJECT_ROOT / rel).exists():
            missing.append(rel)
    return missing


def run_cmd(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=PROJECT_ROOT).returncode


def main() -> int:
    print("=== Member D verification ===\n")

    missing = check_files()
    if missing:
        print("MISSING FILES:")
        for path in missing:
            print(f"  - {path}")
        return 1
    print(f"OK: All {len(REQUIRED_FILES)} required files present.\n")

    print("--- Drift check ---")
    if run_cmd([sys.executable, "scripts/generate_sample_data.py", "--n-samples", "2000"]) != 0:
        return 1
    drift_rc = run_cmd([sys.executable, "scripts/run_drift_check.py"])
    print(f"Drift exit code: {drift_rc} (1 = drift detected, expected for demo data)\n")

    print("--- OpenRouter dry-run ---")
    if run_cmd([sys.executable, "scripts/train_model.py"]) != 0:
        return 1
    if run_cmd([sys.executable, "scripts/evaluate_model.py"]) != 0:
        return 1
    if run_cmd([sys.executable, "scripts/openrouter_report.py", "--dry-run"]) != 0:
        return 1

    print("\n--- pytest (monitoring) ---")
    if run_cmd([sys.executable, "-m", "pytest", "tests/test_monitoring.py", "-q", "--no-cov"]) != 0:
        return 1

    print("\n=== Member D verification PASSED ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
