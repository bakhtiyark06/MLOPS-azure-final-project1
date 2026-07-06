# Pipeline Stage 5 — Docker Build

## Purpose

Package the FastAPI inference service and trained model into a portable container for consistent staging and production deployments.

## Why Docker

- Same runtime on developer laptop, ACI, and AKS
- Immutable artifact tagged in ACR (`acrwoutagemlops.azurecr.io`)
- CI validates `docker build` on every main-branch push

## What the Dockerfile does

```dockerfile
FROM python:3.11-slim
COPY requirements.txt → pip install
COPY configs/ src/ models/
EXPOSE 8000
CMD uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Health check: `GET /health` inside container.

## CI/CD integration

1. `ci.yml` job `docker-build` runs after pytest passes.
2. `scripts/build_image.py --acr <name> --tag <tag> --push` for release builds.
3. `deploy.yml` deploys the tagged image to AKS when gate passes.

## Local commands

```powershell
docker build -t outage-predictor:local .
docker run -p 8000:8000 outage-predictor:local
py scripts/build_image.py --acr acrwoutagemlops --tag v1 --push   # Azure phase
```

## Key files

| File | Role |
|------|------|
| `Dockerfile` | Image definition |
| `scripts/build_image.py` | Build + ACR push |
| `.github/workflows/ci.yml` | Build smoke test |

## Detail

[../stages/stage-05-containerization.md](../stages/stage-05-containerization.md)
