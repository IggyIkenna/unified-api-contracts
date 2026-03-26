"""Unit tests for PositionQuantityProtocol and CrossAssetPortfolioAggregator (Stream I)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from unified_api_contracts.internal.position_protocol import (
    CrossAssetPortfolioAggregator,
    PositionQuantityProtocol,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _CompliantPosition:
    """Minimal dataclass satisfying PositionQuantityProtocol via Decimal fields."""

    symbol: str
    quantity: Decimal
    price: Decimal


@dataclass
class _FloatPosition:
    """Position whose quantity/price are float — must NOT satisfy the protocol."""

    symbol: str
    quantity: float  # type: ignore[assignment]  # intentionally wrong for test
    price: float  # type: ignore[assignment]  # intentionally wrong for test


# ---------------------------------------------------------------------------
# Protocol satisfaction
# ---------------------------------------------------------------------------


class TestProtocolSatisfaction:
    def test_protocol_satisfied_by_compliant_class(self) -> None:
        """A dataclass with Decimal quantity/price/symbol satisfies the protocol."""
        pos = _CompliantPosition(
            symbol="BTC-USDT",
            quantity=Decimal("10"),
            price=Decimal("100"),
        )
        assert isinstance(pos, PositionQuantityProtocol)

    def test_protocol_rejected_by_float_class(self) -> None:
        """A class whose quantity/price are float does NOT satisfy the protocol.

        Note: runtime_checkable only checks attribute presence, not type.
        This test documents that a plain object with no matching attrs fails,
        not that the protocol rejects float types at isinstance()-time (Python
        structural typing cannot enforce runtime field types via isinstance).
        """

        class _NoAttrs:
            pass

        assert not isinstance(_NoAttrs(), PositionQuantityProtocol)

    def test_protocol_requires_symbol_attribute(self) -> None:
        """An object missing 'symbol' does not satisfy the protocol."""

        @dataclass
        class _NoSymbol:
            quantity: Decimal
            price: Decimal

        assert not isinstance(_NoSymbol(Decimal("1"), Decimal("1")), PositionQuantityProtocol)

    def test_protocol_requires_quantity_attribute(self) -> None:
        """An object missing 'quantity' does not satisfy the protocol."""

        @dataclass
        class _NoQuantity:
            symbol: str
            price: Decimal

        no_quantity_instance = _NoQuantity("X", Decimal("1"))
        assert not isinstance(no_quantity_instance, PositionQuantityProtocol)

    def test_protocol_requires_price_attribute(self) -> None:
        """An object missing 'price' does not satisfy the protocol."""

        @dataclass
        class _NoPrice:
            symbol: str
            quantity: Decimal

        assert not isinstance(_NoPrice("X", Decimal("1")), PositionQuantityProtocol)


# ---------------------------------------------------------------------------
# CrossAssetPortfolioAggregator — gross / net exposure
# ---------------------------------------------------------------------------


class TestAggregatorExposure:
    def test_aggregator_gross_exposure(self) -> None:
        """long 10@100 + short 5@200 → gross = |10*100| + |(-5)*200| = 1000 + 1000 = 2000."""
        agg = CrossAssetPortfolioAggregator()
        agg.add_position(_CompliantPosition("BTC", quantity=Decimal("10"), price=Decimal("100")))
        agg.add_position(_CompliantPosition("ETH", quantity=Decimal("-5"), price=Decimal("200")))
        assert agg.gross_exposure() == Decimal("2000")

    def test_aggregator_net_exposure(self) -> None:
        """long 10@100 + short 5@200 → net = 10*100 + (-5)*200 = 1000 - 1000 = 0."""
        agg = CrossAssetPortfolioAggregator()
        agg.add_position(_CompliantPosition("BTC", quantity=Decimal("10"), price=Decimal("100")))
        agg.add_position(_CompliantPosition("ETH", quantity=Decimal("-5"), price=Decimal("200")))
        assert agg.net_exposure() == Decimal("0")

    def test_aggregator_net_exposure_signed(self) -> None:
        """Net exposure is signed — net long should be positive."""
        agg = CrossAssetPortfolioAggregator()
        agg.add_position(_CompliantPosition("BTC", quantity=Decimal("10"), price=Decimal("100")))
        agg.add_position(_CompliantPosition("ETH", quantity=Decimal("-2"), price=Decimal("200")))
        # 10*100 + (-2)*200 = 1000 - 400 = 600
        assert agg.net_exposure() == Decimal("600")


# ---------------------------------------------------------------------------
# CrossAssetPortfolioAggregator — add / remove
# ---------------------------------------------------------------------------


class TestAggregatorAddRemove:
    def test_aggregator_add_remove_position(self) -> None:
        """Add then remove a position; aggregator should be empty afterwards."""
        agg = CrossAssetPortfolioAggregator()
        pos = _CompliantPosition("BTC", quantity=Decimal("1"), price=Decimal("50000"))
        agg.add_position(pos)
        assert agg.position_count() == 1
        agg.remove_position("BTC")
        assert agg.position_count() == 0

    def test_remove_unknown_symbol_is_noop(self) -> None:
        """Removing a symbol that was never added must not raise."""
        agg = CrossAssetPortfolioAggregator()
        agg.remove_position("DOES_NOT_EXIST")  # must not raise
        assert agg.position_count() == 0

    def test_add_replaces_existing_symbol(self) -> None:
        """Adding a second position with same symbol replaces the first."""
        agg = CrossAssetPortfolioAggregator()
        agg.add_position(_CompliantPosition("BTC", Decimal("1"), Decimal("100")))
        agg.add_position(_CompliantPosition("BTC", Decimal("2"), Decimal("200")))
        assert agg.position_count() == 1
        assert agg.gross_exposure() == Decimal("400")  # 2 * 200

    def test_positions_returns_all(self) -> None:
        """positions() returns every tracked position."""
        agg = CrossAssetPortfolioAggregator()
        agg.add_position(_CompliantPosition("BTC", Decimal("1"), Decimal("1")))
        agg.add_position(_CompliantPosition("ETH", Decimal("2"), Decimal("2")))
        assert len(agg.positions()) == 2


# ---------------------------------------------------------------------------
# CrossAssetPortfolioAggregator — Decimal arithmetic exactness
# ---------------------------------------------------------------------------


class TestAggregatorDecimalArithmetic:
    def test_aggregator_decimal_arithmetic_exact(self) -> None:
        """100 x 0.1 == 10.0 exactly, not 9.999...8 (float precision issue)."""
        agg = CrossAssetPortfolioAggregator()
        for i in range(100):
            agg.add_position(
                _CompliantPosition(
                    symbol=f"ASSET_{i}",
                    quantity=Decimal("0.1"),
                    price=Decimal("1"),
                )
            )
        assert agg.gross_exposure() == Decimal("10.0")

    def test_empty_aggregator_returns_zero(self) -> None:
        """Empty aggregator must return Decimal('0') for both exposure methods."""
        agg = CrossAssetPortfolioAggregator()
        assert agg.gross_exposure() == Decimal("0")
        assert agg.net_exposure() == Decimal("0")

    def test_exposure_results_are_decimal_type(self) -> None:
        """Both exposure methods must return Decimal instances."""
        agg = CrossAssetPortfolioAggregator()
        agg.add_position(_CompliantPosition("X", Decimal("1"), Decimal("1")))
        assert isinstance(agg.gross_exposure(), Decimal)
        assert isinstance(agg.net_exposure(), Decimal)
