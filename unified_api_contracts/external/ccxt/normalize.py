"""Venue-specific normalizers for CCXT.

Extracted from normalize_utils/ modules. Each function converts a raw CCXT
schema to its canonical counterpart.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from unified_api_contracts.canonical.crosscutting.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalDuplicateOrderError,
    CanonicalError,
    CanonicalInsufficientBalanceError,
    CanonicalInsufficientMarginError,
    CanonicalInternalServerError,
    CanonicalInvalidRequestError,
    CanonicalNetworkError,
    CanonicalOrderRejectedError,
    CanonicalRateLimitError,
    CanonicalServiceUnavailableError,
    ErrorAction,
)
from unified_api_contracts.canonical.domain import (
    CanonicalDerivativeTicker,
    CanonicalFee,
    CanonicalInstrument,
    CanonicalLiquidation,
    CanonicalOhlcvBar,
    CanonicalOrderBook,
    CanonicalTicker,
    CanonicalTrade,
    FeeType,
)
from unified_api_contracts.canonical.domain.execution import (
    CanonicalFill,
    CanonicalOrder,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from unified_api_contracts.normalize_utils._helpers import (
    d as _d,
)
from unified_api_contracts.normalize_utils._helpers import (
    to_decimal as _to_decimal,
)
from unified_api_contracts.normalize_utils._helpers import (
    to_levels as _to_levels,
)
from unified_api_contracts.normalize_utils._helpers import (
    ts_ms_to_datetime as _ts_ms_to_datetime,
)

from .schemas import (
    CcxtFee as CcxtFeeSchema,
)
from .schemas import (
    CcxtFundingRate,
    CcxtLiquidation,
    CcxtMarket,
    CcxtMarketLimits,
    CcxtOhlcv,
    CcxtOrder,
    CcxtOrderBook,
    CcxtTicker,
    CcxtTrade,
)

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Re-use local helpers from orders_fills (they are small and self-contained)
# ---------------------------------------------------------------------------


def _parse_decimal(val: str | float | Decimal | None) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _ts_ms_to_dt(ts: int | None) -> datetime:
    if ts is None:
        return datetime.now(UTC)
    return datetime.fromtimestamp(ts / 1000.0, tz=UTC)


def _normalize_side(s: str | None) -> OrderSide:
    if not s:
        return OrderSide.BUY
    return OrderSide.SELL if str(s).lower() in ("sell", "short") else OrderSide.BUY


def _normalize_order_type(t: str | None) -> OrderType:
    if not t:
        return OrderType.LIMIT
    t_val = str(t).lower()
    if t_val in ("market", "m"):
        return OrderType.MARKET
    if t_val in ("limit", "l"):
        return OrderType.LIMIT
    if t_val in ("stop", "stop_market"):
        return OrderType.STOP
    if t_val in ("stop_limit", "stop_limit_order"):
        return OrderType.STOP_LIMIT
    return OrderType.LIMIT


def _normalize_order_status(s: str | None) -> OrderStatus:
    if not s:
        return OrderStatus.PENDING
    s_val = str(s).lower()
    if s_val in ("open", "live", "new", "partiallyfilled"):
        return OrderStatus.OPEN
    if s_val in ("partially_filled", "partiallyfilled"):
        return OrderStatus.PARTIALLY_FILLED
    if s_val in ("closed", "filled", "done"):
        return OrderStatus.FILLED
    if s_val in ("canceled", "cancelled", "cancel"):
        return OrderStatus.CANCELLED
    if s_val == "rejected":
        return OrderStatus.REJECTED
    if s_val == "expired":
        return OrderStatus.EXPIRED
    return OrderStatus.PENDING


def _normalize_tif(tif: str | None) -> TimeInForce:
    if not tif:
        return TimeInForce.GTC
    t = str(tif).upper()
    if t in ("IOC", "GTC", "FOK", "GTD", "POST_ONLY"):
        return TimeInForce(t)
    return TimeInForce.GTC


def _extract_ccxt_fee(trade: CcxtTrade) -> tuple[Decimal | None, str | None]:
    fee = trade.fee
    if fee is None:
        return None, None
    if isinstance(fee, dict):
        cost = fee.get("cost")
        currency = fee.get("currency")
        cost_val: str | float | Decimal | None = (
            float(cost)
            if isinstance(cost, (int, float))
            else str(cost)
            if isinstance(cost, str)
            else cost
            if isinstance(cost, Decimal)
            else None
        )
        return (
            _parse_decimal(cost_val) if cost_val is not None else None,
            str(currency) if currency is not None else None,
        )
    if hasattr(fee, "cost") and hasattr(fee, "currency"):
        c = getattr(fee, "cost", None)
        curr = getattr(fee, "currency", None)
        c_val: str | float | Decimal | None = (
            float(c)
            if isinstance(c, (int, float))
            else str(c)
            if isinstance(c, str)
            else c
            if isinstance(c, Decimal)
            else None
        )
        return (_parse_decimal(c_val) if c_val is not None else None, curr)
    return None, None


# ---------------------------------------------------------------------------
# CCXT error map
# ---------------------------------------------------------------------------

CCXT_MAP: dict[str, Callable[..., CanonicalError]] = {
    "RateLimitExceeded": CanonicalRateLimitError,
    "DDoSProtection": CanonicalRateLimitError,
    "RequestTimeout": CanonicalNetworkError,
    "NetworkError": CanonicalNetworkError,
    "ExchangeNotAvailable": CanonicalServiceUnavailableError,
    "OnMaintenance": CanonicalServiceUnavailableError,
    "AuthenticationError": CanonicalAuthenticationError,
    "PermissionDenied": CanonicalAuthorizationError,
    "InsufficientFunds": CanonicalInsufficientBalanceError,
    "InvalidOrder": CanonicalOrderRejectedError,
    "OrderNotFound": CanonicalOrderRejectedError,
    "CancelPending": CanonicalOrderRejectedError,
    "DuplicateOrderId": CanonicalDuplicateOrderError,
    "ExchangeError": CanonicalInternalServerError,
    "BadSymbol": CanonicalInvalidRequestError,
    "BadRequest": CanonicalInvalidRequestError,
    "MarginModeAlreadySet": CanonicalInvalidRequestError,
    "InsufficientMargin": CanonicalInsufficientMarginError,
}


# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


def normalize_ccxt_ticker(raw: CcxtTicker, instrument_key: str | None = None, venue: str = "ccxt") -> CanonicalTicker:
    ik = instrument_key or f"{venue}:SPOT:{raw.symbol or ''}"
    ts = datetime.now(UTC)
    t_ts = raw.info.get("timestamp") if raw.info else None
    if isinstance(t_ts, (int, float)):
        ts = _ts_ms_to_datetime(int(t_ts))
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.last) or Decimal("0"),
        bid_price=_to_decimal(raw.bid),
        ask_price=_to_decimal(raw.ask),
        volume_24h=_to_decimal(raw.volume),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_ccxt_trade(raw: CcxtTrade, venue: str = "ccxt", symbol: str = "") -> CanonicalTrade:
    """Convert CcxtTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.timestamp is not None:
        ts = datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC)
    elif raw.datetime:
        try:
            ts = datetime.fromisoformat(str(raw.datetime).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            _logger.debug(
                "CCXT trade datetime %r is not a valid ISO datetime; using current UTC time",
                raw.datetime,
            )
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or (raw.symbol or "") or "UNKNOWN",
        trade_id=str(raw.id) if raw.id is not None else "",
        timestamp=ts,
        price=Decimal(str(raw.price or 0)),
        quantity=Decimal(str(raw.amount or 0)),
        side=(raw.side or "buy").lower(),
        buyer_maker=raw.takerOrMaker == "maker" if raw.takerOrMaker else None,
        venue_trade_id=str(raw.id) if raw.id else None,
    )


# ---------------------------------------------------------------------------
# OHLCV
# ---------------------------------------------------------------------------


def normalize_ccxt_ohlcv(raw: CcxtOhlcv, symbol: str = "", venue: str = "ccxt") -> CanonicalOhlcvBar:
    """Convert CcxtOhlcv to CanonicalOhlcvBar."""
    ts = datetime.fromtimestamp((raw.timestamp or 0) / 1000.0, tz=UTC)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=_d(raw.open),
        high=_d(raw.high),
        low=_d(raw.low),
        close=_d(raw.close),
        volume=_d(raw.volume),
        quote_volume=None,
        count=None,
        vwap=None,
    )


# ---------------------------------------------------------------------------
# Order Book
# ---------------------------------------------------------------------------


def normalize_ccxt_orderbook(
    raw: CcxtOrderBook,
    venue: str = "ccxt",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert CcxtOrderBook to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC) if raw.timestamp is not None else datetime.now(UTC)
    sym = symbol or (raw.symbol or "")
    bids = _to_levels([[p, q] for p, q in raw.bids])
    asks = _to_levels([[p, q] for p, q in raw.asks])
    return CanonicalOrderBook(
        venue=venue,
        symbol=sym,
        timestamp=ts,
        bids=bids,
        asks=asks,
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_ccxt_order(raw: CcxtOrder, venue: str = "ccxt") -> CanonicalOrder:
    ts = _ts_ms_to_dt(raw.timestamp)
    symbol = raw.symbol or ""
    return CanonicalOrder(
        order_id=raw.id,
        client_order_id=raw.clientOrderId,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        order_type=_normalize_order_type(raw.type),
        quantity=_parse_decimal(raw.amount or 0),
        price=_parse_decimal(raw.price) if raw.price is not None else None,
        time_in_force=_normalize_tif(raw.timeInForce),
        status=_normalize_order_status(raw.status),
        filled_quantity=_parse_decimal(raw.filled or 0),
        remaining_quantity=_parse_decimal(raw.remaining) if raw.remaining is not None else None,
        average_fill_price=_parse_decimal(raw.average) if raw.average is not None else None,
    )


# ---------------------------------------------------------------------------
# Fill (trade-to-fill)
# ---------------------------------------------------------------------------


def normalize_ccxt_trade_to_fill(raw: CcxtTrade, venue: str = "ccxt") -> CanonicalFill:
    ts = _ts_ms_to_dt(raw.timestamp)
    symbol = raw.symbol or ""
    fill_id = raw.id or f"{raw.order or 'unknown'}-{raw.timestamp or 0}"
    fee_val, fee_ccy = _extract_ccxt_fee(raw)
    is_maker = raw.takerOrMaker.lower() == "maker" if raw.takerOrMaker else None
    return CanonicalFill(
        fill_id=str(fill_id),
        order_id=str(raw.order or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        price=_parse_decimal(raw.price or 0),
        quantity=_parse_decimal(raw.amount or 0),
        fee=fee_val,
        fee_currency=fee_ccy,
        is_maker=is_maker,
    )


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


def _ccxt_instrument_type(raw: CcxtMarket) -> str:
    """Infer instrument type from CCXT market boolean flags."""
    if raw.type == "option":
        return "OPTION"
    if raw.swap:
        return "PERPETUAL"
    if raw.futures:
        return "FUTURE"
    if raw.spot:
        return "SPOT_PAIR"
    type_str = (raw.type or "").lower()
    type_map: dict[str, str] = {
        "spot": "SPOT_PAIR",
        "swap": "PERPETUAL",
        "future": "FUTURE",
        "futures": "FUTURE",
        "option": "OPTION",
    }
    return type_map.get(type_str, "SPOT_PAIR")


def normalize_ccxt_market(
    raw: CcxtMarket,
    venue: str = "ccxt",
) -> CanonicalInstrument:
    """Normalize a CcxtMarket to CanonicalInstrument."""
    instrument_type = _ccxt_instrument_type(raw)
    symbol = raw.symbol or raw.id or ""
    instrument_key = f"{venue.upper()}:{instrument_type}:{symbol}"

    tick_size: Decimal | None = None
    min_size: Decimal | None = None

    if raw.precision is not None:
        price_prec = raw.precision.get("price") if isinstance(raw.precision, dict) else raw.precision.price
        if price_prec is not None:
            tick_size = Decimal(str(price_prec))

    if isinstance(raw.limits, CcxtMarketLimits) and raw.limits.amount is not None:
        _min = raw.limits.amount.get("min")
        if _min is not None:
            min_size = Decimal(str(_min))

    return CanonicalInstrument(
        instrument_key=instrument_key,
        venue=venue,
        symbol=symbol,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=min_size,
        contract_size=Decimal(str(raw.contractSize)) if raw.contractSize is not None else None,
        base_asset=raw.base,
        quote_asset=raw.quote,
        settle_asset=raw.settle,
    )


# ---------------------------------------------------------------------------
# Fee
# ---------------------------------------------------------------------------


def normalize_ccxt_fee(
    raw: CcxtFeeSchema,
    venue: str = "ccxt",
    fee_type: FeeType = FeeType.OTHER,
) -> CanonicalFee:
    """Normalize a CcxtFee to CanonicalFee."""
    amount = Decimal(str(raw.cost)) if raw.cost is not None else Decimal("0")
    currency = raw.currency if raw.currency is not None else ""
    return CanonicalFee(
        amount=amount,
        currency=currency,
        asset=None,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# Derivative Ticker (Funding Rate)
# ---------------------------------------------------------------------------


def normalize_ccxt_funding_rate(
    raw: CcxtFundingRate,
    venue: str = "ccxt",
    symbol: str = "",
) -> CanonicalDerivativeTicker:
    """Convert CcxtFundingRate to CanonicalDerivativeTicker."""
    sym = symbol or raw.symbol or ""
    ik = f"{venue.upper()}:PERP:{sym}"
    ts = datetime.fromtimestamp((raw.fundingTimestamp or 0) / 1000.0, tz=UTC)
    funding_rate: Decimal | None = None
    if raw.fundingRate is not None:
        with contextlib.suppress(InvalidOperation):
            funding_rate = Decimal(str(raw.fundingRate))
    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        mark_price=None,
        index_price=None,
        funding_rate=funding_rate,
        next_funding_timestamp=None,
        open_interest=None,
        open_interest_value=None,
        predicted_funding_rate=None,
    )


# ---------------------------------------------------------------------------
# Liquidation
# ---------------------------------------------------------------------------


def normalize_ccxt_liquidation(
    raw: CcxtLiquidation,
    venue: str = "ccxt",
    symbol: str = "",
) -> CanonicalLiquidation:
    """Convert CcxtLiquidation to CanonicalLiquidation."""
    sym = symbol or raw.symbol or ""
    ik = f"{venue.upper()}:PERP:{sym}"
    ts = datetime.fromtimestamp((raw.timestamp or 0) / 1000.0, tz=UTC)
    side_raw = (raw.side or "").lower()
    side = "sell" if side_raw == "long" else "buy"
    price = Decimal(str(raw.price or 0))
    size = Decimal(str(raw.amount or 0))
    return CanonicalLiquidation(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        side=side,
        price=price if price > Decimal("0") else Decimal("0"),
        size=size if size > Decimal("0") else Decimal("0"),
        order_id=None,
        liquidated_account_value=None,
        liquidated_ntl_pos=None,
        liquidated_user=None,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


def normalize_ccxt_error(
    error_code: str | int,
    message: str = "",
    venue: str = "ccxt",
) -> CanonicalError:
    """Map a CCXT exception class name to a CanonicalError subclass."""
    code = str(error_code)
    cls = CCXT_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_ccxt_error",
    "normalize_ccxt_fee",
    "normalize_ccxt_funding_rate",
    "normalize_ccxt_liquidation",
    "normalize_ccxt_market",
    "normalize_ccxt_ohlcv",
    "normalize_ccxt_order",
    "normalize_ccxt_orderbook",
    "normalize_ccxt_ticker",
    "normalize_ccxt_trade",
    "normalize_ccxt_trade_to_fill",
]
