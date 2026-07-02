#!/usr/bin/env python3
# Author: Member D — OpenRouter LLM reporting
# Purpose: Generate human-readable evaluation and failure summaries via OpenRouter

"""Generate LLM evaluation and failure reports using OpenRouter."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.models.evaluate import read_eval_metrics
from src.monitoring.llm_prompts import build_eval_prompt, build_failure_prompt
from src.utils.secrets import get_openrouter_api_key

OPENROUTER_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions")
DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")


def load_drift_summary(path: Path | None) -> dict[str, Any] | None:
    """Load optional drift summary JSON."""
    if path is None or not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def call_openrouter(prompt: str, *, model: str, api_key: str) -> str:
    """
    Send a chat completion request to OpenRouter.

    Args:
        prompt: User message content.
        model: OpenRouter model slug.
        api_key: OpenRouter API key.

    Returns:
        Assistant message content.

    Raises:
        RuntimeError: On HTTP or API errors.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/MLOPS-azure-final-project1",
        "X-Title": "Website Outage Prediction MLOps",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(OPENROUTER_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(f"OpenRouter returned no choices: {data}")

    message = choices[0].get("message", {})
    content = message.get("content", "").strip()
    if not content:
        raise RuntimeError("OpenRouter returned empty content")
    return content


def write_report(path: Path, content: str, title: str) -> None:
    """Write markdown report to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = f"# {title}\n\n{content}\n"
    path.write_text(body, encoding="utf-8")
    print(f"Wrote {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OpenRouter LLM reports")
    parser.add_argument(
        "--eval-metrics",
        type=Path,
        default=_PROJECT_ROOT / "data" / "processed" / "eval_metrics.json",
        help="Path to eval_metrics.json",
    )
    parser.add_argument(
        "--drift-report",
        type=Path,
        default=_PROJECT_ROOT / "reports" / "drift" / "drift_summary.json",
        help="Optional drift summary JSON from run_drift_check.py",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_PROJECT_ROOT / "reports" / "openrouter",
        help="Directory for markdown reports",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model slug")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompts without calling OpenRouter",
    )
    args = parser.parse_args()

    try:
        metrics = read_eval_metrics(args.eval_metrics)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    drift = load_drift_summary(args.drift_report)

    eval_prompt = build_eval_prompt(metrics, drift)
    failure_prompt = build_failure_prompt(metrics, drift)

    if args.dry_run:
        print("=== Evaluation prompt ===")
        print(eval_prompt)
        print("\n=== Failure analysis prompt ===")
        print(failure_prompt)
        return 0

    try:
        api_key = get_openrouter_api_key()
    except EnvironmentError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        eval_content = call_openrouter(eval_prompt, model=args.model, api_key=api_key)
        write_report(args.output_dir / "openrouter_eval_summary.md", eval_content, "Evaluation Summary")

        if not metrics.get("gate_passed") or metrics.get("force_fail_demo"):
            failure_content = call_openrouter(failure_prompt, model=args.model, api_key=api_key)
            write_report(
                args.output_dir / "openrouter_failure_analysis.md",
                failure_content,
                "Failure Analysis",
            )
        else:
            print("Gate passed — skipping failure analysis report")
    except (httpx.HTTPError, RuntimeError) as exc:
        print(f"ERROR: OpenRouter request failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
