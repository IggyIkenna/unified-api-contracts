"""CeFi perp venue REST API base URLs — SSOT for MTDS perp_funding_handler and IS adapters.

Centralises the three venue API endpoints that MTDS perp_funding_handler fetches
funding rates from, replacing per-file hardcoded string literals.

Provenance: URLs verified from public venue API documentation (2026-05-22).
  - Hyperliquid: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api
  - Aster: https://docs.asterdex.com
  - Pacifica: https://docs.pacifica.fi

Graph (gateway.thegraph.com) and Tardis (datasets.tardis.dev) are data-provider
infrastructure, not venue endpoints — they are exempt from this registry.
"""

from __future__ import annotations

from typing import Final

# CeFi perpetuals venue REST API base URLs, keyed by venue name (uppercase).
# Used by MTDS perp_funding_handler and instruments-service CeFi adapters.
# Graph + Tardis infra URLs are exempt (not venue endpoints).
CEFI_PERP_VENUE_API_ENDPOINTS: Final[dict[str, str]] = {
    "HYPERLIQUID": "https://api.hyperliquid.xyz/info",
    "ASTER": "https://fapi.asterdex.com",
    "PACIFICA": "https://api.pacifica.fi/api/v1",
}

__all__ = [
    "CEFI_PERP_VENUE_API_ENDPOINTS",
    "get_cefi_perp_venue_api_url",
]


def get_cefi_perp_venue_api_url(venue: str) -> str | None:
    """Return the REST API base URL for a CeFi perp venue, or None if not registered."""
    return CEFI_PERP_VENUE_API_ENDPOINTS.get(venue.upper())
