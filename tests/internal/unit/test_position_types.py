"""Tests for PositionQuantityProtocol and aggregation helpers (Stream I1)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from unified_api_contracts.internal.position_types import (
    PositionQuantityProtocol,
    aggregate_notional,
    aggregate_positions,
)


def make_mock_position(qty: str, price: str) -> PositionQuantityProtocol:
    """Create a MagicMock satisfying PositionQuantityProtocol."""
    m = MagicMock(spec=PositionQuantityProtocol)
    m.quantity = Decimal(qty)
    m.price = Decimal(price)
    m.last_updated = datetime.now(UTC)
    return m


class TestAggregatePositions:
    def test_aggregate_positions_exact_decimal(self) -> None:
        """10 positions of 0.1 must sum to exactly 1.0 via Decimal arithmetic."""
        positions = [make_mock_position("0.1", "100") for _ in range(10)]
        total = aggregate_positions(positions)
        assert total == Decimal("1.0")

    def test_empty_positions_returns_zero(self) -> None:
        """Empty list must return Decimal(0)."""
        assert aggregate_positions([]) == Decimal(0)

    def test_aggregate_positions_exact_with_many_fills(self) -> None:
        """100 fills of 0.1 must sum to exactly 10.0, not 9.9999999..."""
        positions = [make_mock_position("0.1", "1.0") for _ in range(100)]
        total = aggregate_positions(positions)
        assert total == Decimal("10.0")

    def test_aggregate_positions_returns_decimal_type(self) -> None:
        """Return type must be Decimal even for a single position."""
        positions = [make_mock_position("1.5", "200.0")]
        result = aggregate_positions(positions)
        assert isinstance(result, Decimal)


class TestAggregateNotional:
    def test_aggregate_notional_no_float_cast(self) -> None:
        """Notional computation must use Decimal arithmetic throughout."""
        positions = [
            make_mock_position("1.234567890123456789", "50000.000000000001"),
            make_mock_position("0.765432109876543211", "50000.000000000001"),
        ]
        notional = aggregate_notional(positions)
        assert isinstance(notional, Decimal)

    def test_aggregate_notional_exact_arithmetic(self) -> None:
        """1 unit at price 100 + 2 units at price 50 == 200 exactly."""
        positions = [
            make_mock_position("1", "100"),
            make_mock_position("2", "50"),
        ]
        notional = aggregate_notional(positions)
        assert notional == Decimal("200")

    def test_aggregate_notional_empty_returns_zero(self) -> None:
        """Empty list must return Decimal(0)."""
        assert aggregate_notional([]) == Decimal(0)


class TestProtocolRuntimeCheckable:
    def test_protocol_runtime_checkable(self) -> None:
        """isinstance() check works with PositionQuantityProtocol (runtime_checkable)."""
        m = make_mock_position("1.0", "100.0")
        assert isinstance(m, PositionQuantityProtocol)

    def test_non_conforming_object_fails_isinstance(self) -> None:
        """A plain object without protocol attributes fails isinstance check."""

        class NotAPosition:
            pass

        assert not isinstance(NotAPosition(), PositionQuantityProtocol)
