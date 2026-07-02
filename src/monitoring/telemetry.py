# Author: Member D — Application Insights telemetry
# Purpose: Bootstrap Azure Monitor OpenTelemetry for the FastAPI service

"""Application Insights / Azure Monitor telemetry setup."""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_telemetry_configured = False


def get_app_insights_connection_string() -> Optional[str]:
    """Return Application Insights connection string from environment."""
    return os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING") or None


def setup_telemetry(service_name: str = "outage-predictor-api") -> bool:
    """
    Configure Azure Monitor OpenTelemetry when connection string is set.

    Args:
        service_name: Logical service name for telemetry resource attributes.

    Returns:
        True if telemetry was configured, False if skipped (no connection string).
    """
    global _telemetry_configured
    if _telemetry_configured:
        return True

    connection_string = get_app_insights_connection_string()
    if not connection_string:
        logger.info(
            "APPLICATIONINSIGHTS_CONNECTION_STRING not set — telemetry disabled"
        )
        return False

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(
            connection_string=connection_string,
            resource_attributes={"service.name": service_name},
        )
        _telemetry_configured = True
        logger.info("Application Insights telemetry configured for %s", service_name)
        return True
    except Exception as exc:
        logger.warning("Failed to configure Application Insights: %s", exc)
        return False


def instrument_fastapi(app) -> None:
    """
    Attach OpenTelemetry FastAPI instrumentation when available.

    Args:
        app: FastAPI application instance.
    """
    if not _telemetry_configured:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI OpenTelemetry instrumentation enabled")
    except ImportError:
        logger.info(
            "opentelemetry-instrumentation-fastapi not installed — "
            "using Azure Monitor auto-instrumentation only"
        )
    except Exception as exc:
        logger.warning("FastAPI instrumentation failed: %s", exc)
