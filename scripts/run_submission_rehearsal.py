#!/usr/bin/env python3
# Author: Member D — submission rehearsal runner
# Purpose: Run full local pipeline and collect evidence before demo day

"""One-command local submission rehearsal (pipeline + tests + evidence)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PIPELINE_STEPS: list[tuple[str, list[str]]] = [
    ("Setup DVC (local)", ["scripts/setup_dvc.py", "--skip-remote"]),
    ("Generate data", ["scripts/generate_sample_data.py"]),
    ("Ingest data", ["scripts/ingest_data.py", "--skip-blob"]),
    ("Train model", ["scripts/train_model.py"]),
    ("Evaluate / quality gate", ["scripts/evaluate_model.py"]),
    ("Registry dry-run", ["scripts/register_model.py", "--dry-run"]),
    ("Drift check", ["scripts/run_drift_check.py"]),
    ("OpenRouter dry-run", ["scripts/openrouter_report.py", "--dry-run"]),
]


def run_step(py: str, script_args: list[str]) -> int:
    cmd = [py, *script_args]
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=PROJECT_ROOT).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local submission rehearsal")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-evidence", action="store_true")
    parser.add_argument(
        "--allow-drift-fail",
        action="store_true",
        help="Do not fail rehearsal when drift exits 1 (expected on demo data)",
    )
    args = parser.parse_args()
    py = sys.executable

    print("=" * 60)
    print("  Submission rehearsal — local pipeline")
    print("=" * 60)

    for label, script_args in PIPELINE_STEPS:
        print(f"\n--- {label} ---")
        rc = run_step(py, script_args)
        if label.startswith("Drift") and rc == 1 and args.allow_drift_fail:
            print("Drift detected (exit 1) — expected for demo data; continuing.")
            continue
        if rc != 0:
            print(f"FAILED: {label} (exit {rc})", file=sys.stderr)
            return rc

    if not args.skip_tests:
        print("\n--- pytest ---")
        rc = run_step(py, ["-m", "pytest", "-q", "--no-cov"])
        if rc != 0:
            return rc

    if not args.skip_evidence:
        print("\n--- Collect local evidence ---")
        rc = run_step(py, ["scripts/collect_local_evidence.py"])
        if rc != 0:
            return rc
        run_step(py, ["scripts/audit_python_docs.py"])

    print("\n" + "=" * 60)
    print("  Local rehearsal COMPLETE")
    print("=" * 60)
    print("\nRepo-ready evidence: docs/evidence/")
    print("Still manual / Azure phase:")
    print("  - GitHub: PR history, branch protection, release v1.0.0")
    print("  - Azure: ML logs, registry, ACR, AKS, Monitor alert screenshots")
    print("  - Run: scripts/setup_azure_env.ps1 then scripts/run_azure_phase2.ps1")
    print("\nStart dashboard: py scripts/run_local.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
