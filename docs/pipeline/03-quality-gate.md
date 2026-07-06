# Pipeline Stage 3 — Quality Gate

## Purpose

Prevent underperforming models from reaching the registry or production. The gate encodes minimum ML quality standards as automated policy.

## Why a quality gate exists

A model can train without error but still be unsafe to deploy (low F1, poor recall on outage class). The gate converts business thresholds into a binary pass/fail consumed by registry, deploy workflows, and OpenRouter reports.

## Thresholds checked

Configured in `configs/model_config.yaml` (typical checks):

- **F1 score** ≥ minimum threshold
- **Accuracy** ≥ minimum threshold

Results written to `data/processed/eval_metrics.json`:

```json
{
  "f1_score": 0.92,
  "accuracy": 0.94,
  "gate_passed": true,
  "gate_failure_reasons": []
}
```

## Pass/fail branch behavior

| `gate_passed` | Registry | Deploy (`deploy.yml`) | OpenRouter |
|---------------|----------|----------------------|------------|
| `true` | Allowed | Proceeds | Success summary |
| `false` | Blocked | Blocked | Failure analysis prompt |

## Blocking a bad model

```powershell
py scripts/evaluate_model.py --force-fail
```

- Sets `gate_passed: false` and `force_fail_demo: true`
- `register_model.py` raises `QualityGateError`
- `infra/deploy_aks.py` exits before kubectl apply

## Key files

| File | Role |
|------|------|
| `scripts/evaluate_model.py` | Run evaluation + gate |
| `src/models/evaluate.py` | Metric computation |
| `src/models/registry.py` | `assert_gate_passed()` |

## Demo talking points

- Show pass JSON, then `--force-fail` and explain deploy blockage.

## Detail

[../stages/stage-03-evaluation.md](../stages/stage-03-evaluation.md)
