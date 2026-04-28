"""Unit tests for domain strategy_service schemas and execution contracts.

Covers the 0% modules: strategy_service.monitoring, strategy_service.domain_events,
strategy_service.order, and execution.ManualInstruction.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal


class TestMonitoringDataSchemas:
    """Tests for strategy_service.monitoring data dataclasses."""

    def test_position_data_basic(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.monitoring import PositionData

        pd = PositionData(
            positions={"BINANCE:SPOT:BTCUSDT": 0.5},
            position_type="simulated",
            trigger_source="rebalance",
        )
        assert pd.position_type == "simulated"
        assert pd.positions["BINANCE:SPOT:BTCUSDT"] == 0.5
        assert pd.metadata == {}

    def test_exposure_data_basic(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.monitoring import ExposureData

        ed = ExposureData(
            exposures={"BINANCE:SPOT:BTCUSDT": {"amount": 0.5, "value_share_class": 25000.0}},
            total_delta=25000.0,
        )
        assert ed.total_delta == 25000.0
        assert "BINANCE:SPOT:BTCUSDT" in ed.exposures

    def test_risk_data_defaults(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.monitoring import RiskData

        rd = RiskData(risk_level="low")
        assert rd.risk_level == "low"
        assert rd.warnings == []
        assert rd.breaches == []
        assert rd.health_factor is None
        assert rd.ltv_ratio is None

    def test_risk_data_with_values(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.monitoring import RiskData

        rd = RiskData(
            risk_level="high",
            warnings=["margin near limit"],
            breaches=["health_factor_below_min"],
            health_factor=1.05,
            ltv_ratio=0.8,
            margin_usage=0.95,
        )
        assert rd.risk_level == "high"
        assert len(rd.warnings) == 1
        assert rd.health_factor == 1.05

    def test_pnl_data_basic(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.monitoring import PnLData

        pnl = PnLData(
            total_equity_current=Decimal("110000"),
            total_equity_initial=Decimal("100000"),
            pnl_cumulative=Decimal("10000"),
            pnl_hourly=Decimal("500"),
            pnl_percentage=Decimal("10"),
            total_assets=Decimal("115000"),
            total_debts=Decimal("5000"),
        )
        assert pnl.pnl_cumulative == Decimal("10000")
        assert pnl.share_class == "USDT"
        assert pnl.asset_positions == {}

    def test_order_data_basic(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.monitoring import OrderData

        od = OrderData(
            order_id="ord-001",
            operation_id="op-001",
            operation_type="SPOT_TRADE",
            venue="binance",
            source_venue="binance",
            target_venue="binance",
            source_token="USDT",
            target_token="BTC",
            amount=Decimal("0.01"),
            strategy_id="strat-001",
        )
        assert od.order_id == "ord-001"
        assert od.strategy_intent == ""
        assert od.expected_deltas == {}

    def test_strategy_decision_data_defaults(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.monitoring import (
            StrategyDecisionData,
        )

        sdd = StrategyDecisionData(
            decision_type="HOLD",
            trigger_source="market_tick",
        )
        assert sdd.decision_type == "HOLD"
        assert sdd.orders_generated == 0
        assert sdd.risk_level == "low"
        assert sdd.constraints_violated == []


class TestDomainEvents:
    """Tests for strategy_service.domain_events envelope dataclasses."""

    def test_position_snapshot(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.domain_events import (
            PositionSnapshot,
        )
        from unified_api_contracts.internal.domain.strategy_service.monitoring import PositionData

        pd = PositionData(positions={}, position_type="simulated", trigger_source="test")
        snap = PositionSnapshot(
            timestamp="2025-01-01T00:00:00Z",
            real_utc_time="2025-01-01T00:00:01Z",
            correlation_id="corr-001",
            pid=1234,
            client_name="test-client",
            data=pd,
        )
        assert snap.correlation_id == "corr-001"
        assert snap.order == 0

    def test_exposure_snapshot(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.domain_events import (
            ExposureSnapshot,
        )
        from unified_api_contracts.internal.domain.strategy_service.monitoring import ExposureData

        ed = ExposureData(exposures={})
        snap = ExposureSnapshot(
            timestamp="2025-01-01T00:00:00Z",
            real_utc_time="2025-01-01T00:00:01Z",
            correlation_id="corr-002",
            pid=1234,
            client_name="test-client",
            data=ed,
        )
        assert snap.data.total_delta == 0.0

    def test_risk_assessment(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.domain_events import RiskAssessment
        from unified_api_contracts.internal.domain.strategy_service.monitoring import RiskData

        rd = RiskData(risk_level="medium")
        ra = RiskAssessment(
            timestamp="2025-01-01T00:00:00Z",
            real_utc_time="2025-01-01T00:00:01Z",
            correlation_id="corr-003",
            pid=1234,
            client_name="test-client",
            data=rd,
        )
        assert ra.data.risk_level == "medium"

    def test_pnl_calculation(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.domain_events import PnLCalculation
        from unified_api_contracts.internal.domain.strategy_service.monitoring import PnLData

        pnl = PnLData(
            total_equity_current=Decimal("100"),
            total_equity_initial=Decimal("100"),
            pnl_cumulative=Decimal("0"),
            pnl_hourly=Decimal("0"),
            pnl_percentage=Decimal("0"),
            total_assets=Decimal("100"),
            total_debts=Decimal("0"),
        )
        calc = PnLCalculation(
            timestamp="2025-01-01T00:00:00Z",
            real_utc_time="2025-01-01T00:00:01Z",
            correlation_id="corr-004",
            pid=1234,
            client_name="test-client",
            data=pnl,
        )
        assert calc.data.pnl_cumulative == Decimal("0")

    def test_order_event(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.domain_events import OrderEvent

        oe = OrderEvent(
            timestamp="2025-01-01T00:00:00Z",
            real_utc_time="2025-01-01T00:00:01Z",
            correlation_id="corr-005",
            pid=1234,
            client_name="test-client",
        )
        assert oe.data == []

    def test_strategy_decision(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.domain_events import (
            StrategyDecision,
        )
        from unified_api_contracts.internal.domain.strategy_service.monitoring import (
            StrategyDecisionData,
        )

        sdd = StrategyDecisionData(decision_type="ENTER", trigger_source="signal")
        sd = StrategyDecision(
            timestamp="2025-01-01T00:00:00Z",
            real_utc_time="2025-01-01T00:00:01Z",
            correlation_id="corr-006",
            pid=1234,
            client_name="test-client",
            data=sdd,
        )
        assert sd.data.decision_type == "ENTER"


class TestOrderSchema:
    """Tests for strategy_service.order.Order dataclass."""

    def test_order_basic(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.order import Order

        o = Order(
            operation_id="op-001",
            operation_type="SPOT_TRADE",
            venue="binance",
            source_token="USDT",
            target_token="BTC",
            amount=100.0,
            side="buy",
        )
        assert o.operation_id == "op-001"
        assert o.price is None
        assert o.strategy_id == ""

    def test_order_with_limit_price(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.order import Order

        o = Order(
            operation_id="op-002",
            operation_type="PERP_TRADE",
            venue="deribit",
            source_token="USDT",
            target_token="ETH",
            amount=1.0,
            side="sell",
            price=3000.0,
            strategy_id="strat-xyz",
        )
        assert o.price == 3000.0
        assert o.strategy_id == "strat-xyz"


class TestManualInstruction:
    """Tests for execution.ManualInstruction pydantic model."""

    def test_manual_instruction_basic(self) -> None:
        from unified_api_contracts.internal.execution import ManualInstruction

        ts = datetime.now(UTC)
        mi = ManualInstruction(
            instruction_id="instr-001",
            submitted_by="operator@example.com",
            venue="binance",
            account_id="acct-123",
            instrument_key="BINANCE:SPOT:BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("0.01"),
            submitted_at=ts,
        )
        assert mi.instruction_id == "instr-001"
        assert mi.price is None
        assert mi.reason == "manual_trade"

    def test_manual_instruction_with_limit(self) -> None:
        from unified_api_contracts.internal.execution import ManualInstruction

        ts = datetime.now(UTC)
        mi = ManualInstruction(
            instruction_id="instr-002",
            submitted_by="trader@example.com",
            venue="deribit",
            account_id="acct-456",
            instrument_key="DERIBIT:PERPETUAL:BTCUSDT",
            side="SELL",
            order_type="LIMIT",
            quantity=Decimal("0.5"),
            submitted_at=ts,
            price=Decimal("65000"),
            reason="risk_reduction",
        )
        assert mi.price == Decimal("65000")
        assert mi.reason == "risk_reduction"

    def test_manual_instruction_asset_group_json_key(self) -> None:
        from unified_api_contracts.internal.execution import ManualInstruction

        ts = datetime.now(UTC)
        data = {
            "instruction_id": "instr-003",
            "submitted_by": "trader@example.com",
            "venue": "binance",
            "account_id": "a1",
            "instrument_key": "BINANCE:SPOT:BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "0.1",
            "submitted_at": ts,
            "asset_group": "cefi",
        }
        mi = ManualInstruction.model_validate(data)
        assert mi.asset_group == "cefi"
        dumped = mi.model_dump(mode="json")
        assert dumped["asset_group"] == "cefi"
        assert "category" not in dumped
