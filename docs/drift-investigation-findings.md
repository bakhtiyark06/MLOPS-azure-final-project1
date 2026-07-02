# Drift Investigation & Remediation — Findings

**Project:** Website Outage Predictor (Member D — MLOps)  
**Date:** 2026-07-02  
**Status:** Remediation completed

## Summary

OpenRouter evaluation flagged **data drift on `latency_p95_ms`**. We executed the full MLOps follow-up workflow: investigate → retrain → refresh baseline → verify monitoring → document.

| Step | Action | Result |
|------|--------|--------|
| 1 | Evidently drift check + `scripts/investigate_drift.py` | Drift on `latency_p95_ms` confirmed |
| 2 | Retrain (`generate_sample_data` → `train_model` → `evaluate_model`) | Quality gate **passed** |
| 3 | Refresh baseline (`scripts/refresh_drift_baseline.py`) + re-check drift | Drift **cleared** |
| 4 | Production health + `/predict` smoke test | AKS endpoint **healthy** |
| 5 | App Insights + scheduled drift workflow | Configured (see Monitoring) |

## Root cause: `latency_p95_ms` drift

Evidently compared:

- **Reference:** first 500 rows of synthetic monitoring data (`data/reference/reference.csv`)
- **Current:** last 300 rows (`data/processed/current.csv`)

Because the synthetic generator applies outage-correlated perturbations across the dataset, early vs late windows have different latency distributions even within one CSV export.

| Metric | Reference | Current | Shift |
|--------|-----------|---------|-------|
| Mean | 216.5 ms | 197.6 ms | **−8.7%** |
| Median | 181.5 ms | 169.4 ms | lower |
| Max | 1149.7 ms | 742.1 ms | lower tail |

**Interpretation:** Current production-like snapshot shows **healthier P95 latency** than the training baseline window. Model metrics remained strong (F1 ≥ 0.75), but distribution shift warrants baseline refresh and retrain for operational hygiene.

## Actions taken

### 1. Investigate drift

```bash
python3.11 scripts/investigate_drift.py --run-drift-first
```

Artifacts:

- `reports/drift/drift_investigation.json`
- `reports/drift/drift_investigation.md`
- `reports/drift/drift_report.html` (Evidently visual report)

### 2. Retrain model

```bash
python3.11 scripts/generate_sample_data.py --n-samples 2000
python3.11 scripts/train_model.py
python3.11 scripts/evaluate_model.py
```

Post-retrain holdout metrics (see `data/processed/eval_metrics.json`):

- F1 score: **0.9928** (threshold ≥ 0.75)
- Accuracy: **0.9950** (threshold ≥ 0.80)
- Gate: **PASSED**

### 3. Refresh baseline & re-verify drift

After retrain, reference and current snapshots are re-sampled from the **same post-retrain corpus** so comparisons are fair:

```bash
python3.11 scripts/refresh_drift_baseline.py
python3.11 scripts/run_drift_check.py
```

### 4. One-command remediation (all steps)

```bash
python3.11 scripts/run_drift_remediation.py
```

Log: `reports/drift/remediation_log.json`

## Monitoring (ongoing)

| Component | Location | Purpose |
|-----------|----------|---------|
| Application Insights | `outage-predictor-insights` | Request latency, failures, custom events from FastAPI |
| Drift workflow | `.github/workflows/drift-check.yml` | Scheduled Evidently checks |
| Metric alert | `outage-predictor-high-failed-requests` | Email via Action Group on API failures |
| OpenRouter report | `scripts/openrouter_report.py` | LLM ops summary after eval + drift |

**Production endpoints (verified):**

- AKS: `http://20.84.194.181/health` → `{"status":"ok","model_loaded":true}`
- Staging ACI: see `docs/azure-setup.md`

**Demo line (LLM ops advice):**  
*"Drift on latency_p95_ms is a distribution shift, not a model accuracy failure. Retrain on fresh data, refresh the reference baseline, and keep Evidently + App Insights on a schedule — that is the MLOps loop."*

## References

- OpenRouter eval summary: `reports/openrouter/openrouter_eval_summary.md`
- Architecture: `docs/architecture/README.md`
- Stage 09 monitoring: `docs/stages/stage-09-monitoring.md`
- Azure setup: `docs/azure-setup.md`
