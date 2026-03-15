"""Market state normalizers — map venue-specific trading state strings to CanonicalMarketStateEvent.

Covers all major CeFi venues (Binance, Bybit, OKX, Deribit, Hyperliquid, Coinbase, IBKR)
and sports/prediction venues that expose market status (Kalshi, Betfair, Polymarket).

Per-venue mapping convention:
    NORMAL / TRADING   → MarketState.NORMAL
    HALT / HALTED      → MarketState.HALTED
    AUCTION / CALL     → MarketState.AUCTION
    PRE_TRADING        → MarketState.PRE_MARKET
    POST_TRADING       → MarketState.POST_MARKET
    CLOSED / SETTLED   → MarketState.CLOSED
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..canonical.domain import CanonicalMarketStateEvent, MarketState

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Generic helper — used by all venues
# ---------------------------------------------------------------------------


def normalize_market_state(
    raw_state: str,
    venue: str,
    instrument_key: str,
    state_map: dict[str, MarketState],
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    scheduled_reopen: datetime | None = None,
) -> CanonicalMarketStateEvent:
    """Convert a raw venue state string to CanonicalMarketStateEvent.

    Args:
        raw_state:       Venue-specific state string (e.g. "TRADING", "HALT").
        venue:           Venue tag.
        instrument_key:  VENUE:TYPE:SYMBOL.
        state_map:       Mapping of raw_state strings to MarketState enum values.
        previous_state:  Previous state if known.
        reason:          Halt reason or additional context.
        timestamp:       Event timestamp; defaults to now.
        scheduled_reopen: When trading is expected to resume (for halts/auctions).
    """
    normalized = state_map.get(raw_state.upper().strip(), MarketState.NORMAL)
    return CanonicalMarketStateEvent(
        timestamp=timestamp or _now(),
        venue=venue,
        instrument_key=instrument_key,
        state=normalized,
        previous_state=previous_state,
        reason=reason,
        scheduled_reopen=scheduled_reopen,
    )


# ---------------------------------------------------------------------------
# Binance — Spot/Futures trading status
# ---------------------------------------------------------------------------

_BINANCE_STATE_MAP: dict[str, MarketState] = {
    "TRADING": MarketState.NORMAL,
    "PRE_TRADING": MarketState.PRE_MARKET,
    "POST_TRADING": MarketState.POST_MARKET,
    "END_OF_DAY": MarketState.CLOSED,
    "HALT": MarketState.HALTED,
    "AUCTION_MATCH": MarketState.AUCTION,
    "BREAK": MarketState.HALTED,
    "SETTLING": MarketState.CLOSED,
}


def normalize_binance_market_state(
    status: str,
    symbol: str,
    instrument_type: str = "SPOT",
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "binance",
) -> CanonicalMarketStateEvent:
    """Normalize a Binance symbol status string to CanonicalMarketStateEvent.

    Binance REST /api/v3/exchangeInfo returns status field per symbol:
    TRADING | PRE_TRADING | POST_TRADING | END_OF_DAY | HALT | AUCTION_MATCH | BREAK | SETTLING.

    Args:
        status:          Symbol status from exchangeInfo.
        symbol:          Binance symbol (e.g. BTCUSDT).
        instrument_type: SPOT | PERPETUAL | FUTURE (default: SPOT).
        previous_state:  Previous canonical state.
        reason:          Additional context.
        timestamp:       Event time (defaults to now).
        venue:           Venue tag.
    """
    ik = f"{venue}:{instrument_type}:{symbol}"
    return normalize_market_state(
        raw_state=status,
        venue=venue,
        instrument_key=ik,
        state_map=_BINANCE_STATE_MAP,
        previous_state=previous_state,
        reason=reason,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# Bybit — Linear/Spot market status
# ---------------------------------------------------------------------------

_BYBIT_STATE_MAP: dict[str, MarketState] = {
    "TRADING": MarketState.NORMAL,
    "SETTLING": MarketState.CLOSED,
    "DELIVERING": MarketState.CLOSED,
    "CLOSED": MarketState.CLOSED,
    "PRE-LAUNCH": MarketState.PRE_MARKET,
    "AUCTION": MarketState.AUCTION,
    "HALT": MarketState.HALTED,
    "SUSPENDED": MarketState.HALTED,
}


def normalize_bybit_market_state(
    status: str,
    symbol: str,
    instrument_type: str = "PERPETUAL",
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "bybit",
) -> CanonicalMarketStateEvent:
    """Normalize a Bybit symbol status to CanonicalMarketStateEvent.

    Bybit GET /v5/market/instruments-info returns status per instrument.

    Args:
        status:          Instrument status string.
        symbol:          Bybit symbol (e.g. BTCUSDT).
        instrument_type: PERPETUAL | FUTURE | SPOT | OPTION.
        previous_state:  Previous state.
        reason:          Context.
        timestamp:       Event time.
        venue:           Venue tag.
    """
    ik = f"{venue}:{instrument_type}:{symbol}"
    return normalize_market_state(
        raw_state=status,
        venue=venue,
        instrument_key=ik,
        state_map=_BYBIT_STATE_MAP,
        previous_state=previous_state,
        reason=reason,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# OKX — Instrument state
# ---------------------------------------------------------------------------

_OKX_STATE_MAP: dict[str, MarketState] = {
    "LIVE": MarketState.NORMAL,
    "SUSPEND": MarketState.HALTED,
    "PREOPEN": MarketState.PRE_MARKET,
    "TEST": MarketState.PRE_MARKET,
    "EXPIRED": MarketState.CLOSED,
    "SETTLEMENT": MarketState.CLOSED,
}


def normalize_okx_market_state(
    state: str,
    inst_id: str,
    instrument_type: str = "PERPETUAL",
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "okx",
) -> CanonicalMarketStateEvent:
    """Normalize an OKX instrument state to CanonicalMarketStateEvent.

    OKX GET /api/v5/public/instruments returns state per instrument.
    state values: live | suspend | preopen | test | expired | settlement.

    Args:
        state:           OKX state string.
        inst_id:         OKX instrument ID (e.g. BTC-USDT-SWAP).
        instrument_type: PERPETUAL | FUTURE | OPTION | SPOT.
        previous_state:  Previous state.
        reason:          Context.
        timestamp:       Event time.
        venue:           Venue tag.
    """
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
# Deribit — Instrument state
# ---------------------------------------------------------------------------

_DERIBIT_STATE_MAP: dict[str, MarketState] = {
    "OPEN": MarketState.NORMAL,
    "CLOSED": MarketState.CLOSED,
    "TERMINATED": MarketState.CLOSED,
    "SETTLEMENT": MarketState.CLOSED,
    "CREATED": MarketState.PRE_MARKET,
}


def normalize_deribit_market_state(
    state: str,
    instrument_name: str,
    instrument_type: str = "PERPETUAL",
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "deribit",
) -> CanonicalMarketStateEvent:
    """Normalize a Deribit instrument state to CanonicalMarketStateEvent.

    Deribit instrument states: open | closed | terminated | settlement | created.

    Args:
        state:           Deribit state string.
        instrument_name: Deribit instrument name (e.g. BTC-PERPETUAL).
        instrument_type: PERPETUAL | FUTURE | OPTION | SPOT.
        previous_state:  Previous state.
        reason:          Context.
        timestamp:       Event time.
        venue:           Venue tag.
    """
    ik = f"{venue}:{instrument_type}:{instrument_name}"
    return normalize_market_state(
        raw_state=state,
        venue=venue,
        instrument_key=ik,
        state_map=_DERIBIT_STATE_MAP,
        previous_state=previous_state,
        reason=reason,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# Coinbase — Trading status
# ---------------------------------------------------------------------------

_COINBASE_STATE_MAP: dict[str, MarketState] = {
    "ONLINE": MarketState.NORMAL,
    "OFFLINE": MarketState.HALTED,
    "INTERNAL": MarketState.HALTED,
    "DELISTED": MarketState.CLOSED,
}


def normalize_coinbase_market_state(
    trading_mode: str,
    product_id: str,
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "coinbase",
) -> CanonicalMarketStateEvent:
    """Normalize a Coinbase product trading_mode to CanonicalMarketStateEvent.

    Coinbase Advanced Trade API product trading_mode: ONLINE | OFFLINE | INTERNAL | DELISTED.

    Args:
        trading_mode: Product trading mode string.
        product_id:   Product ID (e.g. BTC-USD).
        previous_state: Previous state.
        reason:       Context.
        timestamp:    Event time.
        venue:        Venue tag.
    """
    ik = f"{venue}:SPOT:{product_id}"
    return normalize_market_state(
        raw_state=trading_mode,
        venue=venue,
        instrument_key=ik,
        state_map=_COINBASE_STATE_MAP,
        previous_state=previous_state,
        reason=reason,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# IBKR — Market trading phase
# ---------------------------------------------------------------------------

_IBKR_STATE_MAP: dict[str, MarketState] = {
    "PREOPEN": MarketState.PRE_MARKET,
    "OPEN": MarketState.NORMAL,
    "CLOSED": MarketState.CLOSED,
    "AFTERHOURS": MarketState.POST_MARKET,
    "AUCTION": MarketState.AUCTION,
    "HALTED": MarketState.HALTED,
    "SUSPENDED": MarketState.HALTED,
}


def normalize_ibkr_market_state(
    trading_phase: str,
    symbol: str,
    sec_type: str = "STK",
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "ibkr",
) -> CanonicalMarketStateEvent:
    """Normalize an IBKR trading phase string to CanonicalMarketStateEvent.

    IBKR trading phase values: PREOPEN | OPEN | CLOSED | AFTERHOURS | AUCTION | HALTED | SUSPENDED.

    Args:
        trading_phase: IBKR market phase string.
        symbol:        Underlying symbol (e.g. AAPL).
        sec_type:      IBKR security type (STK, FUT, OPT, CASH).
        previous_state: Previous state.
        reason:        Context.
        timestamp:     Event time.
        venue:         Venue tag.
    """
    type_map = {"STK": "SPOT", "FUT": "FUTURE", "OPT": "OPTION", "CASH": "SPOT"}
    inst_type = type_map.get(sec_type.upper(), "SPOT")
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
# Kalshi — Prediction market status
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
# Betfair — Sports market status
# ---------------------------------------------------------------------------

_BETFAIR_STATUS_MAP: dict[str, MarketState] = {
    "INACTIVE": MarketState.PRE_MARKET,
    "OPEN": MarketState.NORMAL,
    "SUSPENDED": MarketState.HALTED,
    "CLOSED": MarketState.CLOSED,
}


def normalize_betfair_market_state(
    status: str,
    market_id: str,
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "betfair",
) -> CanonicalMarketStateEvent:
    """Normalize a Betfair market status to CanonicalMarketStateEvent.

    Betfair market status: INACTIVE | OPEN | SUSPENDED | CLOSED.

    Args:
        status:    Market status.
        market_id: Betfair market ID (e.g. 1.234567).
        previous_state: Previous state.
        reason:    Suspension or closure reason.
        timestamp: Event time.
        venue:     Venue tag.
    """
    ik = f"{venue}:MARKET:{market_id}"
    return normalize_market_state(
        raw_state=status,
        venue=venue,
        instrument_key=ik,
        state_map=_BETFAIR_STATUS_MAP,
        previous_state=previous_state,
        reason=reason,
        timestamp=timestamp,
    )


__all__ = [
    "normalize_betfair_market_state",
    "normalize_binance_market_state",
    "normalize_bybit_market_state",
    "normalize_coinbase_market_state",
    "normalize_deribit_market_state",
    "normalize_ibkr_market_state",
    "normalize_kalshi_market_state",
    "normalize_market_state",
    "normalize_okx_market_state",
]
