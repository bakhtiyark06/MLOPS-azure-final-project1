# Final Submission Checklist

Status on the **test** branch. Repo-side items are documented below; live Azure demo evidence is pending final rehearsal.

---

## Completed / repo-side items

| Item | Status | Notes |
|------|--------|-------|
| Clean GitHub repository | Complete | Active development on `test` |
| Root README | Complete | [README.md](../README.md) |
| GitHub Actions workflows | Complete | 6 workflows in `.github/workflows/` |
| Dockerfile | Complete | Root `Dockerfile` |
| Pytest suite | Complete | ≥70% coverage gate in CI |
| CI badge in README | Complete | Green when `main` CI passes |
| No secrets committed | Complete | Placeholders only |
| `docs/` folder structure | Complete | Submission index, pipeline, architecture, evidence |
| Architecture diagram | Complete | `architecture-diagram.mmd` + interactive `/demo/flow` |
| Python author tags | Partial | See [code-documentation/audit-report.md](code-documentation/audit-report.md) |

---

## Pending — demo rehearsal items

| Item | Live Verification |
|------|-------------------|
| Branch protection evidence | Pending final demo run |
| PR history screenshot | Pending final demo run |
| Tagged release v1.0.0 | Pending final demo run |
| Full team demo rehearsal | Pending final demo run |
| Azure ML training logs screenshot | Pending final demo run |
| Model registry screenshot | Pending final demo run |
| ACR image screenshot | Pending final demo run |
| AKS / API demo screenshot | Pending final demo run |
| Azure Monitor alert screenshot | Pending final demo run |
| OpenRouter integration screenshot | Pending final demo run |
| Evidently drift report (local OK; Azure schedule optional) | Pending final demo run |

---

## Final submission items

| Item | Status |
|------|--------|
| Merge `test` → `main` | If required by instructor |
| Evidence PNGs in `docs/evidence/` | Pending final demo run |
| Instructor submission portal | TODO — add course link |
| CI green on `main` | After merge and secrets configured |

---

## Quick verification commands

```powershell
py -m pytest tests/test_architecture_page.py -q
py scripts/check_local.py
py scripts/audit_python_docs.py
```

Azure setup (when ready for live verification):

```powershell
az login
py scripts/build_image.py --acr acrwoutagemlops --tag v1.0.0 --push
py infra/deploy_aks.py --wait-health
```
