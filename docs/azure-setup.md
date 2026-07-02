# Azure Setup — Production Resources (Member D)

Provisioning guide for AKS, Application Insights, alerts, and GitHub Secrets.

## Your team's Azure values (pre-configured)

| Setting | Value |
|---------|--------|
| Subscription | `4c3c4430-0ce6-48bc-8e33-1947f3876ebd` |
| Resource group | `rg-website-outage-mlops` |
| Location | `centralus` |
| Storage account | `stwoutagemlops` |
| ACR | `acrwoutagemlops` |
| App Insights | `outage-predictor-insights` |
| AKS cluster | `aks-outage-predictor` |
| AKS node size | `standard_b2s_v2` (required for this subscription) |

## One-command local setup

```bash
az login
cd MLOPS-azure-final-project1
source scripts/setup_azure_env.sh
```

This writes `.env` and `configs/azure_config.yaml` with your connection strings.

| Resource | Purpose | Suggested name |
|----------|---------|----------------|
| Azure Kubernetes Service | Production API hosting | `aks-outage-predictor` |
| Application Insights | API telemetry | `outage-predictor-insights` |
| Action Group | Alert notifications | `outage-predictor-alerts` |
| Container Registry | Already created by team (Member C) | `acroutagepredictor` |

Member C's ACI staging uses the same ACR image that AKS will deploy.

## Azure CLI — quick provision

```bash
# Variables
RG="<your-resource-group>"
LOCATION="eastus"
AKS_NAME="aks-outage-predictor"
ACR_NAME="<your-acr>"
APP_INSIGHTS="outage-predictor-insights"

# AKS cluster (attach to existing ACR)
az aks create \
  --resource-group $RG \
  --name $AKS_NAME \
  --node-count 2 \
  --enable-addons monitoring \
  --attach-acr $ACR_NAME \
  --generate-ssh-keys

# Application Insights (if not created by AKS monitoring addon)
az monitor app-insights component create \
  --app $APP_INSIGHTS \
  --location $LOCATION \
  --resource-group $RG

# Get connection string
az monitor app-insights component show \
  --app $APP_INSIGHTS \
  --resource-group $RG \
  --query connectionString -o tsv
```

## GitHub Secrets

Add these in **Settings → Secrets and variables → Actions**:

| Secret | Purpose |
|--------|---------|
| `AZURE_CREDENTIALS` | Service principal JSON for `azure/login` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription |
| `AZURE_RESOURCE_GROUP` | Resource group name |
| `AZURE_WORKSPACE_NAME` | ML workspace (Member B registry) |
| `ACR_NAME` | Container registry name |
| `AKS_CLUSTER_NAME` | AKS cluster name |
| `AKS_NAMESPACE` | Kubernetes namespace (default: `outage-predictor`) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights connection string |
| `OPENROUTER_API_KEY` | OpenRouter API key (optional in CI) |

### Service principal for GitHub Actions

```bash
az ad sp create-for-rbac \
  --name "github-mlops-outage-predictor" \
  --role contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/<resource-group> \
  --sdk-auth
```

Paste the JSON output as `AZURE_CREDENTIALS`.

## Local environment variables

```powershell
$env:AZURE_SUBSCRIPTION_ID = "<subscription-id>"
$env:AZURE_RESOURCE_GROUP = "<resource-group>"
$env:AKS_CLUSTER_NAME = "aks-outage-predictor"
$env:AKS_NAMESPACE = "outage-predictor"
$env:ACR_NAME = "<acr-name>"
$env:IMAGE_TAG = "latest"
$env:APPLICATIONINSIGHTS_CONNECTION_STRING = "<connection-string>"
$env:OPENROUTER_API_KEY = "<openrouter-key>"
$env:ALERT_EMAIL = "you@example.com"
```

## Deploy and verify

```powershell
py scripts/generate_sample_data.py
py scripts/train_model.py
py scripts/evaluate_model.py
py scripts/build_image.py --acr <acr> --tag v1 --push
py infra/deploy_aks.py --wait-health
```

## Alert setup

```powershell
py infra/setup_alerts.py --email you@example.com
```

## Related docs

- [stage-08-deployment.md](stages/stage-08-deployment.md)
- [stage-09-monitoring.md](stages/stage-09-monitoring.md)
- [architecture/README.md](architecture/README.md)
