"""Orderbook normalizers: raw venue order book -> CanonicalOrderBook."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...unified_api_contracts_external.binance.market_schemas import BinanceOrderBook
from ...unified_api_contracts_external.bybit.schemas import BybitOrderBook
from ...unified_api_contracts_external.ccxt.schemas import CcxtOrderBook
from ...unified_api_contracts_external.coinbase.schemas import CoinbaseOrderBook
from ...unified_api_contracts_external.databento.schemas import DatabentoMbp1, DatabentoMbp10, DatabentoTbbo
from ...unified_api_contracts_external.deribit.schemas import DeribitOrderBook
from ...unified_api_contracts_external.okx.schemas import OKXOrderBook
from ...unified_api_contracts_external.tardis.schemas import TardisOrderBook
from ...unified_api_contracts_external.upbit.schemas import UpbitOrderBook
from ..domain import CanonicalOrderBook


def _to_levels(
    rows: list[list[str]] | list[list[float]],
) -> list[tuple[Decimal, Decimal]]:
    """Convert [[price, size], ...] to [(Decimal, Decimal), ...]."""
    out: list[tuple[Decimal, Decimal]] = []
    for row in rows:
        if len(row) >= 2:
            out.append((Decimal(str(row[0])), Decimal(str(row[1]))))
    return out


def normalize_binance_orderbook(
    raw: BinanceOrderBook,
    venue: str = "binance",
    symbol: str = "",
    timestamp_ms: int | None = None,
) -> CanonicalOrderBook:
    """Convert BinanceOrderBook to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC) if timestamp_ms is not None else datetime.now(UTC)
    bids = _to_levels([[p, q] for p, q in raw.bids])
    asks = _to_levels([[p, q] for p, q in raw.asks])
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol,
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.lastUpdateId,
    )


def normalize_coinbase_orderbook(
    raw: CoinbaseOrderBook,
    venue: str = "coinbase",
    symbol: str = "",
    timestamp_ms: int | None = None,
) -> CanonicalOrderBook:
    """Convert CoinbaseOrderBook to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC) if timestamp_ms is not None else datetime.now(UTC)
    bids = _to_levels(raw.bids)
    asks = _to_levels(raw.asks)
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol,
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.sequence,
    )


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


def normalize_bybit_orderbook(
    raw: BybitOrderBook,
    venue: str = "bybit",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert BybitOrderBook to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(raw.ts / 1000.0, tz=UTC) if raw.ts is not None else datetime.now(UTC)
    sym = symbol or (raw.s or "")
    bids = _to_levels(raw.b)
    asks = _to_levels(raw.a)
    return CanonicalOrderBook(
        venue=venue,
        symbol=sym,
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.u,
    )


def normalize_okx_orderbook(
    raw: OKXOrderBook,
    venue: str = "okx",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert OKXOrderBook to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(int(raw.ts) / 1000.0, tz=UTC) if raw.ts is not None else datetime.now(UTC)
    bids = _to_levels(raw.bids)
    asks = _to_levels(raw.asks)
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol,
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.seqId,
    )


def normalize_deribit_orderbook(
    raw: DeribitOrderBook,
    venue: str = "deribit",
    symbol: str = "",
    timestamp_ms: int | None = None,
) -> CanonicalOrderBook:
    """Convert DeribitOrderBook to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC) if timestamp_ms is not None else datetime.now(UTC)
    sym = symbol or (raw.instrument_name or "")
    bids = _to_levels([[float(p), float(q)] for p, q in raw.bids])
    asks = _to_levels([[float(p), float(q)] for p, q in raw.asks])
    return CanonicalOrderBook(
        venue=venue,
        symbol=sym,
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.change_id,
    )


def normalize_upbit_orderbook(
    raw: UpbitOrderBook,
    venue: str = "upbit",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert UpbitOrderBook to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(raw.timestamp, tz=UTC) if raw.timestamp is not None else datetime.now(UTC)
    sym = symbol or (raw.market or "")
    bids: list[tuple[Decimal, Decimal]] = []
    asks: list[tuple[Decimal, Decimal]] = []
    for unit in raw.orderbook_units:
        if unit.bid_price is not None and unit.bid_size is not None:
            bids.append((Decimal(str(unit.bid_price)), Decimal(str(unit.bid_size))))
        if unit.ask_price is not None and unit.ask_size is not None:
            asks.append((Decimal(str(unit.ask_price)), Decimal(str(unit.ask_size))))
    return CanonicalOrderBook(
        venue=venue,
        symbol=sym,
        timestamp=ts,
        bids=bids,
        asks=asks,
    )


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
    bids = _to_levels(raw.bids or [])
    asks = _to_levels(raw.asks or [])
    return CanonicalOrderBook(
        venue=v,
        symbol=s,
        timestamp=ts,
        bids=bids,
        asks=asks,
    )


def _databento_price(px: int) -> Decimal:
    """Databento fixed-point price (divide by 1e9)."""
    return Decimal(px) / Decimal("1e9")


def normalize_databento_mbp1_orderbook(
    raw: DatabentoMbp1,
    venue: str = "databento",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert DatabentoMbp1 (BBO) to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(raw.ts_event / 1e9, tz=UTC)
    bids = [(_databento_price(raw.bid_px_00), Decimal(raw.bid_sz_00))]
    asks = [(_databento_price(raw.ask_px_00), Decimal(raw.ask_sz_00))]
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        timestamp=ts,
        bids=bids,
        asks=asks,
    )


def normalize_databento_tbbo_orderbook(
    raw: DatabentoTbbo,
    venue: str = "databento",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert DatabentoTbbo (trade BBO) to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(raw.ts_event / 1e9, tz=UTC)
    bids = [(_databento_price(raw.bid_px_00), Decimal(raw.bid_sz_00))]
    asks = [(_databento_price(raw.ask_px_00), Decimal(raw.ask_sz_00))]
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.sequence,
    )


def _mbp10_levels(raw: DatabentoMbp10) -> tuple[list[tuple[Decimal, Decimal]], list[tuple[Decimal, Decimal]]]:
    """Extract bids/asks from DatabentoMbp10 levels 0-9."""
    bids: list[tuple[Decimal, Decimal]] = []
    asks: list[tuple[Decimal, Decimal]] = []
    for i in range(10):
        bid_px: int | None = getattr(raw, f"bid_px_{i:02d}", None)
        bid_sz: int | None = getattr(raw, f"bid_sz_{i:02d}", None)
        ask_px: int | None = getattr(raw, f"ask_px_{i:02d}", None)
        ask_sz: int | None = getattr(raw, f"ask_sz_{i:02d}", None)
        if isinstance(bid_px, int) and isinstance(bid_sz, int):
            bids.append((_databento_price(bid_px), Decimal(bid_sz)))
        if isinstance(ask_px, int) and isinstance(ask_sz, int):
            asks.append((_databento_price(ask_px), Decimal(ask_sz)))
    return bids, asks


def normalize_databento_mbp10_orderbook(
    raw: DatabentoMbp10,
    venue: str = "databento",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert DatabentoMbp10 (10-level book) to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(raw.ts_event / 1e9, tz=UTC)
    bids, asks = _mbp10_levels(raw)
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.sequence,
        levels=10,
    )
