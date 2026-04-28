"""Tests to close coverage gaps and reach 99% coverage.

Covers the following modules that had 0% or low coverage:
- unified_api_contracts.internal/sports.py (TypedDicts)
- unified_api_contracts.internal/schema_definition.py
  (ColumnSchema, SchemaDefinition, SchemaValidationResult)

Note: this file was split. Additional coverage tests live in:
- test_coverage_gaps_features.py  (execution service sports, features_*)
- test_coverage_gaps_domain.py    (instruments, adapter_models, candle_schema, ml_inference,
                                   instrument_key, instrument_definition, ml, market_tick_data,
                                   websocket_lifecycle)
- test_coverage_gaps_strategy.py  (domain sports execution, strategy_service signal_vector)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unified_api_contracts.internal.schema_definition import SchemaDefinition

# ---------------------------------------------------------------------------
# sports.py — TypedDicts
# ---------------------------------------------------------------------------


class TestSportsTypedDicts:
    """Instantiate every TypedDict in sports.py to hit the module body."""

    def test_league_record(self) -> None:
        from unified_api_contracts.internal.sports import LeagueRecord

        rec: LeagueRecord = {
            "league_id": "PL",
            "name": "Premier League",
            "country": "England",
            "league_type": "league",
            "logo_url": None,
            "season": "2024",
        }
        assert rec["league_id"] == "PL"

    def test_team_record(self) -> None:
        from unified_api_contracts.internal.sports import TeamRecord

        rec: TeamRecord = {
            "team_id": "t1",
            "name": "Arsenal",
            "short_name": "ARS",
            "country": "England",
            "founded": 1886,
            "logo_url": None,
            "venue_id": "v1",
        }
        assert rec["name"] == "Arsenal"

    def test_venue_record(self) -> None:
        from unified_api_contracts.internal.sports import VenueRecord

        rec: VenueRecord = {
            "venue_id": "v1",
            "name": "Emirates Stadium",
            "city": "London",
            "country": "England",
            "capacity": 60260,
            "surface": "grass",
            "latitude": 51.5549,
            "longitude": -0.1084,
        }
        assert rec["capacity"] == 60260

    def test_player_record(self) -> None:
        from unified_api_contracts.internal.sports import PlayerRecord

        rec: PlayerRecord = {
            "player_id": "p1",
            "name": "Bukayo Saka",
            "first_name": "Bukayo",
            "last_name": "Saka",
            "nationality": "English",
            "position": "RW",
            "date_of_birth": "2001-09-05",
            "height_cm": 178,
            "weight_kg": 70,
            "team_id": "t1",
        }
        assert rec["player_id"] == "p1"

    def test_coach_record(self) -> None:
        from unified_api_contracts.internal.sports import CoachRecord

        rec: CoachRecord = {
            "coach_id": "c1",
            "name": "Mikel Arteta",
            "nationality": "Spanish",
            "team_id": "t1",
            "date_of_birth": "1982-03-26",
        }
        assert rec["coach_id"] == "c1"

    def test_referee_record(self) -> None:
        from unified_api_contracts.internal.sports import RefereeRecord

        rec: RefereeRecord = {
            "referee_id": "r1",
            "name": "Michael Oliver",
            "nationality": "English",
        }
        assert rec["name"] == "Michael Oliver"

    def test_fixture_record(self) -> None:
        from unified_api_contracts.internal.sports import FixtureRecord

        rec: FixtureRecord = {
            "fixture_id": "f1",
            "league_id": "PL",
            "season": "2024",
            "match_week": 1,
            "kickoff_utc": "2024-08-17T15:00:00Z",
            "status": "FT",
            "home_team_id": "t1",
            "away_team_id": "t2",
            "venue_id": "v1",
            "referee_id": "r1",
            "home_goals": 2,
            "away_goals": 1,
            "home_goals_halftime": 1,
            "away_goals_halftime": 0,
            "home_xg": 1.8,
            "away_xg": 0.9,
            "home_shots_on_target": 7,
            "away_shots_on_target": 3,
            "home_total_shots": 15,
            "away_total_shots": 9,
            "home_possession": 60,
            "away_possession": 40,
            "round_name": "Regular Season - 1",
        }
        assert rec["fixture_id"] == "f1"

    def test_fixture_stats_record(self) -> None:
        from unified_api_contracts.internal.sports import FixtureStatsRecord

        rec: FixtureStatsRecord = {
            "fixture_id": "f1",
            "team_id": "t1",
            "shots_on_target": 7,
            "shots_off_target": 4,
            "shots_total": 15,
            "shots_blocked": 2,
            "shots_inside_box": 10,
            "shots_outside_box": 5,
            "fouls": 12,
            "corners": 6,
            "offsides": 2,
            "possession_pct": 60,
            "yellow_cards": 1,
            "red_cards": 0,
            "goalkeeper_saves": 2,
            "passes_total": 450,
            "passes_accurate": 390,
            "passes_accuracy_pct": 87,
            "expected_goals": 1.8,
            "goals_prevented": 0.5,
        }
        assert rec["expected_goals"] == 1.8

    def test_fixture_events_record(self) -> None:
        from unified_api_contracts.internal.sports import FixtureEventsRecord

        rec: FixtureEventsRecord = {
            "fixture_id": "f1",
            "team_id": "t1",
            "player_id": "p1",
            "player_name": "Bukayo Saka",
            "minute": 23,
            "extra_time": None,
            "event_type": "goal",
            "detail": "Normal Goal",
            "comments": None,
        }
        assert rec["minute"] == 23

    def test_fixture_lineups_record(self) -> None:
        from unified_api_contracts.internal.sports import FixtureLineupsRecord

        rec: FixtureLineupsRecord = {
            "fixture_id": "f1",
            "team_id": "t1",
            "player_id": "p1",
            "player_name": "Bukayo Saka",
            "shirt_number": 7,
            "position": "RW",
            "grid_position": "4:3",
            "is_substitute": False,
            "formation": "4-3-3",
            "coach_name": "Mikel Arteta",
            "coach_id": "c1",
        }
        assert rec["is_substitute"] is False

    def test_fixture_player_stats_record(self) -> None:
        from unified_api_contracts.internal.sports import FixturePlayerStatsRecord

        rec: FixturePlayerStatsRecord = {
            "fixture_id": "f1",
            "team_id": "t1",
            "player_id": "p1",
            "player_name": "Bukayo Saka",
            "minutes_played": 90,
            "rating": 8.2,
            "is_captain": False,
            "is_substitute": False,
            "shots_total": 4,
            "shots_on_target": 3,
            "goals_total": 1,
            "goals_conceded": None,
            "assists": 1,
            "saves": None,
            "passes_total": 45,
            "passes_key": 3,
            "passes_accuracy": 88,
            "tackles_total": 2,
            "tackles_blocks": 1,
            "tackles_interceptions": 1,
            "duels_total": 8,
            "duels_won": 5,
            "dribbles_attempts": 4,
            "dribbles_success": 3,
            "dribbles_past": None,
            "fouls_drawn": 2,
            "fouls_committed": 1,
            "cards_yellow": 0,
            "cards_red": 0,
            "penalty_won": None,
            "penalty_committed": None,
            "penalty_scored": None,
            "penalty_missed": None,
            "penalty_saved": None,
        }
        assert rec["rating"] == 8.2

    def test_injury_record(self) -> None:
        from unified_api_contracts.internal.sports import InjuryRecord

        rec: InjuryRecord = {
            "fixture_id": "f1",
            "team_id": "t1",
            "player_id": "p1",
            "player_name": "Bukayo Saka",
            "reason": "Hamstring",
            "severity": "minor",
        }
        assert rec["reason"] == "Hamstring"

    def test_standings_record(self) -> None:
        from unified_api_contracts.internal.sports import StandingsRecord

        rec: StandingsRecord = {
            "league_id": "PL",
            "season": "2024",
            "team_id": "t1",
            "rank": 1,
            "points": 72,
            "goals_diff": 40,
            "form": "WWWWW",
            "played": 30,
            "won": 22,
            "drawn": 6,
            "lost": 2,
            "goals_for": 78,
            "goals_against": 38,
            "group": None,
            "description": "Champions League",
        }
        assert rec["rank"] == 1

    def test_round_record(self) -> None:
        from unified_api_contracts.internal.sports import RoundRecord

        rec: RoundRecord = {
            "league_id": "PL",
            "season": "2024",
            "round_name": "Regular Season - 1",
            "start_date": "2024-08-17",
            "end_date": "2024-08-19",
            "is_current": True,
        }
        assert rec["is_current"] is True

    def test_all_exports(self) -> None:
        import unified_api_contracts.internal.sports as m

        for name in m.__all__:
            assert hasattr(m, name), f"Missing export: {name}"


# ---------------------------------------------------------------------------
# schema_definition.py — ColumnSchema, SchemaDefinition, SchemaValidationResult
# ---------------------------------------------------------------------------


class TestColumnSchema:
    def test_defaults(self) -> None:
        from unified_api_contracts.internal.schema_definition import ColumnSchema

        col = ColumnSchema(name="foo", dtype="string")
        assert col.nullable is True
        assert col.nullable_overrides == {}
        assert col.description == ""
        assert col.applies_to is None

    def test_custom_values(self) -> None:
        from unified_api_contracts.internal.schema_definition import ColumnSchema

        col = ColumnSchema(
            name="bar",
            dtype="float64",
            nullable=False,
            nullable_overrides={"CEFI": True},
            description="A bar column",
            applies_to={"CEFI", "DEFI"},
        )
        assert col.nullable is False
        assert col.nullable_overrides == {"CEFI": True}
        assert col.applies_to == {"CEFI", "DEFI"}


class TestSchemaDefinition:
    def _make_schema(self) -> SchemaDefinition:
        from unified_api_contracts.internal.schema_definition import ColumnSchema, SchemaDefinition

        return SchemaDefinition(
            name="test_schema",
            columns=[
                ColumnSchema(name="ts", dtype="datetime64[ns]", nullable=False),
                ColumnSchema(
                    name="optional_cefi",
                    dtype="string",
                    nullable=True,
                    nullable_overrides={"CEFI": False},
                ),
                ColumnSchema(
                    name="compound_col",
                    dtype="string",
                    nullable=True,
                    nullable_overrides={"CEFI:BINANCE-FUTURES": False},
                ),
                ColumnSchema(
                    name="defi_only",
                    dtype="string",
                    nullable=True,
                    applies_to={"DEFI"},
                ),
            ],
            dimension_keys=["asset_group", "venue"],
        )

    def test_get_column_existing(self) -> None:
        schema = self._make_schema()
        from unified_api_contracts.internal.schema_definition import ColumnSchema

        col = schema.get_column("ts")
        assert isinstance(col, ColumnSchema)
        assert col.name == "ts"

    def test_get_column_missing_returns_none(self) -> None:
        schema = self._make_schema()
        assert schema.get_column("nonexistent") is None

    def test_is_nullable_unknown_column_returns_true(self) -> None:
        schema = self._make_schema()
        # Unknown column defaults to nullable=True
        assert schema.is_nullable("ghost", {"asset_group": "CEFI"}) is True

    def test_is_nullable_no_overrides(self) -> None:
        schema = self._make_schema()
        # ts is non-nullable by default, no overrides
        assert schema.is_nullable("ts", {"asset_group": "CEFI"}) is False

    def test_is_nullable_dimension_override_single(self) -> None:
        schema = self._make_schema()
        # optional_cefi: nullable=True but override CEFI=False
        assert schema.is_nullable("optional_cefi", {"asset_group": "CEFI"}) is False
        assert schema.is_nullable("optional_cefi", {"asset_group": "DEFI"}) is True

    def test_is_nullable_compound_key_override(self) -> None:
        schema = self._make_schema()
        # compound_col: nullable=True, override "CEFI:BINANCE-FUTURES"=False
        result = schema.is_nullable("compound_col", {"asset_group": "CEFI", "venue": "BINANCE-FUTURES"})
        assert result is False
        # With DEFI, compound key doesn't match, falls back to nullable=True
        result2 = schema.is_nullable("compound_col", {"asset_group": "DEFI"})
        assert result2 is True

    def test_is_nullable_empty_dimensions(self) -> None:
        schema = self._make_schema()
        # No matching dimensions → fall back to col.nullable
        assert schema.is_nullable("optional_cefi", {}) is True

    def test_is_nullable_individual_key_override_not_compound(self) -> None:
        """Hit line 117: individual dimension key matches override but compound key doesn't."""
        from unified_api_contracts.internal.schema_definition import ColumnSchema, SchemaDefinition

        # Schema with two dimension keys, override only for one individual value.
        # Pass BOTH dimension values so compound key = "CEFI:BINANCE" which is NOT in overrides.
        # But "CEFI" alone IS in overrides — should hit the for-key loop and return False.
        schema = SchemaDefinition(
            name="s",
            columns=[
                ColumnSchema(
                    name="col_a",
                    dtype="string",
                    nullable=True,
                    nullable_overrides={"CEFI": False},
                ),
            ],
            dimension_keys=["asset_group", "venue"],
        )
        # compound key = "CEFI:BINANCE" — not in nullable_overrides
        # for loop: category → "CEFI" → found in overrides → returns False (line 117)
        result = schema.is_nullable("col_a", {"asset_group": "CEFI", "venue": "BINANCE"})
        assert result is False

    def test_get_applicable_columns_no_applies_to(self) -> None:
        schema = self._make_schema()
        # All columns with applies_to=None + those matching dimensions
        cols = schema.get_applicable_columns({"asset_group": "CEFI"})
        names = [c.name for c in cols]
        # ts, optional_cefi, compound_col have applies_to=None
        assert "ts" in names
        assert "optional_cefi" in names

    def test_get_applicable_columns_with_applies_to(self) -> None:
        schema = self._make_schema()
        # defi_only applies to {"DEFI"} — should appear when category=DEFI
        cols_defi = schema.get_applicable_columns({"asset_group": "DEFI"})
        assert any(c.name == "defi_only" for c in cols_defi)
        # Should NOT appear when category=CEFI
        cols_cefi = schema.get_applicable_columns({"asset_group": "CEFI"})
        assert not any(c.name == "defi_only" for c in cols_cefi)

    def test_get_required_columns(self) -> None:
        schema = self._make_schema()
        required = schema.get_required_columns({"asset_group": "CEFI"})
        assert "ts" in required
        assert "optional_cefi" in required  # override: CEFI → not nullable

    def test_get_nullable_columns(self) -> None:
        schema = self._make_schema()
        nullable = schema.get_nullable_columns({"asset_group": "DEFI"})
        assert "optional_cefi" in nullable

    def test_get_column_dtypes(self) -> None:
        schema = self._make_schema()
        dtypes = schema.get_column_dtypes()
        assert dtypes["ts"] == "datetime64[ns]"
        assert "optional_cefi" in dtypes

    def test_to_dict_and_from_dict_roundtrip(self) -> None:
        from unified_api_contracts.internal.schema_definition import SchemaDefinition

        schema = self._make_schema()
        d = schema.to_dict()
        assert d["name"] == "test_schema"
        cols = d.get("columns") or []
        assert len(cols) > 0
        # applies_to should be serialized as list or None
        defi_col = next(c for c in cols if c["name"] == "defi_only")
        assert defi_col.get("applies_to") is not None

        # Roundtrip — to_dict() returns _RawSchema, from_dict() accepts _RawSchema
        schema2 = SchemaDefinition.from_dict(d)
        assert schema2.name == "test_schema"
        assert len(schema2.columns) == len(schema.columns)

    def test_from_dict_minimal(self) -> None:
        from unified_api_contracts.internal.schema_definition import SchemaDefinition

        # Construct minimal _RawSchema-compatible dict via keyword arguments
        schema = SchemaDefinition.from_dict({"name": "minimal", "columns": [{"name": "a", "dtype": "string"}]})
        assert schema.name == "minimal"
        assert schema.columns[0].name == "a"
        assert schema.columns[0].nullable is True
        assert schema.version == "1.0"
        assert schema.description == ""

    def test_version_and_description_defaults(self) -> None:
        from unified_api_contracts.internal.schema_definition import SchemaDefinition

        schema = SchemaDefinition(name="s", columns=[])
        assert schema.version == "1.0"
        assert schema.description == ""
        assert schema.dimension_keys == []


class TestSchemaValidationError:
    def test_str(self) -> None:
        from unified_api_contracts.internal.schema_definition import SchemaValidationError

        err = SchemaValidationError(column="foo", error_type="null", message="foo is null")
        assert str(err) == "foo is null"
        assert err.count == 0
        assert err.dimensions == {}

    def test_with_count_and_dimensions(self) -> None:
        from unified_api_contracts.internal.schema_definition import SchemaValidationError

        err = SchemaValidationError(
            column="bar",
            error_type="missing",
            message="bar missing",
            count=5,
            dimensions={"asset_group": "CEFI"},
        )
        assert err.count == 5
        assert err.dimensions["asset_group"] == "CEFI"


class TestSchemaValidationResult:
    def test_initial_state(self) -> None:
        from unified_api_contracts.internal.schema_definition import SchemaValidationResult

        result = SchemaValidationResult(valid=True, schema_name="test", dimensions={"asset_group": "CEFI"})
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.stats == {}

    def test_add_error_sets_invalid(self) -> None:
        from unified_api_contracts.internal.schema_definition import SchemaValidationResult

        result = SchemaValidationResult(valid=True, schema_name="s", dimensions={"asset_group": "X"})
        result.add_error("col1", "null", "col1 has null", count=3)
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].column == "col1"
        assert result.errors[0].count == 3

    def test_add_warning(self) -> None:
        from unified_api_contracts.internal.schema_definition import SchemaValidationResult

        result = SchemaValidationResult(valid=True)
        result.add_warning("something suspect")
        assert "something suspect" in result.warnings

    def test_get_error_summary_no_errors(self) -> None:
        from unified_api_contracts.internal.schema_definition import SchemaValidationResult

        result = SchemaValidationResult(valid=True)
        assert result.get_error_summary() == "No errors"

    def test_get_error_summary_with_errors(self) -> None:
        from unified_api_contracts.internal.schema_definition import SchemaValidationResult

        result = SchemaValidationResult(valid=True, schema_name="my_schema")
        result.add_error("col_a", "null", "col_a is null")
        summary = result.get_error_summary()
        assert "my_schema" in summary
        assert "col_a is null" in summary
