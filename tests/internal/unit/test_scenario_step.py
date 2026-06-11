"""Tests for the scenario stepper contracts (architecture_v2.scenario_step).

Covers:
  - Import surface via both ``internal`` and ``internal.architecture_v2``.
  - StepInput / TriggerEvaluation / StepReport / ScenarioSession construction.
  - Deterministic round-trip JSON serialisation (model_dump → model_validate).
  - Decimal-not-float on every numeric money/threshold field.
  - StrEnum closure for TriggerKind + reuse of KillSwitchReason / RiskGateLayer.
  - extra="forbid" rejects unknown keys (schema-strict contract).

Plan: capability_wizard_and_manifest_2026_06_11.md Phase 3.5 [SPEC] P1.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal import (
    KillSwitchReason,
    RiskGateDecision,
    RiskGateLayer,
    StrategyArchetype,
)
from unified_api_contracts.internal.architecture_v2.scenario_step import (
    BenchmarkFillMode,
    RiskGateDecisionRecord,
    ScenarioConfigRef,
    ScenarioSession,
    StepFill,
    StepInput,
    StepReport,
    TriggerEvaluation,
    TriggerKind,
)


def test_import_surface_both_paths() -> None:
    """Both the internal facade and the submodule expose the new symbols."""
    from unified_api_contracts.internal import StepInput as FacadeStepInput
    from unified_api_contracts.internal import TriggerEvaluation as FacadeTrigger

    assert FacadeStepInput is StepInput
    assert FacadeTrigger is TriggerEvaluation


def test_trigger_kind_closure() -> None:
    assert {k.value for k in TriggerKind} == {
        "entry",
        "exit",
        "stop_loss",
        "rebalance",
        "kill_switch",
    }


def test_step_input_construction_and_filler_seed() -> None:
    si = StepInput(
        step_index=0,
        mark_price=Decimal("2500.50"),
        feature_values={"binance:mid_price_binance": 2500.0, "_:funding_rate_apy_bps": 1200.0},
        rng_seed=42,
        note="entry tick",
    )
    assert si.step_index == 0
    assert si.mark_price == Decimal("2500.50")
    assert isinstance(si.mark_price, Decimal)
    assert si.feature_values["_:funding_rate_apy_bps"] == 1200.0
    assert si.forced_kill_switch is None
    assert si.rng_seed == 42


def test_step_input_forced_kill_switch_reuses_enum() -> None:
    si = StepInput(step_index=3, forced_kill_switch=KillSwitchReason.DAILY_LOSS_BREACH)
    assert si.forced_kill_switch is KillSwitchReason.DAILY_LOSS_BREACH


def test_step_input_forbids_unknown_keys() -> None:
    with pytest.raises(ValidationError):
        StepInput(step_index=0, bogus_field=1)  # type: ignore[call-arg]


def test_trigger_evaluation_distance_semantics() -> None:
    """The 'arms at -5%, you are at -1.2%' line: distance is signed headroom."""
    te = TriggerEvaluation(
        kind=TriggerKind.KILL_SWITCH,
        label="daily_loss_breach",
        kill_switch_reason=KillSwitchReason.DAILY_LOSS_BREACH,
        threshold=Decimal("-5.0"),
        current_value=Decimal("-1.2"),
        distance_to_trigger=Decimal("3.8"),
        fired=False,
    )
    assert te.kill_switch_reason is KillSwitchReason.DAILY_LOSS_BREACH
    assert isinstance(te.threshold, Decimal)
    assert te.distance_to_trigger == Decimal("3.8")
    assert te.fired is False
    assert te.introspection_gap is False


def test_trigger_evaluation_introspection_gap() -> None:
    te = TriggerEvaluation(
        kind=TriggerKind.STOP_LOSS,
        label="per_position_stop_loss",
        threshold=None,
        current_value=None,
        distance_to_trigger=None,
        fired=False,
        introspection_gap=True,
    )
    assert te.introspection_gap is True
    assert te.threshold is None


def test_risk_gate_decision_record_reuses_layer_enum() -> None:
    rec = RiskGateDecisionRecord(
        layer=RiskGateLayer.STRATEGY_SELF_CHECK,
        decision=RiskGateDecision.REJECTED,
        reason="killed:DAILY_LOSS_BREACH",
    )
    assert rec.layer is RiskGateLayer.STRATEGY_SELF_CHECK
    assert rec.decision is RiskGateDecision.REJECTED


def test_step_fill_reuses_benchmark_fill_mode() -> None:
    fill = StepFill(
        instruction_id="instr-1",
        instrument="ETH-PERP",
        venue="hyperliquid",
        side="SELL",
        quantity=Decimal("1.5"),
        price=Decimal("2500.0"),
        fill_mode=BenchmarkFillMode.ARRIVAL_MID,
        notional_usd=Decimal("3750.0"),
    )
    assert fill.fill_mode is BenchmarkFillMode.ARRIVAL_MID
    assert isinstance(fill.quantity, Decimal)
    assert isinstance(fill.price, Decimal)


def _sample_step_report(idx: int, killed: bool = False) -> StepReport:
    return StepReport(
        step_index=idx,
        timestamp_utc=datetime(2026, 6, 11, 12, 0, idx, tzinfo=UTC),
        mark_price=Decimal("2500.0"),
        instructions_emitted=[{"instruction_id": f"i-{idx}", "action": "TRADE"}],
        fills=[
            StepFill(
                instruction_id=f"i-{idx}",
                instrument="ETH-PERP",
                quantity=Decimal("1.0"),
                price=Decimal("2500.0"),
                fill_mode=BenchmarkFillMode.ARRIVAL_MID,
            )
        ],
        position_deltas={"HYPERLIQUID:PERP:ETH": Decimal("-1.0")},
        position_state={"HYPERLIQUID:PERP:ETH": Decimal("-1.0")},
        pnl_delta_usd=Decimal("12.34"),
        cumulative_pnl_usd=Decimal("12.34"),
        trigger_evaluations=[
            TriggerEvaluation(
                kind=TriggerKind.ENTRY,
                label="net_carry_entry",
                threshold=Decimal("200"),
                current_value=Decimal("350"),
                distance_to_trigger=Decimal("150"),
                fired=True,
            )
        ],
        risk_gate_decisions=[
            RiskGateDecisionRecord(
                layer=RiskGateLayer.STRATEGY_SELF_CHECK,
                decision=RiskGateDecision.APPROVED,
            )
        ],
        killed=killed,
        kill_reason=KillSwitchReason.DAILY_LOSS_BREACH if killed else None,
        introspection_gaps=["per_position_stop_loss"],
    )


def test_step_report_roundtrip_deterministic() -> None:
    report = _sample_step_report(0)
    dumped = report.model_dump(mode="json")
    restored = StepReport.model_validate(dumped)
    assert restored.model_dump(mode="json") == dumped
    # Decimal fields survive as exact strings, not float.
    assert dumped["pnl_delta_usd"] == "12.34"
    assert dumped["position_deltas"]["HYPERLIQUID:PERP:ETH"] == "-1.0"


def test_scenario_session_roundtrip_and_kill_flag() -> None:
    config = ScenarioConfigRef(
        archetype_id=StrategyArchetype.CARRY_STAKED_BASIS,
        strategy_type="STAKED_BASIS",
        venues=["etherfi", "hyperliquid"],
        instruments=["ETH"],
        capital_usd=Decimal("500000"),
        risk_thresholds={
            "entry_bps": Decimal("200"),
            "exit_bps": Decimal("50"),
            "daily_loss_breach_pct": Decimal("-5.0"),
        },
    )
    session = ScenarioSession(
        session_id="sess-1",
        config=config,
        started_at_utc=datetime(2026, 6, 11, 12, 0, 0, tzinfo=UTC),
        steps=[_sample_step_report(0), _sample_step_report(1, killed=True)],
        final_pnl_usd=Decimal("-25000.0"),
        kill_switch_tripped=True,
    )
    dumped = session.model_dump(mode="json")
    restored = ScenarioSession.model_validate(dumped)
    assert restored.kill_switch_tripped is True
    assert restored.steps[1].kill_reason is KillSwitchReason.DAILY_LOSS_BREACH
    assert restored.config.capital_usd == Decimal("500000")
    assert dumped["final_pnl_usd"] == "-25000.0"


def test_scenario_config_ref_requires_positive_capital() -> None:
    with pytest.raises(ValidationError):
        ScenarioConfigRef(
            archetype_id=StrategyArchetype.ARBITRAGE_PRICE_DISPERSION,
            capital_usd=Decimal("0"),
        )
