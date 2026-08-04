"""Venue error classifications for TradFi data providers."""

from __future__ import annotations

from ._types import ErrorAction, VenueErrorClassification, ve

VENUE_ERRORS_TRADFI: dict[str, list[VenueErrorClassification]] = {
    "tardis": [
        ve(
            "tardis",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "tardis",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "tardis",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Server error",
        ),
        ve(
            "tardis",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        # Structural-absence 400 sub-codes (the JSON body's numeric `code`, not the HTTP
        # status) — a PERMANENT impossible/absent combination, NOT a fetch failure. SKIP
        # (honest absence), never FAIL/RETRY — matches
        # TardisHTTPError.STRUCTURAL_ABSENCE_400_CODES in market-tick-data-service. SSOT:
        # plans/active/issues/tardis_impossible_combinations_recorded_as_attempted_failed_2026_07_17.md
        ve(
            "tardis",
            "300",
            retry=False,
            reconnect=False,
            action=ErrorAction.SKIP,
            desc="Invalid 'symbol' param — the symbol is not in Tardis's archive at all (honest absence)",
        ),
        ve(
            "tardis",
            "140",
            retry=False,
            reconnect=False,
            action=ErrorAction.SKIP,
            desc=(
                "Requested dataset is not available for the given date — the symbol IS "
                "archived but the date is outside its availableSince..availableTo window "
                "(honest absence)"
            ),
        ),
    ],
    "yahoo_finance": [
        ve(
            "yahoo_finance",
            "RATE_LIMIT_EXCEEDED",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate",
        ),
        ve(
            "yahoo_finance",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Too many requests",
        ),
        ve(
            "yahoo_finance",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "yahoo_finance",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "yahoo_finance",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Internal server error",
        ),
    ],
    "ibkr": [
        ve(
            "ibkr",
            "100",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Market data farm",
        ),
        ve(
            "ibkr",
            "1100",
            retry=True,
            reconnect=True,
            action=ErrorAction.RECONNECT,
            desc="Connectivity lost",
        ),
        ve(
            "ibkr",
            "1300",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Order rejected",
        ),
        ve(
            "ibkr",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="HTTP rate limit exceeded",
        ),
        ve(
            "ibkr",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "ibkr",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "ibkr",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Internal server error",
        ),
    ],
    "databento": [
        ve(
            "databento",
            "RATE_LIMIT",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit",
        ),
        ve(
            "databento",
            "AUTH_FAILURE",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Auth failed",
        ),
        ve(
            "databento",
            "CONNECTION_RESET",
            retry=True,
            reconnect=True,
            action=ErrorAction.RECONNECT,
            desc="Reset",
        ),
        ve(
            "databento",
            "VALIDATION_ERROR",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Request validation failed (e.g. date range, T+2 embargo)",
        ),
        ve(
            "databento",
            "NOT_FOUND",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Dataset or resource not found",
        ),
        ve(
            "databento",
            "SERVER_ERROR",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Databento internal server error",
        ),
        ve(
            "databento",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="HTTP rate limit exceeded",
        ),
        ve(
            "databento",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
        ve(
            "databento",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "databento",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Internal server error",
        ),
        ve(
            "databento",
            "402",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Payment Required — PAYG credit exhausted / billing failure (DO NOT retry)",
        ),
        ve(
            "databento",
            "DATABENTO_PAYMENT_REQUIRED",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Payment Required from error message (insufficient credit / quota exceeded)",
        ),
        ve(
            "databento",
            "DATABENTO_ENTITLEMENT",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc=(
                "Subscription-entitlement breach (403, NOT 402/PAYG) — request's "
                "(dataset, schema, start) fell outside the paid 3-dataset subscription "
                "or the schema's free included-history window. Pre-request guard refused "
                "it before it reached the vendor (would have been metered). DO NOT retry; "
                "fix the request scope. SSOT: registry/databento_subscription_allowlist.py."
            ),
        ),
        ve(
            "databento",
            "DATABENTO_LOOKBACK_EXCEEDED",
            retry=False,
            reconnect=False,
            action=ErrorAction.SKIP,
            desc=(
                "DatabentoLookbackExceededError — pre-request billing guard: the "
                "requested (data_type, start) falls outside the schema's free "
                "included-history window (L2/L3: 1 month, L1: 1 year). The shard is "
                "structurally (permanently) unavailable at our subscription tier, not "
                "a transient fetch failure — classify as honest-absence (SKIP), never "
                "attempted_failed. SSOT: registry/databento_subscription_allowlist.py."
            ),
        ),
        ve(
            "databento",
            "DATABENTO_SUBSCRIPTION_GUARD",
            retry=False,
            reconnect=False,
            action=ErrorAction.SKIP,
            desc=(
                "DatabentoSubscriptionError (non-lookback) — pre-request billing guard: "
                "request's (dataset, schema, api) fell outside the paid subscription "
                "allowlist (wrong dataset, banned schema, or banned API). Structurally "
                "unavailable at our tier, not a transient failure — SKIP (honest absence). "
                "SSOT: registry/databento_subscription_allowlist.py."
            ),
        ),
    ],
    # "barchart" error table RETIRED 2026-06-24 — Barchart removed (VIX 15m now
    # aggregates from VX futures via Databento XCBF.PITCH). No shim.
    "fred": [
        ve(
            "fred",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "fred",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request — invalid series ID or parameter",
        ),
        ve(
            "fred",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized — invalid API key",
        ),
        ve(
            "fred",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Internal server error",
        ),
    ],
    "ecb": [
        ve(
            "ecb",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "ecb",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request — invalid key or flow",
        ),
        ve(
            "ecb",
            "404",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="No data found for series",
        ),
        ve(
            "ecb",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Internal server error",
        ),
        ve(
            "ecb",
            "503",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Service temporarily unavailable",
        ),
        ve(
            "ecb",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
    ],
    "ofr": [
        ve(
            "ofr",
            "429",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Rate limit exceeded",
        ),
        ve(
            "ofr",
            "400",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Bad request",
        ),
        ve(
            "ofr",
            "404",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Dataset or series not found",
        ),
        ve(
            "ofr",
            "500",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc="Internal server error",
        ),
        ve(
            "ofr",
            "401",
            retry=False,
            reconnect=False,
            action=ErrorAction.FAIL,
            desc="Unauthorized",
        ),
    ],
}
