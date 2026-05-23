"""Boundary tests: UIC domain schemas must not import from UAC.

Integration Layer 0 — UIC side.

Import direction rule:
    UIC → UAC (specifically: unified_api_contracts.canonical)
    is PERMITTED where UIC re-exports or wraps UAC canonical types.
    UAC → UIC is FORBIDDEN (circular dependency).

This file verifies:
1. UIC domain schemas (execution, strategy, risk) instantiate cleanly.
2. circuit_breaker (CircuitBreakerEventMessage) schema instantiates cleanly.
3. Compliance-adjacent schemas instantiate cleanly.
4. UIC does NOT import from UAC in violation of the boundary
   (UAC imports from UIC are forbidden; UIC may import UAC canonical layer).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_uic_python_files() -> list[Path]:
    import unified_api_contracts.internal

    src_root = Path(unified_api_contracts.internal.__file__).resolve().parent
    return [p for p in src_root.rglob("*.py") if "__pycache__" not in p.parts and ".venv" not in p.parts]


# ---------------------------------------------------------------------------
# Boundary: UAC must not import from UIC (run from UIC test suite)
# ---------------------------------------------------------------------------


class TestUACBoundary:
    """UAC source files must never import from unified_api_contracts.internal."""

    def test_uac_does_not_import_uic(self) -> None:
        """Walk all UAC source files and assert none import from UIC."""
        import unified_api_contracts

        uac_root = Path(unified_api_contracts.__file__).resolve().parent
        forbidden = "unified_api_contracts.internal"
        violations: list[str] = []
        for py_file in uac_root.rglob("*.py"):
            if "__pycache__" in py_file.parts or ".venv" in py_file.parts:
                continue
            if forbidden in py_file.read_text():
                violations.append(str(py_file.relative_to(uac_root)))
        assert violations == [], (
            "UAC files import from unified_api_contracts.internal (FORBIDDEN circular dep):\n" + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# UIC execution schemas
# ---------------------------------------------------------------------------


class TestUICExecutionSchemas:
    """UIC execution schemas instantiate cleanly."""

    def test_manual_instruction_basic(self) -> None:
        from unified_api_contracts.internal.execution import ManualInstruction

        mi = ManualInstruction(
            instruction_id="instr-uic-001",
            submitted_by="operator@example.com",
            venue="binance",
            account_id="acct-123",
            instrument_key="BINANCE:SPOT:BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("0.01"),
            submitted_at=datetime.now(UTC),
        )
        assert mi.instruction_id == "instr-uic-001"
        assert mi.venue == "binance"
        assert mi.price is None
        assert mi.reason == "manual_trade"

    def test_manual_instruction_with_limit_price(self) -> None:
        from unified_api_contracts.internal.execution import ManualInstruction

        mi = ManualInstruction(
            instruction_id="instr-uic-002",
            submitted_by="trader@example.com",
            venue="deribit",
            account_id="acct-456",
            instrument_key="DERIBIT:PERPETUAL:BTCUSDT",
            side="SELL",
            order_type="LIMIT",
            quantity=Decimal("0.5"),
            submitted_at=datetime.now(UTC),
            price=Decimal("65000"),
            reason="risk_reduction",
        )
        assert mi.price == Decimal("65000")
        assert mi.reason == "risk_reduction"

    def test_manual_instruction_quantity_is_decimal(self) -> None:
        from unified_api_contracts.internal.execution import ManualInstruction

        mi = ManualInstruction(
            instruction_id="instr-uic-003",
            submitted_by="system",
            venue="coinbase",
            account_id="acct-789",
            instrument_key="COINBASE:SPOT:ETHUSD",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("2.5"),
            submitted_at=datetime.now(UTC),
        )
        assert isinstance(mi.quantity, Decimal)


# ---------------------------------------------------------------------------
# UIC risk schemas
# ---------------------------------------------------------------------------


class TestUICRiskSchemas:
    """UIC risk schemas instantiate cleanly."""

    def test_risk_position_instantiation(self) -> None:
        from unified_api_contracts.internal.risk import RiskPosition

        pos = RiskPosition(
            client_id="client-abc",
            strategy_id="strat-001",
            venue="binance",
            instrument="BTCUSDT",
            quantity=Decimal("0.5"),
            avg_price=Decimal("50000"),
            position_value=Decimal("25000"),
            unrealized_pnl=Decimal("500"),
            realized_pnl=Decimal("0"),
            last_updated=datetime.now(UTC),
        )
        assert pos.venue == "binance"
        assert pos.client_id == "client-abc"

    def test_risk_metrics_instantiation(self) -> None:
        from unified_api_contracts.internal.risk import RiskMetrics, RiskStatus

        metrics = RiskMetrics(
            client_id="client-xyz",
            timestamp=datetime.now(UTC),
            leverage=Decimal("2.5"),
            margin_usage=Decimal("0.4"),
            concentration=Decimal("0.3"),
            drawdown=Decimal("0.05"),
            account_equity=Decimal("100000"),
            total_position_value=Decimal("250000"),
            cash_balance=Decimal("50000"),
            leverage_status=RiskStatus.OK,
            concentration_status=RiskStatus.WARNING,
            drawdown_status=RiskStatus.OK,
        )
        assert metrics.leverage == Decimal("2.5")
        assert isinstance(metrics.account_equity, Decimal)
        assert metrics.leverage_status == RiskStatus.OK

    def test_risk_alert_instantiation(self) -> None:
        from unified_api_contracts.internal.risk import AlertMessage, AlertType

        alert = AlertMessage(
            client_id="client-abc",
            alert_type=AlertType.EXPOSURE_BREACH,
            timestamp=datetime.now(UTC),
            metric="exposure",
            current_value=Decimal("1.5"),
            threshold=Decimal("1.0"),
        )
        assert alert.alert_type == AlertType.EXPOSURE_BREACH


# ---------------------------------------------------------------------------
# UIC circuit_breaker schemas (pubsub)
# ---------------------------------------------------------------------------


class TestUICCircuitBreakerSchema:
    """CircuitBreakerEventMessage instantiates cleanly."""

    def test_circuit_breaker_event_message(self) -> None:
        from unified_api_contracts.internal.pubsub import CircuitBreakerEventMessage

        msg = CircuitBreakerEventMessage(
            name="execution-circuit-breaker",
            previous_state="CLOSED",
            new_state="OPEN",
            timestamp="2024-01-15T10:30:00Z",
            reason="error_rate_exceeded",
            failure_count=5,
            service_name="execution-service",
        )
        assert msg.name == "execution-circuit-breaker"
        assert msg.new_state == "OPEN"
        assert msg.failure_count == 5

    def test_circuit_breaker_defaults(self) -> None:
        from unified_api_contracts.internal.pubsub import CircuitBreakerEventMessage

        msg = CircuitBreakerEventMessage(
            name="risk-circuit-breaker",
            previous_state="OPEN",
            new_state="HALF_OPEN",
            timestamp="2024-01-15T11:00:00Z",
        )
        assert msg.failure_count == 0
        assert msg.reason is None
        assert msg.service_name is None

    def test_health_alert_message(self) -> None:
        from unified_api_contracts.internal.pubsub import HealthAlertMessage

        alert = HealthAlertMessage(
            service_name="strategy-service",
            status="degraded",
            previous_status="healthy",
            timestamp="2024-01-15T10:30:00Z",
            components={"database": "healthy", "pubsub": "degraded"},
            uptime_seconds=3600.0,
        )
        assert alert.service_name == "strategy-service"
        assert alert.status == "degraded"
        assert alert.components["pubsub"] == "degraded"


# ---------------------------------------------------------------------------
# UIC strategy schemas
# ---------------------------------------------------------------------------


class TestUICStrategySchemas:
    """UIC strategy_service domain schemas instantiate cleanly."""

    def test_position_data_basic(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.monitoring import PositionData

        pd = PositionData(
            positions={"BINANCE:SPOT:BTCUSDT": 0.5},
            position_type="live",
            trigger_source="rebalance",
        )
        assert pd.position_type == "live"
        assert pd.metadata == {}

    def test_risk_data_defaults(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.monitoring import RiskData

        rd = RiskData(risk_level="low")
        assert rd.risk_level == "low"
        assert rd.warnings == []
        assert rd.breaches == []

    def test_strategy_decision_data(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.monitoring import (
            StrategyDecisionData,
        )

        sdd = StrategyDecisionData(
            decision_type="ENTER",
            trigger_source="signal",
        )
        assert sdd.decision_type == "ENTER"
        assert sdd.orders_generated == 0


# ---------------------------------------------------------------------------
# UIC __all__ exports resolve
# ---------------------------------------------------------------------------


class TestUICExportsResolve:
    """All UIC __all__ exports must be importable without errors."""

    def test_all_exports_importable(self) -> None:
        import unified_api_contracts.internal

        all_names: list[str] = getattr(unified_api_contracts.internal, "__all__", [])
        missing: list[str] = []
        for name in all_names:
            if not hasattr(unified_api_contracts.internal, name):
                missing.append(name)
        assert missing == [], f"UIC __all__ exports not importable: {missing}"

    def test_instrument_record_is_importable(self) -> None:
        from unified_api_contracts.internal import InstrumentRecord

        rec = InstrumentRecord(
            instrument_key="BINANCE:SPOT:BTCUSDT",
            venue="binance",
            instrument_type="SPOT_PAIR",
            symbol="BTC/USDT",
            raw_symbol="BTCUSDT",
        )
        assert rec.venue == "binance"
