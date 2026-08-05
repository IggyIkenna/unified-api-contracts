"""Venue error classifications for prediction market data sources — Kalshi, Polymarket.

These are vendor/venue API errors surfaced by the MTDS adapter layer. They live under
the real venue key ("kalshi" / "polymarket") so :func:`classify_venue_error` matches
them directly, without falling through to the ``internal`` catch-all or the
``UNCLASSIFIED:`` sentinel bucket.

TRADES_FETCH_FAILED is the shared MTDS-internal signal for "the per-ticker trades
fetch died on a transport error (aiohttp.ClientError / TimeoutError / OSError) after
retries exhausted" — a transient, retry-safe failure at the venue level, distinct
from a genuine venue API error code.
"""

from __future__ import annotations

from ._types import ErrorAction, VenueErrorClassification, ve

VENUE_ERRORS_PREDICTION: dict[str, list[VenueErrorClassification]] = {
    "kalshi": [
        ve(
            "kalshi",
            "TRADES_FETCH_FAILED",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc=(
                "Per-ticker trades fetch died on a transport error "
                "(aiohttp.ClientError / TimeoutError / OSError) — transient, retry-safe"
            ),
        ),
        ve(
            "kalshi",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded (Kalshi basic tier: ~20 req/s published)",
        ),
        ve(
            "kalshi",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized — invalid or expired API credentials",
        ),
        ve(
            "kalshi",
            "403",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Forbidden — IP blocked or endpoint not permitted at current tier",
        ),
        ve(
            "kalshi",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Kalshi internal server error — transient, retry-safe",
        ),
        ve(
            "kalshi",
            "502",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Kalshi gateway error — transient, retry-safe",
        ),
        ve(
            "kalshi",
            "503",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Kalshi service unavailable — transient, retry-safe",
        ),
    ],
    "polymarket": [
        ve(
            "polymarket",
            "TRADES_FETCH_FAILED",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc=(
                "Per-ticker trades fetch died on a transport error "
                "(aiohttp.ClientError / TimeoutError / OSError) — transient, retry-safe"
            ),
        ),
        ve(
            "polymarket",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded (Polymarket Gamma/Data API — ~20 req/s observed safe)",
        ),
        ve(
            "polymarket",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Polymarket internal server error — transient, retry-safe",
        ),
        ve(
            "polymarket",
            "502",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Polymarket gateway error — transient, retry-safe",
        ),
        ve(
            "polymarket",
            "503",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Polymarket service unavailable — transient, retry-safe",
        ),
    ],
}
