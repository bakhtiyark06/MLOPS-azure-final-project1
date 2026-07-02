# Stage 10 — OpenRouter LLM Reports (Member D)

## What this stage does

Uses [OpenRouter](https://openrouter.ai/) to generate human-readable reports from:

- Model evaluation metrics (`eval_metrics.json`)
- Optional drift summary (`reports/drift/drift_summary.json`)

## File

| File | Purpose |
|------|---------|
| `scripts/openrouter_report.py` | Call OpenRouter API and write markdown reports |

## Prerequisites

1. Evaluation completed: `py scripts/evaluate_model.py`
2. Optional drift check: `py scripts/run_drift_check.py`
3. OpenRouter API key in environment (never commit)

## Environment variables

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | Required — API authentication |
| `OPENROUTER_MODEL` | Optional — default `openai/gpt-4o-mini` |
| `OPENROUTER_BASE_URL` | Optional — default OpenRouter API URL |

## Generate reports

### Evaluation summary (gate passed)

```powershell
$env:OPENROUTER_API_KEY = "<your-key>"
py scripts/evaluate_model.py
py scripts/openrouter_report.py
```

Output: `reports/openrouter/openrouter_eval_summary.md`

### Failure analysis (gate failed demo)

```powershell
py scripts/evaluate_model.py --force-fail
py scripts/openrouter_report.py --eval-metrics data/processed/eval_metrics.json
```

Outputs:

- `reports/openrouter/openrouter_eval_summary.md`
- `reports/openrouter/openrouter_failure_analysis.md`

### With drift context

```powershell
py scripts/run_drift_check.py
py scripts/openrouter_report.py --drift-report reports/drift/drift_summary.json
```

## Dry run (no API call)

```powershell
py scripts/openrouter_report.py --dry-run
```

Prints prompts without calling OpenRouter — useful for debugging.

## Demo script

1. Show `eval_metrics.json` with metrics and thresholds
2. Run `py scripts/openrouter_report.py`
3. Open `reports/openrouter/openrouter_eval_summary.md` and read the LLM summary aloud
4. Optional: run `--force-fail` path to show failure analysis narrative

## Cross-reference

- Monitoring + drift: [stage-09-monitoring.md](stage-09-monitoring.md)
- Azure secrets setup: [../azure-setup.md](../azure-setup.md)
