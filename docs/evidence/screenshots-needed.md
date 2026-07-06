# Screenshots Needed for Final Submission

Use this list when collecting evidence. Save files per [README.md](README.md) naming convention.

| # | Screenshot | Status | How to capture |
|---|------------|--------|----------------|
| 1 | CI passing badge | Repo-ready | GitHub Actions `CI` workflow green on `main`, or README badge |
| 2 | Pull request history | Pending — demo rehearsal | GitHub → Pull requests |
| 3 | Branch protection | Pending — demo rehearsal | GitHub → Settings → Branches → rule screenshot |
| 4 | Release tag v1.0.0 | Pending — demo rehearsal | GitHub → Releases or `git tag -l` |
| 5 | Azure ML training logs | **Pending — Azure setup phase** | Azure Portal → ML workspace → Experiment run |
| 6 | Quality gate failure | **Complete (local)** | `docs/evidence/evidence-06-quality-gate-fail.json` |
| 7 | Model registry | **Pending — Azure setup phase** | Azure ML → Models → `website-outage-model` |
| 8 | Docker registry image | **Pending — Azure setup phase** | ACR `acrwoutagemlops` → Repositories |
| 9 | AKS endpoint test | **Pending — Azure setup phase** | `curl http://<lb-ip>/health` + `/predict` response |
| 10 | Evidently drift report | **Complete (local)** | `docs/evidence/evidence-10-drift-report.html` |
| 11 | Azure Monitor alert | **Pending — Azure setup phase** | Portal → Monitor → Alerts → fired rule |
| 12 | OpenRouter integration | **Complete (local)** | `docs/evidence/evidence-12-openrouter-summary.md` |

## Optional bonus evidence

- Application Insights Live Metrics during `/predict` traffic
- Architecture Explorer `/demo/flow` during presentation
- GitHub `drift-check.yml` failed run with annotation
- MLflow UI local experiment view

## Checklist cross-reference

Update [submission-checklist.md](../submission-checklist.md) as each screenshot is captured.
