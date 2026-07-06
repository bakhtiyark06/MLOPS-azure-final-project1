# Final Submission Checklist

Status on **`main`** branch after local rehearsal automation.

---

## Completed / repo-side items

| Item | Status | Notes |
|------|--------|-------|
| Clean GitHub repository | Complete | [bakhtiyark06/MLOPS-azure-final-project1](https://github.com/bakhtiyark06/MLOPS-azure-final-project1) |
| Root README | Complete | [README.md](../README.md) |
| GitHub Actions workflows | Complete | 6 workflows in `.github/workflows/` |
| Dockerfile | Complete | Root `Dockerfile` |
| Pytest suite | Complete | ≥70% coverage gate in CI |
| CI badge in README | Complete | Points to `bakhtiyark06` org |
| No secrets committed | Complete | Placeholders only; `.env` gitignored |
| `docs/` folder structure | Complete | Submission index, pipeline, architecture, evidence |
| Architecture diagram | Complete | Mermaid PNGs + interactive `/demo/flow` |
| Python author tags | Complete | 63/63 — `py scripts/audit_python_docs.py` |
| Local evidence automation | Complete | `py scripts/collect_local_evidence.py` |
| Submission rehearsal script | Complete | `py scripts/run_submission_rehearsal.py` |
| Azure setup (Windows) | Complete | `scripts/setup_azure_env.ps1` + `run_azure_phase2.ps1` |
| MLflow → Azure ML tracking | Complete | Set `MLFLOW_TRACKING_URI` via setup script |

---

## Completed locally (evidence files)

After `py scripts/run_submission_rehearsal.py --allow-drift-fail`:

| Item | Evidence path |
|------|----------------|
| Quality gate pass | `docs/evidence/evidence-06-quality-gate-pass.json` |
| Evidently drift report | `docs/evidence/evidence-10-drift-report.html` |
| Drift summary JSON | `docs/evidence/evidence-10-drift-summary.json` |
| OpenRouter summary | `docs/evidence/evidence-12-openrouter-summary.md` |
| Manifest | `docs/evidence/evidence-manifest.json` |

**Still capture as PNG** (browser screenshots): CI badge, PR history, branch protection, release tag.

---

## Pending — requires GitHub / Azure Portal (manual)

| Item | How to complete |
|------|-----------------|
| Branch protection evidence | GitHub → Settings → Branches → screenshot |
| PR history screenshot | GitHub → Pull requests |
| Tagged release **v1.0.0** | `git tag v1.0.0 && git push origin v1.0.0` |
| Azure ML training logs | `az login` → `setup_azure_env.ps1` → train with `MLFLOW_TRACKING_URI` |
| Model registry screenshot | `py scripts/register_model.py` (no `--dry-run`) |
| ACR image screenshot | `py scripts/build_image.py --acr acrwoutagemlops --tag v1.0.0 --push` |
| AKS / API demo | `py scripts/run_azure_phase2.ps1` or `infra/deploy_aks.py` |
| Azure Monitor alert | `py infra/setup_alerts.py --email you@example.com` |
| Full team live demo | See [demo-script.md](demo-script.md) |

---

## Quick verification commands

```powershell
cd MLOPS-azure-final-project1
.\.venv\Scripts\python.exe scripts\run_submission_rehearsal.py --allow-drift-fail
.\.venv\Scripts\python.exe scripts\check_local.py
.\.venv\Scripts\python.exe scripts\run_local.py
```

Azure phase (after `az login`):

```powershell
.\scripts\setup_azure_env.ps1
.\scripts\run_azure_phase2.ps1
```

---

## Final submission items

| Item | Status |
|------|--------|
| Evidence PNGs in `docs/evidence/` | Partial — JSON/HTML collected; PNGs manual |
| Instructor submission portal | Add course link when provided |
| CI green on `main` | Verify on GitHub Actions after push |
