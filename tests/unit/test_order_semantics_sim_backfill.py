"""Tests for the VENUE_ORDER_SEMANTICS + SIM_ASSUMPTIONS_REGISTRY backfills (2026-06-13).

Both registries were honest-empty until backfilled from a code-scan of the
execution-service venue adapters (order semantics) and the strategy-service
backtest runner (simulation assumptions). These tests assert the backfilled
entries are well-formed, cover the MVP venue universe, carry source citations
in their notes/fill_assumptions, and that wired-vs-scaffold status is honest.

Plan: ``plans/active/capability_wizard_and_manifest_2026_06_11.md`` Phase 2
"Registry backfills"; gap tracker ``capability_wizard_gap_discovery_2026_06_11.md``
(``gap_registry:order_semantics`` escalation + F11 sim-assumptions).
"""

from __future__ import annotations

from unified_api_contracts.internal.architecture_v2.capability_manifest import (
    CapabilityEdgeStatus,
)
from unified_api_contracts.internal.architecture_v2.order_semantics import (
    VENUE_ORDER_SEMANTICS,
    TimeInForce,
)
from unified_api_contracts.internal.architecture_v2.simulation_assumptions import (
    SIM_ASSUMPTIONS_REGISTRY,
    MatchingModel,
)

# ---------------------------------------------------------------------------
# VENUE_ORDER_SEMANTICS
# ---------------------------------------------------------------------------

# binance/bybit/okx moved SCAFFOLD -> WIRED 2026-07-28 (cefi_consolidated_native_ao_extract_2026_07_25.md
# todo 1): the prior "not_registered" verdict cited only the parked *_native.py direct-REST scaffolds
# (BLOCKED-CREDENTIALS, never imported by factory.py) and never checked the actually-live-routed
# *_ccxt.py adapters, which place real orders via ccxt.create_market_order/create_limit_order — the
# same wiring shape already declared AVAILABLE for hyperliquid. drift removed 2026-07-16 (Solana perp
# DEX cull); gmx_v2 removed 2026-07-25 (unreliable historical funding data).
_WIRED_VENUES = {"hyperliquid", "deribit", "aave_v3", "kamino", "binance", "bybit", "okx"}


def _os(venue_id: str):
    return next(v for v in VENUE_ORDER_SEMANTICS if v.venue_id == venue_id)


def test_order_semantics_is_backfilled_not_empty() -> None:
    # Count was >= 9 until "drift" (Solana perp DEX) removed 2026-07-16 (operator ruling: all
    # Solana perp DEXes dropped except Jupiter, not integrated), then >= 8 until "gmx_v2"
    # removed 2026-07-25 (unreliable historical funding data — see
    # unified-trading-pm/plans/active/defi_gmx_venue_removal_2026_07_25.md).
    assert len(VENUE_ORDER_SEMANTICS) >= 7


def test_order_semantics_covers_mvp_venue_universe() -> None:
    ids = {v.venue_id for v in VENUE_ORDER_SEMANTICS}
    assert _WIRED_VENUES.issubset(ids)


def test_every_order_semantics_entry_cites_source() -> None:
    """No invented data: every entry's notes either cite a file (`.py`) source
    OR explicitly document the absence of an adapter ("No ... adapter found")."""
    for v in VENUE_ORDER_SEMANTICS:
        cites_file = ".py" in v.notes
        documents_absence = "no execution adapter found" in v.notes.lower()
        assert cites_file or documents_absence, f"{v.venue_id} order-semantics entry has no source citation"


def test_wired_venues_have_available_auth() -> None:
    for vid in _WIRED_VENUES:
        assert _os(vid).auth_wired == CapabilityEdgeStatus.AVAILABLE


def test_wired_clob_venues_honor_tif() -> None:
    """The CLOB perp/options venues that are wired send at least GTC + IOC."""
    for vid in ("hyperliquid", "deribit", "binance", "bybit", "okx"):  # drift removed 2026-07-16 (Solana perp DEX cull)
        tif = set(_os(vid).honored_tif)
        assert {TimeInForce.GTC, TimeInForce.IOC} <= tif


def test_no_venue_claims_multi_leg_delta_ownership() -> None:
    """The scan found NO component manages inter-leg delta per venue → all None."""
    for v in VENUE_ORDER_SEMANTICS:
        assert v.multi_leg_delta_owner is None


# ---------------------------------------------------------------------------
# SIM_ASSUMPTIONS_REGISTRY
# ---------------------------------------------------------------------------

_EXPECTED_GRANULARITIES = ["1m", "5m", "15m", "1h", "4h", "24h"]


def test_sim_assumptions_is_backfilled_not_empty() -> None:
    assert len(SIM_ASSUMPTIONS_REGISTRY) >= 16


def test_every_sim_entry_has_granularities_and_citation() -> None:
    for s in SIM_ASSUMPTIONS_REGISTRY:
        assert s.supported_granularities == _EXPECTED_GRANULARITIES
        assert "benchmark_fills.py" in s.fill_assumptions, f"{s.venue_id}/{s.instrument_type} missing source citation"


def test_perp_surfaces_use_candle_close() -> None:
    perp = [s for s in SIM_ASSUMPTIONS_REGISTRY if s.instrument_type == "perp"]
    assert perp, "expected perp simulation surfaces"
    assert all(s.matching_model == MatchingModel.CANDLE_CLOSE for s in perp)


def test_amm_surfaces_use_pool_mid_at_block() -> None:
    swaps = [s for s in SIM_ASSUMPTIONS_REGISTRY if s.instrument_type == "swap"]
    assert swaps
    assert all(s.matching_model == MatchingModel.POOL_MID_AT_BLOCK for s in swaps)


def test_lending_and_staking_use_funding_snapshot() -> None:
    fund = [s for s in SIM_ASSUMPTIONS_REGISTRY if s.instrument_type in ("lend", "stake")]
    assert fund
    assert all(s.matching_model == MatchingModel.FUNDING_SNAPSHOT for s in fund)


def test_sim_assumptions_document_batch_live_divergence() -> None:
    """Every entry carries the batch↔live divergence note (FillSource.BENCHMARK etc.)."""
    for s in SIM_ASSUMPTIONS_REGISTRY:
        assert "FillSource.BENCHMARK" in s.fill_assumptions
