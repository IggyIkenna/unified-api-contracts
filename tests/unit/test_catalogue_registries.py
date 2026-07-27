"""Tests for the catalogue-plan P0.4-P0.6 registries.

- coverage_starts (per-asset-group venue → first-data-date map)
- DataTypeCapability (per-tuple live/batch + cutoffs)
- SchemaSpec (per-(asset_group, data_type) parquet column shape)
"""

from __future__ import annotations

from datetime import date

from unified_api_contracts.canonical.coverage_starts import (
    CEFI_SOURCE_COVERAGE_START,
    coverage_start,
)
from unified_api_contracts.canonical.gcs_paths import AssetGroup
from unified_api_contracts.registry.data_type_capability import (
    DATA_TYPE_CAPABILITY_REGISTRY,
    DataTypeCapability,
    capabilities_for_asset_group,
    find_capability,
)
from unified_api_contracts.registry.schema_spec import (
    SCHEMA_SPEC_REGISTRY,
    ColumnSpec,
    find_schema,
)

# ---------------------------------------------------------------------------
# Coverage starts
# ---------------------------------------------------------------------------


def test_cefi_seed_known_venues() -> None:
    """The CeFi venues we onboarded have measured (not venue-launch-date) coverage floors.

    Values corrected 2026-07-27 (coverage_floor_registries_no_cross_
    propagation_2026_07_17.md [DATA] P1) — the prior dates were unverified
    venue-launch-date guesses; see coverage_starts.py's own inline comments
    for the manifest-probe evidence per venue.
    """
    assert coverage_start(AssetGroup.CEFI, "BINANCE") == date(2020, 1, 1)
    assert coverage_start(AssetGroup.CEFI, "DERIBIT") == date(2019, 5, 8)
    assert coverage_start(AssetGroup.CEFI, "HYPERLIQUID") == date(2023, 4, 15)


def test_unknown_venue_returns_none() -> None:
    """Unknown venues return ``None`` — caller treats as no clip."""
    assert coverage_start(AssetGroup.CEFI, "FAKE_VENUE") is None
    assert coverage_start(AssetGroup.DEFI, "MADE_UP_PROTOCOL") is None


def test_sports_re_export_matches_canonical_ssot() -> None:
    """Sports coverage starts re-export the existing canonical SSOT."""
    from unified_api_contracts.canonical.coverage_starts import (
        SPORTS_SOURCE_COVERAGE_START,
    )
    from unified_api_contracts.canonical.domain.sports.league_data import SOURCE_COVERAGE_START

    assert SOURCE_COVERAGE_START == SPORTS_SOURCE_COVERAGE_START


def test_string_asset_group_accepted() -> None:
    assert coverage_start("cefi", "BINANCE") == date(2020, 1, 1)


def test_each_asset_group_has_at_least_one_seed() -> None:
    """Every asset group has at least one seeded coverage_start."""
    for ag in AssetGroup:
        # SPORTS uses lowercase source keys; check the registry has rows.
        any_key = next(iter(_assert_has_seed(ag)), None)
        assert any_key is not None, f"asset_group={ag} has no coverage_start seed"


def _assert_has_seed(ag: AssetGroup) -> list[str]:
    from unified_api_contracts.canonical.coverage_starts import (
        CEFI_SOURCE_COVERAGE_START,
        DEFI_SOURCE_COVERAGE_START,
        PREDICTION_SOURCE_COVERAGE_START,
        SPORTS_SOURCE_COVERAGE_START,
        TRADFI_SOURCE_COVERAGE_START,
    )

    table = {
        AssetGroup.CEFI: CEFI_SOURCE_COVERAGE_START,
        AssetGroup.DEFI: DEFI_SOURCE_COVERAGE_START,
        AssetGroup.TRADFI: TRADFI_SOURCE_COVERAGE_START,
        AssetGroup.PREDICTION: PREDICTION_SOURCE_COVERAGE_START,
        AssetGroup.SPORTS: SPORTS_SOURCE_COVERAGE_START,
    }
    return list(table[ag])


# ---------------------------------------------------------------------------
# DataTypeCapability
# ---------------------------------------------------------------------------


def test_capability_registry_non_empty_per_asset_group() -> None:
    """Every asset_group has at least one capability declaration."""
    for ag in AssetGroup:
        rows = capabilities_for_asset_group(ag)
        assert len(rows) > 0, f"asset_group={ag} has no DataTypeCapability rows"


def test_find_capability_exact_match() -> None:
    """Wire-format venue tokens (BINANCE-FUTURES not BINANCE) per 2026-04-30 split."""
    cap = find_capability(AssetGroup.CEFI, "trades", "BINANCE-FUTURES", "")
    assert cap is not None
    assert cap.live_capable is True
    assert cap.streaming_protocol == "ws"


def test_find_capability_instrument_type_optional() -> None:
    """Passing ``instrument_type=None`` matches the first row regardless."""
    cap = find_capability(AssetGroup.CEFI, "trades", "BINANCE-FUTURES")
    assert cap is not None
    assert cap.venue == "BINANCE-FUTURES"


def test_find_capability_returns_none_for_unknown() -> None:
    assert find_capability(AssetGroup.CEFI, "trades", "MADE_UP_VENUE") is None


def test_perpetual_liquidations_capability() -> None:
    """BINANCE-FUTURES perpetual liquidations is a known live-capable tuple."""
    cap = find_capability(AssetGroup.CEFI, "liquidations", "BINANCE-FUTURES", "perpetual")
    assert cap is not None
    assert cap.live_capable is True
    assert cap.streaming_protocol == "ws"


def test_capability_is_frozen_dataclass() -> None:
    cap = DATA_TYPE_CAPABILITY_REGISTRY[0]
    assert isinstance(cap, DataTypeCapability)
    # Frozen — can't mutate.
    try:
        cap.live_capable = False  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("DataTypeCapability should be frozen")


# ---------------------------------------------------------------------------
# SchemaSpec
# ---------------------------------------------------------------------------


def test_cefi_trades_schema_via_pydantic() -> None:
    """CeFi trades schema is reflected from CanonicalTrade."""
    spec = find_schema(AssetGroup.CEFI, "trades")
    assert spec is not None
    assert spec.source.startswith("pydantic:")
    col_names = {c.name for c in spec.columns}
    assert {"venue", "symbol", "price", "quantity", "timestamp"} <= col_names


def test_sports_fixtures_schema_manual() -> None:
    spec = find_schema(AssetGroup.SPORTS, "FIXTURES")
    assert spec is not None
    assert spec.source == "manual"
    col_names = {c.name for c in spec.columns}
    assert {"fixture_id", "league_id", "home_team_id", "away_team_id"} <= col_names


def test_defi_lending_indices_schema_manual() -> None:
    spec = find_schema(AssetGroup.DEFI, "lending_indices")
    assert spec is not None
    assert spec.source == "manual"
    col_names = {c.name for c in spec.columns}
    assert "instrument_id" in col_names
    assert "liquidity_index" in col_names


def test_unknown_schema_returns_none() -> None:
    assert find_schema(AssetGroup.CEFI, "imaginary_data_type") is None


def test_column_spec_is_frozen() -> None:
    col = ColumnSpec(name="x", dtype="int64")
    try:
        col.name = "y"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("ColumnSpec should be frozen")


def test_at_least_one_schema_per_asset_group() -> None:
    seen: set[AssetGroup] = set()
    for spec in SCHEMA_SPEC_REGISTRY:
        seen.add(spec.asset_group)
    for ag in AssetGroup:
        assert ag in seen, f"asset_group={ag} has no SchemaSpec"


# Force CEFI dict export to participate in test (lint coverage marker)
_ = CEFI_SOURCE_COVERAGE_START
