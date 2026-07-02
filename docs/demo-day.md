# Demo Day Checklist

Full pipeline rehearsal for the team of 4. Each member presents their section; **Member D closes with monitoring, drift, and OpenRouter**.

## Pre-demo setup

```powershell
cd MLOPS-azure-final-project1
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt

py scripts/generate_sample_data.py
py scripts/train_model.py
py scripts/evaluate_model.py
py scripts/register_model.py
py scripts/build_image.py --acr <acr> --tag v1.0.0 --push
py infra/deploy_aci.py --wait-health
py infra/deploy_aks.py --wait-health
```

Set `OPENROUTER_API_KEY` before the OpenRouter demo.

## Presentation order

| # | Member | Demo moment |
|---|--------|-------------|
| 1 | A | DVC pointer, Blob upload, reference/current CSVs |
| 2 | B | MLflow run, quality gate pass, registry |
| 3 | C | Docker build, ACI staging `/predict`, CI green |
| 4 | D | **Drift report + alert + OpenRouter summary** |

## Member D — three demo moments

### 1. Drift report

```powershell
py scripts/run_drift_check.py
start reports/drift/drift_report.html
```

**Say:** "Reference baseline from training vs current production snapshot — Evidently flags feature drift."

### 2. Alert firing

Show one of:

- **Azure Portal** → Monitor → Alerts → fired alert on failed requests
- **GitHub Actions** → Drift Check workflow → failed run with error annotation

**Say:** "When drift is detected or API errors spike, the pipeline notifies the team."

### 3. OpenRouter summary

```powershell
$env:OPENROUTER_API_KEY = "<key>"
py scripts/openrouter_report.py --drift-report reports/drift/drift_summary.json
type reports\openrouter\openrouter_eval_summary.md
```

**Say:** "The LLM turns metrics and drift into an actionable summary for stakeholders."

### Bonus — live App Insights

Hit AKS `/predict` while showing Application Insights Live Metrics in Azure Portal.

## Failure demo (optional)

```powershell
py scripts/evaluate_model.py --force-fail
py scripts/openrouter_report.py
type reports\openrouter\openrouter_failure_analysis.md
```

Shows deploy blocking + LLM failure analysis.

## Release tag

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Architecture slide

Use the rendered PNGs in [docs/architecture/images/](architecture/images/) (or Mermaid in [docs/architecture/README.md](architecture/README.md)):

| Slide | File | Use for |
|-------|------|---------|
| Full pipeline | `01-end-to-end-pipeline.png` | Team overview (Members A–D) |
| AKS flow | `02-production-request-flow.png` | Live `/predict` + App Insights |
| Member D demo | `03-drift-alert-openrouter.png` | Drift → alert → OpenRouter |
| Azure map | `04-azure-resources.png` | Deployed resources in `rg-website-outage-mlops` |

Re-render after diagram edits:

```bash
python3.11 scripts/render_architecture_diagrams.py
```
