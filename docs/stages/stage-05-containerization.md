# Stage 05 — Containerization (Member C)

## What this stage does

Member C packages the approved outage model as a **FastAPI** service and **Docker** image:

1. Load `models/outage_model.joblib` (Member B)
2. Expose `GET /health` and `POST /predict`
3. Accept the same 7 monitoring features defined in `configs/model_config.yaml`
4. Build a container image for ACI staging deploy

## Files Member C owns (Stage 05)

| File | Purpose |
|------|---------|
| `src/api/main.py` | FastAPI app with `/health` and `/predict` |
| `src/api/schemas.py` | Pydantic request/response models |
| `src/api/inference.py` | Model load + prediction helpers |
| `Dockerfile` | Container image definition |
| `scripts/build_image.py` | Build/push image to ACR |

## Prerequisites

```powershell
py scripts/generate_sample_data.py
py scripts/train_model.py
py scripts/evaluate_model.py
```

## Run API locally

```powershell
py -m uvicorn src.api.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for Swagger UI.

### Example predict request

```json
{
  "response_time_ms": 850,
  "status_code": 500,
  "error_rate": 0.12,
  "latency_p95_ms": 1200,
  "request_count": 4200,
  "cpu_usage_percent": 78,
  "memory_usage_percent": 81
}
```

## Docker

```powershell
py scripts/build_image.py --image outage-predictor --tag v1
docker run --rm -p 8000:8000 outage-predictor:v1
```

Push to ACR:

```powershell
py scripts/build_image.py --acr <acr-name> --tag v1 --push
```

## Cross-reference

- Previous: [stage-04-registry.md](stage-04-registry.md)
- Next: [stage-06-testing.md](stage-06-testing.md)
