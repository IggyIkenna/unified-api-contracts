"""Kalshi venue-specific normalizers.

Re-exports all normalize_kalshi_* functions from normalize_utils/ modules
into a single venue-local module.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.errors import (
    CanonicalError,
    CanonicalInsufficientBalanceError,
    CanonicalInternalServerError,
    CanonicalMarketClosedError,
    CanonicalOrderRejectedError,
    CanonicalRateLimitError,
    CanonicalServiceUnavailableError,
    ErrorAction,
)
from unified_api_contracts.canonical.domain import (
    CanonicalBetMarket,
    CanonicalBetOrder,
    CanonicalMarketStateEvent,
    CanonicalOdds,
    CanonicalOhlcvBar,
    CanonicalOrderBook,
    CanonicalTicker,
    CanonicalTrade,
    CanonicalWebSocketLifecycle,
    MarketState,
    WebSocketEvent,
)
from unified_api_contracts.canonical.domain.execution import (
    CanonicalFill,
    OrderSide,
)
from unified_api_contracts.normalize_utils._helpers import d
from unified_api_contracts.normalize_utils.errors._utils import from_http_status
from unified_api_contracts.normalize_utils.market_state import normalize_market_state

from .schemas import (
    KalshiCandlestick,
    KalshiFill,
    KalshiMarket,
    KalshiOrder,
    KalshiOrderBook,
    KalshiTrade,
    KalshiWebSocketTickerMsg,
    KalshiWebSocketTradeMsg,
)

# ---------------------------------------------------------------------------
# Error map
# ---------------------------------------------------------------------------

_KALSHI_ERROR_MAP: dict[str, type[CanonicalError]] = {
    "429": CanonicalRateLimitError,
    "401": CanonicalRateLimitError,
    "500": CanonicalInternalServerError,
    "503": CanonicalServiceUnavailableError,
    "INSUFFICIENT_FUNDS": CanonicalInsufficientBalanceError,
    "MARKET_CLOSED": CanonicalMarketClosedError,
    "ORDER_REJECTED": CanonicalOrderRejectedError,
}

# ---------------------------------------------------------------------------
# Market state map
# ---------------------------------------------------------------------------

_KALSHI_STATUS_MAP: dict[str, MarketState] = {
    "OPEN": MarketState.NORMAL,
    "CLOSED": MarketState.CLOSED,
    "SETTLED": MarketState.CLOSED,
    "DEACTIVATED": MarketState.CLOSED,
    "UPCOMING": MarketState.PRE_MARKET,
    "ACTIVE": MarketState.NORMAL,
    "PAUSED": MarketState.HALTED,
}


# ---------------------------------------------------------------------------
# Sports / prediction normalizers
# ---------------------------------------------------------------------------


def normalize_kalshi_market(raw: KalshiMarket, venue: str = "kalshi") -> CanonicalBetMarket:
    """Convert KalshiMarket to CanonicalBetMarket."""
    now = datetime.now(UTC)
    close_time: datetime | None = None
    if raw.close_time:
        try:
            close_time = datetime.fromisoformat(raw.close_time.replace("Z", "+00:00"))
            if close_time.tzinfo is None:
                close_time = close_time.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            close_time = None
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.ticker or "",
        event_id=raw.event_ticker or "",
        market_name=raw.title or raw.subtitle or "",
        event_name=raw.event_ticker or "",
        sport=None,
        competition=None,
        status=raw.status,
        in_play=False,  # Kalshi is pre-event only
        timestamp=now,
        close_time=close_time,
    )


def normalize_kalshi_odds(raw: KalshiMarket, is_yes: bool = True, venue: str = "kalshi") -> CanonicalOdds:
    """Convert KalshiMarket to CanonicalOdds.

    yes_bid_dollars/yes_ask_dollars/no_bid_dollars/no_ask_dollars are string
    fixed-point dollars (e.g. "0.4500").
    Converts probability to decimal odds: decimal = 1 / probability.
    """
    now = datetime.now(UTC)
    if is_yes:
        price_str = raw.yes_bid_dollars or raw.yes_ask_dollars
        selection_name = "Yes"
        selection_id = f"{raw.ticker or ''}-yes"
    else:
        price_str = raw.no_bid_dollars or raw.no_ask_dollars
        selection_name = "No"
        selection_id = f"{raw.ticker or ''}-no"

    prob = float(price_str) if price_str else 0.5
    # Clamp probability to avoid division by zero or absurd odds
    prob = max(0.01, min(0.99, prob))
    decimal_odds = Decimal(str(round(1.0 / prob, 6)))

    return CanonicalOdds(
        venue=venue,
        event_id=raw.event_ticker or "",
        market_id=raw.ticker or "",
        selection_id=selection_id,
        selection_name=selection_name,
        decimal_odds=decimal_odds,
        timestamp=now,
        is_back=True,
        available_size=None,
        event_name=raw.event_ticker or "",
        sport=None,
        competition=None,
    )


def normalize_kalshi_order(raw: KalshiOrder, venue: str = "kalshi") -> CanonicalBetOrder:
    """Convert KalshiOrder to CanonicalBetOrder."""
    now = datetime.now(UTC)
    ts = now
    if raw.created_time:
        try:
            ts = datetime.fromisoformat(raw.created_time.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            ts = now
    # Kalshi side is "yes" or "no"; action is "buy" or "sell"
    # For CanonicalBetOrder, side is "back" (buy yes) or "lay" (sell yes / buy no)
    side = "back"
    if raw.action == "sell" or raw.side == "no":
        side = "lay"
    # Price: Kalshi orders use integer cent fields (yes_price, no_price)
    price = Decimal("0.5")
    if raw.yes_price is not None:
        price = Decimal(str(raw.yes_price / 100))
    elif raw.no_price is not None:
        # no price in cents, yes price = 1 - no_price/100
        price = Decimal(str(1 - raw.no_price / 100))
    # Convert implied probability to decimal odds
    prob = float(price)
    prob = max(0.01, min(0.99, prob))
    decimal_odds = Decimal(str(round(1.0 / prob, 6)))

    size = Decimal(str(raw.count or 0))
    remaining = Decimal(str(raw.remaining_count or 0)) if raw.remaining_count is not None else None
    matched = size - remaining if remaining is not None else None

    return CanonicalBetOrder(
        venue=venue,
        order_id=raw.order_id or "",
        market_id=raw.ticker or "",
        selection_id=f"{raw.ticker or ''}-{raw.side or 'yes'}",
        side=side,
        price=decimal_odds,
        size=size,
        status=raw.status or "unknown",
        timestamp=ts,
        matched_size=matched,
        remaining_size=remaining,
    )


# ---------------------------------------------------------------------------
# OHLCV
# ---------------------------------------------------------------------------


def normalize_kalshi_candlestick(raw: KalshiCandlestick, symbol: str = "", venue: str = "kalshi") -> CanonicalOhlcvBar:
    """Convert KalshiCandlestick to CanonicalOhlcvBar.

    Kalshi uses yes_*_dollars fields (string decimals) and end_period_ts (ISO string).
    Open/high/low/close are approximated from yes_open/high/low/close_dollars.
    Volume from volume_fp (string float contracts).
    """
    ts = datetime.now(UTC)
    if raw.end_period_ts:
        with contextlib.suppress(ValueError):
            ts = datetime.fromisoformat(raw.end_period_ts.replace("Z", "+00:00"))
    sym = symbol or raw.ticker or ""
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=sym,
        open=d(raw.yes_open_dollars),
        high=d(raw.yes_high_dollars),
        low=d(raw.yes_low_dollars),
        close=d(raw.yes_close_dollars),
        volume=d(raw.volume_fp),
        quote_volume=None,
        count=None,
        vwap=None,
    )


# ---------------------------------------------------------------------------
# Market state
# ---------------------------------------------------------------------------


def normalize_kalshi_market_state(
    status: str,
    ticker: str,
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "kalshi",
) -> CanonicalMarketStateEvent:
    """Normalize a Kalshi market status to CanonicalMarketStateEvent.

    Kalshi market.status: open | closed | settled | deactivated | upcoming | active | paused.

    Args:
        status:    Market status string.
        ticker:    Market ticker (e.g. BTCZ-25JAN31-T50000).
        previous_state: Previous state.
        reason:    Context.
        timestamp: Event time.
        venue:     Venue tag.
    """
    ik = f"{venue}:PREDICTION:{ticker}"
    return normalize_market_state(
        raw_state=status,
        venue=venue,
        instrument_key=ik,
        state_map=_KALSHI_STATUS_MAP,
        previous_state=previous_state,
        reason=reason,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# Fills
# ---------------------------------------------------------------------------


def normalize_kalshi_fill(
    raw: KalshiFill,
    venue: str = "kalshi",
    instrument_id: str = "",
) -> CanonicalFill:
    """Convert KalshiFill to CanonicalFill.

    KalshiFill: yes_price_dollars (str decimal), count_fp (str float contracts),
    fees_dollars (str decimal), is_taker (bool), side ("yes"/"no"), action ("buy"/"sell").
    """
    ts = datetime.now(UTC)
    if raw.created_time:
        with contextlib.suppress(ValueError, TypeError):
            ts = datetime.fromisoformat(raw.created_time.replace("Z", "+00:00"))
    price = Decimal(str(raw.yes_price_dollars or 0))
    qty = Decimal(str(raw.count_fp or 0))
    fee = Decimal(str(raw.fees_dollars or 0))
    side = OrderSide.BUY if (raw.action or "buy").lower() == "buy" else OrderSide.SELL
    return CanonicalFill(
        venue=venue,
        order_id=raw.order_id or "",
        fill_id=raw.trade_id or "",
        instrument_id=instrument_id or raw.ticker or "",
        side=side,
        price=price if price > Decimal("0") else Decimal("0.01"),
        quantity=qty if qty > Decimal("0") else Decimal("0.000001"),
        fee=fee,
        fee_currency="USD",
        timestamp=ts,
        is_maker=not raw.is_taker if raw.is_taker is not None else None,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_kalshi_orderbook(
    raw: KalshiOrderBook,
    venue: str = "kalshi",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert KalshiOrderBook to CanonicalOrderBook.

    Kalshi uses yes_dollars: [("price_str", "size_str"), ...] for bids/asks.
    Yes bids are the bids; no_dollars (complement prices) form the asks.
    """
    sym = symbol or raw.ticker or ""
    bids: list[tuple[Decimal, Decimal]] = []
    asks: list[tuple[Decimal, Decimal]] = []
    for entry in raw.yes_dollars or []:
        if len(entry) >= 2:
            with contextlib.suppress(Exception):
                bids.append((Decimal(str(entry[0])), Decimal(str(entry[1]))))
    for entry in raw.no_dollars or []:
        if len(entry) >= 2:
            with contextlib.suppress(Exception):
                asks.append((Decimal(str(entry[0])), Decimal(str(entry[1]))))
    return CanonicalOrderBook(
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        bids=bids,
        asks=asks,
        sequence_number=None,
        levels=len(bids) or len(asks) or 1,
    )


# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


def normalize_kalshi_ticker(
    raw: KalshiWebSocketTickerMsg,
    instrument_key: str | None = None,
    venue: str = "kalshi",
) -> CanonicalTicker:
    """Convert KalshiWebSocketTickerMsg to CanonicalTicker.

    Kalshi prices are string fixed-point dollars (e.g. "0.4500") as of March 2026.
    Volume and open_interest in integer contracts.
    """
    sym = raw.market_ticker or ""
    ik = instrument_key or f"{venue}:MARKET:{sym}"
    last = Decimal(raw.yes_price_dollars or "0")
    bid = Decimal(raw.yes_bid_dollars) if raw.yes_bid_dollars is not None else None
    ask = Decimal(raw.yes_ask_dollars) if raw.yes_ask_dollars is not None else None
    ts = datetime.fromtimestamp((raw.ts or 0) / 1000.0, tz=UTC) if raw.ts else datetime.now(UTC)
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=last,
        bid_price=bid,
        ask_price=ask,
        volume_24h=Decimal(str(raw.volume)) if raw.volume is not None else None,
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------


def normalize_kalshi_trade(
    raw: KalshiTrade,
    venue: str = "kalshi",
    symbol: str = "",
) -> CanonicalTrade:
    """Convert KalshiTrade (REST) to CanonicalTrade.

    yes_price_dollars is the price of a Yes contract in dollars (string decimal).
    count_fp is the number of contracts (string float).
    taker_side: "yes"/"no" -- mapped to "buy"/"sell".
    """
    sym = symbol or raw.ticker or "UNKNOWN"
    ts = datetime.now(UTC)
    if raw.created_time:
        with contextlib.suppress(ValueError, TypeError):
            ts = datetime.fromisoformat(raw.created_time.replace("Z", "+00:00"))
    side = "buy" if (raw.taker_side or "").lower() == "yes" else "sell"
    price = Decimal(str(raw.yes_price_dollars or 0))
    qty = Decimal(str(raw.count_fp or 0))
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=raw.trade_id or "",
        timestamp=ts,
        price=price if price > Decimal("0") else Decimal("0.01"),
        quantity=qty if qty > Decimal("0") else Decimal("1"),
        side=side,
        buyer_maker=None,
        venue_trade_id=raw.trade_id,
    )


def normalize_kalshi_ws_trade(
    raw: KalshiWebSocketTradeMsg,
    venue: str = "kalshi",
    symbol: str = "",
) -> CanonicalTrade:
    """Convert KalshiWebSocketTradeMsg to CanonicalTrade.

    yes_price_dollars is string fixed-point dollars (e.g. "0.4500") as of March 2026.
    count in integer contracts.
    """
    sym = symbol or raw.market_ticker or "UNKNOWN"
    ts = datetime.fromtimestamp((raw.ts or 0) / 1000.0, tz=UTC) if raw.ts else datetime.now(UTC)
    side = "buy" if (raw.taker_side or "").lower() == "yes" else "sell"
    price = Decimal(raw.yes_price_dollars or "0")
    qty = Decimal(str(raw.count or 0))
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=raw.trade_id or "",
        timestamp=ts,
        price=price if price > Decimal("0") else Decimal("0.01"),
        quantity=qty if qty > Decimal("0") else Decimal("1"),
        side=side,
        buyer_maker=None,
        venue_trade_id=raw.trade_id,
    )


# ---------------------------------------------------------------------------
# WebSocket lifecycle
# ---------------------------------------------------------------------------


def normalize_kalshi_ws_lifecycle(
    action: str,
    market_ticker: str = "",
    venue: str = "kalshi",
) -> CanonicalWebSocketLifecycle:
    """Normalize Kalshi WebSocket market lifecycle event (open/close/settle)."""
    if action in ("opened",):
        evt = WebSocketEvent.CONNECT
    elif action in ("closed", "settled"):
        evt = WebSocketEvent.DISCONNECT
    else:
        evt = WebSocketEvent.SUBSCRIBE
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=evt,
        timestamp=datetime.now(UTC),
        channel=market_ticker or None,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


def normalize_kalshi_error(
    error_code: str | int,
    message: str = "",
    venue: str = "kalshi",
) -> CanonicalError:
    """Map a Kalshi HTTP status or error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _KALSHI_ERROR_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_kalshi_candlestick",
    "normalize_kalshi_error",
    "normalize_kalshi_fill",
    "normalize_kalshi_market",
    "normalize_kalshi_market_state",
    "normalize_kalshi_odds",
    "normalize_kalshi_order",
    "normalize_kalshi_orderbook",
    "normalize_kalshi_ticker",
    "normalize_kalshi_trade",
    "normalize_kalshi_ws_lifecycle",
    "normalize_kalshi_ws_trade",
]
