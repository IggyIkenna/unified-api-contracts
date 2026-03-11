"""Endpoint registry with access mode and version metadata for all venues.

EndpointSpec enables consumers to understand:
- Whether an endpoint is streaming vs polling vs batch file download
- Whether historical data is available, live-only, or both
- API version, deprecation dates, and migration notes

This is complementary to ENDPOINT_SCHEMA_MAP (which maps to schema classes) and
venue_manifest.py (which describes per-venue capability coverage).

ENDPOINT_REGISTRY data lives in _endpoint_registry_data.py (SRP size split).
Type definitions live in _endpoint_registry_types.py (breaks circular import).
"""

from __future__ import annotations

from ._endpoint_registry_data import ENDPOINT_REGISTRY as ENDPOINT_REGISTRY
from ._endpoint_registry_types import AccessMode as AccessMode
from ._endpoint_registry_types import CassetteStatus as CassetteStatus
from ._endpoint_registry_types import DataAvailability as DataAvailability
from ._endpoint_registry_types import EndpointSpec as EndpointSpec
from ._endpoint_registry_types import ResponseFormat as ResponseFormat

__all__ = [
    "ENDPOINT_REGISTRY",
    "AccessMode",
    "CassetteStatus",
    "DataAvailability",
    "EndpointSpec",
    "ResponseFormat",
]
