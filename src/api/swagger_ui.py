# Author: Member C — API documentation presentation
# Purpose: Branded dark Swagger UI at /docs (no endpoint logic changes)

"""Custom Swagger UI registration and OpenAPI metadata."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

OPENAPI_DESCRIPTION = """
Interactive API for the **Website Outage Prediction** MLOps platform on Azure.

Use this service to check readiness, probe public websites for live health signals, and predict outage risk from infrastructure metrics.

- **Dashboard:** [Open local dashboard](/)
- **Architecture demo:** [/demo](/demo)

Metrics returned by `/check-url-metrics` can be sent directly to `/predict`.
"""

OPENAPI_TAGS: list[dict[str, str]] = [
    {
        "name": "System",
        "description": "Service health and model readiness checks.",
    },
    {
        "name": "Prediction",
        "description": "Outage risk inference from monitoring metrics.",
    },
    {
        "name": "Website Health",
        "description": "Live HTTP probing of public website URLs.",
    },
    {
        "name": "Monitoring",
        "description": "Data drift detection and reporting.",
    },
]

SWAGGER_UI_PARAMETERS: dict[str, Any] = {
    "docExpansion": "list",
    "defaultModelsExpandDepth": 1,
    "tryItOutEnabled": True,
    "displayRequestDuration": True,
    "filter": True,
}

SWAGGER_JS_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"
SWAGGER_CSS_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"


def get_custom_swagger_ui_html(
    *,
    openapi_url: str,
    title: str,
) -> str:
    """Build Swagger UI HTML with platform header and dark theme CSS."""
    params_json = json.dumps(SWAGGER_UI_PARAMETERS)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="{SWAGGER_CSS_URL}" />
  <link rel="stylesheet" href="/static/swagger-theme.css" />
</head>
<body>
  <header class="platform-header">
    <div class="platform-header-inner">
      <div class="platform-brand">
        <h1>Website Outage Prediction API</h1>
        <p class="platform-subtitle">
          MLOps inference service — health checks, live URL analysis, and outage risk prediction.
        </p>
      </div>
      <nav class="platform-nav" aria-label="Quick links">
        <a href="/">Dashboard</a>
        <a href="/health">Health</a>
        <a href="/predict">Predict</a>
        <a href="/check-url-metrics">URL Check</a>
        <a href="/demo">Demo</a>
      </nav>
    </div>
  </header>
  <div id="swagger-ui"></div>
  <script src="{SWAGGER_JS_URL}" charset="UTF-8"></script>
  <script>
    window.onload = function() {{
      const uiConfig = {{
        url: "{openapi_url}",
        dom_id: "#swagger-ui",
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
        layout: "BaseLayout",
        deepLinking: true
      }};
      Object.assign(uiConfig, {params_json});
      window.ui = SwaggerUIBundle(uiConfig);
    }};
  </script>
</body>
</html>"""


def register_custom_docs(app: FastAPI) -> None:
    """Register branded GET /docs (requires docs_url=None on FastAPI)."""

    @app.get("/docs", include_in_schema=False)
    def custom_swagger_ui() -> HTMLResponse:
        html = get_custom_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} — API Docs",
        )
        return HTMLResponse(html)
