# Pipeline Stage 1 — Data

## Purpose

Ingest and version website monitoring telemetry so training and drift detection use reproducible, traceable datasets.

## Data source

- Synthetic generator: `scripts/generate_sample_data.py` → `data/raw/website_monitoring.csv`
- Production path: HTTP/metrics ingestion via `scripts/ingest_data.py` (Azure Blob upload)

Features: `response_time_ms`, `status_code`, `error_rate`, `latency_p95_ms`, `request_count`, `cpu_usage_percent`, `memory_usage_percent`, target `outage_within_1h`.

## Data versioning

- **DVC** tracks the raw CSV and produces `.dvc` pointer files.
- **Azure Blob Storage** (`stwoutagemlops`) stores versioned artifacts for team sharing and CI.
- Dataset hash recorded in evaluation artifacts for reproducibility.

## DVC / Azure Blob relationship

```
Local CSV → dvc add → .dvc metadata → (optional) dvc push → Azure Blob container
```

Setup: `py scripts/setup_dvc.py` (use `--skip-remote` for local-only).

## How data feeds training

1. `load_data.py` reads raw CSV.
2. `preprocess.py` / `validate_data.py` clean and validate schema.
3. `build_features.py` splits train/test.
4. `train_model.py` consumes processed matrices.

## Key files

| File | Role |
|------|------|
| `scripts/generate_sample_data.py` | Demo dataset |
| `scripts/ingest_data.py` | Blob upload pipeline |
| `scripts/setup_dvc.py` | DVC + remote config |
| `src/data/load_data.py` | Load raw data |
| `src/data/preprocess.py` | Cleaning |
| `src/data/validate_data.py` | Schema checks |

## Demo talking points

- Member A: show DVC status and Blob container structure.
- Explain why versioning matters when drift baseline is derived from training data.

## Detail

[../stages/stage-01-ingestion.md](../stages/stage-01-ingestion.md)
