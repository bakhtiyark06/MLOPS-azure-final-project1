#!/usr/bin/env python3
# Author: Member C — ACI staging deployment
# Purpose: Deploy the API container to Azure Container Instances

"""Deploy the API container to Azure Container Instances (staging)."""

from __future__ import annotations

import argparse
import os
import sys
import time

from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import (
    Container,
    ContainerGroup,
    ContainerGroupNetworkProtocol,
    EnvironmentVariable,
    ImageRegistryCredential,
    IpAddress,
    Port,
    ResourceRequests,
    ResourceRequirements,
)


def _env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value or ""


def build_image_reference(acr_name: str, image_name: str, tag: str) -> str:
    return f"{acr_name}.azurecr.io/{image_name}:{tag}"


def deploy_aci(
    *,
    subscription_id: str,
    resource_group: str,
    location: str,
    container_name: str,
    dns_label: str,
    image: str,
    cpu: float,
    memory_gb: float,
    acr_name: str | None = None,
) -> str:
    credential = DefaultAzureCredential()
    client = ContainerInstanceManagementClient(credential, subscription_id)

    container = Container(
        name=container_name,
        image=image,
        resources=ResourceRequirements(
            requests=ResourceRequests(cpu=cpu, memory_in_gb=memory_gb)
        ),
        ports=[Port(port=8000, protocol=ContainerGroupNetworkProtocol.tcp)],
    )

    image_registry_credentials = None
    if acr_name:
        registry_user = _env("ACR_USERNAME")
        registry_password = _env("ACR_PASSWORD")
        if registry_user and registry_password:
            image_registry_credentials = [
                ImageRegistryCredential(
                    server=f"{acr_name}.azurecr.io",
                    username=registry_user,
                    password=registry_password,
                )
            ]

    group = ContainerGroup(
        location=location,
        containers=[container],
        os_type="Linux",
        restart_policy="Always",
        ip_address=IpAddress(
            ports=[Port(port=8000, protocol=ContainerGroupNetworkProtocol.tcp)],
            type="Public",
            dns_name_label=dns_label,
        ),
        image_registry_credentials=image_registry_credentials,
    )

    print(f"Creating/updating ACI container group '{container_name}' in {resource_group}...")
    poller = client.container_groups.begin_create_or_update(resource_group, container_name, group)
    result = poller.result()
    fqdn = result.ip_address.fqdn
    print(f"Staging API: http://{fqdn}:8000/health")
    return fqdn


def wait_for_health(fqdn: str, timeout_sec: int = 180) -> bool:
    import urllib.error
    import urllib.request

    url = f"http://{fqdn}:8000/health"
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy outage prediction API to Azure Container Instances")
    parser.add_argument("--subscription-id", default=_env("AZURE_SUBSCRIPTION_ID"))
    parser.add_argument("--resource-group", default=_env("AZURE_RESOURCE_GROUP", required=True))
    parser.add_argument("--location", default=_env("AZURE_LOCATION", "eastus"))
    parser.add_argument("--container-name", default=_env("ACI_CONTAINER_NAME", "outage-predictor-staging"))
    parser.add_argument("--dns-label", default=_env("ACI_DNS_NAME_LABEL", "outage-predictor-staging"))
    parser.add_argument("--acr", default=_env("ACR_NAME"))
    parser.add_argument("--image", default=_env("IMAGE_NAME", "outage-predictor"))
    parser.add_argument("--tag", default=_env("IMAGE_TAG", "latest"))
    parser.add_argument("--cpu", type=float, default=float(_env("ACI_CPU", "1")))
    parser.add_argument("--memory-gb", type=float, default=float(_env("ACI_MEMORY_GB", "1.5")))
    parser.add_argument("--wait-health", action="store_true")
    args = parser.parse_args()

    if not args.subscription_id:
        print("ERROR: AZURE_SUBSCRIPTION_ID or --subscription-id is required", file=sys.stderr)
        return 1
    if not args.acr:
        print("ERROR: ACR_NAME or --acr is required", file=sys.stderr)
        return 1

    image = build_image_reference(args.acr, args.image, args.tag)
    fqdn = deploy_aci(
        subscription_id=args.subscription_id,
        resource_group=args.resource_group,
        location=args.location,
        container_name=args.container_name,
        dns_label=args.dns_label,
        image=image,
        cpu=args.cpu,
        memory_gb=args.memory_gb,
        acr_name=args.acr,
    )

    if args.wait_health and not wait_for_health(fqdn):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
