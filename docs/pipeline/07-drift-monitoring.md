# Pipeline Stage 7 — Drift Monitoring

## Purpose

Detect when production telemetry diverges from the training baseline so the team can retrain before model quality degrades.

## Evidently AI

`src/monitoring/drift.py` uses Evidently to compare:

- **Reference:** `data/processed/reference.csv` (training baseline)
- **Current:** production snapshot or `artifacts/reports/current_observations.csv`

Outputs:

- `drift_summary.json` — scores and recommendation
- `drift_report.html` — visual report

## Drift report generation

| Trigger | Entry |
|---------|--------|
| API | `GET /drift`, dashboard Drift Summary |
| CLI | `py scripts/run_drift_check.py` |
| CI | `.github/workflows/drift-check.yml` |
| Activity | Auto-refresh after 5+ observations from predict/URL check |

## Azure Monitor alert concept

`infra/setup_alerts.py` provisions:

- Metric alert on failed API requests
- Action group `outage-predictor-alerts` → email

Application Insights (`outage-predictor-insights`) collects request telemetry from FastAPI pods.

## Azure status

| Item | Status |
|------|--------|
| Evidently reports (local) | ✅ Complete |
| Dashboard drift UI | ✅ Complete |
| Live App Insights telemetry | **Pending — Azure setup phase** |
| Fired alert screenshot | **Pending — Azure setup phase** |

## Key files

| File | Role |
|------|------|
| `src/monitoring/drift.py` | Evidently logic |
| `src/api/drift_service.py` | API integration |
| `src/monitoring/observations.py` | Observation log |
| `infra/setup_alerts.py` | Azure Monitor rules |

## Detail

[../stages/stage-09-monitoring.md](../stages/stage-09-monitoring.md)
