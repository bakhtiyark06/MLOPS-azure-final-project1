# Member D — Azure Phase 2 deploy rehearsal (Windows)
# Prerequisites: az login, scripts/setup_azure_env.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$py = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "py" }

Write-Host "=== Azure Phase 2 — train, register, push, deploy ===" -ForegroundColor Cyan

& $py scripts/generate_sample_data.py
& $py scripts/train_model.py
& $py scripts/evaluate_model.py
& $py scripts/register_model.py
& $py scripts/build_image.py --acr acrwoutagemlops --tag v1.0.0 --push
& $py infra/deploy_aci.py --wait-health
& $py infra/deploy_aks.py --wait-health

Write-Host ""
Write-Host "Capture screenshots for docs/evidence/:" -ForegroundColor Yellow
Write-Host "  evidence-05-aml-training-logs.png  (Azure ML Experiments)"
Write-Host "  evidence-07-model-registry.png     (Azure ML Models)"
Write-Host "  evidence-08-acr-image.png          (ACR repositories)"
Write-Host "  evidence-09-aks-predict.png          (curl /health and /predict)"
Write-Host "  evidence-11-azure-monitor-alert.png  (Monitor alerts)"
