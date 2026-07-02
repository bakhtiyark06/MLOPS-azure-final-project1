# Stage 06 — API Testing (Member C)

## What this stage does

Member C adds **pytest** coverage for the FastAPI service:

- `GET /health` — ok vs degraded when model missing
- `POST /predict` — valid prediction response
- Validation errors (422) for bad input
- Service unavailable (503) when model not loaded

## Files

| File | Purpose |
|------|---------|
| `tests/test_api.py` | API endpoint tests |
| `pyproject.toml` | Coverage threshold ≥70% |

## Run tests

```powershell
py scripts/generate_sample_data.py
py scripts/train_model.py
py -m pytest tests/test_api.py -v
```

Full suite with coverage:

```powershell
py -m pytest --cov=src --cov=scripts --cov-fail-under=70
```

## Cross-reference

- Previous: [stage-05-containerization.md](stage-05-containerization.md)
- Next: [stage-07-cicd.md](stage-07-cicd.md)
