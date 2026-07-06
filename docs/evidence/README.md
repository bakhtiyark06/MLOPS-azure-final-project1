# Evidence Folder

Store grading screenshots and artifacts here. **Do not commit real API keys or credentials** in any file.

## Naming convention

```
evidence-01-ci-badge.png
evidence-02-pr-history.png
evidence-03-branch-protection.png
evidence-04-release-v1.0.0.png
evidence-05-aml-training-logs.png      # Pending — Azure setup phase
evidence-06-quality-gate-fail.png
evidence-07-model-registry.png         # Pending — Azure setup phase
evidence-08-acr-image.png              # Pending — Azure setup phase
evidence-09-aks-predict.png            # Pending — Azure setup phase
evidence-10-drift-report.png
evidence-11-azure-monitor-alert.png    # Pending — Azure setup phase
evidence-12-openrouter-summary.png
```

## What to capture now (no Azure)

- CI passing badge (GitHub Actions or README badge when `main` is green)
- Pull request history
- Branch protection rules
- Local drift report (`drift_report.html` or dashboard screenshot)
- OpenRouter summary from dashboard (local fallback is valid)
- Quality gate pass/fail from `eval_metrics.json` or `--force-fail` run

## What to capture in Azure phase

See [screenshots-needed.md](screenshots-needed.md) for the full list marked **Pending — Azure setup phase**.

## Git policy

Teams may either:

- Commit PNGs to `docs/evidence/` for submission, or
- Keep screenshots in a private team drive and link in the submission portal

If committing, scrub any URLs or keys visible in browser screenshots.

## Security audit

Repository secret scan: no real credentials found in tracked files (placeholders and env var names only). Re-run before submission if new config files are added.
