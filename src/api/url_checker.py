# Author: Member D — public URL metrics probe
# Purpose: Safely measure public HTTP metrics for dashboard demo

"""Validate URLs and probe public website metrics."""

from __future__ import annotations

import ipaddress
import socket
import statistics
from urllib.parse import urlparse

import httpx

from src.api.schemas import UrlMetricsResponse

BLOCKED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "metadata.google.internal",
}
METADATA_IP = "169.254.169.254"
DEFAULT_CPU_MEMORY = 50.0
PROBE_COUNT = 5
REQUEST_TIMEOUT = 10.0


class UrlValidationError(ValueError):
    """Raised when a URL is not allowed for probing."""


def _is_private_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or str(ip) == METADATA_IP
    )


def validate_public_url(url: str) -> str:
    """
    Validate that a URL is safe to probe from the demo dashboard.

    Args:
        url: User-supplied URL.

    Returns:
        Normalized URL string.

    Raises:
        UrlValidationError: If the URL is invalid or blocked.
    """
    if not url or not url.strip():
        raise UrlValidationError("URL is required.")

    normalized = url.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in ("http", "https"):
        raise UrlValidationError("URL must start with http:// or https://.")
    if not parsed.netloc:
        raise UrlValidationError("URL must include a valid host name.")

    host = parsed.hostname
    if host is None:
        raise UrlValidationError("URL must include a valid host name.")

    host_lower = host.lower()
    if host_lower in BLOCKED_HOSTS:
        raise UrlValidationError("Local and internal URLs are not allowed.")
    if host_lower.endswith(".local"):
        raise UrlValidationError("Local network host names are not allowed.")

    if _is_private_ip(host_lower):
        raise UrlValidationError("Private IP addresses are not allowed.")

    try:
        for info in socket.getaddrinfo(host, None):
            resolved = info[4][0]
            if _is_private_ip(resolved) or resolved == METADATA_IP:
                raise UrlValidationError(
                    "URL resolves to a private or blocked IP address."
                )
    except socket.gaierror as exc:
        raise UrlValidationError(f"Could not resolve host name: {host}") from exc

    return normalized


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    index = max(0, int(round(0.95 * len(sorted_vals))) - 1)
    return sorted_vals[min(index, len(sorted_vals) - 1)]


def probe_url_metrics(url: str) -> UrlMetricsResponse:
    """
    Send repeated HTTP requests and derive public metrics for prediction.

    Args:
        url: Validated public URL.

    Returns:
        UrlMetricsResponse with measured and demo-default fields.
    """
    durations_ms: list[float] = []
    status_codes: list[int] = []
    errors = 0

    with httpx.Client(
        follow_redirects=True,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": "OutagePredictorDemo/1.0"},
    ) as client:
        for _ in range(PROBE_COUNT):
            try:
                with client.stream("GET", url) as response:
                    status_codes.append(response.status_code)
                    elapsed_ms = response.elapsed.total_seconds() * 1000
                    durations_ms.append(elapsed_ms)
                    for _ in response.iter_bytes():
                        pass
            except httpx.HTTPError:
                errors += 1
                status_codes.append(0)

    if not durations_ms and errors == PROBE_COUNT:
        raise UrlValidationError(
            "Could not reach the website. Check the URL and try again."
        )

    measured_durations = durations_ms or [0.0]
    valid_statuses = [code for code in status_codes if code > 0]
    status_code = float(valid_statuses[-1] if valid_statuses else 0)
    response_time_ms = float(statistics.mean(measured_durations))
    latency_p95_ms = float(_p95(measured_durations))
    error_rate = float(errors / PROBE_COUNT)
    request_count = float(PROBE_COUNT)

    note = (
        "Measured public HTTP metrics from 5 probe requests. "
        "CPU and memory default to 50% because they cannot be collected "
        "from public websites unless you own the server or have monitoring access."
    )

    return UrlMetricsResponse(
        response_time_ms=round(response_time_ms, 2),
        status_code=status_code,
        error_rate=round(error_rate, 4),
        latency_p95_ms=round(latency_p95_ms, 2),
        request_count=request_count,
        cpu_usage_percent=DEFAULT_CPU_MEMORY,
        memory_usage_percent=DEFAULT_CPU_MEMORY,
        note=note,
    )
