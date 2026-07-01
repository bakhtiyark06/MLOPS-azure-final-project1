# Stage 01 — Data Ingestion and Versioning (Member A)

## What this stage does

Member A owns the **data layer** of the pipeline:

1. **Generate** synthetic website monitoring data (response time, errors, CPU, etc.)
2. **Validate** the CSV schema before anything downstream uses it
3. **Upload** the dataset to **Azure Blob Storage**
4. **Version** the dataset with **DVC** (Data Version Control)
5. **Record** a dataset hash and ingestion metadata for the Model Registry (Member B)

## Files Member A owns

| File | Purpose |
|------|---------|
| `scripts/generate_sample_data.py` | Create `data/raw/website_monitoring.csv` + reference/current snapshots |
| `scripts/ingest_data.py` | Validate, hash, upload to Blob, DVC track, write metadata |
| `scripts/setup_dvc.py` | `dvc init` + configure Azure Blob remote (Python, no manual steps) |
| `src/data/load_data.py` | Load CSV from disk or download from Blob |
| `src/data/validate_data.py` | Schema validation against `configs/model_config.yaml` |
| `configs/data_config.yaml` | Data paths, blob name, row counts (no secrets) |
| `dvc.yaml` | DVC pipeline: generate → ingest → train → evaluate |
| `.github/workflows/data-ingest.yml` | CI job for Member A stage |
| `tests/test_data_ingestion.py` | Unit tests for this stage |

## How to run locally (step by step)

### Step 1 — Activate environment

```powershell
cd c:\Users\ameer\MlOps-website-prediction\MLOPS-azure-final-project1
.\.venv\Scripts\Activate.ps1
```

### Step 2 — Initialize DVC (one time)

```powershell
py scripts/setup_dvc.py --skip-remote
```

Use without `--skip-remote` when `AZURE_STORAGE_CONNECTION_STRING` is set.

### Step 3 — Generate data

```powershell
py scripts/generate_sample_data.py
```

**You should see:**
- `data/raw/website_monitoring.csv` (2000 rows by default)
- `data/reference/reference.csv` (500 rows for drift baseline)
- `data/processed/current.csv` (300 rows for drift demo)

### Step 4 — Ingest and version (local, no Azure)

```powershell
py scripts/ingest_data.py --skip-blob --skip-dvc
```

**You should see:**
- `Data validation passed`
- `Dataset SHA256: <64-char hash>`
- `data/raw/dataset_hash.txt`
- `data/raw/ingestion_metadata.json`

### Step 5 — Full ingest with Azure + DVC (when credentials ready)

```powershell
$env:AZURE_STORAGE_CONNECTION_STRING = "<from Azure Portal or GitHub Secret>"
py scripts/setup_dvc.py
py scripts/ingest_data.py
```

**You should see:**
- Blob upload confirmation
- `DVC tracked: ...`
- `DVC push to Azure remote succeeded` (if remote configured)

### Step 6 — Run Member A tests

```powershell
py -m pytest tests/test_data_ingestion.py -v
```

## Azure resources used

| Resource | Name (from `configs/azure_config.yaml`) |
|----------|----------------------------------------|
| Storage Account | `stwebsiteoutagemlops` |
| Blob Container | `datasets` |
| Blob path | `raw/website_monitoring.csv` |
| DVC remote prefix | `azure://datasets/dvc-storage` |

## GitHub Secrets required (Member A)

| Secret | Used for |
|--------|----------|
| `AZURE_STORAGE_CONNECTION_STRING` | Blob upload + DVC remote push |

## How Stage 01 connects to Stage 02 (Member B)

```
generate_sample_data.py
        ↓
data/raw/website_monitoring.csv
        ↓
ingest_data.py (hash + Blob + DVC)
        ↓
dataset_hash.txt  ──→  Model Registry tags (Member B)
        ↓
train_model.py reads load_raw_data()
```

Member B runs `py scripts/train_model.py` — it calls `load_raw_data()` which reads the CSV Member A produced.

## What can go wrong

| Problem | Fix |
|---------|-----|
| `Data not found` | Run `py scripts/generate_sample_data.py` first |
| `Data validation failed` | CSV missing columns — regenerate with `generate_sample_data.py` |
| `DVC not initialized` | Run `py scripts/setup_dvc.py` |
| Blob upload skipped | Set `AZURE_STORAGE_CONNECTION_STRING` |
| `dvc: command not found` | `pip install dvc` or use project venv |
| Use `py` not `python` on Windows | Your machine needs the `py` launcher |

## Demo script (Member A presentation)

1. Show `configs/data_config.yaml` and `configs/model_config.yaml`
2. Run `py scripts/generate_sample_data.py` live
3. Run `py scripts/ingest_data.py` — show hash + metadata JSON
4. Open Azure Portal → Storage → `datasets` container → show uploaded blob
5. Show `website_monitoring.csv.dvc` pointer file in git (not the CSV itself)
6. Run `py -m pytest tests/test_data_ingestion.py -v`

## Cross-reference

- Next stage: [stage-02-training.md](stage-02-training.md) (Member B)
- Azure setup: [../azure-setup.md](../azure-setup.md)
