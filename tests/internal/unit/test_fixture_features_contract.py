"""Unit tests for the `FixtureFeatures` per-fixture denormalisation contract.

Verifies:
- Public re-export paths (`unified_api_contracts.internal.FixtureFeatures`
  + `unified_api_contracts.internal.domain.features_sports.FixtureFeatures`).
- Every value-bearing column defaults to `None` (NULL propagation discipline).
- Model is frozen + rejects extra fields (drift protection).
- Round-trip via `model_dump` / `model_validate`.
- `weather_source` Literal enforcement.

SSOT: `unified-trading-pm/codex/02-data/sports-scheduling-and-sharding.md` §9.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal import FixtureFeatures as FixtureFeaturesFromInternal
from unified_api_contracts.internal.domain.features_sports import FixtureFeatures

_KICKOFF = datetime(2024, 9, 1, 15, 30, tzinfo=UTC)
_COMPUTED = datetime(2024, 9, 1, 15, 35, tzinfo=UTC)

_MIN_ROW = {
    "fixture_id": "1206417",
    "kickoff_utc": _KICKOFF,
    "league_id": "145",
    "home_team_id": "19045",
    "away_team_id": "5805",
    "feature_computed_at": _COMPUTED,
}


def test_both_public_import_paths_reach_same_class() -> None:
    assert FixtureFeatures is FixtureFeaturesFromInternal


def test_minimal_row_defaults_to_null_everywhere() -> None:
    row = FixtureFeatures(**_MIN_ROW)
    assert row.home_team_value_eur_as_of_kickoff is None
    assert row.away_team_value_eur_as_of_kickoff is None
    assert row.home_team_value_coverage_pct is None
    assert row.away_team_value_coverage_pct is None
    assert row.home_standing_pre is None
    assert row.away_standing_pre is None
    assert row.home_points_pre is None
    assert row.away_points_pre is None
    assert row.kickoff_temperature_c is None
    assert row.kickoff_precip_mm is None
    assert row.kickoff_wind_kph is None
    assert row.kickoff_humidity_pct is None
    assert row.kickoff_cloud_cover_pct is None
    assert row.kickoff_weather_code is None
    assert row.transfermarkt_values_partition_used is None
    assert row.standings_partition_used is None
    assert row.weather_source == "none"
    assert row.venue_id is None
    assert row.schema_version == 1
    assert row.feature_group == "fixture_features"


def test_model_is_frozen() -> None:
    row = FixtureFeatures(**_MIN_ROW)
    with pytest.raises(ValidationError):
        row.home_standing_pre = 1  # type: ignore[misc]


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        FixtureFeatures(**_MIN_ROW, bogus_column=42)


def test_weather_source_literal_enforced() -> None:
    for src in ("actual", "forecast_t0", "forecast_t24h", "none"):
        row = FixtureFeatures(**_MIN_ROW, weather_source=src)
        assert row.weather_source == src
    with pytest.raises(ValidationError):
        FixtureFeatures(**_MIN_ROW, weather_source="impossible")


def test_feature_group_literal_is_fixed() -> None:
    with pytest.raises(ValidationError):
        FixtureFeatures(**_MIN_ROW, feature_group="derived_features")


def test_fully_populated_row_round_trips() -> None:
    payload = {
        **_MIN_ROW,
        "venue_id": "DE_LEUNEN",
        "home_team_value_eur_as_of_kickoff": 123_456_789.0,
        "away_team_value_eur_as_of_kickoff": 55_000_000.0,
        "home_team_value_coverage_pct": 0.91,
        "away_team_value_coverage_pct": 0.85,
        "home_standing_pre": 1,
        "away_standing_pre": 14,
        "home_points_pre": 70,
        "away_points_pre": 28,
        "kickoff_temperature_c": 30.6,
        "kickoff_precip_mm": 0.0,
        "kickoff_wind_kph": 11.6,
        "kickoff_humidity_pct": 52.0,
        "kickoff_cloud_cover_pct": 47.0,
        "kickoff_weather_code": 1,
        "transfermarkt_values_partition_used": "day=2024-08-30",
        "standings_partition_used": "day=2024-08-31",
        "weather_source": "actual",
    }
    row = FixtureFeatures(**payload)
    dumped = row.model_dump()
    # Round-trip through JSON-compatible dict (datetime stays datetime).
    round_tripped = FixtureFeatures.model_validate(dumped)
    assert round_tripped == row


def test_coverage_pct_accepts_float_in_unit_interval() -> None:
    row = FixtureFeatures(
        **_MIN_ROW,
        home_team_value_coverage_pct=0.0,
        away_team_value_coverage_pct=1.0,
    )
    assert row.home_team_value_coverage_pct == 0.0
    assert row.away_team_value_coverage_pct == 1.0


def test_standing_accepts_int_only() -> None:
    with pytest.raises(ValidationError):
        FixtureFeatures(**_MIN_ROW, home_standing_pre="first")
