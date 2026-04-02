"""Tests for MarginHealthSnapshot schema."""

from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.internal import MarginHealthSnapshot


class TestMarginHealth:
    def test_defi_health_factor(self) -> None:
        snap = MarginHealthSnapshot(
            strategy_id="RECURSIVE_STAKED_BASIS",
            timestamp=datetime.now(UTC),
            venue="aave_v3",
            venue_type="defi",
            position_type="A_TOKEN",
            health_factor=Decimal("1.35"),
            ltv_ratio=Decimal("0.74"),
            collateral_usd=Decimal("100000"),
            debt_usd=Decimal("74000"),
            distance_to_liquidation_pct=Decimal("15.2"),
        )
        assert snap.health_factor == Decimal("1.35")
        assert snap.venue_type == "defi"

    def test_cefi_margin_usage(self) -> None:
        snap = MarginHealthSnapshot(
            strategy_id="MOM_MACD",
            timestamp=datetime.now(UTC),
            venue="binance",
            venue_type="cefi",
            position_type="PERPETUAL",
            margin_usage_pct=Decimal("65.5"),
            collateral_usd=Decimal("50000"),
            liquidation_price=Decimal("55000"),
        )
        assert snap.margin_usage_pct == Decimal("65.5")
        assert snap.venue_type == "cefi"

    def test_defaults(self) -> None:
        snap = MarginHealthSnapshot(
            strategy_id="MOM",
            timestamp=datetime.now(UTC),
            venue="deribit",
            venue_type="cefi",
            position_type="OPTIONS",
        )
        assert snap.health_factor is None
        assert snap.collateral_usd == Decimal("0")
        assert snap.debt_usd == Decimal("0")
