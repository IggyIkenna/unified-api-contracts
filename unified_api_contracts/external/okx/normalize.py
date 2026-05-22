"""OKX normalizers — all normalize_okx_* functions.

Extracted from normalize_utils/ modules.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import (
    CanonicalDerivativeTicker,
    CanonicalFee,
    CanonicalInstrument,
    CanonicalLiquidation,
    CanonicalMarketStateEvent,
    CanonicalOhlcvBar,
    CanonicalOrderBook,
    CanonicalTicker,
    CanonicalTrade,
    CanonicalWebSocketLifecycle,
    FeeType,
    MarketState,
    WebSocketEvent,
)
from ...canonical.domain.execution import (
    CanonicalFill,
    CanonicalOrder,
    OrderSide,
    OrderStatus,
    OrderType,
)
from ...normalize_utils._helpers import d, side, to_decimal, to_levels, ts_ms, ts_ms_to_datetime
from ...normalize_utils.market_state import OKX_STATE_MAP as _OKX_STATE_MAP
from ...normalize_utils.market_state import normalize_market_state
from ..okx.schemas import (
    OKXCandleWS,
    OKXFeeRate,
    OKXFundingRate,
    OKXInstrumentInfo,
    OKXLiquidationOrder,
    OKXOpenInterest,
    OKXOrder,
    OKXOrderBook,
    OKXOrderUpdateWS,
    OKXTicker,
    OKXTrade,
)


def _parse_decimal(val: str | float | Decimal | None) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _normalize_side(s: str | None) -> OrderSide:
    if not s:
        return OrderSide.BUY
    return OrderSide.SELL if str(s).lower() in ("sell", "short") else OrderSide.BUY


def _normalize_order_type(t: str | None) -> OrderType:
    if not t:
        return OrderType.LIMIT
    t = str(t).lower()
    if t in ("market", "m"):
        return OrderType.MARKET
    if t in ("stop", "stop_market"):
        return OrderType.STOP
    if t in ("stop_limit", "stop_limit_order"):
        return OrderType.STOP_LIMIT
    return OrderType.LIMIT


def _normalize_order_status(s: str | None) -> OrderStatus:
    if not s:
        return OrderStatus.PENDING
    s = str(s).lower()
    if s in ("open", "live", "new", "partiallyfilled"):
        return OrderStatus.OPEN
    if s in ("partially_filled", "partiallyfilled"):
        return OrderStatus.PARTIALLY_FILLED
    if s in ("closed", "filled", "done"):
        return OrderStatus.FILLED
    if s in ("canceled", "cancelled", "cancel"):
        return OrderStatus.CANCELLED
    if s == "rejected":
        return OrderStatus.REJECTED
    if s == "expired":
        return OrderStatus.EXPIRED
    return OrderStatus.PENDING


# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


def normalize_okx_ticker(raw: OKXTicker, instrument_key: str | None = None, venue: str = "okx") -> CanonicalTicker:
    ik = instrument_key or f"{venue}:SPOT:{raw.instId or ''}"
    ts = datetime.now(UTC)
    t_ts = raw.info.get("ts") if raw.info else None
    if isinstance(t_ts, (int, float, str)):
        ts = ts_ms_to_datetime(int(t_ts))
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=to_decimal(raw.last) or Decimal("0"),
        bid_price=to_decimal(raw.bidPx),
        ask_price=to_decimal(raw.askPx),
        volume_24h=to_decimal(raw.vol24h),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_okx_orderbook(
    raw: OKXOrderBook,
    venue: str = "okx",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert OKXOrderBook to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(int(raw.ts) / 1000.0, tz=UTC) if raw.ts is not None else datetime.now(UTC)
    bids = to_levels(raw.bids)
    asks = to_levels(raw.asks)
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol,
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.seqId,
    )


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_okx_trade(raw: OKXTrade, venue: str = "okx", symbol: str = "") -> CanonicalTrade:
    """Convert OKXTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.ts:
        ts = datetime.fromtimestamp(int(raw.ts) / 1000.0, tz=UTC)
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or (raw.instId or "") or "UNKNOWN",
        trade_id=str(raw.tradeId) if raw.tradeId else "",
        timestamp=ts,
        price=Decimal(str(raw.px or 0)),
        quantity=Decimal(str(raw.sz or 0)),
        side=(raw.side or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=str(raw.tradeId) if raw.tradeId else None,
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_okx_order(raw: OKXOrder, venue: str = "okx") -> CanonicalOrder:
    ts = datetime.now(UTC)
    symbol = raw.instId or ""
    return CanonicalOrder(
        order_id=str(raw.ordId or ""),
        client_order_id=raw.clOrdId,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        order_type=_normalize_order_type(raw.ordType),
        quantity=_parse_decimal(raw.sz or 0),
        price=_parse_decimal(raw.px) if raw.px else None,
        status=_normalize_order_status(raw.state),
        filled_quantity=_parse_decimal(raw.accFillSz or 0),
        remaining_quantity=None,
        average_fill_price=_parse_decimal(raw.fillPx) if raw.fillPx else None,
    )


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_okx_fill(raw: OKXOrderUpdateWS, venue: str = "okx") -> CanonicalFill | None:
    """Convert OKXOrderUpdateWS (fill event) to CanonicalFill.

    Returns None if this is not a fill event (no fillSz).
    """
    if not raw.fillSz or raw.fillSz == "0":
        return None
    ts = datetime.now(UTC)
    if raw.fillTime:
        ts = ts_ms(raw.fillTime)
    elif raw.uTime:
        ts = ts_ms(raw.uTime)
    is_maker: bool | None = None
    if raw.execType:
        is_maker = raw.execType.upper() == "M"
    fill_id = str(raw.tradeId) if raw.tradeId else f"{raw.ordId}-{raw.fillTime or 0}"
    return CanonicalFill(
        fill_id=fill_id,
        order_id=str(raw.ordId or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=raw.instId or "",
        side=side(raw.side),
        price=d(raw.fillPx),
        quantity=d(raw.fillSz),
        fee=None,
        fee_currency=None,
        is_maker=is_maker,
    )


# ---------------------------------------------------------------------------
# Derivative Ticker
# ---------------------------------------------------------------------------


def normalize_okx_derivative_ticker(
    raw: OKXTicker,
    funding: OKXFundingRate | None = None,
    oi: OKXOpenInterest | None = None,
    instrument_key: str | None = None,
    venue: str = "okx",
) -> CanonicalDerivativeTicker:
    """Normalize OKX ticker (+ optional funding + OI) to CanonicalDerivativeTicker."""
    inst_id = raw.instId or ""
    ik = instrument_key or f"{venue}:PERPETUAL:{inst_id}"
    last_price = to_decimal(raw.last)
    info: dict[str, object] = raw.info or {}

    def _ms_to_utc(ts_ms_val: object | None) -> datetime | None:
        if ts_ms_val is None:
            return None
        try:
            ms = int(str(ts_ms_val))
            if ms <= 0:
                return None
            return datetime.fromtimestamp(ms / 1000.0, tz=UTC)
        except (ValueError, TypeError, OSError):
            return None

    mark_price = to_decimal(info.get("markPx") or info.get("mark_px"))
    index_price = to_decimal(info.get("idxPx") or info.get("idx_px"))
    ts_raw = info.get("ts")
    timestamp: datetime = _ms_to_utc(ts_raw) or datetime.now(UTC) if ts_raw is not None else datetime.now(UTC)

    funding_rate_val: Decimal | None = None
    predicted_funding: Decimal | None = None
    next_funding_timestamp: datetime | None = None
    funding_timestamp: datetime | None = None

    if funding is not None:
        funding_rate_val = to_decimal(funding.fundingRate)
        funding_timestamp = _ms_to_utc(funding.fundingTime)
        predicted_funding = to_decimal(funding.nextFundingRate)
        next_funding_timestamp = _ms_to_utc(funding.nextFundingTime)

    open_interest_val: Decimal | None = None
    open_interest_value_val: Decimal | None = None
    if oi is not None:
        open_interest_val = to_decimal(oi.oi)
        open_interest_value_val = to_decimal(oi.oiCcy)

    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=timestamp,
        mark_price=mark_price,
        index_price=index_price,
        last_price=last_price,
        funding_rate=funding_rate_val,
        predicted_funding_rate=predicted_funding,
        funding_timestamp=funding_timestamp,
        next_funding_timestamp=next_funding_timestamp,
        open_interest=open_interest_val,
        open_interest_value=open_interest_value_val,
    )


# ---------------------------------------------------------------------------
# OHLCV
# ---------------------------------------------------------------------------


def normalize_okx_kline(raw: OKXCandleWS, symbol: str, venue: str = "okx") -> CanonicalOhlcvBar:
    """Convert OKXCandleWS to CanonicalOhlcvBar."""
    ts = datetime.fromtimestamp(int(raw.ts) / 1000.0, tz=UTC)
    quote_vol = d(raw.volCcyQuote) if raw.volCcyQuote is not None else None
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=d(raw.o),
        high=d(raw.h),
        low=d(raw.low),
        close=d(raw.c),
        volume=d(raw.vol),
        quote_volume=quote_vol,
        count=None,
        vwap=None,
    )


# ---------------------------------------------------------------------------
# Fee
# ---------------------------------------------------------------------------


def normalize_okx_fee_rate(
    raw: OKXFeeRate,
    fee_type: FeeType = FeeType.MAKER,
    venue: str = "okx",
) -> CanonicalFee:
    """Normalize an OKXFeeRate to CanonicalFee."""
    raw_rate = raw.taker if fee_type is FeeType.TAKER else raw.maker
    amount = Decimal(raw_rate) if raw_rate is not None else Decimal("0")
    return CanonicalFee(
        amount=amount,
        currency="",
        asset=None,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


def _okx_instrument_type(inst_type: str | None) -> str:
    mapping: dict[str, str] = {
        "SPOT": "SPOT_PAIR",
        "MARGIN": "SPOT_PAIR",
        "SWAP": "PERPETUAL",
        "FUTURES": "FUTURE",
        "OPTION": "OPTION",
    }
    return mapping.get((inst_type or "").upper(), "SPOT_PAIR")


def normalize_okx_market(
    raw: OKXInstrumentInfo,
    venue: str = "okx",
) -> CanonicalInstrument:
    """Normalize an OKXInstrument to CanonicalInstrument."""
    instrument_type = _okx_instrument_type(raw.instType)
    symbol = raw.instId
    instrument_key = f"{venue.upper()}:{instrument_type}:{symbol}"
    tick_size = Decimal(str(raw.tickSz)) if raw.tickSz is not None else None
    min_size = (
        Decimal(str(raw.minSz))
        if raw.minSz is not None
        else (Decimal(str(raw.lotSz)) if raw.lotSz is not None else None)
    )
    contract_size = Decimal(str(raw.ctVal)) if raw.ctVal is not None else None
    return CanonicalInstrument(
        instrument_key=instrument_key,
        venue=venue,
        symbol=symbol,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=min_size,
        contract_size=contract_size,
        base_asset=raw.baseCcy,
        quote_asset=raw.quoteCcy,
        settle_asset=raw.settleCcy,
    )


# ---------------------------------------------------------------------------
# Liquidation
# ---------------------------------------------------------------------------


def normalize_okx_liquidation(
    raw: OKXLiquidationOrder,
    venue: str = "okx",
) -> CanonicalLiquidation:
    """Convert OKXLiquidationOrder to CanonicalLiquidation."""
    raw_symbol: str = str(raw.instId or "UNKNOWN")
    inst_type_map: dict[str, str] = {
        "SWAP": "PERPETUAL",
        "FUTURES": "FUTURE",
        "MARGIN": "SPOT_PAIR",
        "OPTION": "OPTION",
    }
    inst_type: str = inst_type_map.get(str(raw.instType or "SWAP"), "PERPETUAL")
    instrument_key = f"{venue}:{inst_type}:{raw_symbol}"
    liq_side: str = str(raw.side or "buy").lower()
    price = Decimal(str(raw.liqPx or "0"))
    size = Decimal(str(raw.sz or "0"))
    ts_ms_raw = raw.ts or "0"
    ts = datetime.fromtimestamp(int(ts_ms_raw) / 1000.0, tz=UTC)
    return CanonicalLiquidation(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        side=liq_side,
        price=price,
        size=size,
        order_id=None,
        liquidated_account_value=None,
        liquidated_ntl_pos=None,
        liquidated_user=None,
    )


# ---------------------------------------------------------------------------
# Market State
# ---------------------------------------------------------------------------


def normalize_okx_market_state(
    state: str,
    inst_id: str,
    instrument_type: str = "PERPETUAL",
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "okx",
) -> CanonicalMarketStateEvent:
    """Normalize an OKX instrument state to CanonicalMarketStateEvent."""
    ik = f"{venue}:{instrument_type}:{inst_id}"
    return normalize_market_state(
        raw_state=state,
        venue=venue,
        instrument_key=ik,
        state_map=_OKX_STATE_MAP,
        previous_state=previous_state,
        reason=reason,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# WebSocket Connectivity
# ---------------------------------------------------------------------------


def normalize_okx_ws_subscription(
    event_str: str,
    channel: str = "",
    venue: str = "okx",
) -> CanonicalWebSocketLifecycle:
    """Normalize OKX WS subscription response."""
    if event_str == "subscribe":
        evt = WebSocketEvent.SUBSCRIBE
    elif event_str == "unsubscribe":
        evt = WebSocketEvent.UNSUBSCRIBE
    else:
        evt = WebSocketEvent.ERROR
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=evt,
        timestamp=datetime.now(UTC),
        channel=channel or None,
    )


# ---------------------------------------------------------------------------
# Rate Limits
# ---------------------------------------------------------------------------

from ...normalize_utils.rate_limits import extract_okx_rate_limit

__all__ = [
    "extract_okx_rate_limit",
    "normalize_okx_derivative_ticker",
    "normalize_okx_fee_rate",
    "normalize_okx_fill",
    "normalize_okx_kline",
    "normalize_okx_liquidation",
    "normalize_okx_market",
    "normalize_okx_market_state",
    "normalize_okx_order",
    "normalize_okx_orderbook",
    "normalize_okx_ticker",
    "normalize_okx_trade",
    "normalize_okx_ws_subscription",
]
