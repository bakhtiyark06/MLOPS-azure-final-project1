# Stage 03 — Quality Gate (Evaluation) (Member B)

## What this stage does

Member B **evaluates** the trained model on the holdout test set and **blocks bad models** from deploying:

1. **Load** `models/outage_model.joblib` and `data/processed/test_set.csv`
2. **Compute** F1 score (binary) and accuracy on the holdout set
3. **Compare** metrics against thresholds in `configs/model_config.yaml`
4. **Write** `data/processed/eval_metrics.json` for DVC and registry gating
5. **Exit code 1** if the gate fails — no registry or deployment allowed

## Quality gate thresholds

From `configs/model_config.yaml`:

| Metric | Minimum |
|--------|---------|
| F1 score (binary) | 0.75 |
| Accuracy | 0.80 |

## Files Member B owns (Stage 03)

| File | Purpose |
|------|---------|
| `scripts/evaluate_model.py` | CLI entrypoint for evaluation + gate |
| `src/models/evaluate.py` | Metrics, gate logic, eval_metrics.json writer |
| `configs/model_config.yaml` | `quality_gate` thresholds |

## Prerequisites

```powershell
py scripts/train_model.py
```

## How to run locally (step by step)

### Step 1 — Evaluate (pass)

```powershell
py scripts/evaluate_model.py
```

**You should see:**
- Holdout F1 score and accuracy
- `QUALITY GATE PASSED`
- `data/processed/eval_metrics.json` with `"gate_passed": true`

### Step 2 — Demo gate failure (`--force-fail`)

```powershell
py scripts/evaluate_model.py --force-fail
```

**You should see:**
- `QUALITY GATE FAILED (--force-fail demo)`
- `Bad models cannot proceed to registry or deployment.`
- Exit code **1**
- `eval_metrics.json` updated with `"gate_passed": false` and `"force_fail_demo": true`

This flag simulates a bad model for presentations without retraining with poor hyperparameters.

### Step 3 — Re-run pass before registry

```powershell
py scripts/evaluate_model.py
```

Registry (Stage 04) requires `gate_passed: true`.

### Step 4 — Run via DVC

```powershell
dvc repro evaluate
```

## eval_metrics.json format

```json
{
  "f1_score": 0.89,
  "accuracy": 0.91,
  "gate_passed": true,
  "thresholds": {
    "min_f1_score": 0.75,
    "min_accuracy": 0.80
  }
}
```

On failure, `gate_failure_reasons` lists which thresholds were not met.

## What can go wrong

| Problem | Fix |
|---------|-----|
| `Model not found` | Run `py scripts/train_model.py` first |
| `Test set not found` | Training writes `data/processed/test_set.csv` |
| Gate fails on real metrics | Tune model or thresholds; synthetic data should pass by default |
| Registry blocked after `--force-fail` | Re-run evaluate without `--force-fail` |

## Demo script (Member B — quality gate portion)

1. Show thresholds in `configs/model_config.yaml`
2. Run `py scripts/evaluate_model.py` — show `gate_passed: true`
3. Open `data/processed/eval_metrics.json`
4. Run `py scripts/evaluate_model.py --force-fail` — show exit code 1 and blocked message
5. Explain: CI and registry read `gate_passed` before any deploy

## Cross-reference

- Previous stage: [stage-02-training.md](stage-02-training.md)
- Next stage: [stage-04-registry.md](stage-04-registry.md)
