# Pipeline Stage 8 — OpenRouter Integration

## Purpose

Generate human-readable evaluation and drift summaries for stakeholders using an LLM (via OpenRouter), turning raw metrics into actionable narrative.

## Why OpenRouter is included

- Demonstrates LLM integration in an MLOps pipeline (not just batch scoring)
- Produces demo-ready markdown for instructors and ops managers
- Failure path (`gate_passed: false`) triggers remediation-oriented prompts

## Where it connects

```
eval_metrics.json ──┐
drift_summary.json ─┼→ openrouter_service.py → openrouter_eval_summary.md
dataset hash ───────┘
```

| Entry | Path |
|-------|------|
| Dashboard | OpenRouter Summary card → `POST /reports/openrouter/run` |
| CLI | `py scripts/openrouter_report.py` |
| CI | `.github/workflows/openrouter-report.yml` |

Output: `artifacts/reports/openrouter_eval_summary.md` + `.meta.json`

## API key storage

**Never commit keys.** Use:

| Environment | Location |
|-------------|----------|
| Local dev | `$env:OPENROUTER_API_KEY` (PowerShell) |
| GitHub Actions | Repository Secret `OPENROUTER_API_KEY` |
| Production | Same GitHub Secret consumed by workflow |

Config reference only: `configs/monitoring_config.yaml` → `api_key_env: OPENROUTER_API_KEY`

## Fallback without key

If no key is set, the service writes a **local fallback** report with structured metrics — demo works offline.

## Key files

| File | Role |
|------|------|
| `src/api/openrouter_service.py` | API + fallback |
| `scripts/openrouter_report.py` | CLI wrapper |
| `src/monitoring/llm_prompts.py` | Prompt templates |

## Detail

[../stages/stage-10-openrouter.md](../stages/stage-10-openrouter.md)
