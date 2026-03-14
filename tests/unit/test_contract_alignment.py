"""Contract alignment tests for unified-api-contracts (AC).

Verifies that canonical schemas exported from AC (CanonicalOrder, CanonicalFill,
CanonicalTrade, CanonicalTicker) can be imported, instantiated, and meet field
invariants (required fields, Decimal prices, timezone-aware datetimes).

These are Integration Layer 0 tests per the 5-layer integration testing strategy.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

# ---------------------------------------------------------------------------
# CanonicalOrder
# ---------------------------------------------------------------------------


class TestCanonicalOrder:
    """CanonicalOrder: required fields, Decimal prices, AwareDatetime timestamp."""

    def test_import_and_instantiate(self) -> None:
        from unified_api_contracts.canonical.execution import CanonicalOrder, OrderSide, OrderType

        order = CanonicalOrder(
            order_id="ord-001",
            timestamp=datetime.now(UTC),
            venue="binance",
            instrument_id="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
        )
        assert order.order_id == "ord-001"
        assert order.venue == "binance"
        assert order.instrument_id == "BTCUSDT"

    def test_required_fields_present(self) -> None:
        from unified_api_contracts.canonical.execution import CanonicalOrder

        fields = CanonicalOrder.model_fields
        # Core required fields must exist
        for required in ("order_id", "timestamp", "venue", "instrument_id", "side", "order_type", "quantity"):
            assert required in fields, f"CanonicalOrder missing required field: {required}"

    def test_quantity_is_decimal(self) -> None:
        from unified_api_contracts.canonical.execution import CanonicalOrder, OrderSide, OrderType

        order = CanonicalOrder(
            order_id="ord-002",
            timestamp=datetime.now(UTC),
            venue="binance",
            instrument_id="ETHUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1.5"),
            price=Decimal("3000.00"),
        )
        assert isinstance(order.quantity, Decimal)
        assert isinstance(order.price, Decimal)

    def test_timestamp_is_timezone_aware(self) -> None:
        from pydantic import ValidationError

        from unified_api_contracts.canonical.execution import CanonicalOrder, OrderSide, OrderType

        # Naive datetime must be rejected by AwareDatetime
        try:
            order = CanonicalOrder(
                order_id="ord-003",
                timestamp=datetime(2024, 1, 1),  # naive — no tzinfo
                venue="binance",
                instrument_id="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.1"),
            )
            # If pydantic coerces naive to aware, check it has tzinfo
            assert order.timestamp.tzinfo is not None
        except (ValidationError, ValueError):
            pass  # expected — naive datetime rejected

    def test_schema_version_constant(self) -> None:
        from unified_api_contracts.canonical.execution import (
            CANONICAL_ORDER_VERSION,
            CanonicalOrder,
            OrderSide,
            OrderType,
        )

        order = CanonicalOrder(
            order_id="ord-004",
            timestamp=datetime.now(UTC),
            venue="bybit",
            instrument_id="SOLUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("10"),
        )
        assert order.schema_version == CANONICAL_ORDER_VERSION
        assert CANONICAL_ORDER_VERSION == "1.0.0"


# ---------------------------------------------------------------------------
# CanonicalFill
# ---------------------------------------------------------------------------


class TestCanonicalFill:
    """CanonicalFill: required fields, Decimal price/quantity, AwareDatetime."""

    def test_import_and_instantiate(self) -> None:
        from unified_api_contracts.canonical.execution import CanonicalFill, OrderSide

        fill = CanonicalFill(
            fill_id="fill-001",
            order_id="ord-001",
            timestamp=datetime.now(UTC),
            venue="binance",
            instrument_id="BTCUSDT",
            side=OrderSide.BUY,
            price=Decimal("50000.00"),
            quantity=Decimal("0.01"),
        )
        assert fill.fill_id == "fill-001"
        assert fill.venue == "binance"

    def test_required_fields_present(self) -> None:
        from unified_api_contracts.canonical.execution import CanonicalFill

        fields = CanonicalFill.model_fields
        for required in ("fill_id", "order_id", "timestamp", "venue", "instrument_id", "side", "price", "quantity"):
            assert required in fields, f"CanonicalFill missing required field: {required}"

    def test_price_and_quantity_are_decimal(self) -> None:
        from unified_api_contracts.canonical.execution import CanonicalFill, OrderSide

        fill = CanonicalFill(
            fill_id="fill-002",
            order_id="ord-002",
            timestamp=datetime.now(UTC),
            venue="okx",
            instrument_id="ETHUSDT",
            side=OrderSide.SELL,
            price=Decimal("3200.50"),
            quantity=Decimal("2.0"),
            fee=Decimal("0.0032"),
            fee_rate=Decimal("0.001"),
        )
        assert isinstance(fill.price, Decimal)
        assert isinstance(fill.quantity, Decimal)
        # fee is Decimal when present
        assert isinstance(fill.fee, Decimal)

    def test_timestamp_is_timezone_aware(self) -> None:
        from unified_api_contracts.canonical.execution import CanonicalFill, OrderSide

        fill = CanonicalFill(
            fill_id="fill-003",
            order_id="ord-003",
            timestamp=datetime.now(UTC),
            venue="deribit",
            instrument_id="BTC-PERPETUAL",
            side=OrderSide.BUY,
            price=Decimal("50000"),
            quantity=Decimal("1"),
        )
        assert fill.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# CanonicalTrade (from domain module)
# ---------------------------------------------------------------------------


class TestCanonicalTrade:
    """CanonicalTrade: required fields, Decimal prices, AwareDatetime, symbol+venue."""

    def test_import_and_instantiate(self) -> None:
        from unified_api_contracts.canonical.domain import CanonicalTrade

        trade = CanonicalTrade(
            venue="binance",
            symbol="BTCUSDT",
            trade_id="trade-001",
            timestamp=datetime.now(UTC),
            price=Decimal("50000.00"),
            quantity=Decimal("0.01"),
            side="buy",
        )
        assert trade.venue == "binance"
        assert trade.symbol == "BTCUSDT"

    def test_required_fields_symbol_timestamp_venue(self) -> None:
        from unified_api_contracts.canonical.domain import CanonicalTrade

        fields = CanonicalTrade.model_fields
        for required in ("symbol", "timestamp", "venue", "price", "quantity"):
            assert required in fields, f"CanonicalTrade missing field: {required}"

    def test_price_fields_are_decimal(self) -> None:
        from unified_api_contracts.canonical.domain import CanonicalTrade

        trade = CanonicalTrade(
            venue="kraken",
            symbol="ETHUSD",
            trade_id="trade-002",
            timestamp=datetime.now(UTC),
            price=Decimal("3100.50"),
            quantity=Decimal("5"),
            side="sell",
        )
        assert isinstance(trade.price, Decimal), "price must be Decimal, not float"
        assert isinstance(trade.quantity, Decimal), "quantity must be Decimal, not float"

    def test_timestamp_is_aware(self) -> None:
        from unified_api_contracts.canonical.domain import CanonicalTrade

        trade = CanonicalTrade(
            venue="coinbase",
            symbol="BTCUSD",
            trade_id="trade-003",
            timestamp=datetime.now(UTC),
            price=Decimal("49000"),
            quantity=Decimal("0.5"),
            side="buy",
        )
        assert trade.timestamp.tzinfo is not None, "timestamp must be timezone-aware (AwareDatetime)"

    def test_venue_and_symbol_non_empty(self) -> None:
        """venue and symbol have min_length=1 constraint."""
        from pydantic import ValidationError

        from unified_api_contracts.canonical.domain import CanonicalTrade

        with pytest.raises((ValidationError, ValueError)):
            CanonicalTrade(
                venue="",  # empty venue — should fail
                symbol="BTCUSDT",
                trade_id="trade-004",
                timestamp=datetime.now(UTC),
                price=Decimal("50000"),
                quantity=Decimal("1"),
                side="buy",
            )


# ---------------------------------------------------------------------------
# CanonicalTicker
# ---------------------------------------------------------------------------


class TestCanonicalTicker:
    """CanonicalTicker: required fields, Decimal last_price, AwareDatetime, venue."""

    def test_import_and_instantiate(self) -> None:
        from unified_api_contracts.canonical.domain import CanonicalTicker

        ticker = CanonicalTicker(
            instrument_key="binance:SPOT_PAIR:BTCUSDT",
            venue="binance",
            timestamp=datetime.now(UTC),
            last_price=Decimal("50000.00"),
        )
        assert ticker.venue == "binance"
        assert ticker.last_price == Decimal("50000.00")

    def test_required_fields_present(self) -> None:
        from unified_api_contracts.canonical.domain import CanonicalTicker

        fields = CanonicalTicker.model_fields
        for required in ("instrument_key", "venue", "timestamp", "last_price"):
            assert required in fields, f"CanonicalTicker missing required field: {required}"

    def test_last_price_is_decimal(self) -> None:
        from unified_api_contracts.canonical.domain import CanonicalTicker

        ticker = CanonicalTicker(
            instrument_key="okx:SPOT_PAIR:ETHUSDT",
            venue="okx",
            timestamp=datetime.now(UTC),
            last_price=Decimal("3200.00"),
            bid_price=Decimal("3199.50"),
            ask_price=Decimal("3200.50"),
        )
        assert isinstance(ticker.last_price, Decimal)
        assert isinstance(ticker.bid_price, Decimal)
        assert isinstance(ticker.ask_price, Decimal)

    def test_timestamp_is_timezone_aware(self) -> None:
        from unified_api_contracts.canonical.domain import CanonicalTicker

        ticker = CanonicalTicker(
            instrument_key="bybit:PERPETUAL:BTCUSDT",
            venue="bybit",
            timestamp=datetime.now(UTC),
            last_price=Decimal("50100"),
        )
        assert ticker.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# Cross-schema: CanonicalOrder ↔ CanonicalFill field compatibility
# ---------------------------------------------------------------------------


class TestCanonicalOrderFillCompatibility:
    """Fill links back to Order via shared fields — verify compatibility."""

    def test_order_id_links_order_to_fill(self) -> None:
        from unified_api_contracts.canonical.execution import (
            CanonicalFill,
            CanonicalOrder,
            OrderSide,
            OrderType,
        )

        order = CanonicalOrder(
            order_id="ord-link-001",
            timestamp=datetime.now(UTC),
            venue="binance",
            instrument_id="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )
        fill = CanonicalFill(
            fill_id="fill-link-001",
            order_id=order.order_id,  # Links to order
            timestamp=datetime.now(UTC),
            venue=order.venue,
            instrument_id=order.instrument_id,
            side=order.side,
            price=Decimal("50000"),
            quantity=Decimal("0.1"),
        )
        assert fill.order_id == order.order_id
        assert fill.venue == order.venue
        assert fill.instrument_id == order.instrument_id

    def test_fill_price_gt_zero_constraint(self) -> None:
        """price must be >0 per Field(gt=0)."""
        from pydantic import ValidationError

        from unified_api_contracts.canonical.domain import CanonicalTrade

        with pytest.raises((ValidationError, ValueError)):
            CanonicalTrade(
                venue="binance",
                symbol="BTCUSDT",
                trade_id="t001",
                timestamp=datetime.now(UTC),
                price=Decimal("0"),  # violates gt=0
                quantity=Decimal("1"),
                side="buy",
            )
