"""Tests for VaR/stress/P&L attribution schemas added in p2a."""

from datetime import UTC, date, datetime
from decimal import Decimal

from unified_api_contracts.internal import (
    PnLAttributionRecord,
    RealTimePnLRecord,
    StressScenario,
    StressScenarioType,
    StressTestResult,
    VaRMethod,
    VaRRequest,
    VaRResult,
)


class TestVaRSchemas:
    def test_var_method_enum(self) -> None:
        assert VaRMethod.HISTORICAL == "historical"
        assert VaRMethod.MONTE_CARLO == "monte_carlo"

    def test_var_request_defaults(self) -> None:
        req = VaRRequest(portfolio_id="p1")
        assert req.confidence_level == Decimal("0.99")
        assert req.horizon_days == 1
        assert req.method == VaRMethod.HISTORICAL

    def test_var_result(self) -> None:
        result = VaRResult(
            portfolio_id="p1",
            computed_at=datetime.now(UTC),
            method=VaRMethod.HISTORICAL,
            confidence_level=Decimal("0.99"),
            horizon_days=1,
            var_amount=Decimal("10000"),
            cvar_amount=Decimal("15000"),
        )
        assert result.var_amount == Decimal("10000")
        assert result.cvar_amount > result.var_amount

    def test_stress_scenario_type(self) -> None:
        assert StressScenarioType.GFC_2008 == "GFC_2008"

    def test_stress_scenario(self) -> None:
        s = StressScenario(
            name="GFC",
            description="2008 crisis",
            scenario_type=StressScenarioType.GFC_2008,
            factor_shocks={"btc_price": Decimal("-0.40")},
        )
        assert s.factor_shocks["btc_price"] == Decimal("-0.40")

    def test_stress_test_result(self) -> None:
        s = StressScenario(name="test", description="test", factor_shocks={})
        result = StressTestResult(
            portfolio_id="p1",
            scenario=s,
            computed_at=datetime.now(UTC),
            pnl_impact=Decimal("-50000"),
        )
        assert result.pnl_impact < 0

    def test_pnl_attribution_record(self) -> None:
        record = PnLAttributionRecord(
            date=date.today(),
            strategy_id="MOM_MACD",
            total_pnl=Decimal("1234.56"),
            delta_pnl=Decimal("1000"),
            fees=Decimal("10"),
        )
        assert record.total_pnl == Decimal("1234.56")

    def test_realtime_pnl_record(self) -> None:
        record = RealTimePnLRecord(
            timestamp=datetime.now(UTC),
            strategy_id="MOM_MACD",
            unrealized_pnl=Decimal("500"),
            realized_pnl=Decimal("200"),
            total_pnl=Decimal("700"),
        )
        assert record.total_pnl == Decimal("700")
