# Stage 04 — Model Registry (Member B)

## What this stage does

Member B **registers the approved model** in the **Azure ML Model Registry**:

1. **Verify** `data/processed/eval_metrics.json` has `gate_passed: true`
2. **Load** dataset lineage hash from Stage 01 (`dataset_hash.txt` or `ingestion_metadata.json`)
3. **Register** `models/outage_model.joblib` in Azure ML
4. **Tag** the model version with `dataset_hash`, F1, accuracy, and stage metadata

Bad models are **blocked** — registration raises an error if the quality gate did not pass.

## Files Member B owns (Stage 04)

| File | Purpose |
|------|---------|
| `scripts/register_model.py` | CLI entrypoint for registry |
| `src/models/registry.py` | Azure ML `MLClient` registration logic |
| `configs/azure_config.yaml` | Workspace, resource group, model name |

## Prerequisites

1. Stage 01 ingest complete (dataset hash available)
2. Stage 02 training complete (`models/outage_model.joblib`)
3. Stage 03 evaluation passed (`gate_passed: true`)
4. `configs/azure_config.yaml` filled with your workspace values

```powershell
py scripts/generate_sample_data.py
py scripts/ingest_data.py --skip-blob --skip-dvc
py scripts/train_model.py
py scripts/evaluate_model.py
```

## Configure Azure ML

Edit `configs/azure_config.yaml`:

```yaml
subscription_id: "${AZURE_SUBSCRIPTION_ID}"
resource_group: "<your-rg>"
workspace_name: "<your-ml-workspace>"
model_registry_name: website-outage-model
```

Set environment variables locally:

```powershell
$env:AZURE_SUBSCRIPTION_ID = "<subscription-id>"
$env:AZURE_TENANT_ID = "<tenant-id>"
$env:AZURE_CLIENT_ID = "<client-id>"
$env:AZURE_CLIENT_SECRET = "<client-secret>"
```

Or use `az login` with `DefaultAzureCredential` for local development.

## How to run locally (step by step)

### Step 1 — Dry run (no Azure API call)

```powershell
py scripts/register_model.py --dry-run
```

**You should see:**
- `Dry run complete`
- Model name and tags including `dataset_hash`
- Confirmation that quality gate passed

### Step 2 — Register in Azure ML

```powershell
py scripts/register_model.py
```

**You should see:**
- `Model registration successful`
- Model name, version, ARM ID
- Tags: `dataset_hash`, `f1_score`, `accuracy`

### Step 3 — Verify in Azure Portal

1. Open **Azure Machine Learning** workspace
2. Go to **Models** → `website-outage-model`
3. Open latest version → **Tags** tab
4. Confirm `dataset_hash` matches `data/raw/dataset_hash.txt` from Stage 01

## Lineage flow

```
Stage 01: ingest_data.py
        ↓
dataset_hash.txt (SHA256)
        ↓
Stage 02: train_model.py (logs hash to MLflow)
        ↓
Stage 03: evaluate_model.py (gate_passed: true)
        ↓
Stage 04: register_model.py → Azure ML tag: dataset_hash
```

## GitHub Secrets required (Stage 04)

| Secret | Used for |
|--------|----------|
| `AZURE_SUBSCRIPTION_ID` | ML workspace subscription |
| `AZURE_CLIENT_ID` | Service principal auth |
| `AZURE_CLIENT_SECRET` | Service principal auth |
| `AZURE_TENANT_ID` | Service principal auth |

## What can go wrong

| Problem | Fix |
|---------|-----|
| `Quality gate did not pass` | Run `py scripts/evaluate_model.py` (without `--force-fail`) |
| `Dataset hash not found` | Run Stage 01 ingest |
| `AZURE_SUBSCRIPTION_ID is not set` | Set env var or fix `azure_config.yaml` |
| `resource_group` / `workspace_name` placeholder | Fill in real values in `azure_config.yaml` |
| Azure auth failure | Run `az login` or set service principal secrets |

## Demo script (Member B — registry portion)

1. Show `gate_passed: true` in `eval_metrics.json`
2. Show `dataset_hash` in `ingestion_metadata.json`
3. Run `py scripts/register_model.py --dry-run` then live registration
4. Azure Portal → Models → show version + `dataset_hash` tag
5. Explain lineage: same hash links data version to model version

## Cross-reference

- Previous stage: [stage-03-evaluation.md](stage-03-evaluation.md)
- Data handoff from: [stage-01-ingestion.md](stage-01-ingestion.md)
- Next stage: [stage-05-containerization.md](stage-05-containerization.md) (Member C — FastAPI)
