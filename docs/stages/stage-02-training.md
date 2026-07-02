# Stage 02 — Model Training + MLflow (Member B)

## What this stage does

Member B trains the **outage prediction model** and logs the run to MLflow:

1. **Load** raw data from Member A (`load_raw_data()`)
2. **Preprocess** and split into train/test holdout sets
3. **Train** a `RandomForestClassifier` per `configs/model_config.yaml`
4. **Save** `models/outage_model.joblib` and `data/processed/test_set.csv`
5. **Log** hyperparameters, metrics, and model artifact to MLflow

## Files Member B owns (Stage 02)

| File | Purpose |
|------|---------|
| `scripts/train_model.py` | CLI entrypoint for training |
| `src/features/build_features.py` | Feature prep (delegates to Member A preprocess) |
| `src/models/train.py` | Build, fit, and serialize sklearn model |
| `configs/model_config.yaml` | Hyperparameters and feature list |
| `configs/azure_config.yaml` | MLflow experiment name (shared with registry) |

## Prerequisites

Complete Stage 01 first:

```powershell
py scripts/generate_sample_data.py
py scripts/ingest_data.py --skip-blob --skip-dvc
```

## How to run locally (step by step)

### Step 1 — Activate environment

```powershell
cd c:\Users\bakht\MLOps Azure Final Project\MLOPS-azure-final-project1
.\.venv\Scripts\Activate.ps1
```

### Step 2 — Train the model

```powershell
py scripts/train_model.py
```

**You should see:**
- Row counts for train and test splits
- `Model saved: models/outage_model.joblib`
- `Test set saved: data/processed/test_set.csv`
- Training F1 score and accuracy printed to console
- MLflow experiment name and `mlruns/` directory path

### Step 3 — View MLflow runs (optional)

```powershell
mlflow ui
```

Open `http://localhost:5000` and inspect the latest run: params, metrics, and model artifact.

### Step 4 — Run via DVC

```powershell
dvc repro train
```

## Expected artifacts

| Artifact | Path |
|----------|------|
| Trained model | `models/outage_model.joblib` |
| Holdout test set | `data/processed/test_set.csv` |
| MLflow runs | `mlruns/` (gitignored) |

## MLflow configuration

- **Default tracking:** local file store at `./mlruns`
- **Experiment name:** from `configs/azure_config.yaml` → `mlflow_experiment_name`
- **Azure ML tracking (optional):** set `MLFLOW_TRACKING_URI` to your workspace URI when credentials are configured

Logged parameters include `n_estimators`, `max_depth`, `random_state`, feature list, and `dataset_hash` from Stage 01.

## Azure resources used

| Resource | Config key |
|----------|------------|
| MLflow experiment | `mlflow_experiment_name` in `configs/azure_config.yaml` |

## GitHub Secrets (optional for Azure ML tracking)

| Secret | Used for |
|--------|----------|
| `AZURE_SUBSCRIPTION_ID` | Azure ML workspace auth |
| `AZURE_CLIENT_ID` | Service principal |
| `AZURE_CLIENT_SECRET` | Service principal |
| `AZURE_TENANT_ID` | Service principal |

## What can go wrong

| Problem | Fix |
|---------|-----|
| `Raw data not found` | Run Stage 01 (`generate_sample_data.py`) first |
| `Config not found: azure_config.yaml` | Ensure `configs/azure_config.yaml` exists |
| Low train metrics | Regenerate data; synthetic labels are correlated with features |
| `mlflow` import error | `pip install -r requirements.txt` |

## Demo script (Member B — training portion)

1. Show `configs/model_config.yaml` — features and RandomForest hyperparameters
2. Run `py scripts/train_model.py` live
3. Point at printed F1 and accuracy on the train set
4. Open `mlflow ui` or show `mlruns/` folder with logged artifact

## Cross-reference

- Previous stage: [stage-01-ingestion.md](stage-01-ingestion.md) (Member A)
- Next stage: [stage-03-evaluation.md](stage-03-evaluation.md) (quality gate)
