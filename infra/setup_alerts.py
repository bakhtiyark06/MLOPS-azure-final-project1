#!/usr/bin/env python3
# Author: Member D — Azure Monitor alert provisioning
# Purpose: Create Action Group and metric alert for API monitoring / drift

"""Provision Azure Monitor alerts for the outage prediction pipeline."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any


def _env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value or ""


def create_action_group(
    credential: Any,
    subscription_id: str,
    resource_group: str,
    action_group_name: str,
    email_receiver: str,
    location: str = "global",
) -> str:
    """Create or update an Azure Monitor Action Group."""
    from azure.mgmt.monitor import MonitorManagementClient
    from azure.mgmt.monitor.models import ActionGroupResource, EmailReceiver

    client = MonitorManagementClient(credential, subscription_id)
    resource_id = (
        f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        f"/providers/Microsoft.Insights/actionGroups/{action_group_name}"
    )

    group = ActionGroupResource(
        location=location,
        group_short_name=action_group_name[:12],
        enabled=True,
        email_receivers=[
            EmailReceiver(
                name="primary-email",
                email_address=email_receiver,
                use_common_alert_schema=True,
            )
        ],
    )

    print(f"Creating/updating Action Group '{action_group_name}'...")
    client.action_groups.create_or_update(resource_group, action_group_name, group)
    return resource_id


def create_failed_requests_alert(
    credential: Any,
    subscription_id: str,
    resource_group: str,
    app_insights_name: str,
    action_group_id: str,
    alert_name: str = "outage-predictor-high-failed-requests",
    threshold: float = 5.0,
) -> None:
    """Create a metric alert on failed requests in Application Insights."""
    from azure.mgmt.monitor import MonitorManagementClient
    from azure.mgmt.monitor.models import (
        MetricAlertAction,
        MetricAlertResource,
        MetricAlertSingleResourceMultipleMetricCriteria,
        MetricCriteria,
    )

    client = MonitorManagementClient(credential, subscription_id)
    app_insights_id = (
        f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        f"/providers/microsoft.insights/components/{app_insights_name}"
    )

    criteria = MetricCriteria(
        name="FailedRequests",
        metric_namespace="microsoft.insights/components",
        metric_name="requests/failed",
        operator="GreaterThan",
        threshold=threshold,
        time_aggregation="Count",
        dimensions=[],
    )

    alert = MetricAlertResource(
        location="global",
        description="Alert when failed API requests exceed threshold (Member D demo)",
        severity=2,
        enabled=True,
        scopes=[app_insights_id],
        evaluation_frequency="PT5M",
        window_size="PT15M",
        criteria=MetricAlertSingleResourceMultipleMetricCriteria(all_of=[criteria]),
        actions=[
            MetricAlertAction(
                action_group_id=action_group_id,
                web_hook_properties={},
            )
        ],
    )

    print(f"Creating/updating metric alert '{alert_name}'...")
    client.metric_alerts.create_or_update(resource_group, alert_name, alert)


def print_drift_alert_instructions() -> None:
    """Print instructions for drift-based alerting via GitHub Actions."""
    print(
        "\nDrift alert: schedule .github/workflows/drift-check.yml "
        "or run `python scripts/run_drift_check.py` in CI.\n"
        "Non-zero exit triggers GitHub Actions failure notification "
        "(configure repo email notifications or a webhook Action Group)."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision Azure Monitor alerts")
    parser.add_argument("--subscription-id", default=_env("AZURE_SUBSCRIPTION_ID"))
    parser.add_argument("--resource-group", default=_env("AZURE_RESOURCE_GROUP", required=True))
    parser.add_argument(
        "--action-group-name",
        default=_env("ALERT_ACTION_GROUP_NAME", "outage-predictor-alerts"),
    )
    parser.add_argument("--email", default=_env("ALERT_EMAIL"), help="Alert notification email")
    parser.add_argument(
        "--app-insights-name",
        default=_env("APP_INSIGHTS_NAME", "outage-predictor-insights"),
    )
    parser.add_argument("--failed-request-threshold", type=float, default=5.0)
    parser.add_argument("--skip-metric-alert", action="store_true")
    args = parser.parse_args()

    if not args.subscription_id:
        print("ERROR: AZURE_SUBSCRIPTION_ID is required", file=sys.stderr)
        return 1
    if not args.email:
        print("ERROR: --email or ALERT_EMAIL is required", file=sys.stderr)
        return 1

    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()
    action_group_id = create_action_group(
        credential,
        args.subscription_id,
        args.resource_group,
        args.action_group_name,
        args.email,
    )

    if not args.skip_metric_alert:
        try:
            create_failed_requests_alert(
                credential,
                args.subscription_id,
                args.resource_group,
                args.app_insights_name,
                action_group_id,
                threshold=args.failed_request_threshold,
            )
        except Exception as exc:
            print(f"WARNING: Could not create metric alert: {exc}", file=sys.stderr)
            print("Ensure Application Insights resource exists and name is correct.")

    print_drift_alert_instructions()
    print("Alert setup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
