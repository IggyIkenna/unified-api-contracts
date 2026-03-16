"""Venue error classifications for onchain perpetuals."""

from __future__ import annotations

from ._types import ErrorAction, VenueErrorClassification, ve

VENUE_ERRORS_ONCHAIN_PERPS: dict[str, list[VenueErrorClassification]] = {
    "hyperliquid": [
        ve(
            "hyperliquid",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
        ve(
            "hyperliquid",
            "503",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Unavailable",
        ),
        ve(
            "hyperliquid",
            "RATE_LIMIT",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit",
        ),
        ve(
            "hyperliquid",
            "INSUFFICIENT_MARGIN",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Margin",
        ),
    ],
    "aster": [
        ve(
            "aster",
            "-1003",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Too many requests",
        ),
        ve(
            "aster",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "aster",
            "503",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Service unavailable",
        ),
    ],
}
