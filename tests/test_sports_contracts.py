"""Parametrised tests for the 19 SPORTS SchemaContracts registered by
``unified_api_contracts.internal.schemas._sports_contracts``.

Covers the contract gap closed by
``plans/active/sports_uac_schema_contracts_registration_2026_04_24.md``.
Every sports data_type written to GCS must be resolvable via
``lookup_contract(asset_group, instrument_type, data_type)``.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.schemas._sports_contracts import (
    SPORTS_LEAGUES,
    SPORTS_PLAYER_VALUES,
    SPORTS_SFI_PROGRESSIVE_STATS,
    SPORTS_STANDINGS,
    SPORTS_TEAMS,
    SPORTS_VENUES,
)
from unified_api_contracts.internal.schemas._sports_derived_contracts import (
    SPORTS_FIXTURE_FEATURES,
    SPORTS_MATCHES,
    SPORTS_PREDICTIONS,
    SPORTS_WEATHER,
    SPORTS_XG,
)
from unified_api_contracts.internal.schemas._sports_match_contracts import (
    SPORTS_FIXTURE_EVENTS,
    SPORTS_FIXTURE_LINEUPS,
    SPORTS_FIXTURE_STATS,
    SPORTS_FIXTURES,
    SPORTS_INJURIES,
    SPORTS_PLAYER_STATS,
)
from unified_api_contracts.internal.schemas.contracts import (
    CONTRACT_REGISTRY,
    ColumnSpec,
    SchemaContract,
    lookup_contract,
)

# (asset_group, instrument_type, data_type, expected_contract, min_col_count).
SPORTS_CONTRACT_CASES: list[tuple[str, str, str, SchemaContract, int]] = [
    # Family A — API-Football reference
    ("sports", "reference", "leagues", SPORTS_LEAGUES, 5),
    ("sports", "reference", "teams", SPORTS_TEAMS, 17),
    ("sports", "reference", "venues", SPORTS_VENUES, 13),
    # STANDINGS: 14 → 32 per C.7 Follow-up #1 flatten (UAC@2026-05-13).
    ("sports", "league", "standings", SPORTS_STANDINGS, 32),
    # Family B — API-Football fact
    # FIXTURES: 32 → 33 per C.6 Step 1 match_end_time column (UAC@2026-05-13);
    # → 53 per fixture-schedule-split Phase 3 (+9 Q5 phase timestamps, +11 Q6
    # score-distinction columns). The assertion is a >= floor, so 33 still holds.
    ("sports", "match", "fixtures", SPORTS_FIXTURES, 33),
    ("sports", "match", "fixture_events", SPORTS_FIXTURE_EVENTS, 5),
    ("sports", "match", "fixture_stats", SPORTS_FIXTURE_STATS, 2),
    ("sports", "match", "fixture_lineups", SPORTS_FIXTURE_LINEUPS, 3),
    ("sports", "match", "player_stats", SPORTS_PLAYER_STATS, 38),
    ("sports", "match", "injuries", SPORTS_INJURIES, 5),
    # Family C — Transfermarkt (TRANSFERMARKT_LEAGUES retired 2026-05-05; mapping in UAC).
    # PLAYER_VALUES: 7 → 11 per C.4 per-player flatten (UAC@3b29f7e 2026-05-13).
    ("sports", "player", "player_values", SPORTS_PLAYER_VALUES, 11),
    # Family D — SFI (SFI_LEAGUES retired 2026-05-05; mapping in UAC).
    # SFI_PROGRESSIVE_STATS: 43 → 45 per C.6 Step 2 ft_timer + match_end_time (UAC@1848647 2026-05-13).
    ("sports", "match", "sfi_progressive_stats", SPORTS_SFI_PROGRESSIVE_STATS, 45),
    # Family E — Other / derived
    ("sports", "match", "matches", SPORTS_MATCHES, 58),
    ("sports", "match", "predictions", SPORTS_PREDICTIONS, 35),
    ("sports", "match", "xg", SPORTS_XG, 57),
    ("sports", "match", "weather", SPORTS_WEATHER, 72),
    ("sports", "feature", "fixture_features", SPORTS_FIXTURE_FEATURES, 28),
]


@pytest.mark.parametrize(
    ("asset_group", "instrument_type", "data_type", "expected", "min_cols"),
    SPORTS_CONTRACT_CASES,
    ids=[f"{c[0]}/{c[1]}/{c[2]}" for c in SPORTS_CONTRACT_CASES],
)
def test_sports_contract_registered(
    asset_group: str,
    instrument_type: str,
    data_type: str,
    expected: SchemaContract,
    min_cols: int,
) -> None:
    """Every sports contract is registered and resolvable via lookup_contract."""
    key = (asset_group, instrument_type, data_type)
    assert key in CONTRACT_REGISTRY, f"missing from CONTRACT_REGISTRY: {key}"
    resolved = lookup_contract(asset_group=asset_group, instrument_type=instrument_type, data_type=data_type)
    assert resolved is expected, f"CONTRACT_REGISTRY[{key}] is not the same object as the module-level constant"
    assert resolved.asset_group == asset_group
    assert resolved.instrument_type == instrument_type
    assert resolved.data_type == data_type
    assert len(resolved.columns) >= min_cols, f"{key} has {len(resolved.columns)} cols, expected >= {min_cols}"


@pytest.mark.parametrize(
    ("asset_group", "instrument_type", "data_type", "expected", "_min_cols"),
    SPORTS_CONTRACT_CASES,
    ids=[f"{c[0]}/{c[1]}/{c[2]}" for c in SPORTS_CONTRACT_CASES],
)
def test_sports_contract_symbol_column_is_declared(
    asset_group: str,
    instrument_type: str,
    data_type: str,
    expected: SchemaContract,
    _min_cols: int,
) -> None:
    """symbol_column must be an actual column in the contract."""
    column_names = {c.name for c in expected.columns}
    assert expected.symbol_column, f"{asset_group}/{instrument_type}/{data_type} missing symbol_column"
    assert expected.symbol_column in column_names, (
        f"symbol_column={expected.symbol_column!r} not found in columns {sorted(column_names)[:5]}..."
    )


@pytest.mark.parametrize(
    ("asset_group", "instrument_type", "data_type", "expected", "_min_cols"),
    SPORTS_CONTRACT_CASES,
    ids=[f"{c[0]}/{c[1]}/{c[2]}" for c in SPORTS_CONTRACT_CASES],
)
def test_sports_contract_columns_are_valid_column_specs(
    asset_group: str,
    instrument_type: str,
    data_type: str,
    expected: SchemaContract,
    _min_cols: int,
) -> None:
    """Every column is a ColumnSpec with a non-empty name and dtype."""
    assert asset_group, "parametrised sport shard asset_group"
    for col in expected.columns:
        assert isinstance(col, ColumnSpec), f"{data_type}: non-ColumnSpec column {col!r}"
        assert col.name, f"{data_type}: empty column name"
        assert col.dtype, f"{data_type}: empty dtype on column {col.name}"


def test_sports_contract_count_matches_registered() -> None:
    """Guard against accidental drift — every (asset_group, instrument_type,
    data_type) listed here must be present in the global registry, and the
    count should be deliberate. Originally 19 contracts; 17 after retiring
    TRANSFERMARKT_LEAGUES + SFI_LEAGUES on 2026-05-05 (provider-catalog
    mappings moved to UAC config rather than captured GCS data types).
    """
    keys_added_by_this_plan = {(c[0], c[1], c[2]) for c in SPORTS_CONTRACT_CASES}
    assert len(keys_added_by_this_plan) == 17
    for key in keys_added_by_this_plan:
        assert key in CONTRACT_REGISTRY, f"{key} expected in CONTRACT_REGISTRY"


def test_sports_fixtures_uses_af_fixture_id_as_symbol_column() -> None:
    """Anchor the af_ prefix convention — FIXTURES' canonical ID is af_fixture_id.

    Regression guard for the 2026-04-24 drilldown fix in deployment-api where the
    per-fixture breakdown endpoint was 400ing on ``fixture_id``. If this symbol
    ever flips back to ``fixture_id``, the drilldown schema-adaptive code still
    works but the contract should stay honest about the canonical column.
    """
    assert SPORTS_FIXTURES.symbol_column == "af_fixture_id"
    names = {c.name for c in SPORTS_FIXTURES.columns}
    assert "af_fixture_id" in names
    assert "af_league_id" in names
    assert "af_home_id" in names
    assert "af_away_id" in names


# ---------------------------------------------------------------------------
# Cadence field — refdata cadence SSOT (C.11 audit 2026-05-07).
# Drives the data-status panel's expected-denominator computation per
# (asset_group, data_type) shard. Refdata that only changes per-season
# (TEAMS) or essentially never (VENUES) MUST declare cadence so the panel
# doesn't denominator-inflate them across every date in the window.
# ---------------------------------------------------------------------------


def test_sports_teams_cadence_is_per_season() -> None:
    """C.11 audit: TEAMS rosters change per-season at most (transfer windows are
    bounded events, not daily drift). Daily-cadence shards inflated the manifest
    universe by ~830x for no signal. Marked ``cadence='per_season'`` so the
    data-status panel computes denominator = (leagues x active_seasons), not
    (leagues x days)."""
    assert SPORTS_TEAMS.cadence == "per_season"


def test_sports_venues_cadence_is_singleton() -> None:
    """C.11 audit: VENUES is the OpenMeteo geo-enrichment overlay (lat/lon/altitude
    per venue) — values change essentially never. Currently writes 1/1 shard;
    cadence='singleton' documents the intent so the data-status panel expects
    exactly 1 shard regardless of date range."""
    assert SPORTS_VENUES.cadence == "singleton"


def test_sports_fixtures_cadence_default_is_per_day() -> None:
    """Back-compat: contracts that don't declare cadence default to ``per_day``.
    SPORTS_FIXTURES is genuine time-series data (one shard per fixture date) —
    per_day is correct."""
    assert SPORTS_FIXTURES.cadence == "per_day"


def test_cadence_field_default_preserves_back_compat() -> None:
    """Adding the cadence field to SchemaContract MUST default to ``per_day`` so
    every existing contract that doesn't declare cadence keeps its current
    shard atom. The dozens of existing contracts (CeFi ohlcv_*, sports
    FIXTURES, defi swap_state, etc.) are all per-day-cadence by construction."""
    from unified_api_contracts.internal.schemas.contracts import SchemaContract

    minimal = SchemaContract(
        asset_group="cefi",
        instrument_type="reference",
        data_type="dummy_for_test",
        columns=[ColumnSpec(name="x", dtype="int64", nullable=False)],
        symbol_column="x",
    )
    assert minimal.cadence == "per_day"
