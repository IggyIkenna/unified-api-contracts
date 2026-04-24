"""SPORTS Family E — Derived / non-AF provider SchemaContracts.

Extracted from ``_sports_contracts.py`` to keep each module under the codex
900-line limit.

Contracts registered:

- MATCHES — FootyStats match facts (58 cols, many nullable on current adapter)
- PREDICTIONS — FootyStats pre-match prediction markets
- XG — Understat expected-goals fixture feed
- WEATHER — OpenMeteo per-venue per-day forecast + actual (72 cols)
- FIXTURE_FEATURES — features-sports-service derivative (denormalised
  Transfermarkt + standings + weather joined to a fixture)
"""

from __future__ import annotations

from unified_api_contracts.internal.schemas._sports_shared import (
    DATA_AVAILABLE_AT as _DATA_AVAILABLE_AT,
)
from unified_api_contracts.internal.schemas._sports_shared import (
    f64 as _f64,
)
from unified_api_contracts.internal.schemas._sports_shared import (
    i64 as _i64,
)
from unified_api_contracts.internal.schemas._sports_shared import (
    stringy as _stringy,
)
from unified_api_contracts.internal.schemas.contracts import (
    CONTRACT_REGISTRY,
    ColumnSpec,
    SchemaContract,
)

SPORTS_MATCHES = SchemaContract(
    category="sports",
    instrument_type="match",
    data_type="matches",
    columns=[
        _stringy("fixture_id", "FootyStats fixture ID — canonical row identifier.", nullable=False),
        _stringy("source_fixture_id", "Upstream source fixture ID when FootyStats ingests a third party (often null)."),
        _stringy("home_team_team_id", "FootyStats home team ID; underscored-repeated prefix is provider convention."),
        _stringy("home_team_name", "Home team name as published by FootyStats."),
        _stringy("home_team_short_name", "Home team short code (often null for FootyStats)."),
        _stringy("home_team_country", "Home team country (often null)."),
        _stringy("home_team_founded", "Home team founded year (often null)."),
        _stringy("home_team_logo_url", "Home team logo URL (often null)."),
        _stringy("home_team_venue", "Home team's declared venue name (often null)."),
        _stringy("away_team_team_id", "FootyStats away team ID."),
        _stringy("away_team_name", "Away team name."),
        _stringy("away_team_short_name", "Away team short code (often null)."),
        _stringy("away_team_country", "Away team country (often null)."),
        _stringy("away_team_founded", "Away team founded year (often null)."),
        _stringy("away_team_logo_url", "Away team logo URL (often null)."),
        _stringy("away_team_venue", "Away team's declared venue (often null)."),
        _stringy("league_league_id", "FootyStats league ID."),
        _stringy("league_name", "League name."),
        _stringy("league_country", "League country."),
        _stringy("league_league_type", "League type (often null)."),
        _stringy("league_logo_url", "League logo URL (often null)."),
        _stringy("kickoff_utc", "ISO UTC kickoff datetime; string-typed for provider fidelity."),
        _stringy("venue", "Venue name at the match (often null)."),
        _stringy("referee", "Match referee name (often null)."),
        _stringy("season", "Season label (e.g. '2023/2024')."),
        _stringy("match_week", "Matchweek / round within the season."),
        _stringy("source", "Provider slug: 'footystats' — identifies ingestion source."),
        _stringy("status", "Match status: 'complete' | 'scheduled' | 'cancelled' | 'postponed'."),
        _stringy("home_goals", "Final home goals (string; parse to int at read-time)."),
        _stringy("away_goals", "Final away goals (string)."),
        _stringy("home_goals_halftime", "Home goals at halftime (often null in FootyStats MATCHES)."),
        _stringy("away_goals_halftime", "Away goals at halftime (often null)."),
        _stringy("home_xg", "FootyStats home expected-goals (string)."),
        _stringy("away_xg", "FootyStats away expected-goals (string)."),
        _stringy("home_shots_on_target", "Home shots on target (often null in FootyStats MATCHES)."),
        _stringy("away_shots_on_target", "Away shots on target (often null)."),
        _stringy("home_total_shots", "Home total shots."),
        _stringy("away_total_shots", "Away total shots."),
        _stringy("home_possession", "Home possession % (0-100 as string)."),
        _stringy("away_possession", "Away possession %."),
        _stringy("home_corners", "Home corners."),
        _stringy("away_corners", "Away corners."),
        _stringy("home_fouls", "Home fouls committed (often null)."),
        _stringy("away_fouls", "Away fouls committed (often null)."),
        _stringy("home_yellow_cards", "Home yellow cards (often null)."),
        _stringy("away_yellow_cards", "Away yellow cards (often null)."),
        _stringy("home_red_cards", "Home red cards (often null)."),
        _stringy("away_red_cards", "Away red cards (often null)."),
        _stringy("home_shots_blocked", "Home shots blocked (often null)."),
        _stringy("away_shots_blocked", "Away shots blocked (often null)."),
        _stringy("home_offsides", "Home offsides (often null)."),
        _stringy("away_offsides", "Away offsides (often null)."),
        _stringy("home_passes_total", "Home total passes (often null)."),
        _stringy("away_passes_total", "Away total passes (often null)."),
        _stringy("home_passes_accuracy", "Home pass accuracy % (often null)."),
        _stringy("away_passes_accuracy", "Away pass accuracy % (often null)."),
        _stringy(
            "canonical_fixture_id",
            "Canonical fixture ID resolved via mapping to API-Football — join key across providers.",
        ),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
)


SPORTS_PREDICTIONS = SchemaContract(
    category="sports",
    instrument_type="match",
    data_type="predictions",
    columns=[
        _stringy("fixture_id", "FootyStats fixture ID — row identifier.", nullable=False),
        _stringy("source", "Provider slug: 'footystats'."),
        _stringy("kickoff_utc", "ISO UTC kickoff; string-typed."),
        _stringy("home_team", "Home team name."),
        _stringy("away_team", "Away team name."),
        _i64("btts_potential", "Both-teams-to-score market 'potential' % (0-100 integer)."),
        _f64("o25_potential", "Over-2.5-goals market potential (0-100)."),
        _f64("o35_potential", "Over-3.5-goals market potential."),
        _i64("o45_potential", "Over-4.5-goals market potential."),
        _f64("xg_prematch_home", "Pre-match home expected goals."),
        _f64("xg_prematch_away", "Pre-match away expected goals."),
        _i64("btts_fhg_potential", "BTTS first-half-goal potential."),
        _i64("btts_2hg_potential", "BTTS second-half-goal potential."),
        _i64("o05_potential", "Over-0.5 goals potential."),
        _i64("o15_potential", "Over-1.5 goals potential."),
        _i64("u05_potential", "Under-0.5 goals potential."),
        _i64("u15_potential", "Under-1.5 goals potential."),
        _i64("u25_potential", "Under-2.5 goals potential."),
        _i64("u35_potential", "Under-3.5 goals potential."),
        _i64("u45_potential", "Under-4.5 goals potential."),
        _f64("xg_prematch_total", "Total pre-match xG (home + away)."),
        _f64("pre_match_home_ppg", "Pre-match home points-per-game (recent form)."),
        _f64("pre_match_away_ppg", "Pre-match away points-per-game."),
        _stringy("pre_match_home_overall_ppg", "Pre-match home season-long PPG (often null)."),
        _stringy("pre_match_away_overall_ppg", "Pre-match away season-long PPG (often null)."),
        _f64("corners_potential", "Average corners potential."),
        _i64("corners_o85_potential", "Over-8.5 corners potential."),
        _i64("corners_o95_potential", "Over-9.5 corners potential."),
        _i64("corners_o105_potential", "Over-10.5 corners potential."),
        _f64("cards_potential", "Average cards potential."),
        _f64("offsides_potential", "Average offsides potential."),
        _f64("avg_potential", "Blended average-scoring potential."),
        _DATA_AVAILABLE_AT,
        ColumnSpec(
            name="fetched_at",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description=(
                "Timestamp when the adapter actually fetched the prediction (precedes data_available_at when batched)."
            ),
        ),
        _stringy("canonical_fixture_id", "Canonical fixture ID resolved via mapping — join key across providers."),
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
)


SPORTS_XG = SchemaContract(
    category="sports",
    instrument_type="match",
    data_type="xg",
    columns=[
        _stringy("fixture_id", "Understat fixture ID — row identifier.", nullable=False),
        _stringy("source_fixture_id", "Upstream source fixture ID (often null)."),
        _stringy("home_team_team_id", "Understat home team ID."),
        _stringy("home_team_name", "Home team name."),
        _stringy("home_team_short_name", "Home team short name."),
        _stringy("home_team_country", "Home team country (often null)."),
        _stringy("home_team_founded", "Home team founded year (often null)."),
        _stringy("home_team_logo_url", "Home team logo URL (often null)."),
        _stringy("home_team_venue", "Home team venue (often null)."),
        _stringy("away_team_team_id", "Understat away team ID."),
        _stringy("away_team_name", "Away team name."),
        _stringy("away_team_short_name", "Away team short name."),
        _stringy("away_team_country", "Away team country (often null)."),
        _stringy("away_team_founded", "Away team founded year (often null)."),
        _stringy("away_team_logo_url", "Away team logo URL (often null)."),
        _stringy("away_team_venue", "Away team venue (often null)."),
        _stringy("league_league_id", "Understat league ID."),
        _stringy("league_name", "League name."),
        _stringy("league_country", "League country."),
        _stringy("league_league_type", "League type (often null)."),
        _stringy("league_logo_url", "League logo URL (often null)."),
        _stringy("kickoff_utc", "ISO UTC kickoff (string)."),
        _stringy("venue", "Venue name (often null)."),
        _stringy("referee", "Referee name (often null)."),
        _stringy("season", "Season label (e.g. '2023')."),
        _stringy("match_week", "Matchweek (often null for Understat)."),
        _stringy("source", "Provider slug: 'understat'."),
        _stringy("status", "Match status (often null)."),
        _stringy("home_goals", "Home goals (string)."),
        _stringy("away_goals", "Away goals (string)."),
        _stringy("home_goals_halftime", "Home goals at halftime (often null)."),
        _stringy("away_goals_halftime", "Away goals at halftime (often null)."),
        _stringy("home_xg", "Understat home expected goals — the primary Understat signal."),
        _stringy("away_xg", "Understat away expected goals — the primary Understat signal."),
        _stringy("home_shots_on_target", "Home shots on target (often null)."),
        _stringy("away_shots_on_target", "Away shots on target (often null)."),
        _stringy("home_total_shots", "Home total shots (often null)."),
        _stringy("away_total_shots", "Away total shots (often null)."),
        _stringy("home_possession", "Home possession (often null)."),
        _stringy("away_possession", "Away possession (often null)."),
        _stringy("home_corners", "Home corners (often null)."),
        _stringy("away_corners", "Away corners (often null)."),
        _stringy("home_fouls", "Home fouls (often null)."),
        _stringy("away_fouls", "Away fouls (often null)."),
        _stringy("home_yellow_cards", "Home yellow cards (often null)."),
        _stringy("away_yellow_cards", "Away yellow cards (often null)."),
        _stringy("home_red_cards", "Home red cards (often null)."),
        _stringy("away_red_cards", "Away red cards (often null)."),
        _stringy("home_shots_blocked", "Home shots blocked (often null)."),
        _stringy("away_shots_blocked", "Away shots blocked (often null)."),
        _stringy("home_offsides", "Home offsides (often null)."),
        _stringy("away_offsides", "Away offsides (often null)."),
        _stringy("home_passes_total", "Home passes total (often null)."),
        _stringy("away_passes_total", "Away passes total (often null)."),
        _stringy("home_passes_accuracy", "Home pass accuracy (often null)."),
        _stringy("away_passes_accuracy", "Away pass accuracy (often null)."),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
)


SPORTS_WEATHER = SchemaContract(
    category="sports",
    instrument_type="match",
    data_type="weather",
    columns=[
        _stringy("venue_id", "API-Football venue_id (string) — join key back to VENUES.", nullable=False),
        _stringy("date", "Match date (``YYYY-MM-DD``, league-local).", nullable=False),
        _f64("latitude", "Venue latitude (WGS84); sourced from VENUES.", nullable=False),
        _f64("longitude", "Venue longitude (WGS84); sourced from VENUES.", nullable=False),
        _i64(
            "kickoff_hour", "Kickoff hour in UTC (0-23); used as the t=0 anchor for forecast_t0_* cols.", nullable=False
        ),
        # t24h forecast (as known 24h before kickoff)
        _f64("forecast_t24h_ko_temp", "24h-ahead forecast: temperature (°C) at kickoff hour."),
        _f64("forecast_t24h_ko_precip_mm", "24h-ahead forecast: precipitation (mm) at kickoff hour."),
        _f64("forecast_t24h_ko_wind_kmh", "24h-ahead forecast: wind speed (km/h) at kickoff hour."),
        _i64("forecast_t24h_ko_humidity_pct", "24h-ahead forecast: humidity (%) at kickoff hour."),
        _i64("forecast_t24h_ko_cloud_pct", "24h-ahead forecast: cloud cover (%) at kickoff hour."),
        _i64("forecast_t24h_ko_weather_code", "24h-ahead forecast: WMO weather code (0-99) at kickoff hour."),
        _f64("forecast_t24h_1h_temp", "24h-ahead forecast: temperature 1h after kickoff."),
        _f64("forecast_t24h_1h_precip_mm", "24h-ahead forecast: precipitation 1h after kickoff."),
        _f64("forecast_t24h_1h_wind_kmh", "24h-ahead forecast: wind speed 1h after kickoff."),
        _i64("forecast_t24h_1h_humidity_pct", "24h-ahead forecast: humidity 1h after kickoff."),
        _i64("forecast_t24h_1h_cloud_pct", "24h-ahead forecast: cloud cover 1h after kickoff."),
        _i64("forecast_t24h_1h_weather_code", "24h-ahead forecast: WMO code 1h after kickoff."),
        _f64("forecast_t24h_2h_temp", "24h-ahead forecast: temperature 2h after kickoff."),
        _f64("forecast_t24h_2h_precip_mm", "24h-ahead forecast: precipitation 2h after kickoff."),
        _f64("forecast_t24h_2h_wind_kmh", "24h-ahead forecast: wind speed 2h after kickoff."),
        _i64("forecast_t24h_2h_humidity_pct", "24h-ahead forecast: humidity 2h after kickoff."),
        _i64("forecast_t24h_2h_cloud_pct", "24h-ahead forecast: cloud cover 2h after kickoff."),
        _i64("forecast_t24h_2h_weather_code", "24h-ahead forecast: WMO code 2h after kickoff."),
        # t0 forecast (as known at kickoff — final pre-match forecast)
        _f64("forecast_t0_ko_temp", "t=kickoff forecast: temperature at kickoff hour (final pre-match)."),
        _f64("forecast_t0_ko_precip_mm", "t=kickoff forecast: precipitation at kickoff hour."),
        _f64("forecast_t0_ko_wind_kmh", "t=kickoff forecast: wind at kickoff hour."),
        _i64("forecast_t0_ko_humidity_pct", "t=kickoff forecast: humidity at kickoff hour."),
        _i64("forecast_t0_ko_cloud_pct", "t=kickoff forecast: cloud cover at kickoff hour."),
        _i64("forecast_t0_ko_weather_code", "t=kickoff forecast: WMO code at kickoff hour."),
        _f64("forecast_t0_1h_temp", "t=kickoff forecast: temp 1h after kickoff."),
        _f64("forecast_t0_1h_precip_mm", "t=kickoff forecast: precip 1h after kickoff."),
        _f64("forecast_t0_1h_wind_kmh", "t=kickoff forecast: wind 1h after kickoff."),
        _i64("forecast_t0_1h_humidity_pct", "t=kickoff forecast: humidity 1h after kickoff."),
        _i64("forecast_t0_1h_cloud_pct", "t=kickoff forecast: cloud 1h after kickoff."),
        _i64("forecast_t0_1h_weather_code", "t=kickoff forecast: WMO 1h after kickoff."),
        _f64("forecast_t0_2h_temp", "t=kickoff forecast: temp 2h after kickoff."),
        _f64("forecast_t0_2h_precip_mm", "t=kickoff forecast: precip 2h after kickoff."),
        _f64("forecast_t0_2h_wind_kmh", "t=kickoff forecast: wind 2h after kickoff."),
        _i64("forecast_t0_2h_humidity_pct", "t=kickoff forecast: humidity 2h after kickoff."),
        _i64("forecast_t0_2h_cloud_pct", "t=kickoff forecast: cloud 2h after kickoff."),
        _i64("forecast_t0_2h_weather_code", "t=kickoff forecast: WMO 2h after kickoff."),
        # Actual (historical re-analysis)
        _f64("actual_ko_temp", "Observed temperature (°C) at kickoff hour (OpenMeteo historical)."),
        _f64("actual_ko_precip_mm", "Observed precipitation at kickoff hour."),
        _f64("actual_ko_wind_kmh", "Observed wind at kickoff hour."),
        _i64("actual_ko_humidity_pct", "Observed humidity at kickoff hour."),
        _i64("actual_ko_cloud_pct", "Observed cloud cover at kickoff hour."),
        _i64("actual_ko_weather_code", "Observed WMO code at kickoff hour."),
        _f64("actual_1h_temp", "Observed temp 1h after kickoff."),
        _f64("actual_1h_precip_mm", "Observed precip 1h after kickoff."),
        _f64("actual_1h_wind_kmh", "Observed wind 1h after kickoff."),
        _i64("actual_1h_humidity_pct", "Observed humidity 1h after kickoff."),
        _i64("actual_1h_cloud_pct", "Observed cloud 1h after kickoff."),
        _i64("actual_1h_weather_code", "Observed WMO 1h after kickoff."),
        _f64("actual_2h_temp", "Observed temp 2h after kickoff."),
        _f64("actual_2h_precip_mm", "Observed precip 2h after kickoff."),
        _f64("actual_2h_wind_kmh", "Observed wind 2h after kickoff."),
        _i64("actual_2h_humidity_pct", "Observed humidity 2h after kickoff."),
        _i64("actual_2h_cloud_pct", "Observed cloud 2h after kickoff."),
        _i64("actual_2h_weather_code", "Observed WMO 2h after kickoff."),
        # Aggregates
        _f64("forecast_t24h_total_precip_mm", "24h-ahead forecast: total precip over kickoff + 2h window."),
        _i64("forecast_t24h_rain_hours", "24h-ahead forecast: hours with measurable rain."),
        _f64("forecast_t24h_wind_max_kmh", "24h-ahead forecast: max wind across kickoff + 2h window."),
        _f64("forecast_t24h_temp_range", "24h-ahead forecast: temperature range across kickoff + 2h window."),
        _f64("forecast_t0_total_precip_mm", "t=kickoff forecast: total precip over window."),
        _i64("forecast_t0_rain_hours", "t=kickoff forecast: rain hours."),
        _f64("forecast_t0_wind_max_kmh", "t=kickoff forecast: max wind."),
        _f64("forecast_t0_temp_range", "t=kickoff forecast: temp range."),
        _f64("actual_total_precip_mm", "Observed: total precip over window."),
        _i64("actual_rain_hours", "Observed: rain hours over window."),
        _f64("actual_wind_max_kmh", "Observed: max wind over window."),
        _f64("actual_temp_range", "Observed: temperature range over window."),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="venue_id",
    required_row_count_min=0,
)


SPORTS_FIXTURE_FEATURES = SchemaContract(
    category="sports",
    instrument_type="feature",
    data_type="fixture_features",
    columns=[
        ColumnSpec(
            name="fixture_id",
            dtype="string",
            nullable=False,
            description="Canonical fixture identifier — row key. Matches API-Football af_fixture_id (stringified).",
        ),
        ColumnSpec(
            name="kickoff_utc",
            dtype="datetime64[ns, UTC]",
            nullable=False,
            description="Fixture kickoff time in UTC.",
        ),
        ColumnSpec(
            name="league_id", dtype="string", nullable=True, description="Canonical UAC league_id (e.g. 'EPL')."
        ),
        ColumnSpec(
            name="home_team_id",
            dtype="string",
            nullable=False,
            description="Canonical home-team ID (e.g. 'MAN_CITY') — required for team-level denormalisation.",
        ),
        ColumnSpec(
            name="away_team_id", dtype="string", nullable=False, description="Canonical away-team ID — required."
        ),
        ColumnSpec(
            name="venue_id",
            dtype="string",
            nullable=True,
            description="API-Football venue_id (string); used for weather lookup.",
        ),
        ColumnSpec(
            name="home_team_value_eur_as_of_kickoff",
            dtype="float64",
            nullable=True,
            description="Home squad total market value in EUR at as-of-date (Transfermarkt). Null when lookup misses.",
        ),
        ColumnSpec(
            name="away_team_value_eur_as_of_kickoff",
            dtype="float64",
            nullable=True,
            description="Away squad total market value in EUR at as-of-date.",
        ),
        ColumnSpec(
            name="home_team_value_coverage_pct",
            dtype="float64",
            nullable=True,
            description="Home squad valuation coverage (% of players with values) at as-of-date.",
        ),
        ColumnSpec(
            name="away_team_value_coverage_pct",
            dtype="float64",
            nullable=True,
            description="Away squad valuation coverage.",
        ),
        ColumnSpec(
            name="home_standing_pre",
            dtype="int64",
            nullable=True,
            description="Home team's league position on D-1 (from pre_match_standings).",
        ),
        ColumnSpec(
            name="away_standing_pre", dtype="int64", nullable=True, description="Away team's league position on D-1."
        ),
        ColumnSpec(
            name="home_points_pre", dtype="int64", nullable=True, description="Home team's league points on D-1."
        ),
        ColumnSpec(
            name="away_points_pre", dtype="int64", nullable=True, description="Away team's league points on D-1."
        ),
        ColumnSpec(
            name="kickoff_temperature_c",
            dtype="float64",
            nullable=True,
            description=(
                "Temperature (°C) at kickoff hour — selected from WEATHER with "
                "precedence 'actual' > 'forecast_t0' > 'forecast_t24h'."
            ),
        ),
        ColumnSpec(
            name="kickoff_precip_mm",
            dtype="float64",
            nullable=True,
            description="Precipitation (mm) at kickoff hour — same precedence as temperature.",
        ),
        ColumnSpec(
            name="kickoff_wind_kph", dtype="float64", nullable=True, description="Wind speed (km/h) at kickoff hour."
        ),
        ColumnSpec(
            name="kickoff_humidity_pct", dtype="float64", nullable=True, description="Humidity (%) at kickoff hour."
        ),
        ColumnSpec(
            name="kickoff_cloud_cover_pct",
            dtype="float64",
            nullable=True,
            description="Cloud cover (%) at kickoff hour.",
        ),
        ColumnSpec(
            name="kickoff_weather_code",
            dtype="int64",
            nullable=True,
            description="WMO weather code (0-99) at kickoff hour.",
        ),
        ColumnSpec(
            name="transfermarkt_values_partition_used",
            dtype="string",
            nullable=True,
            description="GCS partition identifier for the Transfermarkt values source used (provenance).",
        ),
        ColumnSpec(
            name="standings_partition_used",
            dtype="string",
            nullable=True,
            description="GCS partition identifier for pre_match_standings source (provenance).",
        ),
        ColumnSpec(
            name="weather_source",
            dtype="string",
            nullable=True,
            description="Which weather variant was used: 'actual' | 'forecast_t0' | 'forecast_t24h' | 'none'.",
        ),
        ColumnSpec(
            name="feature_computed_at",
            dtype="datetime64[ns, UTC]",
            nullable=False,
            description="Timestamp when this feature row was computed (UTC).",
        ),
        ColumnSpec(
            name="schema_version",
            dtype="string",
            nullable=True,
            description="Feature schema version (from FixtureFeatures.schema_version).",
        ),
        ColumnSpec(
            name="feature_group",
            dtype="string",
            nullable=True,
            description="Feature-group label (e.g. 'fixture_features' | 'pre_match_context').",
        ),
        ColumnSpec(
            name="date",
            dtype="string",
            nullable=True,
            description="Batch/export date (YYYY-MM-DD) — added post-hoc by writer for partitioning.",
        ),
        ColumnSpec(
            name="timestamp",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description="Export/write timestamp — added post-hoc for lineage.",
        ),
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
)


# ============================================================================
# Registry side-effects
# ============================================================================

CONTRACT_REGISTRY[("sports", "match", "matches")] = SPORTS_MATCHES
CONTRACT_REGISTRY[("sports", "match", "predictions")] = SPORTS_PREDICTIONS
CONTRACT_REGISTRY[("sports", "match", "xg")] = SPORTS_XG
CONTRACT_REGISTRY[("sports", "match", "weather")] = SPORTS_WEATHER
CONTRACT_REGISTRY[("sports", "feature", "fixture_features")] = SPORTS_FIXTURE_FEATURES


__all__ = [
    "SPORTS_FIXTURE_FEATURES",
    "SPORTS_MATCHES",
    "SPORTS_PREDICTIONS",
    "SPORTS_WEATHER",
    "SPORTS_XG",
]
