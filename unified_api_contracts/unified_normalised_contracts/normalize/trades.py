"""Trade normalizers: raw venue trade -> CanonicalTrade."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...unified_api_contracts_external.binance import BinanceTrade
from ...unified_api_contracts_external.bybit.schemas import BybitTrade
from ...unified_api_contracts_external.ccxt.schemas import CcxtTrade
from ...unified_api_contracts_external.coinbase.schemas import CoinbaseTrade
from ...unified_api_contracts_external.databento.schemas import DatabentoTrade
from ...unified_api_contracts_external.deribit.schemas import DeribitTrade
from ...unified_api_contracts_external.okx.schemas import OKXTrade
from ...unified_api_contracts_external.tardis.schemas import TardisTrade
from ...unified_api_contracts_external.upbit.schemas import UpbitTrade
from ..domain import CanonicalTrade


def normalize_binance_trade(raw: BinanceTrade, venue: str = "binance", symbol: str = "") -> CanonicalTrade:
    """Convert BinanceTrade to CanonicalTrade."""
    ts = datetime.fromtimestamp(raw.time / 1000.0, tz=UTC)
    side = "buy" if not raw.isBuyerMaker else "sell"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
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
        symbol=s or "UNKNOWN",
        trade_id=raw.trade_id or "",
        timestamp=ts,
        price=Decimal(str(raw.price or 0)),
        quantity=Decimal(str(raw.size or 0)),
        side=(raw.side or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=raw.trade_id,
    )


def normalize_coinbase_trade(raw: CoinbaseTrade, venue: str = "coinbase", symbol: str = "") -> CanonicalTrade:
    """Convert CoinbaseTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.time:
        try:
            ts = datetime.fromisoformat(raw.time.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            pass
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=str(raw.trade_id),
        timestamp=ts,
        price=raw.price,
        quantity=raw.size,
        side=(raw.side or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=str(raw.trade_id),
    )


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
            pass
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


def normalize_bybit_trade(raw: BybitTrade, venue: str = "bybit", symbol: str = "") -> CanonicalTrade:
    """Convert BybitTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.execTime is not None:
        ts = datetime.fromtimestamp(raw.execTime / 1000.0, tz=UTC)
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or (raw.symbol or "") or "UNKNOWN",
        trade_id=str(raw.execId) if raw.execId else "",
        timestamp=ts,
        price=Decimal(str(raw.execPrice or 0)),
        quantity=Decimal(str(raw.execQty or 0)),
        side=(raw.side or "buy").lower(),
        buyer_maker=raw.isMaker,
        venue_trade_id=str(raw.execId) if raw.execId else None,
    )


def normalize_deribit_trade(raw: DeribitTrade, venue: str = "deribit", symbol: str = "") -> CanonicalTrade:
    """Convert DeribitTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.timestamp is not None:
        ts = datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC)
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or (raw.instrument_name or "") or "UNKNOWN",
        trade_id=str(raw.trade_id) if raw.trade_id else "",
        timestamp=ts,
        price=Decimal(str(raw.price or 0)),
        quantity=Decimal(str(raw.amount or 0)),
        side=(raw.direction or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=str(raw.trade_id) if raw.trade_id else None,
    )


def normalize_upbit_trade(raw: UpbitTrade, venue: str = "upbit", symbol: str = "") -> CanonicalTrade:
    """Convert UpbitTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.timestamp is not None:
        ts = datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC)
    elif raw.sequential_id is not None:
        pass  # no ts from sequential_id
    side = "buy" if (raw.ask_bid or "").upper() == "BID" else "sell"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or (raw.market or "") or "UNKNOWN",
        trade_id=str(raw.sequential_id) if raw.sequential_id is not None else "",
        timestamp=ts,
        price=Decimal(str(raw.trade_price or 0)),
        quantity=Decimal(str(raw.trade_volume or 0)),
        side=side,
        buyer_maker=None,
        venue_trade_id=str(raw.sequential_id) if raw.sequential_id is not None else None,
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
    raise TypeError("Unsupported raw type for trade normalization")
