"""IBKR normalizers — all normalize_ibkr_* functions.

Extracted from normalize_utils/ modules (trades, instruments, options,
orders_fills, tickers, market_state, connectivity, errors).
"""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.crosscutting.errors import (
    CanonicalError,
    CanonicalInvalidRequestError,
    CanonicalNetworkError,
    CanonicalOrderRejectedError,
    CanonicalServiceUnavailableError,
    ErrorAction,
)
from ...canonical.domain import (
    CanonicalInstrument,
    CanonicalMarketStateEvent,
    CanonicalOptionsChainEntry,
    CanonicalTicker,
    CanonicalTrade,
    CanonicalWebSocketLifecycle,
    MarketState,
)
from ...canonical.domain.execution import (
    CanonicalFill,
    CanonicalOrder,
    OrderSide,
    OrderStatus,
    OrderType,
)
from ...normalize_utils._helpers import to_decimal
from ...normalize_utils.connectivity import normalize_ws_disconnect
from ...normalize_utils.market_state import IBKR_STATE_MAP as _IBKR_STATE_MAP
from ...normalize_utils.market_state import normalize_market_state
from .schemas import (
    IBKRContractDetails,
    IBKRExecution,
    IBKROptionGreeks,
    IBKROrder,
    IBKRTicker,
)

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _d(value: float | int | str | Decimal | None) -> Decimal | None:
    """Convert any numeric value to Decimal; return None for None."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _normalize_side(s: str | None) -> str:
    if not s:
        return OrderSide.BUY
    return OrderSide.SELL if str(s).lower() in ("sell", "short", "sld") else OrderSide.BUY


def _normalize_order_type(t: str | None) -> str:
    if not t:
        return OrderType.LIMIT
    t_lower = str(t).lower()
    if "market" in t_lower or t_lower in ("mkt",):
        return OrderType.MARKET
    if "stop_limit" in t_lower or t_lower in ("stp lmt",):
        return OrderType.STOP_LIMIT
    if "stop" in t_lower or t_lower in ("stp",):
        return OrderType.STOP
    return OrderType.LIMIT


def _normalize_order_status(s: str | None) -> str:
    if not s:
        return OrderStatus.PENDING
    s_lower = str(s).lower()
    if s_lower in ("open", "live", "new", "submitted", "presubmitted"):
        return OrderStatus.OPEN
    if s_lower in ("partially_filled", "partiallyfilled"):
        return OrderStatus.PARTIALLY_FILLED
    if s_lower in ("closed", "filled", "done"):
        return OrderStatus.FILLED
    if s_lower in ("canceled", "cancelled", "cancel", "apicancelled"):
        return OrderStatus.CANCELLED
    if s_lower == "rejected":
        return OrderStatus.REJECTED
    if s_lower == "expired":
        return OrderStatus.EXPIRED
    return OrderStatus.PENDING


def _parse_decimal(val: str | float | Decimal | None) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _ibkr_instrument_type(sec_type: str | None) -> str:
    mapping: dict[str, str] = {
        "STK": "EQUITY",
        "CASH": "CURRENCY",
        "CFD": "SPOT_PAIR",
        "IND": "INDEX",
        "FUND": "ETF",
        "CMDTY": "COMMODITY",
        "FUT": "FUTURE",
        "OPT": "OPTION",
        "FOP": "OPTION",
        "WAR": "OPTION",
        "BAG": "FUTURE",
        "BOND": "BOND",
    }
    return mapping.get((sec_type or "").upper(), "SPOT_PAIR")


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_ibkr_trade(
    raw: IBKRExecution,
    venue: str = "ibkr",
    symbol: str = "",
) -> CanonicalTrade:
    """Convert IBKRExecution to CanonicalTrade.

    IBKRExecution is an execution (fill) from execDetails; side is "BOT"/"SLD".
    Mapped as a public trade record. time is a string like "20240101 09:30:00 EST".
    """
    ts = datetime.now(UTC)
    if raw.time:
        with contextlib.suppress(ValueError, TypeError):
            # IBKR format: "20240101 09:30:00 EST" or "20240101  09:30:00"
            ts = datetime.strptime(raw.time[:16].strip(), "%Y%m%d %H:%M").replace(tzinfo=UTC)
    sym = symbol or raw.exchange or ""
    side = "buy" if (raw.side or "").upper() in ("BOT", "BUY") else "sell"
    price = Decimal(str(raw.price or 0))
    qty = Decimal(str(raw.shares or 0))
    return CanonicalTrade(
        venue=venue,
        symbol=sym if sym else "UNKNOWN",
        trade_id=raw.execId or "",
        timestamp=ts,
        price=price if price > Decimal("0") else Decimal("0.000001"),
        quantity=qty if qty > Decimal("0") else Decimal("0.000001"),
        side=side,
        buyer_maker=None,
        venue_trade_id=raw.execId,
    )


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


def normalize_ibkr_contract_details(
    raw: IBKRContractDetails,
    venue: str = "ibkr",
) -> CanonicalInstrument:
    """Normalize an IBKRContractDetails to CanonicalInstrument."""
    instrument_type = _ibkr_instrument_type(raw.secType)
    symbol = raw.localSymbol or raw.symbol or ""
    instrument_key = f"{venue.upper()}:{instrument_type}:{symbol}"

    tick_size = Decimal(str(raw.minTick)) if raw.minTick is not None else None

    contract_size: Decimal | None = None
    if raw.multiplier is not None:
        try:
            contract_size = Decimal(str(raw.multiplier))
        except (ValueError, TypeError):
            contract_size = None

    return CanonicalInstrument(
        instrument_key=instrument_key,
        venue=venue,
        symbol=symbol,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=None,
        contract_size=contract_size,
        base_asset=raw.symbol,
        quote_asset=raw.currency,
        settle_asset=None,
    )


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------


def normalize_ibkr_option_quote(
    raw: IBKRContractDetails,
    ticker: IBKRTicker | None = None,
    greeks: IBKROptionGreeks | None = None,
    venue: str = "ibkr",
) -> CanonicalOptionsChainEntry:
    """Convert IBKRContractDetails (+ optional live ticker + greeks) to CanonicalOptionsChainEntry."""
    ts = datetime.now(tz=UTC)
    opt_type = "put" if (raw.right or "C").upper() == "P" else "call"
    exp: datetime | None = None
    if raw.lastTradeDateOrContractMonth:
        raw_exp = raw.lastTradeDateOrContractMonth.strip()
        try:
            if len(raw_exp) == 8:
                exp = datetime.strptime(raw_exp, "%Y%m%d").replace(tzinfo=UTC)
            elif len(raw_exp) == 6:
                exp = datetime.strptime(raw_exp, "%Y%m").replace(tzinfo=UTC)
        except ValueError:
            exp = None

    bid = ticker.bid if ticker is not None else None
    ask = ticker.ask if ticker is not None else None
    bid_sz = ticker.bidSize if ticker is not None else None
    ask_sz = ticker.askSize if ticker is not None else None
    iv = greeks.impliedVol if greeks is not None else None
    delta = greeks.delta if greeks is not None else None
    gamma = greeks.gamma if greeks is not None else None
    theta = greeks.theta if greeks is not None else None
    vega = greeks.vega if greeks is not None else None

    symbol = raw.localSymbol or raw.symbol or str(raw.conid or "")
    underlying = raw.symbol or ""

    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        underlying=underlying,
        strike=_d(raw.strike) or Decimal("0"),
        option_type=opt_type,
        expiration=exp,
        bid_price=_d(bid),
        ask_price=_d(ask),
        bid_size=_d(bid_sz),
        ask_size=_d(ask_sz),
        implied_volatility=iv,
        delta=delta,
        gamma=gamma,
        theta=theta,
        vega=vega,
        instrument_key=f"{venue}:OPTION:{symbol}",
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_ibkr_order(raw: IBKROrder, instrument_id: str = "", venue: str = "ibkr") -> CanonicalOrder:
    """Convert IBKROrder to CanonicalOrder."""
    ts = datetime.now(UTC)
    return CanonicalOrder(
        order_id=str(raw.orderId or ""),
        client_order_id=str(raw.permId) if raw.permId is not None else None,
        timestamp=ts,
        venue=venue,
        instrument_id=instrument_id,
        side=_normalize_side(raw.action),
        order_type=_normalize_order_type(raw.orderType),
        quantity=_parse_decimal(raw.totalQuantity or 0),
        price=_parse_decimal(raw.lmtPrice) if raw.lmtPrice is not None else None,
        status=_normalize_order_status(raw.status),
        filled_quantity=_parse_decimal(raw.filledQuantity or 0),
        remaining_quantity=None,
        average_fill_price=_parse_decimal(raw.avgFillPrice) if raw.avgFillPrice is not None else None,
    )


# ---------------------------------------------------------------------------
# Fill (Execution)
# ---------------------------------------------------------------------------


def normalize_ibkr_execution(raw: IBKRExecution, instrument_id: str = "", venue: str = "ibkr") -> CanonicalFill:
    """Convert IBKRExecution to CanonicalFill."""
    ts = datetime.now(UTC)
    if raw.time:
        try:
            ts = datetime.fromisoformat(str(raw.time).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            _logger.debug("IBKR execution time %r is not a valid ISO datetime; using current UTC time", raw.time)
    return CanonicalFill(
        fill_id=str(raw.execId or ""),
        order_id=str(raw.orderId or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=instrument_id,
        side=_normalize_side(raw.side),
        price=_parse_decimal(raw.price or 0),
        quantity=_parse_decimal(raw.shares or 0),
        fee=None,
        fee_currency=None,
        is_maker=None,
    )


# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


def normalize_ibkr_ticker(raw: IBKRTicker, instrument_key: str, venue: str = "ibkr") -> CanonicalTicker:
    """Convert IBKRTicker to CanonicalTicker."""
    ts = datetime.now(UTC)
    return CanonicalTicker(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        last_price=to_decimal(raw.last) or Decimal("0"),
        bid_price=to_decimal(raw.bid),
        ask_price=to_decimal(raw.ask),
        volume_24h=to_decimal(raw.volume),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


# ---------------------------------------------------------------------------
# Market State
# ---------------------------------------------------------------------------


def normalize_ibkr_market_state(
    trading_phase: str,
    symbol: str,
    sec_type: str = "STK",
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "ibkr",
) -> CanonicalMarketStateEvent:
    """Normalize an IBKR trading phase string to CanonicalMarketStateEvent."""
    type_map = {
        "STK": "EQUITY",
        "FUT": "FUTURE",
        "OPT": "OPTION",
        "CASH": "CURRENCY",
        "IND": "INDEX",
        "FUND": "ETF",
        "CMDTY": "COMMODITY",
        "BOND": "BOND",
    }
    inst_type = type_map.get(sec_type.upper(), "SPOT_PAIR")
    ik = f"{venue}:{inst_type}:{symbol}"
    return normalize_market_state(
        raw_state=trading_phase,
        venue=venue,
        instrument_key=ik,
        state_map=_IBKR_STATE_MAP,
        previous_state=previous_state,
        reason=reason,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# WebSocket Connectivity
# ---------------------------------------------------------------------------


def normalize_ibkr_ws_close(
    code: int,
    reason: str | None = None,
    venue: str = "ibkr",
) -> CanonicalWebSocketLifecycle:
    """Normalize IBKR WebSocket close frame."""
    return normalize_ws_disconnect(venue=venue, code=code, reason=reason)


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

from collections.abc import Callable

IBKR_MAP: dict[str, Callable[..., CanonicalError]] = {
    "100": CanonicalServiceUnavailableError,
    "1100": CanonicalNetworkError,
    "1300": CanonicalOrderRejectedError,
    "200": CanonicalInvalidRequestError,
    "201": CanonicalOrderRejectedError,
    "2110": CanonicalServiceUnavailableError,
    "10147": CanonicalOrderRejectedError,
    "10148": CanonicalInvalidRequestError,
}


def normalize_ibkr_error(
    error_code: str | int,
    message: str = "",
    venue: str = "ibkr",
) -> CanonicalError:
    """Map an IBKR TWS/Gateway error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = IBKR_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_ibkr_contract_details",
    "normalize_ibkr_error",
    "normalize_ibkr_execution",
    "normalize_ibkr_market_state",
    "normalize_ibkr_option_quote",
    "normalize_ibkr_order",
    "normalize_ibkr_ticker",
    "normalize_ibkr_trade",
    "normalize_ibkr_ws_close",
]
