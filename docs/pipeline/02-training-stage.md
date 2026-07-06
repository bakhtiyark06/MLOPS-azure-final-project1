# Pipeline Stage 2 — Training

## Purpose

Train a Random Forest classifier to predict `outage_within_1h` from monitoring metrics and log the experiment for auditability.

## Training script

`scripts/train_model.py` orchestrates:

1. Load processed data via `prepare_training_data()`.
2. Call `src/models/train.py` → `train_model()`.
3. Save `models/outage_model.joblib`.
4. Save `data/processed/test_set.csv` for evaluation.
5. Log parameters and metrics to MLflow.

## Inputs and outputs

| Input | Output |
|-------|--------|
| `data/raw/website_monitoring.csv` | `models/outage_model.joblib` |
| `configs/model_config.yaml` | `data/processed/test_set.csv` |
| Random seed / hyperparameters | MLflow run ID and metrics |

## Metrics logged

- Accuracy, precision, recall, F1 (on holdout split)
- Feature importances
- Model path and config snapshot

## MLflow and quality gate connection

Training alone does not deploy. The next stage (`evaluate_model.py`) writes `eval_metrics.json` with `gate_passed`. MLflow run links training to evaluation for traceability.

## Key files

| File | Role |
|------|------|
| `scripts/train_model.py` | CLI entrypoint |
| `src/models/train.py` | sklearn training |
| `src/features/build_features.py` | Feature matrix |
| `.github/workflows/train.yml` | Remote training on Azure ML (Phase 2) |

## Demo talking points

- Member B: show MLflow UI or run log; explain hyperparameters from `model_config.yaml`.

## Detail

[../stages/stage-02-training.md](../stages/stage-02-training.md)
