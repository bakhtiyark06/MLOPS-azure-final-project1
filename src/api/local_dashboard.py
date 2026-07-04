# Author: Member D — local dev hub
# Purpose: Single localhost entry point for API, docs, drift, and OpenRouter reports

"""Local dashboard routes and static report serving."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import httpx

from src.api.config import ApiSettings
from src.api.demo_pipeline import run_local_pipeline
from src.api.schemas import UrlCheckRequest, UrlMetricsResponse
from src.api.system_status import get_system_status
from src.api.url_checker import UrlValidationError, probe_url_metrics, validate_public_url
from src.utils.config import get_project_root

_TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "dashboard.html"
_STATIC_DIR = Path(__file__).resolve().parent / "static"


def _file_status(path: Path) -> dict[str, str | bool]:
    """Return availability and label for a report artifact."""
    if path.exists():
        try:
            size_kb = max(1, path.stat().st_size // 1024)
            return {"available": True, "label": f"{path.name} ({size_kb} KB)"}
        except OSError:
            return {"available": True, "label": path.name}
    return {"available": False, "label": f"{path.name} (not generated yet)"}


def _read_json_safe(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _build_nav_tabs(base_url: str, root: Path) -> str:
    """Convert legacy homepage links into modern tab-style navigation."""
    drift_html = root / "reports" / "drift" / "drift_report.html"
    openrouter_eval = root / "reports" / "openrouter" / "openrouter_eval_summary.md"
    openrouter_fail = root / "reports" / "openrouter" / "openrouter_failure_analysis.md"
    arch_img = root / "docs" / "architecture" / "images" / "03-drift-alert-openrouter.png"

    tabs: list[tuple[str, str, bool]] = [
        ("Overview", "#system-status", True),
        ("Pipeline", "#pipeline", True),
        ("URL Check", "#url-check", True),
        ("Predict", "#predict", True),
        ("Swagger UI", f"{base_url}/docs", False),
        ("Health Check", f"{base_url}/health", False),
        ("Eval Metrics", f"{base_url}/monitoring/eval-metrics", False),
        ("Drift Summary", f"{base_url}/monitoring/drift-summary", False),
        ("Combined Status", f"{base_url}/monitoring/status", False),
    ]
    if _file_status(drift_html)["available"]:
        tabs.append(
            ("Drift Report", f"{base_url}/reports/drift/drift_report.html", False)
        )
    if _file_status(openrouter_eval)["available"]:
        tabs.append(
            (
                "OpenRouter Report",
                f"{base_url}/reports/openrouter/openrouter_eval_summary.md",
                False,
            )
        )
    if _file_status(openrouter_fail)["available"]:
        tabs.append(
            (
                "OpenRouter Failure",
                f"{base_url}/reports/openrouter/openrouter_failure_analysis.md",
                False,
            )
        )
    if _file_status(arch_img)["available"]:
        tabs.append(
            (
                "Architecture",
                f"{base_url}/architecture/03-drift-alert-openrouter.png",
                False,
            )
        )

    parts: list[str] = []
    for label, href, is_section in tabs:
        if is_section:
            css = "tab active" if href == "#system-status" else "tab"
            parts.append(f'<a href="{href}" class="{css}" data-section>{label}</a>')
        else:
            parts.append(f'<a href="{href}" class="tab">{label}</a>')
    return "\n    ".join(parts)


def build_dashboard_html(base_url: str, root: Path) -> str:
    """Build the modern prediction dashboard."""
    drift_html = root / "reports" / "drift" / "drift_report.html"
    drift_summary = root / "reports" / "drift" / "drift_summary.json"
    openrouter_eval = root / "reports" / "openrouter" / "openrouter_eval_summary.md"
    eval_metrics = root / "data" / "processed" / "eval_metrics.json"

    drift_status = _file_status(drift_html)
    openrouter_status = _file_status(openrouter_eval)
    metrics = _read_json_safe(eval_metrics) or {}
    drift = _read_json_safe(drift_summary) or {}

    gate = metrics.get("gate_passed")
    if gate is True:
        gate_text = "PASSED"
        gate_class = "ok"
    elif gate is False:
        gate_text = "FAILED"
        gate_class = "warn"
    else:
        gate_text = "unknown"
        gate_class = ""

    drift_summary_text = drift.get("summary", "Run drift check to generate summary")

    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("{{NAV_TABS}}", _build_nav_tabs(base_url, root))
        .replace("{{GATE_TEXT}}", gate_text)
        .replace("{{GATE_CLASS}}", gate_class)
        .replace("{{DRIFT_LABEL}}", drift_status["label"])
        .replace("{{OPENROUTER_LABEL}}", openrouter_status["label"])
        .replace("{{DRIFT_SUMMARY}}", drift_summary_text)
    )


def register_local_dashboard(
    app: FastAPI,
    *,
    get_state: Callable[[], dict[str, Any]] | None = None,
    reload_model: Callable[[], None] | None = None,
    settings: ApiSettings | None = None,
) -> None:
    """Attach dashboard home page, monitoring JSON routes, and static report mounts."""
    root = get_project_root()
    api_settings = settings or ApiSettings()
    reports_dir = root / "reports"
    arch_dir = root / "docs" / "architecture" / "images"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if _STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def local_hub() -> HTMLResponse:
        return HTMLResponse(build_dashboard_html("http://127.0.0.1:8000", root))

    @app.get("/monitoring/eval-metrics", include_in_schema=False)
    def monitoring_eval_metrics() -> dict:
        path = root / "data" / "processed" / "eval_metrics.json"
        data = _read_json_safe(path)
        if data is None:
            return {"error": "eval_metrics.json not found — run scripts/evaluate_model.py"}
        return data

    @app.get("/monitoring/drift-summary", include_in_schema=False)
    def monitoring_drift_summary() -> dict:
        path = root / "reports" / "drift" / "drift_summary.json"
        data = _read_json_safe(path)
        if data is None:
            return {"error": "drift_summary.json not found — run scripts/run_drift_check.py"}
        return data

    @app.get("/monitoring/status", include_in_schema=False)
    def monitoring_status() -> dict:
        eval_data = _read_json_safe(root / "data" / "processed" / "eval_metrics.json")
        drift_data = _read_json_safe(root / "reports" / "drift" / "drift_summary.json")
        return {
            "local_hub": "http://127.0.0.1:8000",
            "api_docs": "http://127.0.0.1:8000/docs",
            "health": "http://127.0.0.1:8000/health",
            "predict": "http://127.0.0.1:8000/predict",
            "gate_passed": eval_data.get("gate_passed") if eval_data else None,
            "eval_metrics": eval_data,
            "drift": drift_data,
            "reports": {
                "drift_html": "/reports/drift/drift_report.html",
                "openrouter_eval": "/reports/openrouter/openrouter_eval_summary.md",
            },
        }

    @app.get("/system-status", include_in_schema=False)
    def system_status() -> dict:
        state = get_state() if get_state else {}
        model_loaded = state.get("model") is not None
        api_status = "ok" if model_loaded else "degraded"
        return get_system_status(
            model_loaded=model_loaded,
            api_status=api_status,
            model_path=api_settings.model_path,
        )

    @app.post("/run-local-pipeline", include_in_schema=False)
    def run_local_pipeline_endpoint() -> dict:
        return run_local_pipeline(reload_model=reload_model)

    @app.post("/check-url-metrics", response_model=UrlMetricsResponse, include_in_schema=False)
    def check_url_metrics(payload: UrlCheckRequest) -> UrlMetricsResponse:
        try:
            url = validate_public_url(payload.url)
            return probe_url_metrics(url)
        except UrlValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail="Could not reach the website. Check the URL and try again.",
            ) from exc

    app.mount("/reports", StaticFiles(directory=str(reports_dir)), name="reports")
    if arch_dir.is_dir():
        app.mount("/architecture", StaticFiles(directory=str(arch_dir)), name="architecture")
