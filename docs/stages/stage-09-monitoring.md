# Stage 09 — Monitoring and Drift (Member D)

## What this stage does

1. **Application Insights** — telemetry from the FastAPI service in AKS
2. **Evidently drift** — compare reference baseline vs current production snapshot
3. **Azure Monitor alerts** — notify on API failures or drift check failures

## Files

| File | Purpose |
|------|---------|
| `src/monitoring/telemetry.py` | Bootstrap Azure Monitor OpenTelemetry |
| `src/monitoring/drift.py` | Evidently drift report logic (scipy KS fallback) |
| `src/api/drift_service.py` | Auto-generate drift reports on API request |
| `scripts/run_drift_check.py` | CLI drift check (exit 1 on drift) |
| `infra/setup_alerts.py` | Provision Action Group + metric alert |
| `.github/workflows/drift-check.yml` | Scheduled daily drift job |

## Prerequisites

1. AKS deployment running ([stage-08-deployment.md](stage-08-deployment.md))
2. Application Insights resource created in Azure
3. Drift datasets from Member A:
   - `data/reference/reference.csv`
   - `data/processed/current.csv`

## Environment variables

| Variable | Purpose |
|----------|---------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights telemetry (set on AKS pods) |
| `ALERT_EMAIL` | Email for Action Group notifications |
| `APP_INSIGHTS_NAME` | App Insights resource name for metric alerts |
| `ALERT_ACTION_GROUP_NAME` | Action Group name (default: `outage-predictor-alerts`) |

## Application Insights

Telemetry is configured automatically when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set on the API container (see `infra/k8s/deployment.yaml`).

Verify in Azure Portal:

1. Open Application Insights → **Live metrics** or **Logs**
2. Hit production API:

```powershell
curl http://<aks-ip>/health
curl -X POST http://<aks-ip>/predict -H "Content-Type: application/json" `
  -d '{"response_time_ms":850,"status_code":500,"error_rate":0.12,"latency_p95_ms":1200,"request_count":4200,"cpu_usage_percent":78,"memory_usage_percent":81}'
```

3. Confirm requests appear in **Transaction search**

## Run drift check

Drift reports are generated automatically when you call the API or open the dashboard drift card. You can also run the CLI manually.

### API (auto-generate)

```powershell
curl http://127.0.0.1:8000/drift
curl -X POST http://127.0.0.1:8000/drift/run
```

- `GET /drift` — returns `drift_summary.json`, generating the report if missing
- `POST /drift/run` — force a new drift analysis
- `GET /monitoring/drift-summary` — same summary (backward compatible)

If reference or current CSVs are missing, the service generates sample monitoring data first (same as the local pipeline).

### Activity-triggered drift (demo)

Each `POST /predict` and `POST /check-url-metrics` appends a row to `artifacts/reports/current_observations.csv` (demo production log). When at least 5 observations exist, drift compares `data/reference/reference.csv` against that rolling snapshot and writes:

- `artifacts/reports/drift_summary.json`
- `artifacts/reports/drift_report.html`

Until 5 observations exist, `GET /drift` returns `insufficient_data: true`. Predictions never fail if drift update fails.

### CLI (scheduled / CI — unchanged)

```powershell
py scripts/generate_sample_data.py
py scripts/run_drift_check.py
```

Outputs:

- `reports/drift/drift_report.html` — Evidently visual report (or scipy fallback HTML)
- `reports/drift/drift_report.json` — machine-readable metrics
- `reports/drift/drift_summary.json` — compact summary for OpenRouter and dashboard

Summary JSON includes: `generated_at`, `drift_score`, `drifted_columns`, `reference_rows`, `current_rows`, `recommendation`, and `method` (`evidently` or `scipy_ks`).

Exit code `1` means drift detected (used for CI alerts).

## Set up alerts

### API metric alert (Azure Portal or script)

```powershell
$env:AZURE_SUBSCRIPTION_ID = "<subscription-id>"
$env:AZURE_RESOURCE_GROUP = "<resource-group>"
$env:ALERT_EMAIL = "you@example.com"
$env:APP_INSIGHTS_NAME = "outage-predictor-insights"

py infra/setup_alerts.py
```

### Drift alert (GitHub Actions)

The `Drift Check` workflow runs daily. When drift is detected:

- Workflow fails with `::error::Data drift detected`
- Configure GitHub repo **Watch → Actions** for email notifications

## Demo — drift + alert

1. Open the dashboard **Drift Summary** section or call `GET /drift` — reports generate automatically
2. Open `reports/drift/drift_report.html` (or click **View HTML Report** on the dashboard)
3. Show failed GitHub Actions run or Azure alert in Portal
4. Proceed to [stage-10-openrouter.md](stage-10-openrouter.md) for LLM summary

## Cross-reference

- AKS deploy: [stage-08-deployment.md](stage-08-deployment.md)
- Architecture: [../architecture/README.md](../architecture/README.md)
