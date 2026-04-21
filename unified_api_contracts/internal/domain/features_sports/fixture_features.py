"""Per-fixture denormalised feature contract.

Output of `features-sports-service` fixture-features pipeline — one row per fixture
with the three-way as-of join of Transfermarkt player values, pre-match league
standings, and kickoff-hour weather. Distinct from the richer `SportsFeatureVector`
(20 mixins, hundreds of calculator-derived features): this contract captures ONLY
the raw-source denormalisations that are too expensive or too lookahead-sensitive
to recompute downstream.

Join contract:
    - Transfermarkt `PLAYER_VALUES`: `as_of_date <= kickoff_date` strict, aggregated
      to `home_team_value_eur_as_of_kickoff` / `away_team_value_eur_as_of_kickoff`
      via per-player asof lookup over the home/away lineup.
    - SFI/API-Football `STANDINGS`: pre-match table from `day=kickoff_date - 1 day`.
      Missing team in standings (promoted/relegated) -> NULL.
    - OpenMeteo `WEATHER`: venue-keyed kickoff-hour bucket already denormalised
      upstream by instruments-service (`actual_ko_*` for historical dates,
      `forecast_t0_ko_*` for forward-poll dates).

Missing raw inputs produce NULL columns — never zeros, never "latest available",
never a fallback to the current date. Every row also stamps which upstream shard
partition fed the join (`*_partition_used`) so downstream consumers can audit.

SSOT: `unified-trading-pm/codex/02-data/sports-scheduling-and-sharding.md` §9
denormalisation contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FixtureFeatures(BaseModel):
    """Per-fixture denormalised feature row.

    Produced by `features-sports-service` fixture-features pipeline. Every
    value-bearing column is `float | None` or `int | None` with NULL reserved
    for "raw input was absent" — downstream ML must treat NULL as missing and
    NEVER impute with zero / "latest available" / current-date proxies.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # --- Fixture identity ---------------------------------------------------
    fixture_id: str = Field(description="Canonical fixture identifier")
    kickoff_utc: datetime = Field(description="Fixture kickoff time (timezone-aware UTC)")
    league_id: str = Field(description="League identifier (provider-native)")
    home_team_id: str = Field(description="Home team identifier")
    away_team_id: str = Field(description="Away team identifier")
    venue_id: str | None = Field(
        default=None,
        description="Venue identifier; NULL when fixture has no assigned venue (neutral/TBD).",
    )

    # --- Transfermarkt: team-value asof -----------------------------------
    home_team_value_eur_as_of_kickoff: float | None = Field(
        default=None,
        description=(
            "Sum over home lineup of per-player Transfermarkt market value "
            "with `as_of_date <= kickoff_date` (strict). NULL when no player "
            "values were resolvable for the lineup."
        ),
    )
    away_team_value_eur_as_of_kickoff: float | None = Field(
        default=None,
        description="Same as home_team_value_eur_as_of_kickoff for the away team.",
    )
    home_team_value_coverage_pct: float | None = Field(
        default=None,
        description=(
            "Fraction [0.0, 1.0] of the home lineup for which a Transfermarkt "
            "asof value was found. NULL when lineup is empty / absent."
        ),
    )
    away_team_value_coverage_pct: float | None = Field(
        default=None,
        description="Same as home_team_value_coverage_pct for the away team.",
    )

    # --- Pre-match league standings ---------------------------------------
    home_standing_pre: int | None = Field(
        default=None,
        description=(
            "Home team position in the league table from `day=kickoff_date - 1`. "
            "NULL when team not in standings (e.g. promoted mid-season) or "
            "standings parquet absent."
        ),
    )
    away_standing_pre: int | None = Field(
        default=None,
        description="Same as home_standing_pre for the away team.",
    )
    home_points_pre: int | None = Field(
        default=None,
        description="Home team league points from `day=kickoff_date - 1`. NULL when absent.",
    )
    away_points_pre: int | None = Field(
        default=None,
        description="Same as home_points_pre for the away team.",
    )

    # --- Weather at kickoff hour ------------------------------------------
    kickoff_temperature_c: float | None = Field(
        default=None,
        description=(
            "Temperature in Celsius for the hourly bucket containing `kickoff_utc`. "
            "Historical dates use `actual_ko_temp` from OpenMeteo ERA5; forward-poll "
            "dates use `forecast_t0_ko_temp`. NULL when weather parquet absent."
        ),
    )
    kickoff_precip_mm: float | None = Field(
        default=None, description="Precipitation (mm) for the kickoff hour. NULL when absent."
    )
    kickoff_wind_kph: float | None = Field(
        default=None, description="Wind speed (km/h) for the kickoff hour. NULL when absent."
    )
    kickoff_humidity_pct: float | None = Field(
        default=None, description="Relative humidity (%) for the kickoff hour. NULL when absent."
    )
    kickoff_cloud_cover_pct: float | None = Field(
        default=None, description="Cloud cover (%) for the kickoff hour. NULL when absent."
    )
    kickoff_weather_code: int | None = Field(
        default=None,
        description="OpenMeteo weather code for the kickoff hour. NULL when absent.",
    )

    # --- Provenance -------------------------------------------------------
    transfermarkt_values_partition_used: str | None = Field(
        default=None,
        description=(
            "Source parquet partition day (`day=YYYY-MM-DD`) consumed by the "
            "Transfermarkt asof join. NULL when no partition matched the asof "
            "predicate for any lineup player."
        ),
    )
    standings_partition_used: str | None = Field(
        default=None,
        description=(
            "Source parquet partition day (`day=YYYY-MM-DD`) consumed for the "
            "pre-match standings join. NULL when no partition matched."
        ),
    )
    weather_source: Literal["actual", "forecast_t0", "forecast_t24h", "none"] = Field(
        default="none",
        description=(
            "Which column family fed the kickoff weather: `actual` (historical ERA5), "
            "`forecast_t0` (nowcast, same-day), `forecast_t24h` (T-24h forecast), "
            "or `none` (parquet absent)."
        ),
    )

    # --- Metadata ---------------------------------------------------------
    feature_computed_at: datetime = Field(description="UTC timestamp when features-sports-service computed this row.")
    schema_version: int = Field(default=1, description="FixtureFeatures schema revision.")
    feature_group: Literal["fixture_features"] = Field(default="fixture_features")


__all__ = ["FixtureFeatures"]
