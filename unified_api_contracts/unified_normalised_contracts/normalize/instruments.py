"""Instrument/reference normalizers: raw venue symbol/definition -> InstrumentWarehouseRow."""

from __future__ import annotations

from datetime import UTC, datetime

from ...unified_api_contracts_external.databento.schemas import DatabentoDefinition, DatabentoSymbol
from ..domain import InstrumentType, InstrumentWarehouseRow, OptionType


def _instrument_class_to_type(ic: str | None) -> InstrumentType:
    if not ic:
        return InstrumentType.SPOT_PAIR
    m = {"F": InstrumentType.FUTURE, "O": InstrumentType.OPTION, "S": InstrumentType.SPOT_PAIR}
    return m.get(ic.upper(), InstrumentType.SPOT_PAIR)


def normalize_databento_definition(raw: DatabentoDefinition, venue: str = "databento") -> InstrumentWarehouseRow:
    """Convert DatabentoDefinition to InstrumentWarehouseRow."""
    ts = datetime.fromtimestamp(raw.ts_recv / 1e9, tz=UTC)
    itype = _instrument_class_to_type(raw.instrument_class)
    symbol = raw.raw_symbol
    instrument_key = f"{venue}:{itype.value}:{symbol}"
    expiry = datetime.fromtimestamp(raw.expiration / 1e9, tz=UTC) if raw.expiration else None
    strike = float(raw.strike_price) / 1e9 if raw.strike_price else None
    return InstrumentWarehouseRow(
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


def normalize_databento_symbol(raw: DatabentoSymbol, venue: str = "databento") -> InstrumentWarehouseRow:
    """Convert DatabentoSymbol to InstrumentWarehouseRow (minimal)."""
    ts = datetime.now(UTC)
    itype = _instrument_class_to_type(raw.instrument_class)
    symbol = raw.raw_symbol
    instrument_key = f"{venue}:{itype.value}:{symbol}"
    return InstrumentWarehouseRow(
        instrument_key=instrument_key,
        venue=venue,
        instrument_type=itype,
        symbol=symbol,
        available_from_datetime=ts,
        timestamp=ts,
        exchange_raw_symbol=raw.raw_symbol,
        databento_symbol=raw.raw_symbol,
    )


__all__ = ["normalize_databento_definition", "normalize_databento_symbol"]
