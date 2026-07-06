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
from src.api.drift_service import ensure_drift_report, get_activity_report_dir, try_update_drift_after_activity
from src.api.openrouter_service import get_openrouter_report_path, read_openrouter_report, run_openrouter_report
from src.api.inference import features_from_request, predict_outage
from src.api.schemas import (
    DriftActivityStatus,
    OpenRouterReportResponse,
    OpenRouterRunResponse,
    UrlCheckRequest,
    UrlMetricsResponse,
)
from src.api.system_status import get_system_status
from src.api.url_checker import UrlValidationError, probe_url_metrics, validate_public_url
from src.api.url_check_history import append_entry, clear_history, list_history
from src.monitoring.observations import append_observation
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


def _activity_drift_html_path(root: Path) -> Path:
    """Prefer activity-triggered drift HTML, fallback to CLI report."""
    activity = root / "artifacts" / "reports" / "drift_report.html"
    if activity.exists():
        return activity
    return root / "reports" / "drift" / "drift_report.html"


def _activity_drift_summary_path(root: Path) -> Path:
    activity = root / "artifacts" / "reports" / "drift_summary.json"
    if activity.exists():
        return activity
    return root / "reports" / "drift" / "drift_summary.json"


def _build_nav_tabs(base_url: str, root: Path) -> str:
    """Convert legacy homepage links into modern tab-style navigation."""
    drift_html = _activity_drift_html_path(root)
    openrouter_eval = get_openrouter_report_path()
    openrouter_fail = root / "reports" / "openrouter" / "openrouter_failure_analysis.md"
    legacy_openrouter = root / "reports" / "openrouter" / "openrouter_eval_summary.md"

    tabs: list[tuple[str, str, bool]] = [
        ("Dashboard", "#dashboard", True),
        ("Demo Hub", f"{base_url}/demo", False),
        ("Architecture", f"{base_url}/demo/flow", False),
        ("System APIs", "#system-apis", True),
        ("Drift Summary", "#drift-summary", True),
        ("OpenRouter Summary", "#openrouter-summary", True),
    ]
    if _file_status(drift_html)["available"]:
        href = (
            f"{base_url}/artifacts/reports/drift_report.html"
            if "artifacts" in str(drift_html)
            else f"{base_url}/reports/drift/drift_report.html"
        )
        tabs.append(("Drift Report", href, False))
    if _file_status(openrouter_eval)["available"]:
        tabs.append(
            (
                "OpenRouter Report",
                f"{base_url}/artifacts/reports/openrouter_eval_summary.md",
                False,
            )
        )
    elif _file_status(legacy_openrouter)["available"]:
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

    tabs.append(("About", "#about", True))

    parts: list[str] = []
    for label, href, is_section in tabs:
        if is_section:
            css = "tab active" if href == "#dashboard" else "tab"
            parts.append(f'<a href="{href}" class="{css}" data-section>{label}</a>')
        else:
            parts.append(f'<a href="{href}" class="tab">{label}</a>')
    return "\n    ".join(parts)


def build_dashboard_html(base_url: str, root: Path) -> str:
    """Build the modern prediction dashboard."""
    drift_html = _activity_drift_html_path(root)
    drift_summary = _activity_drift_summary_path(root)
    openrouter_eval = get_openrouter_report_path()
    eval_metrics = root / "data" / "processed" / "eval_metrics.json"

    drift_status = _file_status(drift_html)
    openrouter_status = _file_status(openrouter_eval)
    if not openrouter_status["available"]:
        openrouter_status = {"available": False, "label": "Not generated"}
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

    if drift:
        drift_label = (
            f"drift_score {drift.get('drift_score', 0):.0%}"
            if drift.get("drift_detected")
            else "No drift detected"
        )
    else:
        drift_label = drift_status["label"]

    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("{{NAV_TABS}}", _build_nav_tabs(base_url, root))
        .replace("{{GATE_TEXT}}", gate_text)
        .replace("{{GATE_CLASS}}", gate_class)
        .replace("{{DRIFT_LABEL}}", drift_label if drift else str(drift_status["label"]))
        .replace("{{OPENROUTER_LABEL}}", openrouter_status["label"])
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
    activity_reports_dir = get_activity_report_dir()
    arch_dir = root / "docs" / "architecture" / "images"
    reports_dir.mkdir(parents=True, exist_ok=True)
    activity_reports_dir.mkdir(parents=True, exist_ok=True)

    if _STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def local_hub() -> HTMLResponse:
        return HTMLResponse(build_dashboard_html("http://127.0.0.1:8000", root))

    @app.get(
        "/drift",
        tags=["Monitoring"],
        summary="Get drift summary",
        description="Returns drift summary JSON, auto-generating the report if missing.",
    )
    def drift_summary() -> dict:
        return ensure_drift_report(force=False)

    @app.post(
        "/drift/run",
        tags=["Monitoring"],
        summary="Regenerate drift report",
        description="Force a new drift analysis and return the updated summary.",
    )
    def drift_run() -> dict:
        return ensure_drift_report(force=True)

    @app.get("/monitoring/eval-metrics", include_in_schema=False)
    def monitoring_eval_metrics() -> dict:
        path = root / "data" / "processed" / "eval_metrics.json"
        data = _read_json_safe(path)
        if data is None:
            return {"error": "eval_metrics.json not found — run scripts/evaluate_model.py"}
        return data

    @app.get("/monitoring/drift-summary", include_in_schema=False)
    def monitoring_drift_summary() -> dict:
        return ensure_drift_report(force=False)

    @app.get("/monitoring/status", include_in_schema=False)
    def monitoring_status() -> dict:
        eval_data = _read_json_safe(root / "data" / "processed" / "eval_metrics.json")
        drift_data = ensure_drift_report(force=False)
        return {
            "local_hub": "http://127.0.0.1:8000",
            "api_docs": "http://127.0.0.1:8000/docs",
            "health": "http://127.0.0.1:8000/health",
            "predict": "http://127.0.0.1:8000/predict",
            "gate_passed": eval_data.get("gate_passed") if eval_data else None,
            "eval_metrics": eval_data,
            "drift": drift_data,
            "reports": {
                "drift_html": "/artifacts/reports/drift_report.html",
                "openrouter_eval": "/artifacts/reports/openrouter_eval_summary.md",
            },
        }

    @app.post(
        "/reports/openrouter/run",
        response_model=OpenRouterRunResponse,
        tags=["Reports"],
        summary="Generate OpenRouter evaluation summary",
        description="Runs OpenRouter report generation (API or local fallback). Never exposes the API key.",
    )
    def openrouter_run() -> dict:
        return run_openrouter_report(force=True)

    @app.get(
        "/reports/openrouter",
        response_model=OpenRouterReportResponse,
        tags=["Reports"],
        summary="Get OpenRouter evaluation summary",
        description="Returns markdown report content and metadata if generated.",
    )
    def openrouter_get() -> dict:
        return read_openrouter_report()

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

    @app.post(
        "/check-url-metrics",
        response_model=UrlMetricsResponse,
        tags=["Website Health"],
        summary="Analyze a website URL using live response signals",
        description=(
            "Probes a public http or https URL with repeated GET requests and returns "
            "metrics (response time, status code, error rate, latency) suitable for "
            "POST /predict. Private or localhost URLs are rejected."
        ),
    )
    def check_url_metrics(payload: UrlCheckRequest) -> UrlMetricsResponse:
        try:
            url = validate_public_url(payload.url)
            result = probe_url_metrics(url)
            append_entry(url, result)

            state = get_state() if get_state else {}
            model = state.get("model")
            outage_predicted: bool | None = None
            outage_probability: float | None = None
            drift_status: DriftActivityStatus | None = None

            if model is not None:
                metrics_dict = result.model_dump()
                features = features_from_request(metrics_dict)
                prediction = predict_outage(model, features)
                outage_predicted = bool(prediction["outage_predicted"])
                outage_probability = float(prediction["outage_probability"])

                # Demo-triggered drift after URL check (non-blocking for probe response).
                try:
                    append_observation(
                        metrics_dict,
                        outage_predicted=outage_predicted,
                        outage_probability=outage_probability,
                        source="url_check",
                        url=url,
                    )
                    drift_status = DriftActivityStatus(**try_update_drift_after_activity())
                except Exception:
                    pass

            return result.model_copy(
                update={
                    "outage_predicted": outage_predicted,
                    "outage_probability": outage_probability,
                    "drift": drift_status,
                }
            )
        except UrlValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail="Could not reach the website. Check the URL and try again.",
            ) from exc

    @app.get("/url-check-history", include_in_schema=False)
    def url_check_history() -> dict:
        return {"items": list_history()}

    @app.delete("/url-check-history", include_in_schema=False)
    def url_check_history_clear() -> dict:
        clear_history()
        return {"items": []}

    # API routes under /reports/* must be registered before static mount.
    app.mount("/reports", StaticFiles(directory=str(reports_dir)), name="reports")
    app.mount(
        "/artifacts/reports",
        StaticFiles(directory=str(activity_reports_dir)),
        name="activity_reports",
    )
    if arch_dir.is_dir():
        app.mount("/architecture", StaticFiles(directory=str(arch_dir)), name="architecture")
