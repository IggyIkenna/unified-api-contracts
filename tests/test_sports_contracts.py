"""Parametrised tests for the 19 SPORTS SchemaContracts registered by
``unified_api_contracts.internal.schemas._sports_contracts``.

Covers the contract gap closed by
``plans/active/sports_uac_schema_contracts_registration_2026_04_24.plan.md``.
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
    ("sports", "league", "standings", SPORTS_STANDINGS, 14),
    # Family B — API-Football fact
    ("sports", "match", "fixtures", SPORTS_FIXTURES, 32),
    ("sports", "match", "fixture_events", SPORTS_FIXTURE_EVENTS, 5),
    ("sports", "match", "fixture_stats", SPORTS_FIXTURE_STATS, 2),
    ("sports", "match", "fixture_lineups", SPORTS_FIXTURE_LINEUPS, 3),
    ("sports", "match", "player_stats", SPORTS_PLAYER_STATS, 38),
    ("sports", "match", "injuries", SPORTS_INJURIES, 5),
    # Family C — Transfermarkt (TRANSFERMARKT_LEAGUES retired 2026-05-05; mapping in UAC).
    ("sports", "player", "player_values", SPORTS_PLAYER_VALUES, 7),
    # Family D — SFI (SFI_LEAGUES retired 2026-05-05; mapping in UAC).
    ("sports", "match", "sfi_progressive_stats", SPORTS_SFI_PROGRESSIVE_STATS, 43),
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
