from datetime import UTC, datetime

from unified_api_contracts.internal import ScopedKillSwitchSpec, ScopedKillSwitchState


class TestScopedKillSwitch:
    def test_company_wide_scope(self) -> None:
        scope = ScopedKillSwitchSpec(entity_type="company")
        assert scope.entity_id is None
        assert scope.strategy_type is None

    def test_client_strategy_venue_scope(self) -> None:
        scope = ScopedKillSwitchSpec(
            entity_type="client",
            entity_id="C1",
            strategy_type="BASIS",
            venue="binance",
        )
        assert scope.entity_id == "C1"
        assert scope.strategy_type == "BASIS"

    def test_scoped_state(self) -> None:
        scope = ScopedKillSwitchSpec(entity_type="client", entity_id="C1")
        state = ScopedKillSwitchState(
            scope=scope,
            is_active=True,
            activated_at=datetime.now(UTC),
            activated_by="risk-monitor",
            reason="Drawdown exceeded 10%",
        )
        assert state.is_active
        assert state.scope.entity_id == "C1"
