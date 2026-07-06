# Website Outage Prediction MLOps Pipeline on Azure

[![CI — Tests and Lint](https://github.com/bakhtiyark06/MLOPS-azure-final-project1/actions/workflows/ci.yml/badge.svg)](https://github.com/bakhtiyark06/MLOPS-azure-final-project1/actions/workflows/ci.yml)

> **Azure deployment status:** Live Azure ML, ACI, AKS, Azure Monitor, and production secrets are **documented but not yet configured** in this phase. See [docs/submission-checklist.md](docs/submission-checklist.md) and [docs/azure-setup.md](docs/azure-setup.md) (Phase 2).

## Project summary

End-to-end MLOps CI/CD pipeline that predicts whether a website is likely to experience an outage within one hour, using monitoring metrics (response time, HTTP status, error rate, P95 latency, request volume, CPU, and memory).

## Problem statement

Operations teams need early warning before customer-facing outages. Reactive alerting after downtime is costly. This project trains a classifier on website telemetry, deploys it as a production API, and monitors model health with drift detection and LLM-generated summaries for stakeholders.

## Solution overview

```
Developer commit → GitHub Actions CI/CD → Data (DVC/Blob) → Train (MLflow)
  → Quality gate → Model registry → Docker build → ACR
  → ACI staging → AKS production → /predict API
  → Application Insights → Evidently drift → Azure Monitor alerts → OpenRouter reports
```

Interactive architecture tour: **http://127.0.0.1:8000/demo/flow** (after starting locally).

## Tech stack

Python 3.11+ · scikit-learn · pandas · FastAPI · uvicorn · Docker · Azure ML · Azure Blob Storage · DVC · MLflow · ACI · AKS · ACR · Application Insights · Azure Monitor · Evidently · OpenRouter · GitHub Actions · pytest

## Folder structure

| Folder | Purpose |
|--------|---------|
| `configs/` | Model thresholds and Azure resource names (no secrets) |
| `data/` | Raw, processed, and reference datasets (gitignored) |
| `docs/` | Submission docs, architecture, pipeline walkthroughs, evidence checklist |
| `infra/` | ACI/AKS deploy scripts and Kubernetes manifests |
| `scripts/` | Pipeline entrypoints (ingest, train, evaluate, deploy helpers) |
| `src/` | Core Python modules (data, models, API, monitoring) |
| `tests/` | pytest suite (≥70% coverage gate) |
| `.github/workflows/` | GitHub Actions CI/CD |

Full documentation index: [docs/README.md](docs/README.md)

## How to run locally

### 1. Virtual environment

```powershell
cd MLOPS-azure-final-project1
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Generate data, train, evaluate

```powershell
py scripts/generate_sample_data.py
py scripts/train_model.py
py scripts/evaluate_model.py
```

### 3. Start the dashboard + API (recommended)

```powershell
py scripts/run_local.py
```

Open **http://127.0.0.1:8000/** (dashboard) or **http://127.0.0.1:8000/docs** (Swagger).

Verify: `py scripts/check_local.py`

Alternative (API only): `py -m uvicorn src.api.main:app --reload --port 8000`

## How to run tests

```powershell
py -m pytest
```

CI enforces ≥70% coverage on `src/` and `scripts/`. Targeted runs:

```powershell
py -m pytest tests/test_api.py tests/test_training.py -v
```

## Docker usage

Build and run the API container locally:

```powershell
docker build -t outage-predictor:local .
docker run -p 8000:8000 outage-predictor:local
```

Push to Azure Container Registry (requires `az login` and ACR access — **pending Azure phase**):

```powershell
az acr login --name acrwoutagemlops
py scripts/build_image.py --acr acrwoutagemlops --tag v1 --push
```

See [docs/pipeline/05-docker-build.md](docs/pipeline/05-docker-build.md).

## GitHub Actions / CI overview

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| [`ci.yml`](.github/workflows/ci.yml) | Push/PR to `main` | pytest + coverage + Docker build smoke test |
| [`train.yml`](.github/workflows/train.yml) | Manual / schedule | Training pipeline on Azure ML |
| [`deploy.yml`](.github/workflows/deploy.yml) | After gate pass | Deploy image to AKS |
| [`data-ingest.yml`](.github/workflows/data-ingest.yml) | Manual | Data ingestion to Blob |
| [`drift-check.yml`](.github/workflows/drift-check.yml) | Schedule / manual | Evidently drift check |
| [`openrouter-report.yml`](.github/workflows/openrouter-report.yml) | Manual | OpenRouter eval summary |

> **Note:** CI badge reflects runs on `main`. Active development may be on the `test` branch until merge.

Details: [docs/stages/stage-07-cicd.md](docs/stages/stage-07-cicd.md) · [docs/pipeline/](docs/pipeline/)

## Architecture overview

- Narrative: [docs/architecture/architecture-overview.md](docs/architecture/architecture-overview.md)
- Component checklist: [docs/architecture/architecture-diagram-notes.md](docs/architecture/architecture-diagram-notes.md)
- Mermaid source: [docs/architecture/architecture-diagram.mmd](docs/architecture/architecture-diagram.mmd)
- Rendered PNGs: [docs/architecture/images/](docs/architecture/images/)

## Demo flow

Live presentation script: [docs/demo-script.md](docs/demo-script.md)

Rehearsal checklist: [docs/demo-day.md](docs/demo-day.md)

Suggested opener: Architecture Explorer at `/demo/flow`, then dashboard predict + drift + OpenRouter cards.

## Team responsibilities

| Member | Primary focus |
|--------|---------------|
| A | Data ingestion, DVC, Azure Blob |
| B | Training, MLflow, quality gate, model registry |
| C | FastAPI, Docker, pytest, CI, ACI staging |
| D | AKS, monitoring, Evidently drift, OpenRouter |

Details: [docs/team-roles.md](docs/team-roles.md) · [docs/code-documentation/file-ownership.md](docs/code-documentation/file-ownership.md)

## Submission checklist

Track repo-side vs Azure-pending vs demo items: [docs/submission-checklist.md](docs/submission-checklist.md)

## Screenshots and evidence

Required captures before grading: [docs/evidence/screenshots-needed.md](docs/evidence/screenshots-needed.md)

Store files under `docs/evidence/` using the naming convention in [docs/evidence/README.md](docs/evidence/README.md).

## Security

**No secrets are committed to this repository.** API keys, Azure credentials, and connection strings belong in:

- GitHub Actions Secrets (`AZURE_CREDENTIALS`, `OPENROUTER_API_KEY`, etc.)
- Local environment variables or `.env` (gitignored)

See [docs/azure-setup.md](docs/azure-setup.md) for the secrets list. Run `py scripts/audit_python_docs.py` and review [docs/code-documentation/audit-report.md](docs/code-documentation/audit-report.md) for documentation coverage.

## Azure setup (Phase 2 — pending)

Provisioning guide: [docs/azure-setup.md](docs/azure-setup.md)

When ready:

```bash
az login
source scripts/setup_azure_env.sh
py scripts/build_image.py --acr acrwoutagemlops --tag v1 --push
py infra/deploy_aci.py --wait-health
py infra/deploy_aks.py --wait-health
```

## Pipeline stages (quick links)

| # | Stage | Doc |
|---|-------|-----|
| 1 | Data + DVC | [docs/pipeline/01-data-stage.md](docs/pipeline/01-data-stage.md) |
| 2 | Training | [docs/pipeline/02-training-stage.md](docs/pipeline/02-training-stage.md) |
| 3 | Quality gate | [docs/pipeline/03-quality-gate.md](docs/pipeline/03-quality-gate.md) |
| 4 | Model registry | [docs/pipeline/04-model-registry.md](docs/pipeline/04-model-registry.md) |
| 5 | Docker | [docs/pipeline/05-docker-build.md](docs/pipeline/05-docker-build.md) |
| 6 | Deployment | [docs/pipeline/06-deployment.md](docs/pipeline/06-deployment.md) |
| 7 | Drift monitoring | [docs/pipeline/07-drift-monitoring.md](docs/pipeline/07-drift-monitoring.md) |
| 8 | OpenRouter | [docs/pipeline/08-openrouter-integration.md](docs/pipeline/08-openrouter-integration.md) |

Implementation detail: [docs/stages/](docs/stages/)
