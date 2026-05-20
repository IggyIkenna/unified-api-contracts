"""Trade normalizers: raw venue trade -> CanonicalTrade."""

# --- Functions without external counterparts (kept inline) ---
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ..canonical.domain import CanonicalTrade
from ..canonical.domain.sports.betting import BetExecution
from ..external.aster.normalize import normalize_aster_trade
from ..external.aster.schemas import AsterTrade
from ..external.binance.market_schemas import BinanceTrade
from ..external.binance.normalize import normalize_binance_trade
from ..external.bybit.normalize import normalize_bybit_trade
from ..external.ccxt.normalize import normalize_ccxt_trade
from ..external.coinbase.normalize import normalize_coinbase_trade
from ..external.databento.normalize import (
    normalize_databento_mbo_to_trade,
    normalize_databento_trade,
)
from ..external.databento.schemas import (
    DatabentoTrade,
)
from ..external.deribit.normalize import normalize_deribit_trade
from ..external.ibkr.normalize import normalize_ibkr_trade
from ..external.kalshi.normalize import (
    normalize_kalshi_trade,
    normalize_kalshi_ws_trade,
)
from ..external.manifold.normalize import normalize_manifold_trade
from ..external.okx.normalize import normalize_okx_trade
from ..external.polymarket.normalize import normalize_polymarket_trade
from ..external.tardis.normalize import normalize_tardis_trade
from ..external.tardis.schemas import TardisTrade
from ..external.upbit.normalize import normalize_upbit_trade
from ..external.versifi.normalize import normalize_versifi_child_order_trade


def normalize_sports_trade(
    raw: BetExecution,
    venue: str = "sports",
    symbol: str = "",
) -> CanonicalTrade:
    """Convert BetExecution (sports canonical) to CanonicalTrade.

    BetExecution represents a filled bet at a bookmaker.
    filled_odds as price, filled_stake as quantity.
    """
    sym = symbol or raw.order_id
    ts = datetime.now(UTC)
    price = raw.filled_odds if raw.filled_odds is not None else Decimal("0")
    qty = raw.filled_stake if raw.filled_stake is not None else Decimal("0")
    return CanonicalTrade(
        venue=venue or raw.bookmaker_ref or "sports",
        symbol=sym if sym else "UNKNOWN",
        trade_id=raw.execution_id,
        timestamp=ts,
        price=price if price > Decimal("0") else Decimal("1"),
        quantity=qty if qty > Decimal("0") else Decimal("0.000001"),
        side="buy",  # sports bets are always "backing"
        buyer_maker=None,
        venue_trade_id=raw.execution_id,
        is_liquidation=None,
    )


def normalize_trade(
    raw: object,
    venue: str = "",
    symbol: str = "",
) -> CanonicalTrade:
    """Dispatch to venue-specific normalizer. Raises TypeError for unsupported raw types."""
    if isinstance(raw, BinanceTrade):
        return normalize_binance_trade(raw, venue=venue or "binance", symbol=symbol)
    if isinstance(raw, DatabentoTrade):
        return normalize_databento_trade(raw, venue=venue or "databento", symbol=symbol)
    if isinstance(raw, TardisTrade):
        return normalize_tardis_trade(raw, venue=venue or None, symbol=symbol or None)
    if isinstance(raw, AsterTrade):
        return normalize_aster_trade(raw, venue=venue or "aster", symbol=symbol)
    raise TypeError("Unsupported raw type for trade normalization")


__all__ = [
    "normalize_aster_trade",
    "normalize_binance_trade",
    "normalize_bybit_trade",
    "normalize_ccxt_trade",
    "normalize_coinbase_trade",
    "normalize_databento_mbo_to_trade",
    "normalize_databento_trade",
    "normalize_deribit_trade",
    "normalize_ibkr_trade",
    "normalize_kalshi_trade",
    "normalize_kalshi_ws_trade",
    "normalize_manifold_trade",
    "normalize_okx_trade",
    "normalize_polymarket_trade",
    "normalize_sports_trade",
    "normalize_tardis_trade",
    "normalize_trade",
    "normalize_upbit_trade",
    "normalize_versifi_child_order_trade",
]
