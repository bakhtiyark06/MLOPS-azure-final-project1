# Documentation Index — Website Outage Prediction MLOps

This folder contains submission-ready documentation for reviewers and the live demo team.

## Start here

1. [Root README](../README.md) — project overview, local run, CI, security
2. [submission-checklist.md](submission-checklist.md) — what is done vs pending (Azure, demo, final)
3. [demo-script.md](demo-script.md) — turn-based live presentation for all 4 members

## Architecture

| Document | Purpose |
|----------|---------|
| [architecture/architecture-overview.md](architecture/architecture-overview.md) | End-to-end narrative from commit to prediction |
| [architecture/architecture-diagram-notes.md](architecture/architecture-diagram-notes.md) | Every required component and labelled flow |
| [architecture/architecture-diagram.mmd](architecture/architecture-diagram.mmd) | Canonical Mermaid diagram source |
| [architecture/README.md](architecture/README.md) | Additional diagrams (01–04) and PNG exports |
| [architecture/images/](architecture/images/) | Rendered diagram PNGs for slides |

## Pipeline walkthrough (submission format)

| Stage | Document | Implementation detail |
|-------|----------|----------------------|
| 1 Data | [pipeline/01-data-stage.md](pipeline/01-data-stage.md) | [stages/stage-01-ingestion.md](stages/stage-01-ingestion.md) |
| 2 Training | [pipeline/02-training-stage.md](pipeline/02-training-stage.md) | [stages/stage-02-training.md](stages/stage-02-training.md) |
| 3 Quality gate | [pipeline/03-quality-gate.md](pipeline/03-quality-gate.md) | [stages/stage-03-evaluation.md](stages/stage-03-evaluation.md) |
| 4 Registry | [pipeline/04-model-registry.md](pipeline/04-model-registry.md) | [stages/stage-04-registry.md](stages/stage-04-registry.md) |
| 5 Docker | [pipeline/05-docker-build.md](pipeline/05-docker-build.md) | [stages/stage-05-containerization.md](stages/stage-05-containerization.md) |
| 6 Deployment | [pipeline/06-deployment.md](pipeline/06-deployment.md) | [stages/stage-08-deployment.md](stages/stage-08-deployment.md) |
| 7 Drift | [pipeline/07-drift-monitoring.md](pipeline/07-drift-monitoring.md) | [stages/stage-09-monitoring.md](stages/stage-09-monitoring.md) |
| 8 OpenRouter | [pipeline/08-openrouter-integration.md](pipeline/08-openrouter-integration.md) | [stages/stage-10-openrouter.md](stages/stage-10-openrouter.md) |

Also see: [stages/stage-06-testing.md](stages/stage-06-testing.md) · [stages/stage-07-cicd.md](stages/stage-07-cicd.md)

## Demo and team

| Document | Purpose |
|----------|---------|
| [demo-script.md](demo-script.md) | Live demo turns, Q&A, end-to-end close |
| [demo-day.md](demo-day.md) | Rehearsal commands and Member D moments |
| [team-roles.md](team-roles.md) | Member A–D ownership |

## Code documentation standards

| Document | Purpose |
|----------|---------|
| [code-documentation/python-commenting-standard.md](code-documentation/python-commenting-standard.md) | Commenting and docstring rules |
| [code-documentation/author-tags.md](code-documentation/author-tags.md) | Author tag template |
| [code-documentation/file-ownership.md](code-documentation/file-ownership.md) | Per-file owner and review status |
| [code-documentation/audit-report.md](code-documentation/audit-report.md) | Generated audit (run `py scripts/audit_python_docs.py`) |

## Evidence for grading

| Document | Purpose |
|----------|---------|
| [evidence/README.md](evidence/README.md) | How to name and store screenshots |
| [evidence/screenshots-needed.md](evidence/screenshots-needed.md) | Required captures (repo vs Azure-pending) |

## Azure (Phase 2 — pending live setup)

| Document | Purpose |
|----------|---------|
| [azure-setup.md](azure-setup.md) | ACR, AKS, App Insights, GitHub Secrets provisioning |

Do not run live Azure steps until credentials and subscription access are confirmed.
