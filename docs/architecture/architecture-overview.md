# Architecture Overview

End-to-end flow from developer commit to production outage prediction on Azure.

## Narrative

### 1. Developer and GitHub

Developers work on feature branches, open pull requests, and merge to `main`. The repository contains code, configs (no secrets), tests, Dockerfile, and infrastructure scripts.

### 2. CI/CD trigger

GitHub Actions `ci.yml` runs on push/PR to `main`: pytest, coverage gate, Docker build smoke test. Additional workflows: `train.yml`, `deploy.yml`, `data-ingest.yml`, `drift-check.yml`, `openrouter-report.yml`.

### 3. Data and training

Raw monitoring CSV is versioned with DVC and stored in Azure Blob (`stwoutagemlops`). Training runs on Azure ML Compute (or locally for dev) and logs to MLflow.

### 4. Quality gate

Evaluation writes `data/processed/eval_metrics.json`. If `gate_passed` is false, registry and deploy are blocked.

### 5. Model registry

Approved models register in Azure ML as `website-outage-model`.

### 6. Containerization

Docker image bundles FastAPI + model. Image pushes to ACR (`acrwoutagemlops`).

### 7. Deployment

ACI staging validates the image; AKS production serves traffic through LoadBalancer ingress to `/predict`.

### 8. Monitoring and LLM

Application Insights and Azure Monitor collect telemetry; Evidently detects drift; OpenRouter generates stakeholder summaries. Secrets flow through GitHub Secrets (Key Vault optional).

---

## Diagrams

- Canonical Mermaid: [architecture-diagram.mmd](architecture-diagram.mmd)
- Component notes: [architecture-diagram-notes.md](architecture-diagram-notes.md)
- Additional views: [README.md](README.md) (diagrams 01–04)
- Interactive UI: http://127.0.0.1:8000/demo/flow

## Related pipeline docs

[../pipeline/](../pipeline/)
