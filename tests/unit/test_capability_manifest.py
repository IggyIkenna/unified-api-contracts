"""Tests for the capability manifest schema and gap registries.

Covers:
  - CapabilityManifest: construction, deterministic serialisation, gap counts.
  - All six gap registries: importable, typed, empty-by-design for unregistered.
  - CapabilityNodeKind / CapabilityEdgeStatus / CapabilityGapType enum closure.
  - TreasurySplitPolicy seeded entries (sourced from wallet-hierarchy-and-capital-flow.md).
  - TimeInForce canonical enum (new UAC definition).
  - MatchingModel / BenchmarkFillMode consistency mapping.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.internal.architecture_v2.capability_manifest import (
    AgentAnnotation,
    CapabilityEdge,
    CapabilityEdgeStatus,
    CapabilityGapType,
    CapabilityManifest,
    CapabilityNode,
    CapabilityNodeKind,
)
from unified_api_contracts.internal.architecture_v2.collateral_registry import (
    BROKER_REGISTRY,
    COLLATERAL_REGISTRY,
    TREASURY_SPLIT_POLICIES,
)
from unified_api_contracts.internal.architecture_v2.fees_registry import (
    FEES_REGISTRY,
    FeeComponent,
    FeeSchedule,
    FeeUnit,
)
from unified_api_contracts.internal.architecture_v2.fund_structures import (
    OFFERED_FUND_STRUCTURES,
    CadenceKind,
    FundStructureKind,
    FundStructureOffering,
)
from unified_api_contracts.internal.architecture_v2.order_semantics import (
    VENUE_ORDER_SEMANTICS,
    MultiLegDeltaOwner,
    RefPricingMode,
    TimeInForce,
    VenueOrderSemantics,
)
from unified_api_contracts.internal.architecture_v2.simulation_assumptions import (
    MATCHING_MODEL_TO_BENCHMARK_FILL,
    SIM_ASSUMPTIONS_REGISTRY,
    MatchingModel,
    SimulationAssumption,
)
from unified_api_contracts.internal.architecture_v2.trading_agent_capability import (
    TRADING_AGENT_CAPABILITIES,
    TradingAgentCapability,
)

# ---------------------------------------------------------------------------
# Enum closure tests
# ---------------------------------------------------------------------------


def test_capability_node_kind_values() -> None:
    """All expected node kinds exist."""
    expected = {
        "archetype",
        "leg",
        "family",
        "venue",
        "chain",
        "instrument_type",
        "execution_algo",
        "instruction_type",
        "feature_group",
        "ml_model",
        "data_source",
        "fund_structure",
        "wallet",
        "broker",
        "custody_provider",
        "signing_surface",
        "risk_gate_layer",
        "kill_switch_reason",
        "gap_registry",
        "collateral_policy",
    }
    assert set(CapabilityNodeKind) == expected


def test_capability_edge_status_values() -> None:
    expected = {"available", "partial", "not_available", "not_registered"}
    assert set(CapabilityEdgeStatus) == expected


def test_capability_gap_type_values() -> None:
    expected = {
        "missing_registry",
        "missing_extraction",
        "needs_code_scan",
        "logical_dead_end",
    }
    assert set(CapabilityGapType) == expected


# ---------------------------------------------------------------------------
# CapabilityNode construction
# ---------------------------------------------------------------------------


def test_capability_node_construction() -> None:
    node = CapabilityNode(
        kind=CapabilityNodeKind.ARCHETYPE,
        node_id="CARRY_STAKED_BASIS",
        label="Carry: Staked Basis",
    )
    assert node.kind == CapabilityNodeKind.ARCHETYPE
    assert node.node_id == "CARRY_STAKED_BASIS"
    assert node.label == "Carry: Staked Basis"
    assert node.metadata == {}


def test_capability_node_metadata() -> None:
    node = CapabilityNode(
        kind=CapabilityNodeKind.VENUE,
        node_id="hyperliquid",
        label="Hyperliquid",
        metadata={"asset_group": "defi", "chain": "arbitrum"},
    )
    assert node.metadata["asset_group"] == "defi"


# ---------------------------------------------------------------------------
# CapabilityEdge construction
# ---------------------------------------------------------------------------


def test_capability_edge_available() -> None:
    edge = CapabilityEdge(
        from_node_id="CARRY_STAKED_BASIS",
        to_node_id="hyperliquid",
        relation="supports",
        status=CapabilityEdgeStatus.AVAILABLE,
    )
    assert edge.gap_type is None
    assert edge.agent_annotation is None


def test_capability_edge_gap() -> None:
    edge = CapabilityEdge(
        from_node_id="CARRY_STAKED_BASIS",
        to_node_id="fees",
        relation="requires_fee_schedule",
        status=CapabilityEdgeStatus.NOT_REGISTERED,
        gap_type=CapabilityGapType.MISSING_REGISTRY,
        reason="Fees registry not yet populated for this venue.",
    )
    assert edge.status == CapabilityEdgeStatus.NOT_REGISTERED
    assert edge.gap_type == CapabilityGapType.MISSING_REGISTRY


def test_capability_edge_with_agent_annotation() -> None:
    annotation = AgentAnnotation(
        annotated_by="agent-orchestrator/slot-3",
        annotated_at=datetime(2026, 6, 11, 12, 0, 0, tzinfo=UTC),
        answer="Fee schedule confirmed from Hyperliquid docs.",
        resolved_status=CapabilityEdgeStatus.AVAILABLE,
    )
    edge = CapabilityEdge(
        from_node_id="CARRY_STAKED_BASIS",
        to_node_id="hyperliquid",
        relation="fee_schedule",
        status=CapabilityEdgeStatus.AVAILABLE,
        agent_annotation=annotation,
    )
    assert edge.agent_annotation is not None
    assert edge.agent_annotation.resolved_status == CapabilityEdgeStatus.AVAILABLE


# ---------------------------------------------------------------------------
# CapabilityManifest — construction and deterministic serialisation
# ---------------------------------------------------------------------------


def _make_test_manifest() -> CapabilityManifest:
    return CapabilityManifest(
        manifest_version="1.0.0",
        generated_from_commit="abc123",
        nodes=[
            CapabilityNode(
                kind=CapabilityNodeKind.ARCHETYPE,
                node_id="CARRY_STAKED_BASIS",
                label="Carry: Staked Basis",
            ),
            CapabilityNode(
                kind=CapabilityNodeKind.VENUE,
                node_id="hyperliquid",
                label="Hyperliquid",
            ),
        ],
        edges=[
            CapabilityEdge(
                from_node_id="CARRY_STAKED_BASIS",
                to_node_id="hyperliquid",
                relation="supports",
                status=CapabilityEdgeStatus.AVAILABLE,
            ),
            CapabilityEdge(
                from_node_id="CARRY_STAKED_BASIS",
                to_node_id="fees_unknown",
                relation="requires_fee_schedule",
                status=CapabilityEdgeStatus.NOT_REGISTERED,
                gap_type=CapabilityGapType.MISSING_REGISTRY,
            ),
        ],
    )


def test_manifest_construction() -> None:
    manifest = _make_test_manifest()
    assert manifest.manifest_version == "1.0.0"
    assert len(manifest.nodes) == 2
    assert len(manifest.edges) == 2


def test_manifest_to_canonical_dict_is_deterministic() -> None:
    """Two manifests with nodes/edges in different order produce identical JSON."""
    m1 = _make_test_manifest()
    # Reverse node order
    m2 = CapabilityManifest(
        manifest_version="1.0.0",
        generated_from_commit="abc123",
        nodes=list(reversed(m1.nodes)),
        edges=list(reversed(m1.edges)),
    )
    d1 = m1.to_canonical_dict()
    d2 = m2.to_canonical_dict()
    assert d1 == d2
    # JSON round-trip
    j1 = json.dumps(d1, sort_keys=True)
    j2 = json.dumps(d2, sort_keys=True)
    assert j1 == j2


def test_manifest_gap_counts_recomputed() -> None:
    manifest = _make_test_manifest()
    d = manifest.to_canonical_dict()
    gaps = d["gaps"]
    assert gaps["not_registered_total"] == 1
    assert gaps["missing_registry"] == 1
    assert gaps["missing_extraction"] == 0
    assert gaps["needs_code_scan"] == 0
    assert gaps["logical_dead_end"] == 0


def test_manifest_empty_nodes_and_edges() -> None:
    manifest = CapabilityManifest(manifest_version="0.1.0")
    d = manifest.to_canonical_dict()
    assert d["nodes"] == []
    assert d["edges"] == []
    assert d["gaps"]["not_registered_total"] == 0


# ---------------------------------------------------------------------------
# Collateral registry — treasury split policies (seeded, sourced)
# ---------------------------------------------------------------------------


def test_treasury_split_policies_are_seeded() -> None:
    assert len(TREASURY_SPLIT_POLICIES) == 3


def test_treasury_split_defi_policy() -> None:
    defi = next(p for p in TREASURY_SPLIT_POLICIES if p.asset_group == "defi")
    assert defi.treasury_pct == Decimal("20")
    assert defi.hot_pct == Decimal("80")
    assert defi.rebalance_min_threshold_pct == Decimal("10")
    assert defi.rebalance_max_threshold_pct == Decimal("30")


def test_treasury_split_cefi_policy() -> None:
    cefi = next(p for p in TREASURY_SPLIT_POLICIES if p.asset_group == "cefi")
    assert cefi.treasury_pct == Decimal("0")
    assert cefi.hot_pct == Decimal("100")
    assert cefi.rebalance_min_threshold_pct is None


def test_treasury_split_sports_policy() -> None:
    sports = next(p for p in TREASURY_SPLIT_POLICIES if p.asset_group == "sports")
    assert sports.treasury_pct == Decimal("0")
    assert sports.hot_pct == Decimal("100")
    assert "no split" in sports.notes.lower() or "no treasury" in sports.notes.lower()


def test_collateral_registry_is_backfilled() -> None:
    """COLLATERAL_REGISTRY backfilled for the MVP venue universe (2026-06-12).

    Was honest-empty; now carries sourced per-venue policies. The exhaustive
    backfill assertions (per-venue counts, source_of_truth non-empty, missing
    venues) live in ``test_collateral_registry_backfill.py``.
    """
    assert len(COLLATERAL_REGISTRY) >= 9  # 7 perp + 2 lending MVP venues
    assert all(p.source_of_truth for p in COLLATERAL_REGISTRY)


def test_broker_registry_is_empty_honest_gap() -> None:
    """Brokers remain an honest gap — not in the DeFi/CeFi MVP venue set."""
    assert BROKER_REGISTRY == []


# ---------------------------------------------------------------------------
# Fees registry — importable and empty
# ---------------------------------------------------------------------------


def test_fees_registry_backfilled() -> None:
    """Backfilled 2026-06-13 (MVP venue universe; CeFi official base tiers +
    code-cited DeFi). See test_order_semantics_sim_backfill.py for coverage."""
    assert len(FEES_REGISTRY) >= 20


def test_fee_component_values_coverage() -> None:
    expected = {
        "exchange_maker",
        "exchange_taker",
        "gas",
        "broker",
        "clearing",
        "funding_passthrough",
    }
    assert set(FeeComponent) == expected


def test_fee_unit_values() -> None:
    expected = {"bps", "absolute", "gas_units"}
    assert set(FeeUnit) == expected


def test_fee_schedule_construction() -> None:
    schedule = FeeSchedule(
        venue_id="binance",
        component=FeeComponent.EXCHANGE_TAKER,
        value=Decimal("5"),
        unit=FeeUnit.BPS,
        instrument_type="spot",
        source_note="Binance fee schedule 2026-05",
    )
    assert schedule.value == Decimal("5")
    assert schedule.unit == FeeUnit.BPS


# ---------------------------------------------------------------------------
# Simulation assumptions — matching model vocab + BenchmarkFillMode alignment
# ---------------------------------------------------------------------------


def test_sim_assumptions_registry_backfilled() -> None:
    """Backfilled 2026-06-13 from the strategy-service backtest-runner scan (F11);
    see test_order_semantics_sim_backfill.py for full coverage assertions."""
    assert len(SIM_ASSUMPTIONS_REGISTRY) >= 16


def test_matching_model_benchmark_fill_mapping_complete() -> None:
    """Every MatchingModel has an entry in the consistency mapping."""
    for model in MatchingModel:
        assert model in MATCHING_MODEL_TO_BENCHMARK_FILL


def test_matching_model_to_benchmark_fill_none_only_for_ohlc() -> None:
    """Only CANDLE_OHLC_INTERPOLATED maps to None (needs_code_scan gap)."""
    none_mappings = [k for k, v in MATCHING_MODEL_TO_BENCHMARK_FILL.items() if v is None]
    assert none_mappings == [MatchingModel.CANDLE_OHLC_INTERPOLATED]


def test_simulation_assumption_construction() -> None:
    assumption = SimulationAssumption(
        venue_id="hyperliquid",
        instrument_type="perp",
        supported_granularities=["1m", "5m", "1h"],
        matching_model=MatchingModel.CANDLE_CLOSE,
        fill_assumptions="Fills at candle close; no partial-fill logic.",
    )
    assert assumption.matching_model == MatchingModel.CANDLE_CLOSE
    assert "1h" in assumption.supported_granularities


# ---------------------------------------------------------------------------
# Fund structures — importable and empty, ShareClass reuse confirmed
# ---------------------------------------------------------------------------


def test_offered_fund_structures_backfilled() -> None:
    """Backfilled 2026-06-13 from sma-vs-pooled.md (POOLED + SMA)."""
    assert len(OFFERED_FUND_STRUCTURES) == 2


def test_fund_structure_kind_values() -> None:
    expected = {"pooled", "sma", "prop"}
    assert set(FundStructureKind) == expected


def test_cadence_kind_values() -> None:
    expected = {"daily", "weekly", "monthly", "on_demand"}
    assert set(CadenceKind) == expected


def test_fund_structure_offering_construction() -> None:
    from unified_api_contracts.internal.architecture_v2.enums import ShareClass

    offering = FundStructureOffering(
        kind=FundStructureKind.POOLED,
        share_classes=[ShareClass.USDC, ShareClass.ETH],
        subscription_cadence=[CadenceKind.ON_DEMAND],
        redemption_cadence=[CadenceKind.ON_DEMAND],
        rebalance_cadence=[CadenceKind.DAILY],
        supports_daily_withdraw_deposit=True,
    )
    assert offering.kind == FundStructureKind.POOLED
    assert offering.supports_daily_withdraw_deposit is True
    assert ShareClass.USDC in offering.share_classes


def test_fund_structures_module_share_class_is_same_as_enums_share_class() -> None:
    """Confirm no duplicate definition — fund_structures re-exports from enums."""
    from unified_api_contracts.internal.architecture_v2 import enums as _enums
    from unified_api_contracts.internal.architecture_v2 import fund_structures as _fs

    assert _fs.ShareClass is _enums.ShareClass


# ---------------------------------------------------------------------------
# Order semantics — TimeInForce (new UAC canonical enum), empty registry
# ---------------------------------------------------------------------------


def test_venue_order_semantics_backfilled() -> None:
    """Backfilled 2026-06-13 from the execution-service venue-adapter scan;
    see test_order_semantics_sim_backfill.py for full coverage assertions."""
    assert len(VENUE_ORDER_SEMANTICS) >= 9


def test_time_in_force_values() -> None:
    expected = {"GTC", "IOC", "FOK", "GTD", "POST_ONLY", "REDUCE_ONLY"}
    assert set(TimeInForce) == expected


def test_ref_pricing_mode_values() -> None:
    expected = {"fixed", "delta_adjusted_to_underlying"}
    assert set(RefPricingMode) == expected


def test_multi_leg_delta_owner_values() -> None:
    expected = {"atomic_bundle", "execution_algo", "strategy_engine", "unmanaged"}
    assert set(MultiLegDeltaOwner) == expected


def test_venue_order_semantics_construction() -> None:
    from unified_api_contracts.internal.architecture_v2.capability_manifest import (
        CapabilityEdgeStatus,
    )
    from unified_api_contracts.internal.architecture_v2.enums import AtomicExecutionMode

    semantics = VenueOrderSemantics(
        venue_id="binance",
        honored_tif=[TimeInForce.GTC, TimeInForce.IOC, TimeInForce.FOK],
        post_only=True,
        make_take_modes=["make", "take"],
        ref_pricing_modes=[RefPricingMode.FIXED],
        multi_leg_delta_owner=MultiLegDeltaOwner.EXECUTION_ALGO,
        atomic_execution_modes=[AtomicExecutionMode.LEADER_HEDGE],
        auth_wired=CapabilityEdgeStatus.AVAILABLE,
    )
    assert semantics.post_only is True
    assert TimeInForce.GTC in semantics.honored_tif


def test_order_semantics_atomic_execution_mode_reused() -> None:
    """AtomicExecutionMode re-exported from order_semantics is the same as enums."""
    from unified_api_contracts.internal.architecture_v2 import enums as _enums
    from unified_api_contracts.internal.architecture_v2 import order_semantics as _os

    assert _os.AtomicExecutionMode is _enums.AtomicExecutionMode


# ---------------------------------------------------------------------------
# Trading agent capability — importable and empty
# ---------------------------------------------------------------------------


def test_trading_agent_capabilities_backfilled() -> None:
    """Backfilled 2026-06-13 from trading-agent-service (stub, enabled=False)."""
    assert len(TRADING_AGENT_CAPABILITIES) == 3
    assert all(not c.enabled for c in TRADING_AGENT_CAPABILITIES)


def test_trading_agent_capability_construction() -> None:
    from unified_api_contracts.internal.architecture_v2.enums import StrategyArchetype

    cap = TradingAgentCapability(
        archetype=StrategyArchetype.CARRY_STAKED_BASIS,
        allowed_decision_models=["anthropic/claude-sonnet-4-6"],
        parameter_guidance_scope="Position sizing multipliers only.",
        enabled=False,
    )
    assert cap.archetype == StrategyArchetype.CARRY_STAKED_BASIS
    assert cap.enabled is False


def test_trading_agent_capability_reuses_strategy_archetype() -> None:
    """StrategyArchetype re-exported from trading_agent_capability is canonical."""
    from unified_api_contracts.internal.architecture_v2 import enums as _enums
    from unified_api_contracts.internal.architecture_v2 import trading_agent_capability as _tac

    assert _tac.StrategyArchetype is _enums.StrategyArchetype
