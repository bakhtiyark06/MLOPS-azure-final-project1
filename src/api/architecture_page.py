# Author: Presentation layer — interactive architecture dashboard
# Purpose: Serve /demo hub and /demo/flow without changing API behavior

"""Routes for the interactive architecture presentation pages."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_DEMO_HUB = _TEMPLATE_DIR / "demo_hub.html"
_ARCH_FLOW = _TEMPLATE_DIR / "architecture_flow.html"


def _read_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def register_architecture_pages(app: FastAPI) -> None:
    """Register GET /demo and GET /demo/flow (HTML only)."""

    @app.get("/demo", response_class=HTMLResponse, include_in_schema=False)
    def demo_hub() -> HTMLResponse:
        return HTMLResponse(_read_template(_DEMO_HUB))

    @app.get("/demo/flow", response_class=HTMLResponse, include_in_schema=False)
    def demo_flow() -> HTMLResponse:
        return HTMLResponse(_read_template(_ARCH_FLOW))
