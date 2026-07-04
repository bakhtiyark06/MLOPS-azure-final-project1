# Stage: API UI Demo Dashboard

Modern localhost dashboard that runs the full local MLOps demo workflow from the browser.

## Before you start

The dashboard can run the local demo workflow and prediction flow from the browser. **The app itself still must be running** either locally with FastAPI or deployed on Azure. Once it is running, users can operate the demo from the dashboard without manually running each pipeline command.

## Run the app locally

From the project root:

```bash
python3.11 scripts/run_local.py
```

Or:

```bash
python scripts/run_local.py
```

Alternative (API with auto-reload):

```bash
python3.11 -m uvicorn src.api.main:app --reload --port 8000
```

## Open the dashboard

- **Dashboard:** http://127.0.0.1:8000/
- **Swagger API docs:** http://127.0.0.1:8000/docs
- **Health check:** http://127.0.0.1:8000/health

For Azure deployment, open your deployed service URL (for example the AKS load balancer IP).

## Dashboard sections

| Section | What it does |
|---------|----------------|
| **System Status** | API health, model loaded, data/model files, evaluation status |
| **Run Local Pipeline** | Generate data → ingest/validate → train → evaluate |
| **Check Public Website URL** | Probe a public URL and auto-fill metrics |
| **Predict Outage Risk** | Send metrics to `POST /predict` and show risk |
| **How the Model Works** | Visual flow from URL/metrics to prediction |
| **How to Predict Any Website** | Step-by-step demo guide |
| **Public URL limits** | What can and cannot be measured externally |

## Tab navigation

Existing hub links are modern tabs at the top:

| Tab | Destination |
|-----|-------------|
| Overview | `#system-status` |
| Pipeline | `#pipeline` |
| URL Check | `#url-check` |
| Predict | `#predict` |
| Swagger UI | `/docs` |
| Health Check | `/health` |
| Eval Metrics | `/monitoring/eval-metrics` |
| Drift Summary | `/monitoring/drift-summary` |
| Combined Status | `/monitoring/status` |
| Drift Report | `/reports/drift/drift_report.html` (when generated) |
| OpenRouter Report | `/reports/openrouter/openrouter_eval_summary.md` (when generated) |

## Run the full local pipeline from the browser

1. Open http://127.0.0.1:8000/
2. Go to **Run Local MLOps Demo Pipeline**
3. Click **Run Full Local Pipeline**
4. Wait for step results (generate → ingest → train → evaluate)
5. Click **Refresh System Status** to confirm model loaded and gate passed

The backend endpoint is `POST /run-local-pipeline`.

If Azure credentials are missing, the pipeline completes locally and shows:

> Azure credentials not found, local demo pipeline completed without Azure upload/registry.

## Check a public website URL from the browser

1. Go to **Check Public Website URL**
2. Enter a public URL such as `https://example.com`
3. Click **Check Website Metrics**
4. The form auto-fills with:
   - `response_time_ms`
   - `status_code`
   - `error_rate`
   - `latency_p95_ms`
   - `request_count`
5. `cpu_usage_percent` and `memory_usage_percent` default to **50** (demo values)

Blocked URLs: localhost, 127.0.0.1, private IPs, and cloud metadata endpoints.

Endpoint: `POST /check-url-metrics`

## Predict outage risk from the browser

1. Fill the form manually, use **Load Healthy Example** / **Load Outage Risk Example**, or auto-fill from URL check
2. Edit CPU and memory if needed (real values if you own the site, demo estimates otherwise)
3. Click **Predict Outage Risk**
4. Read **Healthy** or **Outage Risk**, outage probability, risk meter, and explanation cards

Uses existing `POST /predict` — no page reload.

### Healthy example

```json
{
  "response_time_ms": 220,
  "status_code": 200,
  "error_rate": 0.01,
  "latency_p95_ms": 280,
  "request_count": 300,
  "cpu_usage_percent": 35,
  "memory_usage_percent": 42
}
```

### Outage-risk example

```json
{
  "response_time_ms": 3100,
  "status_code": 500,
  "error_rate": 0.18,
  "latency_p95_ms": 4500,
  "request_count": 1200,
  "cpu_usage_percent": 94,
  "memory_usage_percent": 91
}
```

## Why public URLs cannot reveal CPU and memory

From a public URL you do not own, the dashboard can only probe HTTP responses. CPU, memory, internal request counts, server logs, and full application error rates require access to your own monitoring stack (Azure Monitor, Application Insights, Prometheus, etc.).

## What to say during the demo

> “Our model does not predict from the website name alone. It predicts from monitoring metrics. In a real company, these metrics come from Azure Monitor, Application Insights, logs, and health checks. For this demo, we run the local pipeline from the dashboard, optionally check a public URL for basic metrics, and predict outage risk from the form.”

## API endpoints added for the dashboard

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/system-status` | GET | System readiness snapshot |
| `/run-local-pipeline` | POST | Run local generate/ingest/train/evaluate |
| `/check-url-metrics` | POST | Probe public URL and return metrics |

Existing endpoints unchanged: `/health`, `/predict`, `/docs`.

## Run tests

```bash
python3.11 -m pytest
```

Key checks:

- `GET /` returns dashboard with workflow buttons
- `GET /health` and `POST /predict` still work
- `POST /check-url-metrics` validates and blocks unsafe URLs
- `POST /run-local-pipeline` returns structured JSON

## Commit changes (when ready)

```bash
git add src/api/ tests/ docs/stages/stage-api-ui-demo.md
git commit -m "Add browser-driven local MLOps demo workflow to dashboard"
```
