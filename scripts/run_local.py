#!/usr/bin/env python3
# Author: Member D — single local dev server
# Purpose: Start API + dashboard + reports on http://localhost:8000

"""Run the full local MLOps hub on one localhost port."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def run_step(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=_PROJECT_ROOT, check=False).returncode


def ensure_model(py: str, skip_setup: bool) -> bool:
    """Generate data and train model if artifact is missing."""
    if skip_setup:
        return True
    model_path = _PROJECT_ROOT / "models" / "outage_model.joblib"
    if model_path.exists():
        print(f"Model found: {model_path}")
        return True
    print("Model not found — generating data and training...")
    for script in ("scripts/generate_sample_data.py", "scripts/train_model.py"):
        if run_step([py, script]) != 0:
            return False
    return model_path.exists()


def print_banner(host: str, port: int) -> None:
    base = f"http://{host}:{port}"
    alt = f"http://localhost:{port}" if host == "127.0.0.1" else base
    print("\n" + "=" * 60)
    print("  Website Outage Predictor — Local Hub")
    print("=" * 60)
    print("\n  >>> SERVER IS RUNNING when you see:")
    print("      'Application startup complete' below.")
    print("  >>> Do NOT press Ctrl+C — that STOPS the server.")
    print("  >>> Open these links in your browser (Safari/Chrome):\n")
    print(f"  Dashboard:     {base}/")
    print(f"  Swagger UI:      {base}/docs")
    if alt != base:
        print(f"  (also works)     {alt}/docs")
    print(f"  Health:          {base}/health")
    print(f"  Predict (POST):  {base}/predict")
    print(f"  Drift report:    {base}/reports/drift/drift_report.html")
    print("\n  Test in a NEW terminal tab:")
    print(f"    curl {base}/health")
    print("\n  Press Ctrl+C in THIS window only when you want to stop.\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local hub on http://localhost:8000")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-reload", action="store_true")
    parser.add_argument("--skip-setup", action="store_true", help="Do not auto-train if model missing")
    args = parser.parse_args()

    py = sys.executable
    if not ensure_model(py, args.skip_setup):
        print("ERROR: Could not prepare model artifact.", file=sys.stderr)
        return 1

    print_banner(args.host, args.port)

    cmd = [
        py,
        "-m",
        "uvicorn",
        "src.api.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if not args.no_reload:
        cmd.append("--reload")

    return subprocess.run(cmd, cwd=_PROJECT_ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
