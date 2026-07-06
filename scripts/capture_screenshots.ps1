# Open browser tabs and print capture steps for submission evidence PNGs.
# Run: powershell -ExecutionPolicy Bypass -File .\scripts\capture_screenshots.ps1
# Save screenshots to: docs\evidence\  (Win+Shift+S)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EvidenceDir = Join-Path $ProjectRoot "docs\evidence"
$Repo = "https://github.com/bakhtiyark06/MLOPS-azure-final-project1"
$Sub = "4c3c4430-0ce6-48bc-8e33-1947f3876ebd"
$Rg = "rg-website-outage-mlops"

Write-Host ""
Write-Host "=== Submission screenshot helper ===" -ForegroundColor Cyan
Write-Host "Save each capture as PNG in: $EvidenceDir"
Write-Host "Use Win+Shift+S (Snipping Tool) - crop to the relevant panel only."
Write-Host "NEVER include API keys, connection strings, or passwords in screenshots."
Write-Host ""

$steps = @(
    @{
        File = "evidence-01-ci-badge.png"
        Title = "1. CI passing (GitHub Actions)"
        Url = "$Repo/actions/workflows/ci.yml"
        Hint = "Show the latest run on main with a green checkmark. README badge also works."
    },
    @{
        File = "evidence-02-pr-history.png"
        Title = "2. Pull request history"
        Url = "$Repo/pulls?q=is%3Apr+is%3Aclosed"
        Hint = 'Show merged PRs (e.g. PR number 6 test to main).'
    },
    @{
        File = "evidence-03-branch-protection.png"
        Title = "3. Branch protection"
        Url = "$Repo/settings/branches"
        Hint = "Screenshot the rule for main (require PR, status checks, etc.). Needs repo admin access."
    },
    @{
        File = "evidence-04-release-v1.0.0.png"
        Title = "4. Release tag v1.0.0"
        Url = "$Repo/releases/tag/v1.0.0"
        Hint = "If no GitHub Release page yet: Code -> Tags -> v1.0.0, or run: git tag -l"
    },
    @{
        File = "evidence-05-aml-training-logs.png"
        Title = "5. Azure ML training logs"
        Url = "https://ml.azure.com"
        Hint = "ML Azure -> mlw-website-outage -> Experiments -> website-outage-prediction -> latest run metrics."
    },
    @{
        File = "evidence-06-quality-gate-fail.png"
        Title = "6. Quality gate (pass or fail)"
        Url = "file:///$((Join-Path $EvidenceDir 'evidence-06-quality-gate-pass.json') -replace '\\','/')"
        Hint = "Open evidence-06-quality-gate-pass.json in browser OR screenshot eval_metrics.json / terminal QUALITY GATE PASSED."
    },
    @{
        File = "evidence-07-model-registry.png"
        Title = "7. Model registry"
        Url = "https://ml.azure.com"
        Hint = "mlw-website-outage -> Models -> website-outage-model -> Version 1 (accuracy/F1 tags)."
    },
    @{
        File = "evidence-08-acr-image.png"
        Title = "8. ACR Docker image"
        Url = 'https://portal.azure.com/#@/resource/subscriptions/' + $Sub + '/resourceGroups/' + $Rg + '/providers/Microsoft.ContainerRegistry/registries/acrwoutagemlops/repository'
        Hint = "Repositories -> outage-predictor -> tags v1.0.0 (and v1)."
    },
    @{
        File = "evidence-09-aks-predict.png"
        Title = "9. AKS endpoint test"
        Url = $null
        Hint = "Screenshot THIS terminal after running the predict test below."
    },
    @{
        File = "evidence-10-drift-report.png"
        Title = "10. Evidently drift report"
        Url = "file:///$((Join-Path $EvidenceDir 'evidence-10-drift-report.html') -replace '\\','/')"
        Hint = 'Open evidence-10-drift-report.html in Chrome/Edge - capture the drift summary panel.'
    },
    @{
        File = "evidence-11-azure-monitor-alert.png"
        Title = "11. Azure Monitor alert"
        Url = 'https://portal.azure.com/#view/Microsoft_Azure_Monitoring/AzureMonitoringBrowseBlade/~/alertsV2'
        Hint = "Monitor -> Alerts -> outage-predictor-high-failed-requests (rule definition is enough if not fired)."
    },
    @{
        File = "evidence-12-openrouter-summary.png"
        Title = "12. OpenRouter integration"
        Url = "file:///$((Join-Path $EvidenceDir 'evidence-12-openrouter-summary.md') -replace '\\','/')"
        Hint = 'Open evidence-12-openrouter-summary.md OR local dashboard at http://127.0.0.1:8000/'
    }
)

foreach ($s in $steps) {
    Write-Host "--- $($s.Title) ---" -ForegroundColor Yellow
    Write-Host "  Save as: $($s.File)"
    Write-Host "  $($s.Hint)"
    if ($s.Url) {
        Write-Host "  Opening: $($s.Url)"
        Start-Process $s.Url
        Start-Sleep -Seconds 2
    }
    Write-Host ""
}

Write-Host '=== Run this for screenshot 9 (AKS + ACI predict) ===' -ForegroundColor Cyan
$aks = "http://20.84.194.181"
$aci = "http://outage-predictor-staging.centralus.azurecontainer.io:8000"
$payload = '{"response_time_ms":850,"status_code":500,"error_rate":0.12,"latency_p95_ms":1200,"request_count":4200,"cpu_usage_percent":78,"memory_usage_percent":81}'
Write-Host "AKS /health:" -ForegroundColor Green
Invoke-RestMethod "$aks/health" | ConvertTo-Json
Write-Host "AKS /predict:" -ForegroundColor Green
Invoke-RestMethod -Method Post -Uri "$aks/predict" -Body $payload -ContentType "application/json" | ConvertTo-Json
Write-Host "ACI /health:" -ForegroundColor Green
Invoke-RestMethod "$aci/health" | ConvertTo-Json
Write-Host ""
Write-Host 'Screenshot the output above -> evidence-09-aks-predict.png' -ForegroundColor Yellow
Write-Host ""
Write-Host 'Optional: local hub for demo -> http://127.0.0.1:8000/  (run scripts/run_local.py first)' -ForegroundColor Gray
