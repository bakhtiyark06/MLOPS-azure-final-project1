# Website Outage Prediction MLOps Pipeline on Azure

[![CI — Tests and Lint](https://github.com/YOUR_ORG/MLOPS-azure-final-project1/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_ORG/MLOPS-azure-final-project1/actions/workflows/ci.yml)

End-to-end MLOps CI/CD pipeline that predicts whether a website is likely to have an outage within one hour, based on monitoring metrics (response time, status code, error rate, latency, request count, CPU, memory).

## Project structure

| Folder | Purpose |
|--------|---------|
| `configs/` | Model thresholds and Azure resource names (no secrets) |
| `data/` | Raw, processed, and reference datasets (gitignored) |
| `docs/` | Architecture diagram, stage walkthroughs, Azure setup |
| `infra/` | Azure provisioning and ACI/AKS deploy scripts |
| `scripts/` | Pipeline entrypoints (ingest, train, evaluate, deploy helpers) |
| `src/` | Core Python modules (data, models, API, monitoring) |
| `tests/` | pytest suite (≥70% coverage) |
| `.github/workflows/` | GitHub Actions CI/CD |

## Local Azure connection (one command)

After `az login`, run from the project root:

```bash
cd MLOPS-azure-final-project1
source scripts/setup_azure_env.sh
```

This will:
- Set subscription `4c3c4430-0ce6-48bc-8e33-1947f3876ebd`
- Use resource group `rg-website-outage-mlops`
- Create/verify ACR `acrwoutagemlops` and App Insights `outage-predictor-insights`
- Write `.env` and `configs/azure_config.yaml` (gitignored)

Then deploy staging:

```bash
python3 scripts/build_image.py --acr acrwoutagemlops --tag v1 --push
python3 infra/deploy_aci.py --wait-health
```

For AKS, create the cluster first (use `standard_b2s_v2` in centralus):

```bash
az aks create --resource-group rg-website-outage-mlops --name aks-outage-predictor \
  --location centralus --node-count 1 --node-vm-size standard_b2s_v2 \
  --enable-addons monitoring --attach-acr acrwoutagemlops --generate-ssh-keys
python3 infra/deploy_aks.py --wait-health
```

See [docs/azure-setup.md](docs/azure-setup.md) for GitHub Secrets.

## Member D — AKS, monitoring, drift, OpenRouter (complete)

See [docs/stages/stage-08-deployment.md](docs/stages/stage-08-deployment.md) (AKS section), [stage-09-monitoring.md](docs/stages/stage-09-monitoring.md), and [stage-10-openrouter.md](docs/stages/stage-10-openrouter.md).

```powershell
py scripts/verify_member_d.py
py scripts/evaluate_model.py
py infra/deploy_aks.py --wait-health
py scripts/run_drift_check.py
py infra/setup_alerts.py --email you@example.com
py scripts/openrouter_report.py --dry-run
```

Architecture diagram: [docs/architecture/README.md](docs/architecture/README.md)

### Local hub (single localhost — API + reports)

Start everything on **http://127.0.0.1:8000** (keep the terminal open):

```bash
python3.11 scripts/run_local.py
```

Open **http://127.0.0.1:8000/** for the dashboard, or **http://127.0.0.1:8000/docs** for Swagger.

Drift reports auto-generate via `GET /drift` or the dashboard **Drift Summary** card. After each **Predict** or **URL check**, observations append to `artifacts/reports/current_observations.csv`; once 5+ exist, drift refreshes automatically. In production, drift is usually run on a schedule or batch window—not every request.

**OpenRouter summary** reads model metrics (`eval_metrics.json`), quality gate result, drift summary, and dataset hash. Set `OPENROUTER_API_KEY` locally or as the GitHub Secret `OPENROUTER_API_KEY`. Without a key, the API writes a **local fallback** report to `artifacts/reports/openrouter_eval_summary.md`. Generate from the dashboard **OpenRouter Summary** card or `POST /reports/openrouter/run`; fetch with `GET /reports/openrouter`.

Verify the server is running:

```bash
python3.11 scripts/check_local.py
```

## Member C — API, Docker, CI, ACI staging (complete)

See [docs/stages/stage-05-containerization.md](docs/stages/stage-05-containerization.md) through [stage-08-deployment.md](docs/stages/stage-08-deployment.md).

```powershell
py scripts/generate_sample_data.py
py scripts/train_model.py
py -m uvicorn src.api.main:app --reload --port 8000
py -m pytest tests/test_api.py -v
py scripts/build_image.py --acr <acr> --tag v1 --push
py infra/deploy_aci.py --wait-health
```

## Member A — Data pipeline (complete)

See [docs/stages/stage-01-ingestion.md](docs/stages/stage-01-ingestion.md) for full walkthrough.

```powershell
py scripts/setup_dvc.py --skip-remote
py scripts/generate_sample_data.py
py scripts/ingest_data.py --skip-blob
py -m pytest tests/test_data_ingestion.py -v
```

## Quick start (local)

### 1. Create virtual environment

```powershell
cd MLOPS-azure-final-project1
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Generate data and train

```powershell
py scripts/generate_sample_data.py
py scripts/train_model.py
py scripts/evaluate_model.py
py scripts/register_model.py
```

### 3. Run API locally

```powershell
py -m uvicorn src.api.main:app --reload --port 8000
```

Test: `http://localhost:8000/docs`

### 4. Run tests

```powershell
py -m pytest
```

## Pipeline stages

1. Data ingestion + DVC → `docs/stages/stage-01-ingestion.md`
2. Model training + MLflow → `docs/stages/stage-02-training.md`
3. Quality gate → `docs/stages/stage-03-evaluation.md`
4. Model registry → `docs/stages/stage-04-registry.md`
5. Docker + FastAPI → `docs/stages/stage-05-containerization.md`
6. pytest → `docs/stages/stage-06-testing.md`
7. GitHub Actions → `docs/stages/stage-07-cicd.md`
8. ACI + AKS deploy → `docs/stages/stage-08-deployment.md`
9. Monitoring + Evidently → `docs/stages/stage-09-monitoring.md`
10. OpenRouter LLM → `docs/stages/stage-10-openrouter.md`

## Azure setup

See [docs/azure-setup.md](docs/azure-setup.md) for resource provisioning and GitHub Secrets.

## Team

See [docs/team-roles.md](docs/team-roles.md) for stage ownership (team of 4).

## Demo day

See [docs/demo-day.md](docs/demo-day.md) for live demo checklist and release tag `v1.0.0`.

## Tech stack

Python 3.11+ · scikit-learn · FastAPI · Docker · Azure ML · Blob Storage · ACI · AKS · MLflow · DVC · Evidently · OpenRouter · GitHub Actions · pytest
