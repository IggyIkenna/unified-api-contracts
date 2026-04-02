"""Tests for emergency exit playbook schemas."""

from decimal import Decimal

from unified_api_contracts.internal import (
    ClientRiskTolerance,
    EmergencyExitPlaybook,
    EmergencyExitStep,
    EmergencyExitType,
)


class TestEmergencyExit:
    def test_exit_type_enum(self) -> None:
        assert EmergencyExitType.ATOMIC_UNWIND == "atomic_unwind"
        assert EmergencyExitType.DELEVERAGE_SEQUENCE == "deleverage_sequence"

    def test_basis_trade_playbook(self) -> None:
        playbook = EmergencyExitPlaybook(
            strategy_type="BASIS",
            exit_type=EmergencyExitType.ATOMIC_UNWIND,
            steps=[
                EmergencyExitStep(order=1, action="close_perp_leg", urgency="immediate"),
                EmergencyExitStep(order=1, action="close_spot_leg", urgency="immediate"),
            ],
            description="Unwind both legs simultaneously to avoid naked exposure",
        )
        assert len(playbook.steps) == 2
        assert playbook.steps[0].order == playbook.steps[1].order  # simultaneous

    def test_deleverage_sequence(self) -> None:
        playbook = EmergencyExitPlaybook(
            strategy_type="RECURSIVE_STAKED_BASIS",
            exit_type=EmergencyExitType.DELEVERAGE_SEQUENCE,
            steps=[
                EmergencyExitStep(order=1, action="repay_debt", instrument_filter="WETH_DEBT"),
                EmergencyExitStep(order=2, action="withdraw_collateral", instrument_filter="aweETH"),
                EmergencyExitStep(order=3, action="swap_to_stable", max_slippage_bps=200),
            ],
            description="Deleverage: repay → withdraw → swap",
        )
        assert playbook.steps[0].order < playbook.steps[1].order  # sequential

    def test_client_risk_tolerance(self) -> None:
        tolerance = ClientRiskTolerance(
            client_id="c1",
            max_drawdown_pct=Decimal("10.0"),
            auto_kill_switch_timeout_minutes=30,
        )
        assert tolerance.max_drawdown_pct == Decimal("10.0")

    def test_sports_stop_new_only(self) -> None:
        playbook = EmergencyExitPlaybook(
            strategy_type="SPORTS",
            exit_type=EmergencyExitType.STOP_NEW_ONLY,
            steps=[],
            description="Cannot close settled bets — just stop new ones",
        )
        assert len(playbook.steps) == 0
