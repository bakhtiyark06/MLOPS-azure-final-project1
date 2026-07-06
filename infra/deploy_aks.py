#!/usr/bin/env python3
# Author: Member D — AKS production deployment
# Purpose: Deploy the API container to Azure Kubernetes Service

"""Deploy the outage prediction API to Azure Kubernetes Service (production)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
K8S_DIR = Path(__file__).resolve().parent / "k8s"

AZ_CLI = "az.cmd" if sys.platform == "win32" else "az"
KUBECTL = "kubectl.exe" if sys.platform == "win32" else "kubectl"


def _env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value or ""


def build_image_reference(acr_name: str, image_name: str, tag: str) -> str:
    return f"{acr_name}.azurecr.io/{image_name}:{tag}"


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def get_aks_credentials(
    resource_group: str, cluster_name: str, subscription_id: str | None = None
) -> None:
    cmd = [
        AZ_CLI,
        "aks",
        "get-credentials",
        "--resource-group",
        resource_group,
        "--name",
        cluster_name,
        "--overwrite-existing",
    ]
    if subscription_id:
        cmd.extend(["--subscription", subscription_id])
    result = run(cmd)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())


def render_manifest(template_path: Path, replacements: dict[str, str]) -> str:
    content = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        content = content.replace(f"${{{key}}}", value)
    return content


def create_acr_pull_secret(namespace: str, acr_name: str) -> None:
    """Create or update Kubernetes secret for ACR image pulls."""
    username = _env("ACR_USERNAME")
    password = _env("ACR_PASSWORD")
    if not username or not password:
        print("WARNING: ACR_USERNAME/ACR_PASSWORD not set — skipping image pull secret", file=sys.stderr)
        return

    server = f"{acr_name}.azurecr.io"
    run([KUBECTL, "delete", "secret", "acr-secret", "-n", namespace], check=False)
    run(
        [
            KUBECTL,
            "create",
            "secret",
            "docker-registry",
            "acr-secret",
            f"--docker-server={server}",
            f"--docker-username={username}",
            f"--docker-password={password}",
            f"--namespace={namespace}",
        ],
        check=False,
    )


def apply_manifests(
    namespace: str,
    image: str,
    app_insights_connection_string: str = "",
    acr_name: str | None = None,
) -> None:
    replacements = {
        "IMAGE": image,
        "APPLICATIONINSIGHTS_CONNECTION_STRING": app_insights_connection_string,
    }
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for name in ("deployment.yaml", "service.yaml"):
            src = K8S_DIR / name
            rendered = render_manifest(src, replacements)
            out = tmp_path / name
            out.write_text(rendered, encoding="utf-8")

        run([KUBECTL, "create", "namespace", namespace], check=False)
        if acr_name:
            create_acr_pull_secret(namespace, acr_name)
        for name in ("deployment.yaml", "service.yaml"):
            run([KUBECTL, "apply", "-n", namespace, "-f", str(tmp_path / name)])


def wait_for_rollout(namespace: str, deployment: str = "outage-predictor", timeout_sec: int = 300) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        result = run(
            [
                KUBECTL,
                "rollout",
                "status",
                f"deployment/{deployment}",
                "-n",
                namespace,
                "--timeout=30s",
            ],
            check=False,
        )
        if result.returncode == 0:
            print(f"Deployment '{deployment}' is ready in namespace '{namespace}'")
            return True
        time.sleep(5)
    print(f"Rollout timed out for deployment/{deployment}", file=sys.stderr)
    return False


def get_service_external_ip(namespace: str, service: str = "outage-predictor", timeout_sec: int = 300) -> str | None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        result = run(
            [
                KUBECTL,
                "get",
                "svc",
                service,
                "-n",
                namespace,
                "-o",
                "jsonpath={.status.loadBalancer.ingress[0].ip}",
            ],
            check=False,
        )
        ip = (result.stdout or "").strip()
        if ip:
            return ip
        time.sleep(10)
    return None


def wait_for_health(host: str, timeout_sec: int = 180) -> bool:
    import urllib.error
    import urllib.request

    url = f"http://{host}/health"
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                if response.status == 200:
                    print(f"Health check OK: {url}")
                    return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5)
    print(f"Health check timed out: {url}", file=sys.stderr)
    return False


def check_quality_gate(eval_metrics_path: Path) -> bool:
    import json

    if not eval_metrics_path.exists():
        print(f"ERROR: Eval metrics not found at {eval_metrics_path}", file=sys.stderr)
        print("Run scripts/evaluate_model.py first (Member B sign-off required).", file=sys.stderr)
        return False

    with open(eval_metrics_path, encoding="utf-8") as f:
        metrics = json.load(f)

    if not metrics.get("gate_passed"):
        reasons = metrics.get("gate_failure_reasons", ["unknown"])
        print("ERROR: Quality gate failed — deploy blocked.", file=sys.stderr)
        for reason in reasons:
            print(f"  - {reason}", file=sys.stderr)
        return False

    print("Quality gate passed — deploy allowed.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy outage prediction API to Azure Kubernetes Service")
    parser.add_argument("--subscription-id", default=_env("AZURE_SUBSCRIPTION_ID"))
    parser.add_argument("--resource-group", default=_env("AZURE_RESOURCE_GROUP", required=True))
    parser.add_argument("--cluster-name", default=_env("AKS_CLUSTER_NAME", required=True))
    parser.add_argument("--namespace", default=_env("AKS_NAMESPACE", "outage-predictor"))
    parser.add_argument("--acr", default=_env("ACR_NAME"))
    parser.add_argument("--image", default=_env("IMAGE_NAME", "outage-predictor"))
    parser.add_argument("--tag", default=_env("IMAGE_TAG", "latest"))
    parser.add_argument(
        "--app-insights-connection-string",
        default=_env("APPLICATIONINSIGHTS_CONNECTION_STRING", ""),
    )
    parser.add_argument(
        "--eval-metrics",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "eval_metrics.json",
    )
    parser.add_argument("--skip-gate-check", action="store_true", help="Skip quality gate (not for production)")
    parser.add_argument("--wait-health", action="store_true")
    args = parser.parse_args()

    if not args.subscription_id:
        print("ERROR: AZURE_SUBSCRIPTION_ID or --subscription-id is required", file=sys.stderr)
        return 1
    if not args.acr:
        print("ERROR: ACR_NAME or --acr is required", file=sys.stderr)
        return 1

    if not args.skip_gate_check and not check_quality_gate(args.eval_metrics):
        return 1

    image = build_image_reference(args.acr, args.image, args.tag)
    print(f"Deploying image: {image}")
    print(f"Cluster: {args.cluster_name} | Namespace: {args.namespace}")

    get_aks_credentials(args.resource_group, args.cluster_name, args.subscription_id)
    apply_manifests(args.namespace, image, args.app_insights_connection_string or "", args.acr)

    if not wait_for_rollout(args.namespace):
        return 1

    external_ip = get_service_external_ip(args.namespace)
    if external_ip:
        print(f"Production API: http://{external_ip}/health")
        if args.wait_health and not wait_for_health(external_ip):
            return 1
    else:
        print("LoadBalancer IP not ready yet. Check with:")
        print(f"  kubectl get svc outage-predictor -n {args.namespace}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
