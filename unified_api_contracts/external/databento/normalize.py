"""Databento normalizers — all normalize_databento_* functions.

Extracted from normalize_utils/ modules (trades, orderbooks, ohlcv,
instruments, options, errors).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.crosscutting.errors import (
    CanonicalError,
    ErrorAction,
)
from ...canonical.domain import (
    CanonicalInstrument,
    CanonicalOhlcvBar,
    CanonicalOptionsChainEntry,
    CanonicalOrderBook,
    CanonicalTrade,
    InstrumentType,
    OptionType,
)
from ...normalize_utils._helpers import _d, _databento_price
from ...normalize_utils.errors._utils import from_http_status
from .schemas import (
    DATABENTO_PRICE_DIVISOR,
    DatabentoBbo1m,
    DatabentoBbo1s,
    DatabentoCmbp1,
    DatabentoCMEOptionQuote,
    DatabentoDefinition,
    DatabentoMbo,
    DatabentoMbp1,
    DatabentoMbp10,
    DatabentoOhlcvBar,
    DatabentoOptionQuote,
    DatabentoSymbol,
    DatabentoTbbo,
    DatabentoTrade,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_price(px: int) -> Decimal:
    return Decimal(str(float(px) / float(DATABENTO_PRICE_DIVISOR)))


def _d_opt(value: float | int | str | Decimal | None) -> Decimal | None:
    """Convert any numeric value to Decimal; return None for None."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _instrument_class_to_type(ic: str | None) -> InstrumentType:
    if not ic:
        return InstrumentType.SPOT_PAIR
    m = {"F": InstrumentType.FUTURE, "O": InstrumentType.OPTION, "S": InstrumentType.SPOT_PAIR}
    return m.get(ic.upper(), InstrumentType.SPOT_PAIR)


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


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_databento_mbo_to_trade(
    raw: DatabentoMbo, venue: str = "databento", symbol: str = ""
) -> CanonicalTrade | None:
    """Convert DatabentoMbo to CanonicalTrade when action is T (trade)."""
    if raw.action != "T":
        return None
    ts = datetime.fromtimestamp(raw.ts_event / 1e9, tz=UTC)
    price = Decimal(raw.price) / Decimal(str(DATABENTO_PRICE_DIVISOR))
    side = "sell" if raw.side == "A" else "buy"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        trade_id=str(raw.order_id),
        timestamp=ts,
        price=price,
        quantity=Decimal(raw.size),
        side=side,
        buyer_maker=None,
        venue_trade_id=str(raw.order_id),
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


# ---------------------------------------------------------------------------
# Orderbook (6 variants)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# OHLCV
# ---------------------------------------------------------------------------


def normalize_databento_ohlcv_bar(
    raw: DatabentoOhlcvBar, venue: str = "databento", symbol: str = ""
) -> CanonicalOhlcvBar:
    """Convert DatabentoOhlcvBar to CanonicalOhlcvBar."""
    ts = datetime.fromtimestamp(raw.ts_event / 1e9, tz=UTC)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        open=_databento_price(raw.open),
        high=_databento_price(raw.high),
        low=_databento_price(raw.low),
        close=_databento_price(raw.close),
        volume=_d(raw.volume),
        quote_volume=None,
        count=None,
        vwap=None,
    )


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


def normalize_databento_definition(raw: DatabentoDefinition, venue: str = "databento") -> CanonicalInstrument:
    """Convert DatabentoDefinition to CanonicalInstrument."""
    ts = datetime.fromtimestamp(raw.ts_recv / 1e9, tz=UTC)
    itype = _instrument_class_to_type(raw.instrument_class)
    symbol = raw.raw_symbol
    instrument_key = f"{venue}:{itype.value}:{symbol}"
    expiry = datetime.fromtimestamp(raw.expiration / 1e9, tz=UTC) if raw.expiration else None
    strike = float(raw.strike_price) / 1e9 if raw.strike_price else None
    return CanonicalInstrument(
        instrument_key=instrument_key,
        venue=venue,
        instrument_type=itype,
        symbol=symbol,
        available_from_datetime=ts,
        timestamp=ts,
        exchange_raw_symbol=raw.raw_symbol,
        databento_symbol=raw.raw_symbol,
        strike=strike,
        underlying=raw.underlying,
        expiry=expiry,
        option_type=OptionType.CALL if raw.instrument_class == "O" else None,
    )


def normalize_databento_symbol(raw: DatabentoSymbol, venue: str = "databento") -> CanonicalInstrument:
    """Convert DatabentoSymbol to CanonicalInstrument (minimal)."""
    ts = datetime.now(UTC)
    itype = _instrument_class_to_type(raw.instrument_class)
    symbol = raw.raw_symbol
    instrument_key = f"{venue}:{itype.value}:{symbol}"
    return CanonicalInstrument(
        instrument_key=instrument_key,
        venue=venue,
        instrument_type=itype,
        symbol=symbol,
        available_from_datetime=ts,
        timestamp=ts,
        exchange_raw_symbol=raw.raw_symbol,
        databento_symbol=raw.raw_symbol,
    )


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------


def normalize_databento_option_quote(
    raw: DatabentoOptionQuote, venue: str = "databento", symbol: str = ""
) -> CanonicalOptionsChainEntry:
    """Convert DatabentoOptionQuote (OPRA) to CanonicalOptionsChainEntry."""
    ts = datetime.fromtimestamp(raw.ts_event / 1e9, tz=UTC)
    opt_type = "call" if (raw.option_type or "C").upper() == "C" else "put"
    exp = datetime.fromtimestamp(raw.expiration / 1e9, tz=UTC) if raw.expiration else None
    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        underlying=raw.underlying,
        strike=_db_price(raw.strike_price),
        option_type=opt_type,
        expiration=exp,
        bid_price=_db_price(raw.bid_px_00),
        ask_price=_db_price(raw.ask_px_00),
        bid_size=_d_opt(raw.bid_sz_00),
        ask_size=_d_opt(raw.ask_sz_00),
        implied_volatility=float(_db_price(raw.implied_volatility)) if raw.implied_volatility else None,
        delta=float(_db_price(raw.delta)) if raw.delta else None,
        gamma=float(_db_price(raw.gamma)) if raw.gamma else None,
        theta=float(_db_price(raw.theta)) if raw.theta else None,
        vega=float(_db_price(raw.vega)) if raw.vega else None,
        instrument_key=f"{venue}:OPTION:{symbol or raw.instrument_id}",
    )


def normalize_databento_cme_option_quote(
    raw: DatabentoCMEOptionQuote, venue: str = "databento", symbol: str = ""
) -> CanonicalOptionsChainEntry:
    """Convert DatabentoCMEOptionQuote (CME) to CanonicalOptionsChainEntry."""
    ts = datetime.fromtimestamp(raw.ts_event / 1e9, tz=UTC)
    opt_type = "call" if (raw.option_type or "C").upper() == "C" else "put"
    exp = datetime.fromtimestamp(raw.expiration / 1e9, tz=UTC) if raw.expiration else None
    return CanonicalOptionsChainEntry(
        timestamp=ts,
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        underlying=raw.underlying,
        strike=_db_price(raw.strike_price),
        option_type=opt_type,
        expiration=exp,
        bid_price=_db_price(raw.bid_px_00),
        ask_price=_db_price(raw.ask_px_00),
        bid_size=_d_opt(raw.bid_sz_00),
        ask_size=_d_opt(raw.ask_sz_00),
        implied_volatility=float(_db_price(raw.implied_volatility)) if raw.implied_volatility else None,
        delta=float(_db_price(raw.delta)) if raw.delta else None,
        gamma=float(_db_price(raw.gamma)) if raw.gamma else None,
        theta=float(_db_price(raw.theta)) if raw.theta else None,
        vega=float(_db_price(raw.vega)) if raw.vega else None,
        instrument_key=f"{venue}:OPTION:{symbol or raw.instrument_id}",
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


def normalize_databento_error(
    error_code: str | int,
    message: str = "",
    venue: str = "databento",
) -> CanonicalError:
    """Map a Databento HTTP status to a CanonicalError subclass.

    Databento uses standard HTTP semantics; no proprietary error codes.
    """
    code = str(error_code)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_databento_bbo1m_orderbook",
    "normalize_databento_bbo1s_orderbook",
    "normalize_databento_cmbp1_orderbook",
    "normalize_databento_cme_option_quote",
    "normalize_databento_definition",
    "normalize_databento_error",
    "normalize_databento_mbo_to_trade",
    "normalize_databento_mbp1_orderbook",
    "normalize_databento_mbp10_orderbook",
    "normalize_databento_ohlcv_bar",
    "normalize_databento_option_quote",
    "normalize_databento_symbol",
    "normalize_databento_tbbo_orderbook",
    "normalize_databento_trade",
]
