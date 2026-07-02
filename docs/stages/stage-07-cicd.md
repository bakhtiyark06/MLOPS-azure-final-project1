# Stage 07 — CI/CD (Member C)

## What this stage does

Member C wires **GitHub Actions** to validate the API on every push:

1. Install dependencies
2. Generate data + train model (creates `models/outage_model.joblib` for tests)
3. Run `pytest` with ≥70% coverage
4. Build Docker image after tests pass

## Workflow

`.github/workflows/ci.yml`

| Job | Steps |
|-----|-------|
| `test` | generate → train → pytest with coverage |
| `docker-build` | generate → train → `docker build` |

## GitHub setup

Push to `main` or `Sana's-branch` triggers CI.

No secrets required for the test job. ACR push/deploy secrets are added when staging deploy is automated.

## Cross-reference

- Previous: [stage-06-testing.md](stage-06-testing.md)
- Next: [stage-08-deployment.md](stage-08-deployment.md) (ACI staging — Member C; AKS — Member D)
