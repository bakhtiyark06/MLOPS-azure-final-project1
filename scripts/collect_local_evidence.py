#!/usr/bin/env python3
# Author: Member D — submission evidence collector
# Purpose: Copy local demo artifacts into docs/evidence/ for grading

"""Collect repo-ready submission evidence (no Azure screenshots)."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence"

# Source path relative to project root -> evidence filename
ARTIFACT_MAP: dict[str, str] = {
    "reports/drift/drift_report.html": "evidence-10-drift-report.html",
    "reports/drift/drift_summary.json": "evidence-10-drift-summary.json",
    "data/processed/eval_metrics.json": "evidence-06-quality-gate-pass.json",
    "reports/openrouter/openrouter_eval_summary.md": "evidence-12-openrouter-summary.md",
    "artifacts/reports/openrouter_eval_summary.md": "evidence-12-openrouter-summary-fallback.md",
    "data/raw/ingestion_metadata.json": "evidence-data-ingestion-metadata.json",
    "models/outage_model.joblib": "evidence-model-outage_model.joblib",
}


def collect() -> dict[str, str | bool]:
    """Copy known artifacts; return manifest of what was collected."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, str | bool] = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "evidence_dir": str(EVIDENCE_DIR.relative_to(PROJECT_ROOT)),
    }
    for rel_src, dest_name in ARTIFACT_MAP.items():
        src = PROJECT_ROOT / rel_src
        dest = EVIDENCE_DIR / dest_name
        if src.exists():
            if src.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
            manifest[dest_name] = "ok"
        else:
            manifest[dest_name] = "missing"
    manifest_path = EVIDENCE_DIR / "evidence-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    manifest = collect()
    ok = sum(1 for k, v in manifest.items() if v == "ok")
    print(f"Collected {ok} evidence artifact(s) -> {EVIDENCE_DIR}")
    for name, status in manifest.items():
        if name in ("collected_at", "evidence_dir"):
            continue
        print(f"  {name}: {status}")
    print(f"Manifest: docs/evidence/evidence-manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
