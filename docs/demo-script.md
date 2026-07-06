# Live Demo Script — Team of 4

**Duration:** ~15–20 minutes · **Branch:** `test` (local demo) or `main` + Azure (Phase 2)

> The trainer may choose presentation order. **Every member must be able to explain every section**, not only their own.

**Interactive opener (recommended):** http://127.0.0.1:8000/demo/flow — Architecture Explorer with Live Flow animation.

**Local setup before demo:**

```powershell
py scripts/generate_sample_data.py
py scripts/train_model.py
py scripts/evaluate_model.py
py scripts/run_local.py
```

---

## Member A — GitHub, branches, CI trigger

**Suggested segment (~3 min)**

1. Show GitHub repository structure and `docs/README.md` index.
2. Explain branch workflow: feature branches → PR → `main`; current work on `test`.
3. Open **Actions** → `CI` workflow (`ci.yml`): pytest, coverage ≥70%, Docker build smoke test.
4. Point to `.github/workflows/` — train, deploy, drift-check, openrouter-report.

**Say:** "Every push to `main` runs automated tests before any deploy. Bad code never reaches production."

**Backup talking points**

- DVC tracks `data/raw/website_monitoring.csv`; Blob upload via `data-ingest.yml`.
- Reference/current CSVs feed drift detection later in the pipeline.
- No secrets in repo — only env var names in configs.

**Azure (Phase 2):** Show Blob container `stwoutagemlops` in Portal.

---

## Member B — Tests, training, quality gate

**Suggested segment (~4 min)**

1. Run or show green pytest: `py -m pytest -q`.
2. Walk through `scripts/train_model.py` → `models/outage_model.joblib`.
3. Show MLflow experiment (local or Azure ML workspace when configured).
4. Open `data/processed/eval_metrics.json` — highlight `gate_passed: true` and F1 threshold.
5. Optional failure demo: `py scripts/evaluate_model.py --force-fail`.

**Say:** "The quality gate blocks registry and deploy if F1 or accuracy falls below configured thresholds."

**Backup talking points**

- Features: response time, status code, error rate, latency P95, request count, CPU, memory.
- `scripts/register_model.py` refuses to register when `gate_passed` is false.
- Deploy workflow reads the same gate before AKS promotion.

---

## Member C — Docker, API, deployment flow

**Suggested segment (~4 min)**

1. Show `Dockerfile` — Python 3.11, copies `models/`, runs uvicorn.
2. `docker build` or CI docker-build job artifact.
3. Open Swagger: http://127.0.0.1:8000/docs — `POST /predict` with healthy vs outage payload.
4. Dashboard: URL check + prediction cards.
5. Explain ACI staging → AKS production path (scripts in `infra/`).

**Say:** "Same container image goes to ACR, then ACI for staging validation, then AKS for production LoadBalancer."

**Backup talking points**

- FastAPI loads `outage_model.joblib` at startup; 503 if model missing.
- `scripts/build_image.py --acr <name> --push` for registry.
- CI badge in README links to automated test pipeline.

**Azure (Phase 2):** `curl http://<aks-ip>/health` and live `/predict`.

---

## Member D — Drift, OpenRouter, end-to-end close

**Suggested segment (~5 min)**

1. Dashboard **Drift Summary** or `GET /drift` — Evidently report, drift score.
2. Open `artifacts/reports/drift_report.html` in browser.
3. **OpenRouter Summary** card or `POST /reports/openrouter/run` — show markdown preview.
4. Explain observation log: predictions append to `current_observations.csv`; drift after 5+ rows.
5. Close with monitoring: App Insights + Azure Monitor alerts (Portal when Azure phase done).

**Say:** "Drift compares training baseline to production observations. OpenRouter turns metrics into a stakeholder-ready narrative."

**Backup talking points**

- `drift-check.yml` runs on schedule in CI.
- `OPENROUTER_API_KEY` in GitHub Secrets only; local fallback without key.
- `infra/setup_alerts.py` provisions email alerts on API failures.

**Azure (Phase 2):** Fired alert screenshot + Application Insights Live Metrics.

---

## Common trainer questions

| Question | Short answer |
|----------|--------------|
| What blocks a bad model from production? | Quality gate in `eval_metrics.json`; registry and `deploy.yml` check `gate_passed`. |
| Where are secrets stored? | GitHub Actions Secrets and local env vars — never in git. |
| How is drift detected? | Evidently compares `reference.csv` baseline to current observations/production snapshot. |
| Why Docker? | Reproducible API runtime; same image in ACI staging and AKS production. |
| What if OpenRouter is down? | Local fallback report; API still returns structured summary without LLM. |
| How do you version data? | DVC + Azure Blob; dataset hash in eval artifacts. |

---

## Final end-to-end walkthrough (~2 min)

**Any member can deliver this closing script:**

1. Developer commits code → GitHub Actions runs pytest and Docker build.
2. Data ingested and versioned → training produces `outage_model.joblib`.
3. Evaluation writes metrics → gate must pass before registry.
4. Docker image pushed to ACR → ACI staging → AKS production.
5. User sends metrics to `/predict` → outage probability returned.
6. Observations accumulate → Evidently flags drift → alerts notify the team.
7. OpenRouter generates an executive summary for remediation decisions.

**Closing line:** "This is a complete MLOps loop: build, validate, deploy, monitor, and explain — with automation at every gate."

---

## Related docs

- [demo-day.md](demo-day.md) — rehearsal commands
- [submission-checklist.md](submission-checklist.md) — evidence still needed
- [evidence/screenshots-needed.md](evidence/screenshots-needed.md)
