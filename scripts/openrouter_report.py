#!/usr/bin/env python3
# Author: Member D — OpenRouter LLM reporting
# Purpose: Generate human-readable evaluation and failure summaries via OpenRouter

"""Generate LLM evaluation and failure reports using OpenRouter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.api.openrouter_service import (  # noqa: E402
    DEFAULT_MODEL,
    build_local_fallback_report,
    collect_report_context,
    run_openrouter_report,
)
from src.monitoring.llm_prompts import build_eval_prompt, build_failure_prompt  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OpenRouter LLM reports")
    parser.add_argument(
        "--eval-metrics",
        type=Path,
        default=_PROJECT_ROOT / "data" / "processed" / "eval_metrics.json",
        help="Path to eval_metrics.json (used for dry-run context)",
    )
    parser.add_argument(
        "--drift-report",
        type=Path,
        default=None,
        help="Optional drift summary JSON override for dry-run display",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_PROJECT_ROOT / "artifacts" / "reports",
        help="Directory for markdown reports",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model slug")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompts without calling OpenRouter",
    )
    args = parser.parse_args()

    if args.dry_run:
        context = collect_report_context(_PROJECT_ROOT)
        metrics = context.get("metrics") or {}
        drift = context.get("drift")
        if not metrics and args.eval_metrics.exists():
            import json

            metrics = json.loads(args.eval_metrics.read_text(encoding="utf-8"))
        if args.drift_report and args.drift_report.exists():
            import json

            drift = json.loads(args.drift_report.read_text(encoding="utf-8"))
        print("=== Evaluation prompt ===")
        print(build_eval_prompt(metrics, drift))
        print("\n=== Failure analysis prompt ===")
        print(build_failure_prompt(metrics, drift))
        print("\n=== Local fallback preview ===")
        print(build_local_fallback_report(context))
        return 0

    result = run_openrouter_report(
        output_dir=args.output_dir,
        model=args.model,
        root=_PROJECT_ROOT,
    )
    print(f"Wrote {result['report_path']} ({result['source']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
