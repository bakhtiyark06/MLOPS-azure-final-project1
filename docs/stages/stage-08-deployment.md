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
- AKS production deploy: Member D (below)

---

# AKS production deploy (Member D)

## What this stage does

Promote the same ACR image from ACI staging to **Azure Kubernetes Service** for production. Deploy is blocked unless Member B's quality gate passed.

## Files

| File | Purpose |
|------|---------|
| `infra/deploy_aks.py` | Deploy to AKS via kubectl |
| `infra/k8s/deployment.yaml` | Kubernetes Deployment manifest |
| `infra/k8s/service.yaml` | LoadBalancer Service |
| `.github/workflows/deploy.yml` | CD workflow (gate check + AKS deploy) |

## Prerequisites

1. Member B sign-off: `gate_passed: true` in `data/processed/eval_metrics.json`
2. Image in ACR (`py scripts/build_image.py --acr <acr> --push`)
3. AKS cluster provisioned — see [../azure-setup.md](../azure-setup.md)
4. `az` CLI and `kubectl` installed locally

## Environment variables

| Variable | Purpose |
|----------|---------|
| `AZURE_SUBSCRIPTION_ID` | Azure subscription |
| `AZURE_RESOURCE_GROUP` | Target resource group |
| `AKS_CLUSTER_NAME` | AKS cluster name |
| `AKS_NAMESPACE` | Kubernetes namespace (default: `outage-predictor`) |
| `ACR_NAME` | Container registry |
| `IMAGE_TAG` | Image tag to deploy |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Optional App Insights on pods |

## Deploy

```powershell
$env:AZURE_SUBSCRIPTION_ID = "<subscription-id>"
$env:AZURE_RESOURCE_GROUP = "<resource-group>"
$env:AKS_CLUSTER_NAME = "aks-outage-predictor"
$env:ACR_NAME = "<acr-name>"
$env:IMAGE_TAG = "v1"

py scripts/evaluate_model.py
py infra/deploy_aks.py --wait-health
```

## Demo — hit production API

```powershell
curl http://<load-balancer-ip>/health

curl -X POST http://<load-balancer-ip>/predict `
  -H "Content-Type: application/json" `
  -d '{"response_time_ms":850,"status_code":500,"error_rate":0.12,"latency_p95_ms":1200,"request_count":4200,"cpu_usage_percent":78,"memory_usage_percent":81}'
```

## Cross-reference

- Monitoring + drift: [stage-09-monitoring.md](stage-09-monitoring.md)
- OpenRouter reports: [stage-10-openrouter.md](stage-10-openrouter.md)
