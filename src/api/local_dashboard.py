# Author: Member D — local dev hub
# Purpose: Single localhost entry point for API, docs, drift, and OpenRouter reports

"""Local dashboard routes and static report serving."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.utils.config import get_project_root


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


def build_dashboard_html(base_url: str, root: Path) -> str:
    """Build the local hub landing page."""
    drift_html = root / "reports" / "drift" / "drift_report.html"
    drift_summary = root / "reports" / "drift" / "drift_summary.json"
    openrouter_eval = root / "reports" / "openrouter" / "openrouter_eval_summary.md"
    openrouter_fail = root / "reports" / "openrouter" / "openrouter_failure_analysis.md"
    eval_metrics = root / "data" / "processed" / "eval_metrics.json"
    arch_img = root / "docs" / "architecture" / "images" / "03-drift-alert-openrouter.png"

    drift_status = _file_status(drift_html)
    openrouter_status = _file_status(openrouter_eval)
    metrics = _read_json_safe(eval_metrics) or {}
    drift = _read_json_safe(drift_summary) or {}

    gate = metrics.get("gate_passed")
    gate_text = "PASSED" if gate is True else "FAILED" if gate is False else "unknown"
    drift_text = drift.get("summary", "Run drift check to generate summary")

    links = [
        ("API Swagger UI", f"{base_url}/docs", "Try /health and /predict interactively"),
        ("Health check", f"{base_url}/health", "JSON model status"),
        ("Eval metrics", f"{base_url}/monitoring/eval-metrics", "Quality gate JSON"),
        ("Drift summary", f"{base_url}/monitoring/drift-summary", "Evidently drift JSON"),
        ("Combined status", f"{base_url}/monitoring/status", "All monitoring in one JSON"),
    ]
    if drift_status["available"]:
        links.append(("Drift HTML report", f"{base_url}/reports/drift/drift_report.html", "Evidently visual report"))
    if openrouter_status["available"]:
        links.append(("OpenRouter eval report", f"{base_url}/reports/openrouter/openrouter_eval_summary.md", "LLM summary"))
    if _file_status(openrouter_fail)["available"]:
        links.append(("OpenRouter failure report", f"{base_url}/reports/openrouter/openrouter_failure_analysis.md", "LLM failure analysis"))
    if _file_status(arch_img)["available"]:
        links.append(("Architecture diagram", f"{base_url}/architecture/03-drift-alert-openrouter.png", "Member D demo slide"))

    link_rows = "\n".join(
        f"""
        <tr>
          <td><a href="{url}">{title}</a></td>
          <td>{desc}</td>
        </tr>"""
        for title, url, desc in links
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Outage Predictor — Local Hub</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
    h1 {{ margin-bottom: 0.25rem; }}
    .subtitle {{ color: #555; margin-top: 0; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1.5rem 0; }}
    th, td {{ border: 1px solid #ddd; padding: 0.6rem 0.8rem; text-align: left; }}
    th {{ background: #f5f5f5; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0; }}
    .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem; background: #fafafa; }}
    .ok {{ color: #0a7; font-weight: 600; }}
    .warn {{ color: #c60; font-weight: 600; }}
    code {{ background: #eee; padding: 0.1rem 0.35rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>Website Outage Predictor</h1>
  <p class="subtitle">Single local hub — API, monitoring, drift &amp; OpenRouter reports</p>

  <div class="cards">
    <div class="card"><strong>Quality gate</strong><br/><span class="{'ok' if gate else 'warn'}">{gate_text}</span></div>
    <div class="card"><strong>Drift report</strong><br/>{drift_status['label']}</div>
    <div class="card"><strong>OpenRouter</strong><br/>{openrouter_status['label']}</div>
  </div>

  <p><strong>Drift:</strong> {drift_text}</p>

  <h2>All endpoints on this host</h2>
  <table>
    <thead><tr><th>Link</th><th>Description</th></tr></thead>
    <tbody>{link_rows}</tbody>
  </table>

  <h2>Generate reports (terminal)</h2>
  <pre><code>python3.11 scripts/run_drift_check.py
python3.11 scripts/openrouter_report.py</code></pre>
</body>
</html>"""


def register_local_dashboard(app: FastAPI) -> None:
    """Attach dashboard home page, monitoring JSON routes, and static report mounts."""
    root = get_project_root()
    reports_dir = root / "reports"
    arch_dir = root / "docs" / "architecture" / "images"
    reports_dir.mkdir(parents=True, exist_ok=True)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def local_hub() -> HTMLResponse:
        return HTMLResponse(build_dashboard_html("http://localhost:8000", root))

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
            "local_hub": "http://localhost:8000",
            "api_docs": "http://localhost:8000/docs",
            "health": "http://localhost:8000/health",
            "predict": "http://localhost:8000/predict",
            "gate_passed": eval_data.get("gate_passed") if eval_data else None,
            "eval_metrics": eval_data,
            "drift": drift_data,
            "reports": {
                "drift_html": "/reports/drift/drift_report.html",
                "openrouter_eval": "/reports/openrouter/openrouter_eval_summary.md",
            },
        }

    app.mount("/reports", StaticFiles(directory=str(reports_dir)), name="reports")
    if arch_dir.is_dir():
        app.mount("/architecture", StaticFiles(directory=str(arch_dir)), name="architecture")
