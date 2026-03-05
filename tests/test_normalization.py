"""Normalization tests: per-venue and property-based.

Per-venue: BinanceTrade -> CanonicalTrade, DatabentoTrade -> CanonicalTrade, etc.
Property-based: all venues produce same core CanonicalTrade fields.
"""

from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from unified_api_contracts.unified_api_contracts_external.binance.market_schemas import BinanceTrade
from unified_api_contracts.unified_api_contracts_external.databento.schemas import DatabentoTrade
from unified_api_contracts.unified_api_contracts_external.tardis.schemas import TardisTrade
from unified_api_contracts.unified_normalised_contracts import CanonicalTrade
from unified_api_contracts.unified_normalised_contracts.normalize import (
    normalize_binance_trade,
    normalize_databento_trade,
    normalize_tardis_trade,
    normalize_trade,
)

# Venues with trade normalization
ALL_TRADE_VENUES = ("binance", "databento", "tardis")


# --- Per-venue tests ---


def test_binance_to_canonical() -> None:
    """BinanceTrade normalizes to CanonicalTrade."""
    raw = BinanceTrade(
        id=12345,
        price=Decimal("50000.5"),
        qty=Decimal("0.1"),
        quoteQty=Decimal("5000.05"),
        time=1700000000000,
        isBuyerMaker=True,
        isBestMatch=True,
    )
    canonical = normalize_binance_trade(raw, symbol="BTCUSDT")
    assert isinstance(canonical, CanonicalTrade)
    assert canonical.venue == "binance"
    assert canonical.symbol == "BTCUSDT"
    assert canonical.trade_id == "12345"
    assert canonical.price == Decimal("50000.5")
    assert canonical.quantity == Decimal("0.1")
    assert canonical.side == "sell"
    assert canonical.buyer_maker is True


def test_databento_to_canonical() -> None:
    """DatabentoTrade normalizes to CanonicalTrade."""
    raw = DatabentoTrade(
        ts_event=1700000000000000000,
        rtype=1,
        publisher_id=1,
        instrument_id=123,
        action="T",
        side="B",
        price=50000500000000,
        size=100,
        sequence=999,
    )
    canonical = normalize_databento_trade(raw, symbol="ES.c.0")
    assert isinstance(canonical, CanonicalTrade)
    assert canonical.venue == "databento"
    assert canonical.symbol == "ES.c.0"
    assert canonical.trade_id == "999"
    assert canonical.price == Decimal("50000.5")
    assert canonical.quantity == Decimal("100")
    assert canonical.side == "buy"


def test_tardis_to_canonical() -> None:
    """TardisTrade normalizes to CanonicalTrade."""
    raw = TardisTrade(
        timestamp="1700000000000000",
        exchange="BINANCE",
        symbol="BTCUSDT",
        price=50000.5,
        size=0.1,
        side="buy",
        trade_id="abc-123",
        info=None,
    )
    canonical = normalize_tardis_trade(raw)
    assert isinstance(canonical, CanonicalTrade)
    assert canonical.venue == "BINANCE"
    assert canonical.symbol == "BTCUSDT"
    assert canonical.trade_id == "abc-123"
    assert canonical.price == Decimal("50000.5")
    assert canonical.quantity == Decimal("0.1")
    assert canonical.side == "buy"


def test_normalize_trade_dispatch() -> None:
    """normalize_trade dispatches to correct venue normalizer."""
    binance_raw = BinanceTrade(
        id=1,
        price=Decimal("1"),
        qty=Decimal("1"),
        quoteQty=Decimal("1"),
        time=1700000000000,
        isBuyerMaker=False,
        isBestMatch=True,
    )
    c1 = normalize_trade(binance_raw, venue="binance", symbol="X")
    assert c1.venue == "binance"

    databento_raw = DatabentoTrade(
        ts_event=1700000000000000000,
        rtype=1,
        publisher_id=1,
        instrument_id=1,
        action="T",
        side="B",
        price=1_000_000_000,
        size=1,
        sequence=1,
    )
    c2 = normalize_trade(databento_raw, venue="databento", symbol="Y")
    assert c2.venue == "databento"


def test_normalize_trade_unsupported_type() -> None:
    """normalize_trade raises TypeError for unsupported raw type."""
    with pytest.raises(TypeError, match="Unsupported raw type"):
        normalize_trade("not a trade", venue="x", symbol="y")  # type: ignore[arg-type]


# --- Property-based tests ---


def _core_fields(c: CanonicalTrade) -> tuple[str, str, str, Decimal, Decimal, str]:
    """Extract core fields for property check."""
    return (c.venue, c.symbol, c.trade_id, c.price, c.quantity, c.side)


@given(
    trade_id=st.integers(min_value=1, max_value=10**12),
    price=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000000"), places=8),
    qty=st.decimals(min_value=Decimal("0.0001"), max_value=Decimal("10000"), places=8),
    time_ms=st.integers(min_value=1600000000000, max_value=2000000000000),
)
@settings(max_examples=50)
def test_normalization_preserves_core_fields_binance(
    trade_id: int,
    price: Decimal,
    qty: Decimal,
    time_ms: int,
) -> None:
    """All Binance normalizations produce same core CanonicalTrade fields."""
    raw = BinanceTrade(
        id=trade_id,
        price=price,
        qty=qty,
        quoteQty=price * qty,
        time=time_ms,
        isBuyerMaker=False,
        isBestMatch=True,
    )
    canonical = normalize_binance_trade(raw, symbol="BTCUSDT")
    assert hasattr(canonical, "venue")
    assert hasattr(canonical, "symbol")
    assert hasattr(canonical, "trade_id")
    assert hasattr(canonical, "price")
    assert hasattr(canonical, "quantity")
    assert hasattr(canonical, "side")
    assert canonical.symbol == "BTCUSDT"
    assert canonical.price == price
    assert canonical.quantity == qty


@given(
    ts_event=st.integers(min_value=1600000000000000000, max_value=2000000000000000000),
    price_int=st.integers(min_value=1, max_value=10**15),
    size=st.integers(min_value=1, max_value=10**9),
    sequence=st.integers(min_value=1, max_value=10**12),
)
@settings(max_examples=50)
def test_normalization_preserves_core_fields_databento(
    ts_event: int,
    price_int: int,
    size: int,
    sequence: int,
) -> None:
    """All Databento normalizations produce same core CanonicalTrade fields."""
    raw = DatabentoTrade(
        ts_event=ts_event,
        rtype=1,
        publisher_id=1,
        instrument_id=1,
        action="T",
        side="B",
        price=price_int,
        size=size,
        sequence=sequence,
    )
    canonical = normalize_databento_trade(raw, symbol="ES")
    assert hasattr(canonical, "venue")
    assert hasattr(canonical, "symbol")
    assert hasattr(canonical, "trade_id")
    assert hasattr(canonical, "price")
    assert hasattr(canonical, "quantity")
    assert hasattr(canonical, "side")
    assert canonical.quantity == Decimal(size)
