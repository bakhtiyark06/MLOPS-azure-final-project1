# Architecture Diagram Notes

Checklist of every submission-guide component with file/workflow references.

## Component coverage

| Component | Reference |
|-----------|-----------|
| GitHub repository + branches | README, PR workflow |
| GitHub Actions CI/CD trigger | `.github/workflows/ci.yml` |
| Azure Blob Storage / DVC | `stwoutagemlops`, `setup_dvc.py` |
| Azure ML Compute | `train.yml`, `train_model.py` |
| MLflow experiment tracking | `train_model.py`, Azure ML workspace |
| Quality gate pass/fail | `eval_metrics.json`, `evaluate_model.py` |
| Azure ML Model Registry | `website-outage-model`, `register_model.py` |
| Docker build | `Dockerfile`, `build_image.py` |
| Container Registry (ACR) | `acrwoutagemlops` |
| ACI staging deployment | `infra/deploy_aci.py` |
| AKS production deployment | `infra/deploy_aks.py`, `infra/k8s/` |
| AKS ingress / LoadBalancer | `infra/k8s/service.yaml` |
| FastAPI prediction endpoint | `src/api/main.py`, `/predict` |
| Evidently AI drift detection | `src/monitoring/drift.py` |
| Azure Monitor | `infra/setup_alerts.py` |
| Application Insights | `outage-predictor-insights`, `telemetry.py` |
| Azure Key Vault | `src/utils/secrets.py` (optional; GitHub Secrets primary) |
| OpenRouter secret handling | `OPENROUTER_API_KEY` via GitHub Secrets |

## Arrow legend

| Arrow style | Meaning | Example |
|-------------|---------|---------|
| Solid data flow | Artifacts passed between stages | `CSV → train → joblib` |
| Dashed control | Automation trigger or optional path | `Key Vault → GitHub Secrets` |
| Label on edge | Payload or trigger name | `gate_passed`, `image:tag` |

## Labelled flows

1. **Commit → CI** — source + test results
2. **Blob → Train** — versioned dataset
3. **Train → MLflow** — metrics + parameters
4. **Eval → Gate** — `eval_metrics.json`
5. **Gate → Registry** — approved `joblib` only if pass
6. **Registry → Docker** — model in image
7. **Docker → ACR** — `image:tag`
8. **ACR → ACI/AKS** — container pull
9. **AKS → Ingress → API** — public HTTP
10. **Client → API** — JSON metrics → prediction
11. **API → App Insights** — request telemetry
12. **Reference/Current → Evidently** — drift report
13. **Metrics → OpenRouter** — markdown summary
14. **Secrets → CI/Deploy** — `AZURE_CREDENTIALS`, API keys

## Diagram source

```powershell
py scripts/render_architecture_diagrams.py
```

Output: `architecture/images/architecture-diagram.png`
