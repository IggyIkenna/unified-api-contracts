"""M2 source-mode capability registry + M8 cadence + M9 mock — Phase 0.1.

Asserts only the LOAD-BEARING facts (completeness + batch-for-all + the
operator-stated live/replay facts + mock semantics), so the DRAFT live/replay
flags for the uncertain sources can change freely on per-source ratification
without breaking CI. SSOT plan:
``pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md`` (M2/M8/M9).
"""

from __future__ import annotations

from unified_api_contracts import (
    SOURCE_MODE_CAPABILITY,
    Cadence,
    Mode,
    PipelineMode,
    mode_of,
    modes_for_source,
    source_supports,
    sources_supporting,
)
from unified_api_contracts.canonical.crosscutting.source_priority import (
    COMPUTED_SOURCES,
    SOURCE_PRIORITY,
)

MOCK = "mock"


def _all_external_sources() -> set[str]:
    srcs: set[str] = set()
    for priority_list in SOURCE_PRIORITY.values():
        srcs.update(priority_list)
    return srcs - set(COMPUTED_SOURCES)


# ---------------------------------------------------------------------------
# Completeness + the certain fact: every external source is batch-capable
# ---------------------------------------------------------------------------


def test_every_external_source_has_a_capability_entry() -> None:
    """No external SOURCE_PRIORITY source may be unclassified (closed-set)."""
    missing = _all_external_sources() - set(SOURCE_MODE_CAPABILITY)
    assert not missing, f"sources missing a capability entry: {sorted(missing)}"


def test_every_capability_source_is_batch_capable() -> None:
    """BATCH is the certain, round-trip-derivable floor — every source has it."""
    for src, modes in SOURCE_MODE_CAPABILITY.items():
        assert Mode.BATCH in modes, f"{src} must be batch-capable"


def test_capability_keys_are_real_sources() -> None:
    """No typo'd / phantom source in the registry."""
    stray = set(SOURCE_MODE_CAPABILITY) - _all_external_sources()
    assert not stray, f"capability registry has non-SOURCE_PRIORITY sources: {sorted(stray)}"


# ---------------------------------------------------------------------------
# Operator-stated facts (load-bearing — these encode real decisions)
# ---------------------------------------------------------------------------


def test_chain_rpcs_are_replay_capable() -> None:
    """DeFi chain RPCs are deterministic ⇒ fully replayable (operator-stated)."""
    for src in ("onchain_rpc", "solana_rpc", "helius_rpc"):
        assert source_supports(src, Mode.REPLAY), f"{src} should be replay-capable"


def test_tardis_is_live_but_not_replay() -> None:
    """Operator: Tardis streams live but does NOT allow tick-replay."""
    assert source_supports("tardis", Mode.LIVE)
    assert not source_supports("tardis", Mode.REPLAY)


def test_massive_and_databento_are_live_and_replay_capable() -> None:
    """Operator 2026-06-05 + vendor-doc check: the TradFi vendors stream live AND
    support intraday replay (today-since-start backfill). databento via the Live-API
    24h intraday replay (Historical API is 24h-embargoed); massive (=Polygon.io) via
    REST tick within a time range. (massive live is 15-min delayed on Starter tier.)"""
    for src in ("massive", "databento"):
        assert source_supports(src, Mode.LIVE)
        assert source_supports(src, Mode.REPLAY)


def test_no_sports_source_is_live_yet() -> None:
    """Operator 2026-06-05: the live sports source is undecided — seeded batch-only
    until a vendor is chosen. (Change deliberately when a live sports source lands.)"""
    for src in ("api_football", "footystats", "odds_api", "understat"):
        assert not source_supports(src, Mode.LIVE)


# ---------------------------------------------------------------------------
# Helpers + mock + enums
# ---------------------------------------------------------------------------


def test_sources_supporting_replay_is_nonempty_and_subset() -> None:
    replayers = sources_supporting(Mode.REPLAY)
    assert "onchain_rpc" in replayers
    assert replayers <= set(SOURCE_MODE_CAPABILITY)


def test_unregistered_source_defaults_to_batch_only() -> None:
    assert modes_for_source("totally_new_vendor") == frozenset({Mode.BATCH})


def test_mock_source_supports_all_modes() -> None:
    """M9 — a mock fixture can stand in for any mode (dev-tier only)."""
    assert modes_for_source(MOCK) == frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY})


def test_mode_of_maps_pipeline_mode_to_reconciliation_class() -> None:
    assert mode_of(PipelineMode.BATCH_DATABENTO) is Mode.BATCH
    assert mode_of(PipelineMode.LIVE_WEBSOCKET) is Mode.LIVE


def test_cadence_values_are_the_agreed_set() -> None:
    assert {c.value for c in Cadence} == {
        "one_off_backfill",
        "t1_daily",
        "scheduled_recurring",
        "continuous_live",
        "recovery_replay",
    }
