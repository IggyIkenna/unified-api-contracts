"""Unit tests for api_contracts.nautilus schemas and mocks."""

from api_contracts.nautilus import (
    mock_account,
    mock_cache,
    mock_clock,
    mock_fill,
    mock_instrument,
    mock_order,
    mock_position,
)


class TestNautilusSchemas:
    """Test Pydantic schemas."""

    def test_order_schema(self) -> None:
        """Order schema validates and serializes."""
        order = mock_order()
        assert order.order_id == "O-001"
        assert order.side == "BUY"
        assert order.status == "FILLED"
        assert order.instrument_id == "BTCUSDT-PERP.BINANCE"

    def test_position_schema(self) -> None:
        """Position schema validates and serializes."""
        pos = mock_position()
        assert pos.position_id == "P-001"
        assert pos.side == "LONG"
        assert pos.is_open is True

    def test_instrument_schema(self) -> None:
        """Instrument schema validates and serializes."""
        inst = mock_instrument()
        assert inst.instrument_id == "BTCUSDT-PERP.BINANCE"
        assert inst.venue == "BINANCE"
        assert inst.asset_class == "CRYPTO"

    def test_fill_schema(self) -> None:
        """Fill schema validates and serializes."""
        fill = mock_fill()
        assert fill.fill_id == "F-001"
        assert fill.order_id == "O-001"
        assert fill.side == "BUY"

    def test_account_schema(self) -> None:
        """Account schema validates and serializes."""
        acc = mock_account()
        assert acc.account_id == "SIM-001"
        assert acc.currency == "USDT"


class TestMockCache:
    """Test MockCache implementation."""

    def test_cache_get_order(self) -> None:
        """MockCache returns added orders."""
        cache = mock_cache()
        order = cache.get_order("O-001")
        assert order is not None
        assert order.order_id == "O-001"

    def test_cache_get_position(self) -> None:
        """MockCache returns added positions."""
        cache = mock_cache()
        pos = cache.get_position("P-001")
        assert pos is not None
        assert pos.position_id == "P-001"

    def test_cache_get_instrument(self) -> None:
        """MockCache returns added instruments."""
        cache = mock_cache()
        inst = cache.get_instrument("BTCUSDT-PERP.BINANCE")
        assert inst is not None
        assert inst.instrument_id == "BTCUSDT-PERP.BINANCE"

    def test_cache_get_fills(self) -> None:
        """MockCache returns fills, optionally filtered by order_id."""
        cache = mock_cache()
        fills = cache.get_fills()
        assert len(fills) >= 1
        fills_for_order = cache.get_fills(order_id="O-001")
        assert all(f.order_id == "O-001" for f in fills_for_order)

    def test_cache_get_account(self) -> None:
        """MockCache returns added accounts."""
        cache = mock_cache()
        acc = cache.get_account("SIM-001")
        assert acc is not None
        assert acc.account_id == "SIM-001"

    def test_cache_clear(self) -> None:
        """MockCache clear removes all data."""
        cache = mock_cache()
        cache.clear()
        assert cache.get_order("O-001") is None
        assert cache.get_position("P-001") is None


class TestMockClock:
    """Test MockClock implementation."""

    def test_clock_with_fixed_timestamp(self) -> None:
        """MockClock with fixed timestamp returns deterministic values."""
        ts_ns = 1700000000 * 1_000_000_000  # Fixed epoch
        clock = mock_clock(timestamp_ns=ts_ns)
        assert clock.timestamp_ns() == ts_ns
        assert clock.timestamp() == 1700000000.0

    def test_clock_utc_now(self) -> None:
        """MockClock utc_now returns datetime with UTC."""
        clock = mock_clock(timestamp_ns=1700000000 * 1_000_000_000)
        dt = clock.utc_now()
        assert dt.tzinfo is not None
        assert dt.year == 2023
