"""Unit tests for `canonical.crosscutting.scenario_overlay` + per-asset_group registry.

Phase 1 of `simulation_scenarios_topology_price_shocks_2026_05_09.md`
(slot 7 Day-2 2026-05-12). Covers:

- Closed-set enum membership + count (`ScenarioCategory` / `ScenarioOverlayLayer` / `OutcomeCategory`).
- `scenario_id` regex validator.
- `ScenarioOverlay` Pydantic round-trip (frozen + extra-forbid + serialization).
- `ScenarioMutationSpec` discriminated-union dispatch (11 mutation types).
- `ScenarioOutcomeAssertion` cross-references to risk / breaker / kill-switch / alert SSOTs resolve.
- Registry completeness — 10 scenarios shipped, 2 cefi + 6 defi + 2 cross_asset.
- `register_scenario` idempotency + duplicate-detection.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from unified_api_contracts import (
    SCENARIO_REGISTRY,
    AlertCode,
    BookSpoof,
    BreakerAction,
    CircuitBreakerId,
    DropRows,
    EventDrop,
    EventDuplicate,
    GasSurge,
    KillSwitchId,
    LatencyInject,
    ManifestPhantom,
    OracleDeviate,
    OutcomeCategory,
    PriceShift,
    RejectFills,
    ScenarioApplicabilityFilter,
    ScenarioCategory,
    ScenarioOutcomeAssertion,
    ScenarioOverlay,
    ScenarioOverlayLayer,
    StaleHold,
    register_scenario,
)
from unified_api_contracts.risk import RiskRuleConsequence

# ---------------------------------------------------------------------------
# Closed-set enums
# ---------------------------------------------------------------------------


def test_scenario_category_count_seven() -> None:
    """7 categories per Phase 1.A spec."""
    assert len(list(ScenarioCategory)) == 7


def test_scenario_overlay_layer_count_six() -> None:
    """6 pipeline-tap layers per Phase 1.A spec."""
    assert len(list(ScenarioOverlayLayer)) == 6


def test_outcome_category_count_nine() -> None:
    """9 outcome assertion categories per Phase 1.C spec."""
    assert len(list(OutcomeCategory)) == 9


@pytest.mark.parametrize(
    "category",
    [
        ScenarioCategory.TOPOLOGY_GAP,
        ScenarioCategory.STALENESS,
        ScenarioCategory.PRICE_SHOCK,
        ScenarioCategory.VENUE_OUTAGE,
        ScenarioCategory.DATA_CORRUPTION,
        ScenarioCategory.CROSS_ASSET,
        ScenarioCategory.OPERATIONAL,
    ],
)
def test_scenario_category_member_resolution(category: ScenarioCategory) -> None:
    assert isinstance(category.value, str)
    assert category.value == category.name


# ---------------------------------------------------------------------------
# scenario_id regex validation
# ---------------------------------------------------------------------------


def _minimal_overlay(scenario_id: str) -> ScenarioOverlay:
    return ScenarioOverlay(
        scenario_id=scenario_id,
        category=ScenarioCategory.TOPOLOGY_GAP,
        layer=ScenarioOverlayLayer.RAW_TICK,
        asset_groups=frozenset({"cefi"}),
        mutation_spec=DropRows(drop_rate=Decimal("0.5"), duration_seconds=60),
        expected_outcomes=(
            ScenarioOutcomeAssertion(
                archetype="test_archetype",
                category=OutcomeCategory.STRATEGY_HALTED,
                expected_within_seconds=30,
            ),
        ),
    )


def test_scenario_id_snake_case_accepted() -> None:
    assert _minimal_overlay("test_scenario_1_xyz").scenario_id == "test_scenario_1_xyz"


@pytest.mark.parametrize(
    "bad_id",
    [
        "1_starts_with_digit",
        "UPPERCASE",
        "has-dashes",
        "has spaces",
        "",
        "x",  # 1 char fails the `[a-z][a-z0-9_]+` pattern (needs >= 2 chars)
        "has.dots",
    ],
)
def test_scenario_id_rejects_non_snake_case(bad_id: str) -> None:
    with pytest.raises(ValueError, match="scenario_id"):
        _minimal_overlay(bad_id)


def test_empty_expected_outcomes_rejected() -> None:
    with pytest.raises(ValueError, match="at least 1 ScenarioOutcomeAssertion"):
        ScenarioOverlay(
            scenario_id="empty_outcomes_test",
            category=ScenarioCategory.TOPOLOGY_GAP,
            layer=ScenarioOverlayLayer.RAW_TICK,
            asset_groups=frozenset({"cefi"}),
            mutation_spec=DropRows(drop_rate=Decimal("0.5"), duration_seconds=60),
            expected_outcomes=(),
        )


# ---------------------------------------------------------------------------
# Mutation discriminated-union — instantiate every member
# ---------------------------------------------------------------------------


def test_price_shift_discriminator() -> None:
    m = PriceShift(target_value_bps=Decimal("100"), duration_seconds=600)
    assert m.mutation_type == "PriceShift"
    assert m.recovery_curve == "step"


def test_stale_hold_discriminator() -> None:
    m = StaleHold(stale_duration_seconds=300)
    assert m.mutation_type == "StaleHold"


def test_latency_inject_discriminator() -> None:
    m = LatencyInject(added_latency_seconds=Decimal("60"), duration_seconds=600)
    assert m.mutation_type == "LatencyInject"


def test_book_spoof_discriminator() -> None:
    m = BookSpoof(book_depth_scale=Decimal("0.3"), duration_seconds=300)
    assert m.mutation_type == "BookSpoof"


def test_reject_fills_discriminator() -> None:
    m = RejectFills(reject_rate=Decimal("1.0"), duration_seconds=300, reject_reason="VenueHalted")
    assert m.mutation_type == "RejectFills"


def test_oracle_deviate_discriminator() -> None:
    m = OracleDeviate(deviation_sigma=Decimal("30"), deviation_duration_heartbeats=1, oracle_id="pyth_solana_usdc")
    assert m.mutation_type == "OracleDeviate"


def test_gas_surge_discriminator() -> None:
    m = GasSurge(
        surge_multiplier=Decimal("50"),
        baseline_gwei=Decimal("30"),
        surge_duration_seconds=600,
    )
    assert m.mutation_type == "GasSurge"


def test_drop_rows_discriminator() -> None:
    m = DropRows(drop_rate=Decimal("0.5"), duration_seconds=60)
    assert m.mutation_type == "DropRows"


def test_event_drop_discriminator() -> None:
    m = EventDrop(event_types=frozenset({"chain_slot_progressed"}), duration_seconds=60)
    assert m.mutation_type == "EventDrop"


def test_event_duplicate_discriminator() -> None:
    m = EventDuplicate(event_type="venue_halted", payload_template="{}")
    assert m.mutation_type == "EventDuplicate"


def test_manifest_phantom_discriminator() -> None:
    m = ManifestPhantom(target_capture_status="captured", target_value=Decimal("0.99"))
    assert m.mutation_type == "ManifestPhantom"


# ---------------------------------------------------------------------------
# Pydantic invariants — frozen + extra-forbid
# ---------------------------------------------------------------------------


def test_overlay_is_frozen() -> None:
    from pydantic import ValidationError

    o = _minimal_overlay("frozen_test")
    with pytest.raises(ValidationError):
        o.scenario_id = "different"  # type: ignore[misc]


def test_overlay_rejects_extra_fields() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="extra"):
        ScenarioOverlay(  # type: ignore[call-arg]
            scenario_id="extra_test",
            category=ScenarioCategory.TOPOLOGY_GAP,
            layer=ScenarioOverlayLayer.RAW_TICK,
            asset_groups=frozenset({"cefi"}),
            mutation_spec=DropRows(drop_rate=Decimal("0.5"), duration_seconds=60),
            expected_outcomes=(
                ScenarioOutcomeAssertion(
                    archetype="test",
                    category=OutcomeCategory.STRATEGY_HALTED,
                    expected_within_seconds=30,
                ),
            ),
            unknown_field="bogus",
        )


def test_applicability_filter_defaults_to_empty() -> None:
    f = ScenarioApplicabilityFilter()
    assert f.venues is None
    assert f.chains is None
    assert f.protocols is None


# ---------------------------------------------------------------------------
# Outcome assertion — cross-reference resolution
# ---------------------------------------------------------------------------


def test_outcome_assertion_with_full_seam_5tuple() -> None:
    """The full 6-tuple per handshake doc fragment 11."""
    a = ScenarioOutcomeAssertion(
        archetype="ARBITRAGE_PRICE_DISPERSION",
        category=OutcomeCategory.RISK_BREAKER_TRIPPED,
        consequence=RiskRuleConsequence.BLOCK,
        breaker_id=CircuitBreakerId.FUNDING_RATE_FLIP_BPS,
        breaker_action=BreakerAction.BLOCK_NEW,
        kill_switch_id=KillSwitchId.KILL_PER_ARCHETYPE_ARBITRAGE_PRICE_DISPERSION,
        alert_codes=frozenset({AlertCode.RISK_RULE_BLOCKED, AlertCode.CIRCUIT_BREAKER_OPEN}),
        expected_within_seconds=60,
    )
    # All references are typed against UAC closed sets — no fabricated strings.
    assert a.consequence is RiskRuleConsequence.BLOCK
    assert a.breaker_id is CircuitBreakerId.FUNDING_RATE_FLIP_BPS
    assert a.breaker_action is BreakerAction.BLOCK_NEW
    assert a.kill_switch_id is KillSwitchId.KILL_PER_ARCHETYPE_ARBITRAGE_PRICE_DISPERSION
    assert AlertCode.RISK_RULE_BLOCKED in a.alert_codes


def test_outcome_assertion_minimum_fields_ok() -> None:
    """For PNL_BOUNDED_BY / RECONCILIATION_FLAGGED — most seam refs optional."""
    a = ScenarioOutcomeAssertion(
        archetype="carry_staked_basis",
        category=OutcomeCategory.PNL_BOUNDED_BY,
        pnl_lower_bound_bps=Decimal("-200"),
        pnl_upper_bound_bps=Decimal("50"),
        expected_within_seconds=3600,
    )
    assert a.pnl_lower_bound_bps == Decimal("-200")


# ---------------------------------------------------------------------------
# Registry completeness — Phase 1.D
# ---------------------------------------------------------------------------


_EXPECTED_SCENARIO_IDS: frozenset[str] = frozenset(
    {
        # CeFi (2)
        "cefi_venue_circuit_breaker_trip",
        "cefi_funding_spike_10x",
        # DeFi (6)
        "defi_chain_rpc_outage_solana",
        "defi_liquidity_drain_lending_pool",
        "defi_oracle_deviation_30sigma",
        "defi_gas_surge_50x",
        "defi_mempool_congestion_inclusion_delay",
        "defi_stablecoin_depeg",
        # Cross-asset (2)
        "cross_asset_flash_crash",
        "cross_asset_basis_blowout_perp_spot",
    },
)


def test_registry_has_all_10_day1_scenarios() -> None:
    """Every Day-1-design-shipped scenario MUST be in the registry."""
    assert _EXPECTED_SCENARIO_IDS.issubset(set(SCENARIO_REGISTRY)), (
        f"Missing from registry: {_EXPECTED_SCENARIO_IDS - set(SCENARIO_REGISTRY)}"
    )


def test_registry_total_count_at_least_ten() -> None:
    assert len(SCENARIO_REGISTRY) >= 10


@pytest.mark.parametrize("scenario_id", sorted(_EXPECTED_SCENARIO_IDS))
def test_per_scenario_in_registry_has_outcomes(scenario_id: str) -> None:
    scenario = SCENARIO_REGISTRY[scenario_id]
    assert len(scenario.expected_outcomes) >= 1
    assert scenario.scenario_id == scenario_id
    assert scenario.real_world_referent != ""
    assert scenario.description != ""


def test_per_asset_group_split() -> None:
    """2 cefi + 7 defi + 2 cross_asset = 11 total."""
    cefi = [s for s in SCENARIO_REGISTRY.values() if s.scenario_id.startswith("cefi_")]
    defi = [s for s in SCENARIO_REGISTRY.values() if s.scenario_id.startswith("defi_")]
    cross = [s for s in SCENARIO_REGISTRY.values() if s.scenario_id.startswith("cross_asset_")]
    assert len(cefi) == 2
    assert len(defi) == 7
    assert len(cross) == 2


# ---------------------------------------------------------------------------
# register_scenario idempotency
# ---------------------------------------------------------------------------


def test_register_scenario_idempotent_same_instance() -> None:
    overlay = _minimal_overlay("idempotent_test_a")
    register_scenario(overlay)
    # Re-register identical instance — no-op
    register_scenario(overlay)
    assert SCENARIO_REGISTRY["idempotent_test_a"] == overlay
    # Cleanup so this test is hermetic when re-run within session.
    del SCENARIO_REGISTRY["idempotent_test_a"]


def test_register_scenario_rejects_duplicate_with_different_content() -> None:
    a = _minimal_overlay("dup_test_b")
    b = ScenarioOverlay(
        scenario_id="dup_test_b",
        category=ScenarioCategory.PRICE_SHOCK,  # different
        layer=ScenarioOverlayLayer.RAW_TICK,
        asset_groups=frozenset({"defi"}),  # different
        mutation_spec=DropRows(drop_rate=Decimal("0.5"), duration_seconds=60),
        expected_outcomes=(
            ScenarioOutcomeAssertion(
                archetype="test",
                category=OutcomeCategory.STRATEGY_HALTED,
                expected_within_seconds=30,
            ),
        ),
    )
    register_scenario(a)
    with pytest.raises(ValueError, match="duplicate scenario_id"):
        register_scenario(b)
    del SCENARIO_REGISTRY["dup_test_b"]


# ---------------------------------------------------------------------------
# Per-scenario seam-reference sanity (per fragment 11 6-tuple contract)
# ---------------------------------------------------------------------------


def test_every_registry_scenario_outcome_uses_typed_breaker_id_or_none() -> None:
    """Every breaker_id reference resolves to an existing CircuitBreakerId — Pydantic catches at instantiation,
    but this test makes the invariant explicit (catches a future API drift)."""
    for scenario in SCENARIO_REGISTRY.values():
        for outcome in scenario.expected_outcomes:
            if outcome.breaker_id is not None:
                assert outcome.breaker_id in set(CircuitBreakerId)


def test_every_registry_scenario_outcome_uses_typed_kill_switch_id_or_none() -> None:
    for scenario in SCENARIO_REGISTRY.values():
        for outcome in scenario.expected_outcomes:
            if outcome.kill_switch_id is not None:
                assert outcome.kill_switch_id in set(KillSwitchId)


def test_every_registry_scenario_outcome_uses_typed_alert_codes() -> None:
    for scenario in SCENARIO_REGISTRY.values():
        for outcome in scenario.expected_outcomes:
            for code in outcome.alert_codes:
                assert code in set(AlertCode)
