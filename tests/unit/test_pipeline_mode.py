"""Unit tests for the pipeline_mode SSOT.

Covers the closed-set round-trip rule: every batch ``PipelineMode`` value
must correspond to a SOURCE_PRIORITY entry, and every source string in
SOURCE_PRIORITY must have a matching batch ``PipelineMode``.

Plans:

* ``gcs_migration_bundle_pipeline_mode_2026_05_08`` Phase 1A
* ``live_pipeline_mtds_mdps_features_2026_05_08`` Phase 1
"""

from __future__ import annotations

import json

import pytest

from unified_api_contracts.canonical.crosscutting.pipeline_mode import (
    _SPORTS_ENTITY_TO_PIPELINE_MODE,
    Mode,
    PipelineMode,
    Transport,
    _split_transport,
    default_transport_for_source,
    is_batch,
    is_live,
    pipeline_mode_for_source,
    pipeline_mode_for_sports_entity,
    source_string_for,
    transport_of,
)
from unified_api_contracts.canonical.crosscutting.source_priority import SOURCE_PRIORITY

# ---------------------------------------------------------------------------
# Enum shape
# ---------------------------------------------------------------------------


def test_pipeline_mode_is_str_enum() -> None:
    assert isinstance(PipelineMode.LIVE_BINANCE, str)
    assert PipelineMode.LIVE_BINANCE == "live_binance"


def test_pipeline_mode_has_source_aware_live_member() -> None:
    assert PipelineMode.LIVE_BINANCE.value == "live_binance"


def test_pipeline_mode_values_use_a_mode_prefix() -> None:
    """Every member is ``{mode}_{source}`` — prefixed batch_/live_/replay_ (M1)."""
    members = list(PipelineMode)
    assert members, "expected at least one PipelineMode member"
    for m in members:
        assert m.value.startswith(("batch_", "live_", "replay_")), (
            f"PipelineMode {m.name}={m.value!r} does not start with a mode prefix"
        )


def test_pipeline_mode_still_has_batch_members() -> None:
    batch_members = [m for m in PipelineMode if m.value.startswith("batch_")]
    assert batch_members, "expected at least one batch PipelineMode member"


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------


def test_pipeline_mode_json_round_trip() -> None:
    payload = {"mode": PipelineMode.BATCH_TARDIS}
    serialized = json.dumps(payload)
    assert "batch_tardis" in serialized
    parsed = json.loads(serialized)
    assert PipelineMode(parsed["mode"]) is PipelineMode.BATCH_TARDIS


# ---------------------------------------------------------------------------
# Closed-set round-trip with SOURCE_PRIORITY
# ---------------------------------------------------------------------------


def _all_source_strings() -> set[str]:
    sources: set[str] = set()
    for source_list in SOURCE_PRIORITY.values():
        sources.update(source_list)
    return sources


def test_every_source_priority_source_has_pipeline_mode() -> None:
    """Bidirectional: every source in SOURCE_PRIORITY has a BATCH_<SOURCE> mode."""

    sources = _all_source_strings()
    missing: list[str] = []
    for source in sources:
        try:
            pipeline_mode_for_source(source)
        except ValueError:
            missing.append(source)
    assert not missing, (
        f"SOURCE_PRIORITY references sources with no PipelineMode: {sorted(missing)}; "
        "add BATCH_<SOURCE> values to PipelineMode (closed-set round-trip required)."
    )


def test_every_batch_pipeline_mode_maps_to_source_priority_source() -> None:
    """Bidirectional: every BATCH_<SOURCE> mode maps to a source in SOURCE_PRIORITY."""

    sources = _all_source_strings()
    orphan_modes: list[str] = []
    for mode in PipelineMode:
        if not is_batch(mode):
            continue
        source = source_string_for(mode)
        assert source is not None
        if source not in sources:
            orphan_modes.append(mode.value)
    assert not orphan_modes, (
        f"PipelineMode has batch values with no SOURCE_PRIORITY entry: {sorted(orphan_modes)}; "
        "either remove the orphan modes or add SOURCE_PRIORITY entries (closed-set round-trip required)."
    )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def test_is_batch_distinguishes_live_and_batch() -> None:
    assert is_batch(PipelineMode.BATCH_TARDIS)
    assert not is_batch(PipelineMode.LIVE_BINANCE)


def test_is_live_distinguishes_live_and_batch() -> None:
    assert is_live(PipelineMode.LIVE_BINANCE)
    assert not is_live(PipelineMode.BATCH_TARDIS)


def test_source_string_for_batch_mode_returns_underlying_source() -> None:
    assert source_string_for(PipelineMode.BATCH_TARDIS) == "tardis"
    assert source_string_for(PipelineMode.BATCH_DATABENTO) == "databento"


def test_source_string_for_live_mode_returns_source() -> None:
    assert source_string_for(PipelineMode.LIVE_BINANCE) == "binance"
    assert transport_of(PipelineMode.LIVE_BINANCE) is None


def test_pipeline_mode_for_source_round_trip_for_known_source() -> None:
    assert pipeline_mode_for_source("tardis") is PipelineMode.BATCH_TARDIS


def test_pipeline_mode_for_source_raises_for_unknown_source() -> None:
    with pytest.raises(ValueError, match="No PipelineMode for source"):
        _ = pipeline_mode_for_source("does_not_exist")


# ---------------------------------------------------------------------------
# Public-export surface
# ---------------------------------------------------------------------------


def test_pipeline_mode_is_exposed_from_crosscutting_namespace() -> None:
    from unified_api_contracts.canonical.crosscutting import (
        PipelineMode as CrosscuttingPipelineMode,
    )

    assert CrosscuttingPipelineMode is PipelineMode


# ---------------------------------------------------------------------------
# Phase 4.MTDS operator-approved Q2=(A) 2026-05-12 enum extension
# Per-member round-trip tests for the 6 new batch sources added at PM@52d289c
# (UAC enum + SOURCE_PRIORITY) — pinning each (enum value, source string)
# pair so accidental rename of either side fails CI loudly. Composes with
# `test_every_batch_pipeline_mode_maps_to_source_priority_source` above (which
# enforces existence) by adding per-member name-string fidelity.
# ---------------------------------------------------------------------------


def test_batch_yahoo_round_trip() -> None:
    """VIX 15m rolling 60d fallback route — Yahoo Finance free-tier intraday."""
    assert PipelineMode.BATCH_YAHOO.value == "batch_yahoo"
    assert pipeline_mode_for_source("yahoo") is PipelineMode.BATCH_YAHOO
    assert source_string_for(PipelineMode.BATCH_YAHOO) == "yahoo"


def test_batch_barchart_round_trip() -> None:
    """VIX 15m historical preload 2020-01-02 → 2025-11-12 per CLAUDE.md."""
    assert PipelineMode.BATCH_BARCHART.value == "batch_barchart"
    assert pipeline_mode_for_source("barchart") is PipelineMode.BATCH_BARCHART
    assert source_string_for(PipelineMode.BATCH_BARCHART) == "barchart"


def test_batch_footystats_round_trip() -> None:
    """Sports multi-source merge candidate — 1h cadence fallback to api_football."""
    assert PipelineMode.BATCH_FOOTYSTATS.value == "batch_footystats"
    assert pipeline_mode_for_source("footystats") is PipelineMode.BATCH_FOOTYSTATS
    assert source_string_for(PipelineMode.BATCH_FOOTYSTATS) == "footystats"


def test_batch_hyperliquid_round_trip() -> None:
    """DeFi perp_funding/solana_defi via Hyperliquid (vendor; REST transport is a
    column, never glued to the source name — operator R4 2026-06-07)."""
    assert PipelineMode.BATCH_HYPERLIQUID.value == "batch_hyperliquid"
    assert pipeline_mode_for_source("hyperliquid") is PipelineMode.BATCH_HYPERLIQUID
    assert source_string_for(PipelineMode.BATCH_HYPERLIQUID) == "hyperliquid"


def test_no_hyperliquid_rest_member_remains() -> None:
    """The transport-glued ``hyperliquid_rest`` antipattern is fully retired (R4):
    no PipelineMode value contains it, in any mode."""
    assert not any("hyperliquid_rest" in m.value for m in PipelineMode)


# ---------------------------------------------------------------------------
# C-TRANSPORT — transport axis (operator R4 2026-06-07): the [_{transport}] suffix
# appears in the pipeline_mode KEY only for >1-transport sources (none today); the
# transport COLUMN is always populated via default_transport_for_source.
# ---------------------------------------------------------------------------


def test_transport_enum_is_the_agreed_column_set() -> None:
    assert {t.value for t in Transport} == {"rest", "websocket", "flat_file"}


def test_transport_of_is_none_for_every_current_member() -> None:
    """No source runs >1 transport per shard today → no member carries a suffix →
    transport_of is None for all (the suffix-omitted-for-single-transport rule)."""
    for member in PipelineMode:
        assert transport_of(member) is None, f"{member.value} unexpectedly carries a transport suffix"


def test_transport_of_parses_a_synthetic_multi_transport_suffix() -> None:
    """When a >1-transport source DOES carry the suffix, source_string_for strips it
    to the VENDOR and the transport is recoverable (the suffix-present case)."""
    # _split_transport is the shared parser behind both source_string_for + transport_of.
    assert _split_transport("tardis_websocket") == ("tardis", "websocket")
    assert _split_transport("hyperliquid_rest") == ("hyperliquid", "rest")
    assert _split_transport("databento_flat_file") == ("databento", "flat_file")
    # A bare source (no transport token) → (source, None).
    assert _split_transport("hyperliquid") == ("hyperliquid", None)
    assert _split_transport("onchain_rpc") == ("onchain_rpc", None)


def test_default_transport_for_source_follows_the_ratified_matrix() -> None:
    """tardis batch = flat_file archive; every other batch source is REST-family."""
    assert default_transport_for_source("tardis") == "flat_file"
    assert default_transport_for_source("hyperliquid") == "rest"
    assert default_transport_for_source("databento") == "rest"
    assert default_transport_for_source("onchain_subgraph") == "rest"  # graphql→http→rest
    assert default_transport_for_source("pyth_hermes") == "rest"  # sse/rest→rest
    # Unknown source → safe REST default.
    assert default_transport_for_source("totally_new_vendor") == "rest"


def test_source_string_for_round_trips_with_transport_split() -> None:
    """Vendor round-trips for batch/live/replay even though source names contain
    underscores (onchain_rpc, polymarket_clob) — the split only strips a trailing
    transport token, which no current source name is."""
    assert source_string_for(PipelineMode.BATCH_HYPERLIQUID) == "hyperliquid"
    assert source_string_for(PipelineMode.LIVE_HYPERLIQUID) == "hyperliquid"
    assert source_string_for(PipelineMode.REPLAY_HYPERLIQUID) == "hyperliquid"
    assert source_string_for(PipelineMode.BATCH_ONCHAIN_RPC) == "onchain_rpc"
    assert source_string_for(PipelineMode.REPLAY_POLYMARKET_CLOB) == "polymarket_clob"


def test_hyperliquid_round_trips_all_three_modes() -> None:
    """The unified hyperliquid vendor round-trips batch + live + replay (one source,
    three capture modes) — transport lives in the column, not the source."""
    for mode in (Mode.BATCH, Mode.LIVE, Mode.REPLAY):
        member = pipeline_mode_for_source("hyperliquid", mode)
        assert member.value == f"{mode.value}_hyperliquid"
        assert source_string_for(member) == "hyperliquid"
        assert transport_of(member) is None


def test_batch_pyth_hermes_round_trip() -> None:
    """Solana on-chain price feeds via Hermes endpoint (Pyth-unbanned 2026-05-06)."""
    assert PipelineMode.BATCH_PYTH_HERMES.value == "batch_pyth_hermes"
    assert pipeline_mode_for_source("pyth_hermes") is PipelineMode.BATCH_PYTH_HERMES
    assert source_string_for(PipelineMode.BATCH_PYTH_HERMES) == "pyth_hermes"


def test_batch_chainlink_round_trip() -> None:
    """EVM on-chain oracle prices via Chainlink aggregator rounds."""
    assert PipelineMode.BATCH_CHAINLINK.value == "batch_chainlink"
    assert pipeline_mode_for_source("chainlink") is PipelineMode.BATCH_CHAINLINK
    assert source_string_for(PipelineMode.BATCH_CHAINLINK) == "chainlink"


def test_six_new_enum_members_present_in_pipeline_mode() -> None:
    """Phase 4.MTDS Q2=(A) extension landed all 6 new members atomically."""
    new_members = {
        PipelineMode.BATCH_YAHOO,
        PipelineMode.BATCH_BARCHART,
        PipelineMode.BATCH_FOOTYSTATS,
        PipelineMode.BATCH_HYPERLIQUID,
        PipelineMode.BATCH_PYTH_HERMES,
        PipelineMode.BATCH_CHAINLINK,
    }
    assert new_members.issubset(set(PipelineMode))


# ---------------------------------------------------------------------------
# pipeline_mode_for_sports_entity — workspace SSOT for sports_reference entities
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "entity,expected",
    [
        # API Football
        ("fixtures", PipelineMode.BATCH_API_FOOTBALL),
        ("injuries", PipelineMode.BATCH_API_FOOTBALL),
        ("fixture_stats", PipelineMode.BATCH_API_FOOTBALL),
        ("fixture_events", PipelineMode.BATCH_API_FOOTBALL),
        ("fixture_lineups", PipelineMode.BATCH_API_FOOTBALL),
        ("player_stats", PipelineMode.BATCH_API_FOOTBALL),
        ("teams", PipelineMode.BATCH_API_FOOTBALL),
        ("standings", PipelineMode.BATCH_API_FOOTBALL),
        # FootyStats
        ("footystats_predictions", PipelineMode.BATCH_FOOTYSTATS),
        ("footystats_matches", PipelineMode.BATCH_FOOTYSTATS),
        ("footystats_odds", PipelineMode.BATCH_ODDS_API),
        # Understat
        ("understat_xg", PipelineMode.BATCH_UNDERSTAT),
        ("understat_xg_shots", PipelineMode.BATCH_UNDERSTAT),
        # Transfermarkt
        ("player_values", PipelineMode.BATCH_TRANSFERMARKT),
        # SFI
        ("progressive_stats", PipelineMode.BATCH_SOCCER_FOOTBALL_INFO),
        # Open Meteo
        ("weather", PipelineMode.BATCH_OPEN_METEO),
    ],
)
def test_pipeline_mode_for_sports_entity_known(entity: str, expected: PipelineMode) -> None:
    """Each known entity maps to the correct PipelineMode — parity with IS _ENTITY_NAME_TO_PIPELINE_MODE."""
    assert pipeline_mode_for_sports_entity(entity) is expected


def test_pipeline_mode_for_sports_entity_unknown_fallback() -> None:
    """Unknown entity falls back to BATCH_INSTRUMENTS_SERVICE."""
    assert pipeline_mode_for_sports_entity("unknown_entity_xyz") is PipelineMode.BATCH_INSTRUMENTS_SERVICE


def test_pipeline_mode_for_sports_entity_case_insensitive() -> None:
    """Entity lookup is case-insensitive (normalises to lowercase)."""
    assert pipeline_mode_for_sports_entity("FIXTURES") is PipelineMode.BATCH_API_FOOTBALL
    assert pipeline_mode_for_sports_entity("Understat_XG") is PipelineMode.BATCH_UNDERSTAT


def test_pipeline_mode_for_sports_entity_closed_set_parity() -> None:
    """Every entry in _SPORTS_ENTITY_TO_PIPELINE_MODE is reachable via pipeline_mode_for_sports_entity."""
    for entity, expected_mode in _SPORTS_ENTITY_TO_PIPELINE_MODE.items():
        assert pipeline_mode_for_sports_entity(entity) is expected_mode, (
            f"Closed-set parity failed for entity {entity!r}: "
            f"got {pipeline_mode_for_sports_entity(entity)!r}, expected {expected_mode!r}"
        )


def test_pipeline_mode_for_sports_entity_exported_from_root() -> None:
    """pipeline_mode_for_sports_entity is importable from the UAC root facade."""
    from unified_api_contracts import pipeline_mode_for_sports_entity as root_fn

    assert root_fn is pipeline_mode_for_sports_entity
