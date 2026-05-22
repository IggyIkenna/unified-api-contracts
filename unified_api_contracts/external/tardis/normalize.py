"""Tardis normalizers — all normalize_tardis_* functions.

Extracted from normalize_utils/ modules (trades, orderbooks, instruments,
options, derivative_tickers, liquidations, connectivity, errors).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...canonical.crosscutting.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalError,
    CanonicalInternalServerError,
    CanonicalRateLimitError,
    CanonicalServiceUnavailableError,
    ErrorAction,
)
from ...canonical.domain import (
    CanonicalDerivativeTicker,
    CanonicalInstrument,
    CanonicalLiquidation,
    CanonicalOptionsChainEntry,
    CanonicalOrderBook,
    CanonicalTrade,
    CanonicalWebSocketLifecycle,
    WebSocketEvent,
)
from ...normalize_utils._helpers import to_levels
from ...normalize_utils.errors._utils import from_http_status
from ..tardis import TardisOptionQuote
from .schemas import (
    TardisInstrument,
    TardisLiquidations,
    TardisOrderBook,
    TardisTrade,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _d(value: float | int | str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _to_decimal(val: float | str | int | None) -> Decimal | None:
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (ValueError, InvalidOperation):
        return None


def _ms_to_utc(ts_raw: object) -> datetime | None:
    if ts_raw is None:
        return None
    try:
        ms = int(str(ts_raw))
        if ms <= 0:
            return None
        return datetime.fromtimestamp(ms / 1000.0, tz=UTC)
    except (ValueError, TypeError, OSError):
        return None


def _now_utc() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_tardis_trade(raw: TardisTrade, venue: str | None = None, symbol: str | None = None) -> CanonicalTrade:
    """Convert TardisTrade to CanonicalTrade."""
    v = venue or (raw.exchange or "tardis")
    s = symbol or (raw.symbol or "")
    ts_str = raw.timestamp or "0"
    try:
        ts_val = int(float(ts_str) / 1000) if "." in ts_str else int(ts_str) // 1000
        ts = datetime.fromtimestamp(ts_val, tz=UTC)
    except (ValueError, TypeError):
        ts = datetime.now(UTC)
    return CanonicalTrade(
        venue=v,
        symbol=s or "UNKNOWN",
        trade_id=raw.trade_id or "",
        timestamp=ts,
        price=Decimal(str(raw.price or 0)),
        quantity=Decimal(str(raw.size or 0)),
        side=(raw.side or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=raw.trade_id,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_tardis_orderbook(
    raw: TardisOrderBook,
    venue: str | None = None,
    symbol: str | None = None,
) -> CanonicalOrderBook:
    """Convert TardisOrderBook to CanonicalOrderBook."""
    v = venue or (raw.exchange or "tardis")
    s = symbol or (raw.symbol or "")
    ts_str = raw.timestamp or "0"
    try:
        ts_val = int(float(ts_str) / 1000) if "." in ts_str else int(ts_str) // 1000
        ts = datetime.fromtimestamp(ts_val, tz=UTC)
    except (ValueError, TypeError):
        ts = datetime.now(UTC)
    bids = to_levels(raw.bids or [])
    asks = to_levels(raw.asks or [])
    return CanonicalOrderBook(
        venue=v,
        symbol=s,
        timestamp=ts,
        bids=bids,
        asks=asks,
    )


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


def normalize_tardis_instrument(
    raw: TardisInstrument,
    venue: str = "",
) -> CanonicalInstrument:
    """Normalize TardisInstrument to CanonicalInstrument."""
    v = venue or raw.exchange or "tardis"
    sym = raw.symbol or ""
    ik = f"{v.upper()}:UNKNOWN:{sym}"
    return CanonicalInstrument(
        instrument_key=ik,
        venue=v,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------


def normalize_tardis_option_quote(raw: TardisOptionQuote, venue: str = "tardis") -> CanonicalOptionsChainEntry:
    """Convert TardisOptionQuote to CanonicalOptionsChainEntry."""
    ts = datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC)
    exp = datetime.fromtimestamp(raw.expiration / 1000.0, tz=UTC) if raw.expiration is not None else None
    opt_type = (raw.option_type or "call").lower()
    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=raw.symbol,
        underlying=(raw.underlying_price is not None and str(raw.underlying_price)) or raw.symbol.split("-")[0],
        strike=_d(raw.strike_price) or Decimal("0"),
        option_type=opt_type,
        expiration=exp,
        bid_price=_d(raw.bid_price),
        ask_price=_d(raw.ask_price),
        bid_size=_d(raw.bid_amount),
        ask_size=_d(raw.ask_amount),
        implied_volatility=raw.mark_iv,
        delta=raw.delta,
        gamma=raw.gamma,
        theta=raw.theta,
        vega=raw.vega,
        instrument_key=f"{venue}:OPTION:{raw.symbol}",
    )


# ---------------------------------------------------------------------------
# Derivative Ticker
# ---------------------------------------------------------------------------


def normalize_tardis_derivative_ticker(
    raw: dict[str, str | int | float | None],
    instrument_key: str | None = None,
    venue: str = "tardis",
) -> CanonicalDerivativeTicker:
    """Normalize a Tardis replay derivative ticker dict to CanonicalDerivativeTicker."""
    symbol = str(raw.get("symbol") or raw.get("s") or "")
    ik = instrument_key or f"{venue}:PERPETUAL:{symbol}"

    ts_raw = raw.get("timestamp") or raw.get("ts")
    timestamp = _ms_to_utc(ts_raw) or _now_utc()

    mark_price = _to_decimal(raw.get("markPrice") or raw.get("mark_price"))
    index_price = _to_decimal(raw.get("indexPrice") or raw.get("index_price"))
    last_price = _to_decimal(raw.get("lastPrice") or raw.get("last_price"))
    funding_rate = _to_decimal(raw.get("fundingRate") or raw.get("funding_rate"))
    next_funding_timestamp = _ms_to_utc(raw.get("nextFundingTime") or raw.get("next_funding_timestamp"))
    open_interest = _to_decimal(raw.get("openInterest") or raw.get("open_interest"))
    open_interest_value = _to_decimal(raw.get("openInterestValue") or raw.get("open_interest_value"))

    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=timestamp,
        mark_price=mark_price,
        index_price=index_price,
        last_price=last_price,
        funding_rate=funding_rate,
        next_funding_timestamp=next_funding_timestamp,
        open_interest=open_interest,
        open_interest_value=open_interest_value,
    )


# ---------------------------------------------------------------------------
# Liquidation
# ---------------------------------------------------------------------------


def normalize_tardis_liquidation(
    raw: TardisLiquidations,
    venue: str = "",
    symbol: str = "",
) -> CanonicalLiquidation:
    """Convert TardisLiquidations to CanonicalLiquidation."""
    v = venue or raw.exchange or "tardis"
    sym = symbol or raw.symbol or ""
    ik = f"{v.upper()}:PERP:{sym}"
    ts = datetime.fromtimestamp((raw.timestamp or 0) / 1_000_000.0, tz=UTC)
    side = raw.side if raw.side in ("buy", "sell") else "sell"
    return CanonicalLiquidation(
        instrument_key=ik,
        venue=v,
        timestamp=ts,
        side=side,
        price=Decimal("0"),
        size=Decimal("0"),
        order_id=raw.id,
        liquidated_account_value=None,
        liquidated_ntl_pos=None,
        liquidated_user=None,
    )


# ---------------------------------------------------------------------------
# WebSocket Connectivity
# ---------------------------------------------------------------------------


def normalize_tardis_ws_subscription(
    subscribed: bool,
    channel: str = "",
    venue: str = "tardis",
) -> CanonicalWebSocketLifecycle:
    """Normalize Tardis replay WS subscription acknowledgement."""
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=WebSocketEvent.SUBSCRIBE if subscribed else WebSocketEvent.ERROR,
        timestamp=datetime.now(UTC),
        channel=channel or None,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

TARDIS_MAP: dict[str, Callable[..., CanonicalError]] = {
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
    "503": CanonicalServiceUnavailableError,
}


def normalize_tardis_error(
    error_code: str | int,
    message: str = "",
    venue: str = "tardis",
) -> CanonicalError:
    """Map a Tardis HTTP status code to a CanonicalError subclass."""
    code = str(error_code)
    cls = TARDIS_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_tardis_derivative_ticker",
    "normalize_tardis_error",
    "normalize_tardis_instrument",
    "normalize_tardis_liquidation",
    "normalize_tardis_option_quote",
    "normalize_tardis_orderbook",
    "normalize_tardis_trade",
    "normalize_tardis_ws_subscription",
]
