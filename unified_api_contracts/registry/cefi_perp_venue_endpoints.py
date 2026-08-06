"""CeFi perp venue REST API base URLs — SSOT for MTDS perp_funding_handler and IS adapters.

Centralises the three venue API endpoints that MTDS perp_funding_handler fetches
funding rates from, replacing per-file hardcoded string literals.

Provenance: URLs verified from public venue API documentation (2026-05-22).
  - Hyperliquid: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api
  - Aster: https://docs.asterdex.com
  - Kalshi-perp: https://docs.kalshi.com/margin (perps_openapi.yaml), re-verified
    2026-07-14 with a live GET against external-api.kalshi.com/trade-api/v2/margin/markets.

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
    # PACIFICA endpoint removed 2026-07-16 (operator ruling: all Solana perp
    # DEXes dropped except Jupiter, not integrated). SSOT: unified-trading-
    # pm/codex/04-architecture/solana-defi-coverage.md.
    # Kalshi-perp: CFTC-regulated crypto perpetuals (launched 2026-05-29).
    # Public-read REST (no auth for market data). History from 2026-05-29.
    # CONFIRMED 2026-07-14 (mtds_perp_funding_backfill_hang_2026_07_14.md
    # endpoint-research todo, live repro): this is a SEPARATE margin/perps API
    # (docs.kalshi.com/margin, perps_openapi.yaml) — NOT the prediction-markets
    # host (api.elections.kalshi.com) the collector used before this fix, which
    # has no perps product at all and caused a catastrophic ticker-list churn.
    # Endpoint: GET /margin/markets[?status=active] (list, no pagination)
    #           GET /margin/trades?ticker=...  (cursor-paginated, <=1000/call)
    #           GET /margin/funding_rates/historical?ticker=...&start_ts=...&end_ts=...
    # SSOT: prediction-perps-sourcing.md
    "KALSHI_PERP": "https://external-api.kalshi.com/trade-api/v2",
    # Polymarket-perp: CFTC-regulated crypto perpetuals (launched 2026-04-21).
    # UPSTREAM RECOVERED 2026-08-05: perps-api.polymarket.com was DNS NXDOMAIN as of
    # 2026-06-21, but the Polymarket perps API launched under a different hostname —
    # api.perpetuals.polymarket.com (verified live, HTTP 200, 2026-08-05).
    # See docs.polymarket.com/perps/market-data.
    "POLYMARKET_PERP": "https://api.perpetuals.polymarket.com",
}

__all__ = [
    "CEFI_PERP_VENUE_API_ENDPOINTS",
    "get_cefi_perp_venue_api_url",
]


def get_cefi_perp_venue_api_url(venue: str) -> str | None:
    """Return the REST API base URL for a CeFi perp venue, or None if not registered."""
    return CEFI_PERP_VENUE_API_ENDPOINTS.get(venue.upper())
