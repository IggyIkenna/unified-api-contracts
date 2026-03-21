"""Venue error classifications for alternative data providers."""

from __future__ import annotations

from ._types import ErrorAction, VenueErrorClassification, ve

VENUE_ERRORS_ALTDATA: dict[str, list[VenueErrorClassification]] = {
    "glassnode": [
        ve(
            "glassnode",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "glassnode",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized — invalid API key",
        ),
        ve(
            "glassnode",
            "403",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Forbidden — metric requires higher tier",
        ),
        ve(
            "glassnode",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request — invalid metric or parameter",
        ),
        ve(
            "glassnode",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Internal server error",
        ),
    ],
    "polygon": [
        ve("polygon", "400", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Bad request"),
        ve("polygon", "401", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Unauthorized"),
        ve("polygon", "403", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Forbidden"),
        ve("polygon", "429", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit exceeded"),
        ve("polygon", "500", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Internal server error"),
        ve("polygon", "503", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Service unavailable"),
    ],
    "fear_greed": [
        ve("fear_greed", "400", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Bad request"),
        ve("fear_greed", "401", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Unauthorized"),
        ve("fear_greed", "403", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Forbidden"),
        ve("fear_greed", "429", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit exceeded"),
        ve("fear_greed", "500", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Internal server error"),
        ve("fear_greed", "503", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Service unavailable"),
    ],
}
