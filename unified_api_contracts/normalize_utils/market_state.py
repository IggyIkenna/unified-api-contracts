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

# --- Functions without external counterparts (kept inline) ---
from __future__ import annotations

from datetime import UTC, datetime

from ..canonical.domain import CanonicalMarketStateEvent, MarketState
from ..external.betfair.normalize import normalize_betfair_market_state
from ..external.binance.normalize import normalize_binance_market_state
from ..external.bybit.normalize import normalize_bybit_market_state
from ..external.coinbase.normalize import normalize_coinbase_market_state
from ..external.deribit.normalize import normalize_deribit_market_state
from ..external.ibkr.normalize import normalize_ibkr_market_state
from ..external.kalshi.normalize import normalize_kalshi_market_state
from ..external.okx.normalize import normalize_okx_market_state


def _now() -> datetime:
    return datetime.now(UTC)


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


__all__ = [
    "_now",
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
