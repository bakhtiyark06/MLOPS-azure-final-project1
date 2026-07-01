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
