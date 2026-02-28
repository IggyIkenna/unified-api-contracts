"""Normalize raw venue responses to canonical schemas.

One-hop conversion: BinanceTrade -> CanonicalTrade, etc.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from api_contracts.api_contracts_external.binance.schemas import BinanceTrade
from api_contracts.api_contracts_external.databento.schemas import DatabentoTrade
from api_contracts.api_contracts_external.tardis.schemas import TardisTrade
from api_contracts.internal.domain import CanonicalTrade


def normalize_binance_trade(raw: BinanceTrade, venue: str = "binance", symbol: str = "") -> CanonicalTrade:
    """Convert BinanceTrade to CanonicalTrade."""
    ts = datetime.fromtimestamp(raw.time / 1000.0, tz=UTC)
    side = "buy" if not raw.isBuyerMaker else "sell"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol,
        trade_id=str(raw.id),
        timestamp=ts,
        price=raw.price,
        quantity=raw.qty,
        side=side,
        buyer_maker=raw.isBuyerMaker,
        venue_trade_id=str(raw.id),
    )


def normalize_databento_trade(raw: DatabentoTrade, venue: str = "databento", symbol: str = "") -> CanonicalTrade:
    """Convert DatabentoTrade to CanonicalTrade."""
    ts = datetime.fromtimestamp(raw.ts_event / 1e9, tz=UTC)
    price = Decimal(raw.price) / Decimal("1e9")
    side = "sell" if raw.side == "A" else "buy"
    trade_id = str(raw.sequence) if raw.sequence is not None else f"{raw.ts_event}-{raw.instrument_id}"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        trade_id=trade_id,
        timestamp=ts,
        price=price,
        quantity=Decimal(raw.size),
        side=side,
        buyer_maker=None,
        venue_trade_id=trade_id,
    )


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
        symbol=s,
        trade_id=raw.trade_id or "",
        timestamp=ts,
        price=Decimal(str(raw.price or 0)),
        quantity=Decimal(str(raw.size or 0)),
        side=(raw.side or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=raw.trade_id,
    )


def normalize_trade(
    raw: BinanceTrade | DatabentoTrade | TardisTrade, venue: str = "", symbol: str = ""
) -> CanonicalTrade:
    """Dispatch to venue-specific normalizer."""
    if isinstance(raw, BinanceTrade):
        return normalize_binance_trade(raw, venue=venue or "binance", symbol=symbol)
    if isinstance(raw, DatabentoTrade):
        return normalize_databento_trade(raw, venue=venue or "databento", symbol=symbol)
    if isinstance(raw, TardisTrade):
        return normalize_tardis_trade(raw, venue=venue or None, symbol=symbol or None)
    raise TypeError(f"Unsupported raw type: {type(raw)}")
