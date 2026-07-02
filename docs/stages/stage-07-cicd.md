# Stage 07 — CI/CD (Member C + Member D)

## What this stage does

GitHub Actions validate, train, deploy, and monitor the pipeline:

| Workflow | Owner | Purpose |
|----------|-------|---------|
| `ci.yml` | Member C | Test + Docker build on push/PR |
| `train.yml` | Member D | Retrain → eval → registry → ACR push → drift check |
| `deploy.yml` | Member D | Quality gate → deploy to AKS |
| `drift-check.yml` | Member D | Daily drift detection + alert annotation |
| `data-ingest.yml` | Member A | Scheduled data ingestion |

## CI workflow (Member C)

`.github/workflows/ci.yml`

| Job | Steps |
|-----|-------|
| `test` | generate → train → pytest with coverage |
| `docker-build` | generate → train → `docker build` |

Push to `main` or `Sana's-branch` triggers CI. No secrets required for tests.

## Train workflow (Member D)

`.github/workflows/train.yml`

1. Generate data (2000 rows)
2. Train model
3. Evaluate + quality gate
4. Upload `eval_metrics.json` artifact
5. Register model (skips if Azure not configured)
6. Build + push Docker image to ACR (skips if `ACR_NAME` not set)
7. Run drift check (fails workflow if drift detected)

Triggers: `workflow_dispatch`, weekly schedule, push to `main` on `src/`, `scripts/`, `configs/`.

## Deploy workflow (Member D)

`.github/workflows/deploy.yml`

1. Download eval metrics from Train workflow (or regenerate on manual dispatch)
2. Block deploy if `gate_passed` is false
3. Azure login + `kubectl`
4. Run `infra/deploy_aks.py`

Triggers: after successful Train workflow, or manual `workflow_dispatch`.

## Drift check workflow (Member D)

`.github/workflows/drift-check.yml` — daily scheduled drift job with failed-workflow notification.

## GitHub Secrets (production)

See [../azure-setup.md](../azure-setup.md):

- `AZURE_CREDENTIALS`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`
- `ACR_NAME`, `AKS_CLUSTER_NAME`, `APPLICATIONINSIGHTS_CONNECTION_STRING`
- `OPENROUTER_API_KEY` (optional, for LLM reports)

## Cross-reference

- Previous: [stage-06-testing.md](stage-06-testing.md)
- Next: [stage-08-deployment.md](stage-08-deployment.md) (ACI staging — Member C; AKS — Member D)
- Monitoring: [stage-09-monitoring.md](stage-09-monitoring.md)
