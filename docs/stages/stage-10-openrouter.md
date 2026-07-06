# Stage 10 — OpenRouter LLM Reports (Member D)

## What this stage does

Uses [OpenRouter](https://openrouter.ai/) to generate human-readable reports from:

- Model evaluation metrics (`eval_metrics.json`)
- Drift summary (`artifacts/reports/drift_summary.json` or `reports/drift/drift_summary.json`)
- Dataset hash (`data/raw/dataset_hash.txt` or `ingestion_metadata.json`)

## Files

| File | Purpose |
|------|---------|
| `scripts/openrouter_report.py` | CLI entry point for report generation |
| `src/api/openrouter_service.py` | Shared generation logic (API + CLI) |

## Prerequisites

1. Evaluation completed: `py scripts/evaluate_model.py`
2. Optional drift check: `py scripts/run_drift_check.py` or dashboard drift refresh
3. OpenRouter API key in environment (optional — local fallback works without it)

## Environment variables

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | API authentication (GitHub Secret in CI; never commit) |
| `OPENROUTER_MODEL` | Optional — default `openai/gpt-4o-mini` |
| `OPENROUTER_BASE_URL` | Optional — default OpenRouter API URL |

## Canonical output path

Dashboard and API use:

`artifacts/reports/openrouter_eval_summary.md`

Metadata sidecar: `artifacts/reports/openrouter_eval_summary.meta.json`

## API routes (local hub)

| Route | Purpose |
|-------|---------|
| `GET /reports/openrouter` | Return markdown content + metadata if generated |
| `POST /reports/openrouter/run` | Generate report (OpenRouter API or local fallback) |

The API **never** returns or logs the API key.

## Generate reports

### Dashboard (recommended)

1. Open http://127.0.0.1:8000/
2. Scroll to **OpenRouter Summary**
3. Click **Generate OpenRouter Summary**
4. Use **View OpenRouter Report** to open the markdown file

### CLI — evaluation summary

```powershell
$env:OPENROUTER_API_KEY = "<your-key>"   # optional
py scripts/evaluate_model.py
py scripts/openrouter_report.py
```

Default output: `artifacts/reports/openrouter_eval_summary.md`

CI workflows can still use `--output-dir reports/openrouter` without changing workflow files.

### Local fallback (no API key)

```powershell
py scripts/openrouter_report.py
```

Writes a deterministic local report starting with:

> OpenRouter API key was not configured, so this report was generated locally.

Includes accuracy, F1, quality gate, dataset hash, drift status, drifted columns, deployment recommendation, risks, and next actions.

### Failure analysis (gate failed, API key required)

```powershell
py scripts/evaluate_model.py --force-fail
$env:OPENROUTER_API_KEY = "<your-key>"
py scripts/openrouter_report.py --output-dir reports/openrouter
```

Outputs:

- `openrouter_eval_summary.md`
- `openrouter_failure_analysis.md` (when gate failed and API key present)

### With drift context

```powershell
py scripts/run_drift_check.py
py scripts/openrouter_report.py
```

Drift summary is auto-discovered from `artifacts/reports/` or `reports/drift/`.

## Dry run (no API call)

```powershell
py scripts/openrouter_report.py --dry-run
```

Prints prompts and local fallback preview without calling OpenRouter.

## Demo script

1. Show `eval_metrics.json` with metrics and thresholds
2. Click **Generate OpenRouter Summary** on the dashboard (or run `py scripts/openrouter_report.py`)
3. Open `artifacts/reports/openrouter_eval_summary.md` and read the summary aloud
4. Optional: run `--force-fail` path to show failure analysis narrative (requires API key)

## Cross-reference

- Monitoring + drift: [stage-09-monitoring.md](stage-09-monitoring.md)
- Azure secrets setup: [../azure-setup.md](../azure-setup.md)
