# Pipeline Stage 6 — Deployment

## Purpose

Promote the gated container image from registry to runnable endpoints: ACI for staging validation, AKS for production traffic.

## Staging — Azure Container Instances

`infra/deploy_aci.py`:

- Pulls image from ACR
- Exposes public FQDN on port 8000
- Waits for `/health` when `--wait-health`

```powershell
py infra/deploy_aci.py --wait-health
# http://<dns-label>.<region>.azurecontainer.io:8000/health
```

## Production — Azure Kubernetes Service

`infra/deploy_aks.py`:

- Renders `infra/k8s/deployment.yaml` + `service.yaml`
- LoadBalancer Service maps port 80 → container 8000
- Requires `gate_passed: true` before deploy

```powershell
py infra/deploy_aks.py --wait-health
# http://<external-ip>/health
```

## API prediction flow

```
Client → LoadBalancer → AKS Pod → FastAPI /predict
  → inference.py loads model → features_from_request()
  → predict_outage() → JSON { outage_probability, risk_level }
```

Observations optionally logged for drift (`append_observation`).

## Local equivalent (no Azure)

```powershell
py scripts/run_local.py
curl -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" -d "{...metrics...}"
```

## Azure status

| Step | Status |
|------|--------|
| Scripts and K8s manifests in repo | ✅ Complete |
| Live ACI deploy | **Pending — Azure setup phase** |
| Live AKS deploy + external IP | **Pending — Azure setup phase** |
| Ingress / TLS (optional) | Documented; LoadBalancer used by default |

## Key files

| File | Role |
|------|------|
| `infra/deploy_aci.py` | Staging |
| `infra/deploy_aks.py` | Production |
| `infra/k8s/deployment.yaml` | Pod spec |
| `infra/k8s/service.yaml` | LoadBalancer |
| `.github/workflows/deploy.yml` | CD workflow |

## Detail

[../stages/stage-08-deployment.md](../stages/stage-08-deployment.md)
