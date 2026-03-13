"""Service health response schema with cloud/mode indicators.

Used by all service /health endpoints to report operational status,
including cloud_provider and mock_mode for observability dashboards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ServiceHealthResponse:
    """Standard health endpoint response for all services.

    Includes cloud_provider and mock_mode so that monitoring dashboards
    and SIT runners can verify the deployment environment at a glance.

    Fields:
        status: Service health status (healthy, degraded, unhealthy).
        service_name: Canonical service name from pyproject.toml.
        version: Service version string.
        cloud_provider: Active cloud provider (gcp, aws, local).
        mock_mode: Whether CLOUD_MOCK_MODE is active (true in CI/local).
        uptime_seconds: Seconds since service startup.
        timestamp: Current UTC timestamp.
        checks: Named sub-check results (db, pubsub, cache, etc.).
    """

    status: str
    service_name: str
    version: str
    cloud_provider: str = "unknown"
    mock_mode: bool = False
    uptime_seconds: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    checks: dict[str, str] = field(default_factory=dict)


__all__ = [
    "ServiceHealthResponse",
]
