#!/usr/bin/env python3
# Author: Member D — post-drift remediation pipeline
# Purpose: Retrain, refresh baseline, re-check drift, verify monitoring

"""Execute recommended MLOps follow-ups after drift detection."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _python_executable() -> str:
    """Prefer Python 3.10+ (PEP 604 union types in src.models.evaluate)."""
    for candidate in ("python3.12", "python3.11", "python3"):
        import shutil

        path = shutil.which(candidate)
        if not path:
            continue
        try:
            out = subprocess.run(
                [path, "-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"],
                capture_output=True,
                check=False,
            )
            if out.returncode == 0:
                return path
        except OSError:
            continue
    return sys.executable


def run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=_PROJECT_ROOT, check=False).returncode


def check_url(url: str) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            body = resp.read().decode("utf-8")[:200]
            return resp.status == 200, body
    except (urllib.error.URLError, TimeoutError) as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run post-drift remediation steps")
    parser.add_argument("--production-url", default="http://20.84.194.181")
    parser.add_argument("--skip-deploy", action="store_true")
    args = parser.parse_args()

    py = _python_executable()
    print(f"Using Python: {py}")
    steps: list[tuple[str, int]] = []

    print("=== Step 1: Investigate drift (pre-remediation) ===")
    rc = run([py, "scripts/investigate_drift.py", "--run-drift-first"])
    steps.append(("investigate_drift_pre", rc))

    print("\n=== Step 2: Retrain on fresh data ===")
    for cmd in [
        [py, "scripts/generate_sample_data.py", "--n-samples", "2000"],
        [py, "scripts/train_model.py"],
        [py, "scripts/evaluate_model.py"],
    ]:
        rc = run(cmd)
        if rc != 0:
            print(f"ERROR: command failed with exit {rc}", file=sys.stderr)
            return rc
    steps.append(("retrain", 0))

    eval_path = _PROJECT_ROOT / "data" / "processed" / "eval_metrics.json"
    metrics = json.loads(eval_path.read_text(encoding="utf-8"))
    if not metrics.get("gate_passed"):
        print("ERROR: Quality gate failed after retrain", file=sys.stderr)
        return 1

    print("\n=== Step 3: Refresh baseline & re-run drift check ===")
    rc = run([py, "scripts/refresh_drift_baseline.py"])
    if rc != 0:
        return rc
    rc = run([py, "scripts/run_drift_check.py"])
    steps.append(("post_retrain_drift_check", rc))
    run([py, "scripts/investigate_drift.py"])

    print("\n=== Step 4: Verify production monitoring ===")
    health_url = f"{args.production_url.rstrip('/')}/health"
    ok, body = check_url(health_url)
    print(f"Production health ({health_url}): {'OK' if ok else 'FAIL'}")
    if ok:
        print(f"  Response: {body}")
    steps.append(("production_health", 0 if ok else 1))

    predict_url = f"{args.production_url.rstrip('/')}/predict"
    try:
        import httpx

        payload = {
            "response_time_ms": 850,
            "status_code": 500,
            "error_rate": 0.12,
            "latency_p95_ms": 1200,
            "request_count": 4200,
            "cpu_usage_percent": 78,
            "memory_usage_percent": 81,
        }
        resp = httpx.post(predict_url, json=payload, timeout=15.0)
        print(f"Production predict: {resp.status_code} {resp.text[:120]}")
        steps.append(("production_predict", 0 if resp.status_code == 200 else 1))
    except Exception as exc:
        print(f"Production predict failed: {exc}", file=sys.stderr)
        steps.append(("production_predict", 1))

    if not args.skip_deploy:
        print("\n=== Step 5: Optional redeploy (requires .env + Azure) ===")
        env_file = _PROJECT_ROOT / ".env"
        if env_file.exists():
            print("Run manually if needed: python infra/deploy_aks.py --wait-health")
        else:
            print("Skipped — no .env found for Azure deploy")

    print("\n=== Step 6: Write remediation log ===")
    log = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "steps": {name: ("pass" if code == 0 else "fail") for name, code in steps},
        "eval_metrics": metrics,
        "drift_after_retrain_exit_code": steps[-3][1] if len(steps) >= 3 else None,
        "production_url": args.production_url,
    }
    log_path = _PROJECT_ROOT / "reports" / "drift" / "remediation_log.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"Remediation log: {log_path}")

    failed = [name for name, code in steps if code != 0 and name != "investigate_drift_pre"]
    if failed:
        print(f"\nCompleted with warnings: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("\nAll remediation steps completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
