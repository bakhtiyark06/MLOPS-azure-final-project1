# Pipeline Stage 4 — Model Registry

## Purpose

Register approved models in Azure ML Model Registry with version metadata so deployment consumes a known, gated artifact.

## Registration flow

1. Verify `eval_metrics.json` has `gate_passed: true`.
2. Upload `models/outage_model.joblib` to Azure ML.
3. Attach metadata: metrics, dataset hash, training config.

```powershell
py scripts/register_model.py
```

Registry name (config): `website-outage-model`.

## Versioning and metadata

Each registered version stores:

- Model file URI in Azure ML
- Evaluation metrics snapshot
- Timestamp and run correlation ID

## How deployment consumes the model

- **Docker image** embeds `models/outage_model.joblib` at build time (`COPY models/` in Dockerfile).
- **CI/CD** builds image only after gate pass.
- **AKS pods** load the bundled model at container start via `src/api/inference.py`.

Azure ML registry is the system of record; the container carries the runtime copy.

## Key files

| File | Role |
|------|------|
| `scripts/register_model.py` | Registration CLI |
| `src/models/registry.py` | Azure ML SDK calls |
| `configs/azure_config.yaml` | Workspace names (no secrets) |

## Azure status

**Pending — Azure setup phase:** Portal screenshot of registered model versions.

## Detail

[../stages/stage-04-registry.md](../stages/stage-04-registry.md)
