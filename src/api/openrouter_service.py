# Author: Member D — OpenRouter API service
# Purpose: Generate evaluation summaries via OpenRouter or local fallback

"""API-facing OpenRouter report orchestration."""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from src.api.drift_service import get_activity_report_dir
from src.monitoring.llm_prompts import build_eval_prompt, build_failure_prompt
from src.utils.config import get_project_root

logger = logging.getLogger(__name__)

OPENROUTER_URL = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"
)
DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

REPORT_FILENAME = "openrouter_eval_summary.md"
META_FILENAME = "openrouter_eval_summary.meta.json"
FAILURE_FILENAME = "openrouter_failure_analysis.md"

_openrouter_lock = threading.Lock()

FALLBACK_DISCLAIMER = (
    "OpenRouter API key was not configured, so this report was generated locally."
)


def get_openrouter_report_path() -> Path:
    """Return canonical OpenRouter markdown path under artifacts/reports."""
    return get_activity_report_dir() / REPORT_FILENAME


def get_openrouter_meta_path() -> Path:
    """Return sidecar JSON path for report metadata."""
    return get_activity_report_dir() / META_FILENAME


def _read_json_safe(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _first_existing(*paths: Path) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def collect_report_context(root: Path | None = None) -> dict[str, Any]:
    """
    Load eval metrics, drift summary, drift HTML status, and dataset hash.

    Uses activity-triggered paths first, then legacy batch paths.
    """
    root = root or get_project_root()
    activity_dir = root / "artifacts" / "reports"

    drift_summary_path = _first_existing(
        activity_dir / "drift_summary.json",
        root / "reports" / "drift" / "drift_summary.json",
    )
    drift_html_path = _first_existing(
        activity_dir / "drift_report.html",
        root / "reports" / "drift" / "drift_report.html",
    )
    eval_path = _first_existing(
        root / "data" / "processed" / "eval_metrics.json",
        root / "reports" / "metrics.json",
    )

    metrics = _read_json_safe(eval_path) if eval_path else None
    drift = _read_json_safe(drift_summary_path) if drift_summary_path else None

    dataset_hash: str | None = None
    hash_file = root / "data" / "raw" / "dataset_hash.txt"
    if hash_file.exists():
        try:
            dataset_hash = hash_file.read_text(encoding="utf-8").strip()
        except OSError:
            dataset_hash = None
    if not dataset_hash:
        meta = _read_json_safe(root / "data" / "raw" / "ingestion_metadata.json")
        if meta:
            dataset_hash = meta.get("dataset_hash")

    drifted_columns: list[str] = []
    if drift:
        drifted_columns = list(drift.get("drifted_columns") or [])
        if not drifted_columns and drift.get("column_drifts"):
            drifted_columns = [
                k for k, v in drift["column_drifts"].items() if v.get("drifted")
            ]

    return {
        "metrics": metrics,
        "drift": drift,
        "dataset_hash": dataset_hash,
        "drift_html_available": drift_html_path is not None,
        "drift_summary_path": str(drift_summary_path) if drift_summary_path else None,
        "eval_metrics_path": str(eval_path) if eval_path else None,
        "drifted_columns": drifted_columns,
    }


def call_openrouter(prompt: str, *, model: str, api_key: str) -> str:
    """Send a chat completion request to OpenRouter."""
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
        raise RuntimeError("OpenRouter returned no choices")

    content = choices[0].get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("OpenRouter returned empty content")
    return content


def _fmt(value: Any, default: str = "—") -> str:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return "PASSED" if value else "FAILED"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _deployment_recommendation(metrics: dict[str, Any] | None, drift: dict[str, Any] | None) -> str:
    gate = metrics.get("gate_passed") if metrics else None
    drift_detected = False
    if drift:
        drift_detected = bool(drift.get("drift_detected") or drift.get("dataset_drift"))

    if gate is False:
        return "Do not deploy — quality gate failed. Retrain or fix data before release."
    if drift_detected:
        return "Hold deployment — investigate drifted features and refresh baseline if needed."
    if gate is True:
        return "Proceed with deployment — metrics meet thresholds and no drift detected."
    return "Run evaluation and drift checks before deployment."


def build_local_fallback_report(context: dict[str, Any]) -> str:
    """Build deterministic markdown when OpenRouter API is unavailable."""
    metrics = context.get("metrics") or {}
    drift = context.get("drift") or {}
    drifted = context.get("drifted_columns") or []

    accuracy = metrics.get("accuracy", metrics.get("test_accuracy"))
    f1 = metrics.get("f1_score", metrics.get("f1_macro", metrics.get("test_f1_macro")))
    gate = metrics.get("gate_passed")
    gate_reasons = metrics.get("gate_failure_reasons", [])

    drift_detected = drift.get("drift_detected") or drift.get("dataset_drift")
    drift_score = drift.get("drift_score")
    drift_summary = drift.get("summary", "—")

    risks: list[str] = []
    if gate is False:
        risks.append("Quality gate failed — model may not meet production thresholds.")
    if drift_detected:
        risks.append("Data drift detected — feature distributions may have shifted.")
    if not metrics:
        risks.append("Evaluation metrics unavailable — run scripts/evaluate_model.py.")
    if not drift:
        risks.append("Drift summary unavailable — run drift analysis or demo predictions.")
    if not risks:
        risks.append("No critical risks identified from available artifacts.")

    next_actions: list[str] = []
    if gate is False:
        next_actions.append("Review gate_failure_reasons and retrain or adjust thresholds.")
    if drift_detected:
        next_actions.append("Investigate drifted columns and refresh reference baseline if needed.")
    if gate is True and not drift_detected:
        next_actions.append("Continue monitoring and schedule periodic drift checks.")
    if not next_actions:
        next_actions.append("Generate eval metrics and drift summary, then regenerate this report.")

    lines = [
        FALLBACK_DISCLAIMER,
        "",
        "## Executive Summary",
        "",
        "Local MLOps evaluation summary compiled from project artifacts "
        "(eval metrics, drift summary, dataset hash).",
        "",
        "## Model Metrics",
        "",
        f"- **Accuracy:** {_fmt(accuracy)}",
        f"- **F1 Score:** {_fmt(f1)}",
        f"- **Quality Gate:** {_fmt(gate)}",
        "",
        "## Dataset",
        "",
        f"- **Dataset Hash:** {_fmt(context.get('dataset_hash'))}",
        "",
        "## Drift Status",
        "",
        f"- **Drift Detected:** {_fmt(drift_detected)}",
        f"- **Drift Score:** {_fmt(drift_score)}",
        f"- **Drift Summary:** {drift_summary}",
        f"- **Drift HTML Report:** {'available' if context.get('drift_html_available') else 'not generated'}",
        "",
        "## Drifted Columns",
        "",
    ]
    if drifted:
        lines.extend(f"- {col}" for col in drifted)
    else:
        lines.append("- None identified")

    lines.extend(
        [
            "",
            "## Deployment Recommendation",
            "",
            _deployment_recommendation(metrics, drift),
            "",
            "## Risks",
            "",
        ]
    )
    lines.extend(f"- {r}" for r in risks)

    if gate_reasons:
        lines.extend(["", "### Gate Failure Reasons", ""])
        lines.extend(f"- {r}" for r in gate_reasons)

    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {a}" for a in next_actions)

    return "\n".join(lines)


def _write_markdown(path: Path, body: str, *, title: str = "Evaluation Summary") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")


def _write_meta(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _preview_text(content: str, max_len: int = 300) -> str:
    flat = " ".join(content.split())
    if len(flat) <= max_len:
        return flat
    return flat[: max_len - 3] + "..."


def read_openrouter_report() -> dict[str, Any]:
    """Return report content and metadata, or a helpful missing message."""
    report_path = get_openrouter_report_path()
    meta_path = get_openrouter_meta_path()

    if not report_path.exists():
        return {
            "exists": False,
            "message": "OpenRouter report not found. Run POST /reports/openrouter/run to generate.",
            "report_path": str(report_path),
        }

    content = report_path.read_text(encoding="utf-8")
    meta = _read_json_safe(meta_path) or {}

    return {
        "exists": True,
        "content": content,
        "report_path": str(report_path),
        "generated_at": meta.get("generated_at"),
        "source": meta.get("source", "unknown"),
        "openrouter_api_used": meta.get("openrouter_api_used", False),
        "preview": meta.get("preview") or _preview_text(content),
        "message": meta.get("message", "Report available."),
    }


def run_openrouter_report(
    *,
    force: bool = False,
    output_dir: Path | None = None,
    model: str | None = None,
    root: Path | None = None,
    write_failure_report: bool = True,
) -> dict[str, Any]:
    """
    Generate OpenRouter eval summary (API or local fallback).

    Never raises for missing API key — writes local fallback instead.
    """
    del force  # reserved for future cache-skip logic
    root = root or get_project_root()
    out_dir = output_dir or get_activity_report_dir()
    report_path = out_dir / REPORT_FILENAME
    meta_path = out_dir / META_FILENAME
    model = model or DEFAULT_MODEL

    context = collect_report_context(root)
    metrics = context.get("metrics") or {}
    drift = context.get("drift")

    generated_at = datetime.now(timezone.utc).isoformat()
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

    with _openrouter_lock:
        source = "local_fallback"
        openrouter_api_used = False
        message = "Report generated locally (no API key)."

        if api_key:
            try:
                prompt = build_eval_prompt(metrics, drift)
                body = call_openrouter(prompt, model=model, api_key=api_key)
                source = "openrouter"
                openrouter_api_used = True
                message = "Report generated via OpenRouter API."

                if write_failure_report and (
                    metrics.get("gate_passed") is False or metrics.get("force_fail_demo")
                ):
                    try:
                        failure_prompt = build_failure_prompt(metrics, drift)
                        failure_body = call_openrouter(
                            failure_prompt, model=model, api_key=api_key
                        )
                        _write_markdown(
                            out_dir / FAILURE_FILENAME,
                            failure_body,
                            title="Failure Analysis",
                        )
                    except (httpx.HTTPError, RuntimeError) as exc:
                        logger.warning("Failure analysis report skipped: %s", exc)

            except (httpx.HTTPError, RuntimeError) as exc:
                logger.warning("OpenRouter API failed, using local fallback: %s", exc)
                body = build_local_fallback_report(context)
                message = f"OpenRouter request failed; local fallback used. ({type(exc).__name__})"
        else:
            body = build_local_fallback_report(context)

        _write_markdown(report_path, body)

        preview = _preview_text(body)
        meta = {
            "generated_at": generated_at,
            "source": source,
            "report_path": str(report_path),
            "openrouter_api_used": openrouter_api_used,
            "preview": preview,
            "message": message,
        }
        _write_meta(meta_path, meta)

    return {
        "success": True,
        "report_path": str(report_path),
        "generated_at": generated_at,
        "source": source,
        "openrouter_api_used": openrouter_api_used,
        "preview": preview,
        "message": message,
        "exists": True,
    }
