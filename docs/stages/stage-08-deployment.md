# Stage 08 — Deployment (ACI staging — Member C)

## What this stage does

Member C deploys the Docker image to **Azure Container Instances** for staging validation before Member D promotes to AKS.

## File

| File | Purpose |
|------|---------|
| `infra/deploy_aci.py` | Create/update ACI container group |

## Prerequisites

1. Image pushed to ACR (`py scripts/build_image.py --acr <acr> --push`)
2. Azure credentials (`az login` or service principal env vars)
3. Resource group and subscription configured

## Environment variables

| Variable | Purpose |
|----------|---------|
| `AZURE_SUBSCRIPTION_ID` | Azure subscription |
| `AZURE_RESOURCE_GROUP` | Target resource group |
| `ACR_NAME` | Container registry name |
| `IMAGE_TAG` | Image tag to deploy |
| `ACI_DNS_NAME_LABEL` | Public DNS label for staging URL |
| `ACR_USERNAME` / `ACR_PASSWORD` | Optional ACR pull credentials |

## Deploy

```powershell
$env:AZURE_SUBSCRIPTION_ID = "<subscription-id>"
$env:AZURE_RESOURCE_GROUP = "<resource-group>"
$env:ACR_NAME = "<acr-name>"
$env:IMAGE_TAG = "v1"

py infra/deploy_aci.py --wait-health
```

## Demo — hit staging API

```powershell
curl http://<dns-label>.<region>.azurecontainer.io:8000/health

curl -X POST http://<fqdn>:8000/predict `
  -H "Content-Type: application/json" `
  -d '{"response_time_ms":850,"status_code":500,"error_rate":0.12,"latency_p95_ms":1200,"request_count":4200,"cpu_usage_percent":78,"memory_usage_percent":81}'
```

## Cross-reference

- Container build: [stage-05-containerization.md](stage-05-containerization.md)
- AKS production deploy: Member D (`infra/deploy_aks.py`)
