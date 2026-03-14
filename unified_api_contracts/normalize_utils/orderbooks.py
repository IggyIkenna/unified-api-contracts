"""Orderbook normalizers: raw venue order book -> CanonicalOrderBook."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal

from ..canonical.domain import CanonicalOrderBook
from ..external.aster.schemas import AsterOrderBook
from ..external.binance.market_schemas import BinanceOrderBook
from ..external.bybit.schemas import BybitOrderBook
from ..external.ccxt.schemas import CcxtOrderBook
from ..external.coinbase.schemas import CoinbaseOrderBook
from ..external.databento.schemas import (
    DatabentoBbo1m,
    DatabentoBbo1s,
    DatabentoCmbp1,
    DatabentoMbp1,
    DatabentoMbp10,
    DatabentoTbbo,
)
from ..external.deribit.schemas import DeribitOrderBook
from ..external.hyperliquid.schemas import (
    HyperliquidL2Book,
    HyperliquidL2Level,
)
from ..external.kalshi.schemas import KalshiOrderBook
from ..external.okx.schemas import OKXOrderBook
from ..external.polymarket.schemas import PolymarketOrderBook
from ..external.smarkets.schemas import SmarketsOrderBook
from ..external.tardis.schemas import TardisOrderBook
from ..external.upbit.schemas import UpbitOrderBook
from ._helpers import _databento_price, _to_levels


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


def normalize_aster_orderbook(
    raw: AsterOrderBook,
    venue: str = "aster",
    symbol: str = "",
    timestamp_ms: int | None = None,
) -> CanonicalOrderBook:
    """Convert AsterOrderBook to CanonicalOrderBook."""
    ts = (
        datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC)
        if timestamp_ms is not None
        else (datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC) if raw.timestamp else datetime.now(UTC))
    )
    bids = _to_levels(raw.bids or [])
    asks = _to_levels(raw.asks or [])
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol or (raw.market_id or ""),
        timestamp=ts,
        bids=bids,
        asks=asks,
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


def normalize_databento_bbo1s_orderbook(
    raw: DatabentoBbo1s, venue: str = "databento", symbol: str = ""
) -> CanonicalOrderBook:
    """Convert DatabentoBbo1s (1s BBO) to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(raw.ts_recv / 1e9, tz=UTC)
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


def normalize_databento_bbo1m_orderbook(
    raw: DatabentoBbo1m, venue: str = "databento", symbol: str = ""
) -> CanonicalOrderBook:
    """Convert DatabentoBbo1m (1m BBO) to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(raw.ts_recv / 1e9, tz=UTC)
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


def normalize_databento_cmbp1_orderbook(
    raw: DatabentoCmbp1, venue: str = "databento", symbol: str = ""
) -> CanonicalOrderBook:
    """Convert DatabentoCmbp1 (consolidated MBP-1) to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(raw.ts_recv / 1e9, tz=UTC)
    bids = [(_databento_price(raw.bid_px_00), Decimal(raw.bid_sz_00))]
    asks = [(_databento_price(raw.ask_px_00), Decimal(raw.ask_sz_00))]
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        timestamp=ts,
        bids=bids,
        asks=asks,
    )


def _hl_levels(levels: list[HyperliquidL2Level]) -> list[tuple[Decimal, Decimal]]:
    """Convert a list of HyperliquidL2Level to [(price, size), ...]."""
    out: list[tuple[Decimal, Decimal]] = []
    for lvl in levels:
        if lvl.px is not None and lvl.sz is not None:
            out.append((Decimal(lvl.px), Decimal(lvl.sz)))
    return out


def normalize_hyperliquid_orderbook(
    raw: HyperliquidL2Book,
    venue: str = "hyperliquid",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert HyperliquidL2Book to CanonicalOrderBook.

    HyperliquidL2Book.levels is [[bid_levels], [ask_levels]].
    Timestamp is milliseconds since epoch.
    All Hyperliquid markets are USDC-settled perps; symbol = coin + "-USDC-PERP".
    """
    ts = datetime.fromtimestamp(raw.time / 1000.0, tz=UTC) if raw.time is not None else datetime.now(UTC)
    sym = symbol or (f"{raw.coin}-USDC-PERP" if raw.coin else "UNKNOWN")
    levels = raw.levels or []
    bids = _hl_levels(levels[0]) if len(levels) > 0 else []
    asks = _hl_levels(levels[1]) if len(levels) > 1 else []
    return CanonicalOrderBook(
        venue=venue,
        symbol=sym,
        timestamp=ts,
        bids=bids,
        asks=asks,
    )


def _mbp10_levels(
    raw: DatabentoMbp10,
) -> tuple[list[tuple[Decimal, Decimal]], list[tuple[Decimal, Decimal]]]:
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


def normalize_polymarket_orderbook(
    raw: PolymarketOrderBook,
    venue: str = "polymarket",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert PolymarketOrderBook to CanonicalOrderBook.

    Polymarket bids/asks: [[price, size], ...] as float lists.
    """
    sym = symbol or raw.market or raw.asset_id or ""
    bids: list[tuple[Decimal, Decimal]] = []
    asks: list[tuple[Decimal, Decimal]] = []
    for entry in raw.bids or []:
        if len(entry) >= 2:
            with contextlib.suppress(Exception):
                bids.append((Decimal(str(entry[0])), Decimal(str(entry[1]))))
    for entry in raw.asks or []:
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


def normalize_smarkets_orderbook(
    raw: SmarketsOrderBook,
    venue: str = "smarkets",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert SmarketsOrderBook to CanonicalOrderBook.

    Smarkets backs/lays are lists of SmarketsPriceLevel (back=bid, lay=ask).
    """
    sym = symbol or (f"{raw.market_id}:{raw.runner_id}" if raw.runner_id else raw.market_id or "")
    bids: list[tuple[Decimal, Decimal]] = []
    asks: list[tuple[Decimal, Decimal]] = []
    for level in raw.backs or []:
        if level.price is not None and level.size is not None:
            bids.append((Decimal(str(level.price)), Decimal(str(level.size))))
    for level in raw.lays or []:
        if level.price is not None and level.size is not None:
            asks.append((Decimal(str(level.price)), Decimal(str(level.size))))
    return CanonicalOrderBook(
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        bids=bids,
        asks=asks,
        sequence_number=None,
        levels=len(bids) or len(asks) or 1,
    )
