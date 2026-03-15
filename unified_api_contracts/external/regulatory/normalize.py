"""Regulatory normalizers — all normalize_regulatory_* functions.

Extracted from normalize_utils/ modules (trades, errors).
"""

from __future__ import annotations

from ...canonical.crosscutting.errors import (
    CanonicalAuthorizationError,
    CanonicalError,
    CanonicalInvalidRequestError,
    ErrorAction,
)
from ...canonical.domain import CanonicalTrade
from ...normalize_utils.errors._utils import from_http_status
from .schemas import MifidIITradeReport

# ---------------------------------------------------------------------------
# Trade normalizer (from normalize_utils/trades.py)
# ---------------------------------------------------------------------------


def normalize_regulatory_trade_report(
    raw: MifidIITradeReport,
    venue: str = "regulatory",
) -> CanonicalTrade:
    """Convert MifidIITradeReport to CanonicalTrade.

    MiFID II trade report is a regulatory filing; maps to CanonicalTrade for record-keeping.
    instrument_key uses trading venue MIC.
    """
    sym = raw.instrument_isin or ""
    return CanonicalTrade(
        venue=venue or raw.trading_venue_mic,
        symbol=sym if sym else "UNKNOWN",
        trade_id=raw.exec_id,
        timestamp=raw.trading_datetime,
        price=raw.price,
        quantity=raw.quantity,
        side="buy",  # MiFID report doesn't specify buy/sell (depends on reporting entity)
        buyer_maker=None,
        venue_trade_id=raw.exec_id,
    )


# ---------------------------------------------------------------------------
# Error normalizer (from normalize_utils/errors/_normalize_b.py)
# ---------------------------------------------------------------------------


def normalize_regulatory_error(
    error_code: str | int,
    message: str = "",
    venue: str = "regulatory",
) -> CanonicalError:
    """Map a trade-reporting / regulatory API error to a CanonicalError subclass."""
    code = str(error_code)
    if code.startswith("VALIDATION"):
        return CanonicalInvalidRequestError(message=message, venue=venue)
    if code.startswith("AUTH"):
        return CanonicalAuthorizationError(message=message, venue=venue)
    try:
        return from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_regulatory_error",
    "normalize_regulatory_trade_report",
]
