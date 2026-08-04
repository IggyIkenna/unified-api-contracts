"""Venue error classifications for alternative data providers.

HTTP-status classifications for the free macro/alt-data REST sources
(CFTC COT, EIA, Baker Hughes, crypto fear & greed). All are public/free
batch sources, so the action set is the standard REST taxonomy:
  429 -> RETRY (rate-limited, back off)
  401/403 -> FAIL (auth/forbidden — never silently retry a credential error)
  404 -> SKIP (series/report not found for the requested window)
  500/502/503/504 -> RETRY (transient upstream)
Consumed by ``classify_venue_error(venue, http_status)`` in MTDS adapters.
"""

from __future__ import annotations

from ._types import ErrorAction, VenueErrorClassification, ve


def _rest_macro_errors(venue: str) -> list[VenueErrorClassification]:
    """Standard HTTP-status classifications for a free REST macro source."""
    retry = ErrorAction.RETRY
    fail = ErrorAction.FAIL
    skip = ErrorAction.SKIP
    return [
        ve(venue, "429", retry=True, reconnect=False, action=retry, desc="Rate limited — back off and retry"),
        ve(venue, "401", retry=False, reconnect=False, action=fail, desc="Unauthorized (bad/missing API key)"),
        ve(venue, "403", retry=False, reconnect=False, action=fail, desc="Forbidden"),
        ve(venue, "404", retry=False, reconnect=False, action=skip, desc="Series/report not found for window"),
        ve(venue, "500", retry=True, reconnect=False, action=retry, desc="Upstream server error"),
        ve(venue, "502", retry=True, reconnect=False, action=retry, desc="Bad gateway"),
        ve(venue, "503", retry=True, reconnect=False, action=retry, desc="Service unavailable"),
        ve(venue, "504", retry=True, reconnect=False, action=retry, desc="Gateway timeout"),
    ]


VENUE_ERRORS_ALTDATA: dict[str, list[VenueErrorClassification]] = {
    "cftc": _rest_macro_errors("cftc"),
    "eia": _rest_macro_errors("eia"),
    "baker_hughes": _rest_macro_errors("baker_hughes"),
    "fear_greed": _rest_macro_errors("fear_greed"),
    "kalshi": [
        *_rest_macro_errors("kalshi"),
        ve(
            "kalshi",
            "TIMEOUT",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Request timed out — transient network",
        ),
        ve(
            "kalshi",
            "CONNECTION_ERROR",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Connection error (DNS/TCP/SSL) — transient infrastructure",
        ),
    ],
}
