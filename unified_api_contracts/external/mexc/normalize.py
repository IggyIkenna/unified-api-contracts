"""Venue-specific normalizers for MEXC.

Extracted from normalize_utils/ modules. Each function converts a raw MEXC
schema to its canonical counterpart.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalError,
    CanonicalInsufficientBalanceError,
    CanonicalInternalServerError,
    CanonicalInvalidRequestError,
    CanonicalOrderRejectedError,
    CanonicalRateLimitError,
    CanonicalSizeLimitError,
    ErrorAction,
)
from unified_api_contracts.canonical.domain import (
    CanonicalOrderBook,
    CanonicalTicker,
    CanonicalTrade,
)
from unified_api_contracts.canonical.domain.execution import (
    CanonicalFill,
    CanonicalOrder,
)
from unified_api_contracts.normalize_utils._helpers import (
    _d,
    _order_type,
    _side,
    _status,
    _tif,
    _to_decimal,
    _ts_ms,
)
from unified_api_contracts.normalize_utils.errors._utils import from_http_status

from .schemas import (
    MexcFill,
    MexcOrder,
    MexcOrderBook,
    MexcTicker,
    MexcTrade,
)

# ---------------------------------------------------------------------------
# Error map
# ---------------------------------------------------------------------------

MEXC_MAP: dict[str, Callable[..., CanonicalError]] = {
    "10072": CanonicalAuthenticationError,
    "10073": CanonicalAuthenticationError,
    "10074": CanonicalAuthenticationError,
    "10076": CanonicalAuthorizationError,
    "30004": CanonicalInsufficientBalanceError,
    "30005": CanonicalInvalidRequestError,
    "30016": CanonicalOrderRejectedError,
    "30018": CanonicalSizeLimitError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
}


# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


def normalize_mexc_ticker(raw: MexcTicker, instrument_key: str | None = None, venue: str = "mexc") -> CanonicalTicker:
    """Convert MexcTicker to CanonicalTicker."""
    ik = instrument_key or f"{venue}:SPOT:{raw.symbol or ''}"
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=datetime.now(UTC),
        last_price=_to_decimal(raw.lastPrice) or Decimal("0"),
        bid_price=_to_decimal(raw.bidPrice),
        ask_price=_to_decimal(raw.askPrice),
        volume_24h=_to_decimal(raw.volume),
        quote_volume_24h=_to_decimal(raw.quoteVolume),
        price_change_24h=_to_decimal(raw.priceChange),
        price_change_percent_24h=_to_decimal(raw.priceChangePercent),
    )


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_mexc_trade(raw: MexcTrade, symbol: str = "", venue: str = "mexc") -> CanonicalTrade:
    """Convert MexcTrade to CanonicalTrade."""
    ts = _ts_ms(raw.time)
    side = "sell" if raw.isBuyerMaker else "buy"
    if raw.tradeType:
        side = "sell" if raw.tradeType.upper() == "ASK" else "buy"
    trade_id = str(raw.id) if raw.id else ""
    sym = symbol or "UNKNOWN"
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=trade_id,
        timestamp=ts,
        price=_d(raw.price),
        quantity=_d(raw.qty),
        side=side,
        buyer_maker=raw.isBuyerMaker,
        venue_trade_id=trade_id or None,
    )


# ---------------------------------------------------------------------------
# Order Book
# ---------------------------------------------------------------------------


def normalize_mexc_orderbook(raw: MexcOrderBook, symbol: str = "", venue: str = "mexc") -> CanonicalOrderBook:
    """Convert MexcOrderBook to CanonicalOrderBook."""
    ts = _ts_ms(raw.timestamp) if raw.timestamp else datetime.now(UTC)
    bids = [(Decimal(row[0]), Decimal(row[1])) for row in raw.bids if len(row) >= 2]
    asks = [(Decimal(row[0]), Decimal(row[1])) for row in raw.asks if len(row) >= 2]
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.lastUpdateId,
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_mexc_order(raw: MexcOrder, venue: str = "mexc") -> CanonicalOrder:
    """Convert MexcOrder to CanonicalOrder."""
    ts = _ts_ms(raw.time)
    return CanonicalOrder(
        order_id=str(raw.orderId or ""),
        client_order_id=raw.clientOrderId,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol or "",
        side=_side(raw.side),
        order_type=_order_type(raw.type),
        quantity=_d(raw.origQty),
        price=_d(raw.price) if raw.price else None,
        time_in_force=_tif(raw.timeInForce),
        status=_status(raw.status),
        filled_quantity=_d(raw.executedQty),
        remaining_quantity=None,
        average_fill_price=_d(raw.avgPrice) if raw.avgPrice else None,
    )


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_mexc_fill(raw: MexcFill, venue: str = "mexc") -> CanonicalFill:
    """Convert MexcFill to CanonicalFill."""
    ts = _ts_ms(raw.time)
    side = "buy" if raw.isBuyer else "sell"
    return CanonicalFill(
        fill_id=str(raw.id or ""),
        order_id=str(raw.orderId or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol or "",
        side=_side(side),
        price=_d(raw.price),
        quantity=_d(raw.qty),
        fee=_d(raw.commission) if raw.commission else None,
        fee_currency=raw.commissionAsset,
        is_maker=raw.isMaker,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


def normalize_mexc_error(
    error_code: str | int,
    message: str = "",
    venue: str = "mexc",
) -> CanonicalError:
    """Map a MEXC REST/WS error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = MEXC_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_mexc_error",
    "normalize_mexc_fill",
    "normalize_mexc_order",
    "normalize_mexc_orderbook",
    "normalize_mexc_ticker",
    "normalize_mexc_trade",
]
