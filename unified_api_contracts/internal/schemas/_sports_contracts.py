"""SPORTS SchemaContracts — Families A (API-Football reference), C (Transfermarkt), D (SFI).

Family B (API-Football match-fact) lives in ``_sports_match_contracts``.
Family E (derived / other providers) lives in ``_sports_derived_contracts``.
Shared ColumnSpec helpers are in ``_sports_shared``.

This split keeps each module under the codex 900-line limit. All three
modules register into ``CONTRACT_REGISTRY`` as side-effects on import; the
parent ``contracts.py`` pulls them in at the bottom of that file. SSOT plan:
``plans/active/sports_uac_schema_contracts_registration_2026_04_24.plan``.

Column-name conventions (shared with Families B / E):

- API-Football parquets key IDs with the ``af_`` prefix (``af_fixture_id``,
  ``af_league_id``, ``af_home_id``, ``af_away_id``, ``af_winner_id``,
  ``af_home_name``, ``af_away_name``) to avoid collision with downstream
  canonical IDs.
- Nested API-Football structures (STANDINGS' ``team`` / ``all`` / ``home`` /
  ``away``) land in parquet as ``struct<...>`` columns. UAC's
  ``DtypeLiteral`` does not yet include ``struct``; we declare these as
  ``string`` and note the nested shape in the column description.
"""

from __future__ import annotations

from unified_api_contracts.internal.schemas._sports_shared import DATA_AVAILABLE_AT as _DATA_AVAILABLE_AT
from unified_api_contracts.internal.schemas.contracts import (
    CONTRACT_REGISTRY,
    ColumnSpec,
    SchemaContract,
)

# ============================================================================
# Family A — API-Football REFERENCE
# ============================================================================


SPORTS_LEAGUES = SchemaContract(
    asset_group="sports",
    instrument_type="reference",
    data_type="leagues",
    columns=[
        ColumnSpec(
            name="league_id",
            dtype="string",
            nullable=False,
            description=(
                "Canonical league identifier (UAC ``LeagueDefinition.league_id``, "
                "e.g. 'EPL', 'BUNDESLIGA', 'LA_LIGA'). Stable across providers; "
                "maps via ``get_provider_league_id()`` to each provider's native code."
            ),
        ),
        ColumnSpec(
            name="name",
            dtype="string",
            nullable=False,
            description="Human-readable league name (e.g. 'Premier League').",
        ),
        ColumnSpec(
            name="country",
            dtype="string",
            nullable=True,
            description="ISO country name of league jurisdiction (e.g. 'England').",
        ),
        ColumnSpec(
            name="league_type",
            dtype="string",
            nullable=True,
            description=(
                "League classification: 'domestic_top_flight', 'domestic_second', "
                "'international_club', 'international_country'. Sparse today."
            ),
        ),
        ColumnSpec(
            name="logo_url",
            dtype="string",
            nullable=True,
            description="HTTPS URL to league logo PNG; provider-hosted, used by UIs.",
        ),
    ],
    symbol_column="league_id",
    required_row_count_min=1,
)


SPORTS_TEAMS = SchemaContract(
    asset_group="sports",
    instrument_type="reference",
    data_type="teams",
    columns=[
        ColumnSpec(
            name="team_id",
            dtype="int64",
            nullable=False,
            description="API-Football numeric team ID — canonical row identifier.",
        ),
        ColumnSpec(
            name="team_name",
            dtype="string",
            nullable=False,
            description="Official team name as published by API-Football.",
        ),
        ColumnSpec(
            name="team_code",
            dtype="string",
            nullable=True,
            description="Short 3-letter team code (e.g. 'MUN') when available.",
        ),
        ColumnSpec(
            name="team_country",
            dtype="string",
            nullable=True,
            description="Club nationality (country registered) — distinct from venue country for internationals.",
        ),
        ColumnSpec(
            name="team_founded",
            dtype="float64",
            nullable=True,
            description="Year the club was founded; float because some rows are null and pandas promotes to float64.",
        ),
        ColumnSpec(
            name="team_national",
            dtype="bool",
            nullable=False,
            description="True for national teams, False for clubs.",
        ),
        ColumnSpec(
            name="team_logo",
            dtype="string",
            nullable=True,
            description="HTTPS URL to team crest PNG (provider-hosted).",
        ),
        ColumnSpec(
            name="venue_id",
            dtype="float64",
            nullable=True,
            description="API-Football home venue ID; float to allow nulls for teams without a venue.",
        ),
        ColumnSpec(
            name="venue_name",
            dtype="string",
            nullable=True,
            description="Home venue name (stadium).",
        ),
        ColumnSpec(
            name="venue_address",
            dtype="string",
            nullable=True,
            description="Street address of the home venue.",
        ),
        ColumnSpec(
            name="venue_city",
            dtype="string",
            nullable=True,
            description="City of the home venue.",
        ),
        ColumnSpec(
            name="venue_capacity",
            dtype="float64",
            nullable=True,
            description="Stated seating capacity of the home venue; float for null tolerance.",
        ),
        ColumnSpec(
            name="venue_surface",
            dtype="string",
            nullable=True,
            description="Pitch surface type: 'grass' | 'artificial' | 'hybrid'.",
        ),
        ColumnSpec(
            name="venue_image",
            dtype="string",
            nullable=True,
            description="HTTPS URL to a venue photograph (provider-hosted).",
        ),
        ColumnSpec(
            name="season",
            dtype="int64",
            nullable=False,
            description="Season year (e.g. 2024 for 2024-25 season) — added by orchestrator for provenance.",
        ),
        ColumnSpec(
            name="af_league_id",
            dtype="int64",
            nullable=False,
            description="API-Football numeric league ID this team row was fetched under.",
        ),
        ColumnSpec(
            name="data_available_at",
            dtype="string",
            nullable=True,
            description=(
                "Fetch timestamp; stored as string in TEAMS reference parquet "
                "(differs from fact tables where dtype is datetime64[ns, UTC])."
            ),
        ),
    ],
    symbol_column="team_id",
    required_row_count_min=1,
    # C.11 audit 2026-05-07: TEAMS rosters change per-season at most (transfer windows
    # are bounded events, not daily drift). Daily-cadence shards inflated the manifest
    # universe by ~830x for no signal. Per-season cadence: shard atom is
    # (asset_group=sports, source=api_football, data_type=teams, league_id, season,
    # fetch_day_when_changed) — orchestrator only emits on payload-fingerprint change
    # (Unit 2 of the C.11 migration). Data-status panel reads cadence to compute
    # per-season denominator (leagues x active_seasons).
    cadence="per_season",
)


SPORTS_VENUES = SchemaContract(
    asset_group="sports",
    instrument_type="reference",
    data_type="venues",
    columns=[
        ColumnSpec(
            name="id",
            dtype="int64",
            nullable=False,
            description="Internal venue PK — may duplicate venue_id for some writes.",
        ),
        ColumnSpec(
            name="venue_id",
            dtype="int64",
            nullable=False,
            description="API-Football numeric venue ID — canonical row identifier.",
        ),
        ColumnSpec(
            name="name",
            dtype="string",
            nullable=False,
            description="Official venue name (e.g. 'Old Trafford').",
        ),
        ColumnSpec(
            name="address",
            dtype="string",
            nullable=True,
            description="Street address of the venue.",
        ),
        ColumnSpec(
            name="city",
            dtype="string",
            nullable=True,
            description="City the venue is in.",
        ),
        ColumnSpec(
            name="country",
            dtype="string",
            nullable=True,
            description="Country of the venue.",
        ),
        ColumnSpec(
            name="capacity",
            dtype="int64",
            nullable=True,
            description="Stated seating capacity.",
        ),
        ColumnSpec(
            name="surface",
            dtype="string",
            nullable=True,
            description="Pitch surface: 'grass' | 'artificial' | 'hybrid'.",
        ),
        ColumnSpec(
            name="image",
            dtype="string",
            nullable=True,
            description="HTTPS URL to a venue photograph.",
        ),
        ColumnSpec(
            name="latitude",
            dtype="float64",
            nullable=True,
            description="Venue latitude (WGS84 decimal degrees) — used by OpenMeteo weather lookups.",
        ),
        ColumnSpec(
            name="longitude",
            dtype="float64",
            nullable=True,
            description="Venue longitude (WGS84 decimal degrees) — used by OpenMeteo weather lookups.",
        ),
        ColumnSpec(
            name="altitude",
            dtype="float64",
            nullable=True,
            description="Venue altitude in metres above sea level — influences ball flight / atmospheric features.",
        ),
        ColumnSpec(
            name="data_available_at",
            dtype="string",
            nullable=True,
            description="Fetch timestamp; stored as string in the static VENUES reference parquet.",
        ),
    ],
    symbol_column="venue_id",
    required_row_count_min=1,
    # C.11 audit 2026-05-07: VENUES is the OpenMeteo geo-enrichment overlay
    # (lat/lon/altitude per venue) — values change essentially never (a venue's
    # location is fixed). Currently writes 1/1 shard (correct). cadence=singleton
    # documents the intent; data-status panel expects exactly 1 shard regardless
    # of date range.
    cadence="singleton",
)


SPORTS_STANDINGS = SchemaContract(
    asset_group="sports",
    instrument_type="league",
    data_type="standings",
    columns=[
        ColumnSpec(
            name="rank",
            dtype="int64",
            nullable=False,
            description="Team's league-table position (1 = top).",
        ),
        # Team flat columns (was nested ``team`` struct pre-flatten 2026-05-13).
        ColumnSpec(
            name="team_id",
            dtype="int64",
            nullable=False,
            description="API-Football numeric team ID — row + join key.",
        ),
        ColumnSpec(
            name="team_name",
            dtype="string",
            nullable=False,
            description="Team display name from API-Football.",
        ),
        ColumnSpec(
            name="team_logo",
            dtype="string",
            nullable=True,
            description="HTTPS URL to team crest PNG (provider-hosted).",
        ),
        ColumnSpec(
            name="points",
            dtype="int64",
            nullable=False,
            description="Total league points accumulated so far in the season.",
        ),
        ColumnSpec(
            name="goals_diff",
            dtype="int64",
            nullable=False,
            description="Goal difference (goals-for minus goals-against). Renamed from camelcase goalsDiff 2026-05-13.",
        ),
        ColumnSpec(
            name="group",
            dtype="string",
            nullable=True,
            description="Group name for group-stage competitions (UCL, WC); null for round-robin leagues.",
        ),
        ColumnSpec(
            name="form",
            dtype="string",
            nullable=True,
            description="Recent-form streak string, e.g. 'WWDLW' — most-recent-first, 5 matches.",
        ),
        ColumnSpec(
            name="status",
            dtype="string",
            nullable=True,
            description="Standings status: 'same' | 'up' | 'down' — movement vs last snapshot.",
        ),
        ColumnSpec(
            name="description",
            dtype="string",
            nullable=True,
            description="Qualification / relegation annotation (e.g. 'Promotion - Champions League (Group Stage)').",
        ),
        # ``all`` flat columns — overall stats across home + away (was nested struct pre-flatten 2026-05-13).
        ColumnSpec(name="all_played", dtype="int64", nullable=True, description="Total matches played (home + away)."),
        ColumnSpec(name="all_win", dtype="int64", nullable=True, description="Total wins."),
        ColumnSpec(name="all_draw", dtype="int64", nullable=True, description="Total draws."),
        ColumnSpec(name="all_lose", dtype="int64", nullable=True, description="Total losses."),
        ColumnSpec(name="all_goals_for", dtype="int64", nullable=True, description="Total goals scored."),
        ColumnSpec(name="all_goals_against", dtype="int64", nullable=True, description="Total goals conceded."),
        # Home flat columns (was nested struct pre-flatten 2026-05-13).
        ColumnSpec(name="home_played", dtype="int64", nullable=True, description="Home matches played."),
        ColumnSpec(name="home_win", dtype="int64", nullable=True, description="Home wins."),
        ColumnSpec(name="home_draw", dtype="int64", nullable=True, description="Home draws."),
        ColumnSpec(name="home_lose", dtype="int64", nullable=True, description="Home losses."),
        ColumnSpec(name="home_goals_for", dtype="int64", nullable=True, description="Goals scored at home."),
        ColumnSpec(name="home_goals_against", dtype="int64", nullable=True, description="Goals conceded at home."),
        # Away flat columns (was nested struct pre-flatten 2026-05-13).
        ColumnSpec(name="away_played", dtype="int64", nullable=True, description="Away matches played."),
        ColumnSpec(name="away_win", dtype="int64", nullable=True, description="Away wins."),
        ColumnSpec(name="away_draw", dtype="int64", nullable=True, description="Away draws."),
        ColumnSpec(name="away_lose", dtype="int64", nullable=True, description="Away losses."),
        ColumnSpec(name="away_goals_for", dtype="int64", nullable=True, description="Goals scored away."),
        ColumnSpec(name="away_goals_against", dtype="int64", nullable=True, description="Goals conceded away."),
        ColumnSpec(
            name="update",
            dtype="string",
            nullable=True,
            description="API-Football's own update timestamp (ISO string) — distinct from data_available_at.",
        ),
        ColumnSpec(
            name="league_id",
            dtype="int64",
            nullable=False,
            description="API-Football numeric league ID — partition / join key.",
        ),
        ColumnSpec(
            name="season",
            dtype="int64",
            nullable=True,
            description="Season year (e.g. 2024 for 2024-25 season). Added 2026-05-13 — orchestrator stamps at write.",
        ),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="team_id",
    required_row_count_min=1,
)


# ============================================================================
# Family C — Transfermarkt
# ============================================================================


# SPORTS_TRANSFERMARKT_LEAGUES retired 2026-05-05 — was a static provider-
# catalog mapping; now lives in UAC TRANSFERMARKT_IDS as versioned config
# rather than as a captured GCS data type.


SPORTS_PLAYER_VALUES = SchemaContract(
    asset_group="sports",
    instrument_type="player",
    data_type="player_values",
    columns=[
        ColumnSpec(
            name="player_id",
            dtype="string",
            nullable=False,
            description=(
                "Transfermarkt player ID (e.g. 'p123456'). Row identifier — one row per "
                "(player_id, team_id, season, fetch_day)."
            ),
        ),
        ColumnSpec(
            name="player_name",
            dtype="string",
            nullable=True,
            description="Player full name as published by Transfermarkt.",
        ),
        ColumnSpec(
            name="position",
            dtype="string",
            nullable=True,
            description="Player position on field (e.g. 'CB', 'CM', 'ST'). Transfermarkt position codes.",
        ),
        ColumnSpec(
            name="age",
            dtype="int64",
            nullable=True,
            description="Player age in years at valuation snapshot date.",
        ),
        ColumnSpec(
            name="market_value_eur",
            dtype="float64",
            nullable=True,
            description=(
                "Estimated market value in EUR — Transfermarkt weekly valuation. Primary signal for squad analysis."
            ),
        ),
        ColumnSpec(
            name="contract_until",
            dtype="string",
            nullable=True,
            description="Contract expiry date as string (e.g. '2027-06-30'). Null if contract unknown/indefinite.",
        ),
        ColumnSpec(
            name="current_club_id",
            dtype="string",
            nullable=False,
            description="Transfermarkt club ID where player is employed (same as team_id for this snapshot).",
        ),
        ColumnSpec(
            name="nationality_iso",
            dtype="string",
            nullable=True,
            description="ISO 3166-1 country code or Transfermarkt nationality string.",
        ),
        ColumnSpec(
            name="team_id",
            dtype="string",
            nullable=False,
            description="Transfermarkt team/club ID — foreign key for team-level aggregation.",
        ),
        ColumnSpec(
            name="league_id",
            dtype="string",
            nullable=False,
            description="Canonical league_id (UAC) for this team at valuation time.",
        ),
        ColumnSpec(
            name="season",
            dtype="int64",
            nullable=False,
            description="Season year (e.g. 2024 for 2024-25 season). Added post-hoc by orchestrator at write time.",
        ),
    ],
    symbol_column="player_id",
    required_row_count_min=0,
)


# ============================================================================
# Family D — SFI (SoccerFootball Insights)
# ============================================================================


# SPORTS_SFI_LEAGUES retired 2026-05-05 — was a static provider-catalog
# mapping; now lives in UAC SOCCER_FOOTBALL_INFO_IDS as versioned config.


SPORTS_SFI_PROGRESSIVE_STATS = SchemaContract(
    asset_group="sports",
    instrument_type="match",
    data_type="sfi_progressive_stats",
    columns=[
        ColumnSpec(
            name="fixture_id",
            dtype="string",
            nullable=False,
            description=(
                "SFI fixture ID (not API-Football's). One row per progressive snapshot; "
                "use ``(fixture_id, timer_seconds)`` as composite join key."
            ),
        ),
        ColumnSpec(
            name="timer_seconds",
            dtype="int64",
            nullable=True,
            description="Seconds elapsed from match start to this snapshot; monotone across a fixture's rows.",
        ),
        ColumnSpec(
            name="team",
            dtype="string",
            nullable=True,
            description="'home' | 'away' — which team this team-side stat row pertains to.",
        ),
        ColumnSpec(name="goals", dtype="int64", nullable=True, description="Goals scored up to this timer snapshot."),
        ColumnSpec(
            name="possession_pct",
            dtype="float64",
            nullable=True,
            description="Ball possession % (0-100) at snapshot time.",
        ),
        ColumnSpec(
            name="dangerous_attacks",
            dtype="int64",
            nullable=True,
            description="SFI 'dangerous attack' count — proprietary definition, roughly attacks entering box.",
        ),
        ColumnSpec(
            name="attacks",
            dtype="int64",
            nullable=True,
            description="Total attacks count (superset of dangerous_attacks).",
        ),
        ColumnSpec(
            name="shots_on_target", dtype="int64", nullable=True, description="Shots on target at snapshot time."
        ),
        ColumnSpec(
            name="shots_off_target", dtype="int64", nullable=True, description="Shots off target at snapshot time."
        ),
        ColumnSpec(name="corners", dtype="int64", nullable=True, description="Corner kicks taken."),
        ColumnSpec(name="fouls", dtype="int64", nullable=True, description="Fouls committed."),
        ColumnSpec(name="yellow_cards", dtype="int64", nullable=True, description="Yellow cards received."),
        ColumnSpec(name="red_cards", dtype="int64", nullable=True, description="Red cards received."),
        ColumnSpec(name="substitutions", dtype="int64", nullable=True, description="Substitutions made."),
        ColumnSpec(
            name="dominance_pct",
            dtype="float64",
            nullable=True,
            description="SFI dominance index (0-100): composite of attacks/possession/location.",
        ),
        ColumnSpec(
            name="xg_home", dtype="float64", nullable=True, description="Accumulated expected goals for home team."
        ),
        ColumnSpec(
            name="xg_away", dtype="float64", nullable=True, description="Accumulated expected goals for away team."
        ),
        ColumnSpec(
            name="dominance_index_home",
            dtype="float64",
            nullable=True,
            description="Dominance index for home side at this snapshot.",
        ),
        ColumnSpec(
            name="dominance_index_away",
            dtype="float64",
            nullable=True,
            description="Dominance index for away side at this snapshot.",
        ),
        ColumnSpec(
            name="dominance_avg_home",
            dtype="float64",
            nullable=True,
            description="Rolling mean of home dominance across the match-to-date.",
        ),
        ColumnSpec(
            name="dominance_avg_away",
            dtype="float64",
            nullable=True,
            description="Rolling mean of away dominance across the match-to-date.",
        ),
        ColumnSpec(
            name="attacks_normal", dtype="int64", nullable=True, description="Home-side normal (non-dangerous) attacks."
        ),
        ColumnSpec(name="attacks_dangerous", dtype="int64", nullable=True, description="Home-side dangerous attacks."),
        ColumnSpec(name="attacks_normal_away", dtype="int64", nullable=True, description="Away-side normal attacks."),
        ColumnSpec(
            name="attacks_dangerous_away", dtype="int64", nullable=True, description="Away-side dangerous attacks."
        ),
        ColumnSpec(
            name="shoots_total",
            dtype="int64",
            nullable=True,
            description="Alias/typo variant of total shots; provider spelling preserved.",
        ),
        ColumnSpec(
            name="shoots_on_target", dtype="int64", nullable=True, description="Alias variant of shots_on_target."
        ),
        ColumnSpec(
            name="shoots_off_target", dtype="int64", nullable=True, description="Alias variant of shots_off_target."
        ),
        ColumnSpec(
            name="odds_1x2_home",
            dtype="float64",
            nullable=True,
            description="SFI 1X2 odds for home win at snapshot time.",
        ),
        ColumnSpec(name="odds_1x2_draw", dtype="float64", nullable=True, description="SFI 1X2 odds for draw."),
        ColumnSpec(name="odds_1x2_away", dtype="float64", nullable=True, description="SFI 1X2 odds for away win."),
        ColumnSpec(
            name="odds_ou_over",
            dtype="float64",
            nullable=True,
            description="Over/Under odds for total goals — over side.",
        ),
        ColumnSpec(name="odds_ou_under", dtype="float64", nullable=True, description="Over/Under odds — under side."),
        ColumnSpec(
            name="odds_ou_line", dtype="float64", nullable=True, description="O/U line (total-goals threshold)."
        ),
        ColumnSpec(name="odds_ah_home", dtype="float64", nullable=True, description="Asian handicap odds — home side."),
        ColumnSpec(name="odds_ah_away", dtype="float64", nullable=True, description="Asian handicap odds — away side."),
        ColumnSpec(
            name="odds_ah_line", dtype="float64", nullable=True, description="Asian handicap line (goal-spread)."
        ),
        ColumnSpec(
            name="odds_asian_corner_over",
            dtype="float64",
            nullable=True,
            description="Asian corners market — over side.",
        ),
        ColumnSpec(
            name="odds_asian_corner_under",
            dtype="float64",
            nullable=True,
            description="Asian corners market — under side.",
        ),
        ColumnSpec(
            name="odds_asian_corner_line", dtype="float64", nullable=True, description="Asian corners line threshold."
        ),
        ColumnSpec(
            name="ht_start_timer",
            dtype="int64",
            nullable=True,
            description="Halftime-start timer_seconds — stamped on snapshots taken during/after HT.",
        ),
        ColumnSpec(name="ht_end_timer", dtype="int64", nullable=True, description="Halftime-end timer_seconds."),
        ColumnSpec(
            name="ft_timer",
            dtype="int64",
            nullable=True,
            description=(
                "Final-time timer_seconds — the raw timer value from the last live snapshot "
                "before match freeze. Used to detect match completion via freeze-detection patterns."
            ),
        ),
        ColumnSpec(
            name="match_end_time",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description=(
                "Detected match end timestamp — the UTC time of the last snapshot where "
                "timer_seconds advanced. Freezing of timer_seconds is the canonical match-end signal. "
                "Computed post-hoc from kickoff + ft_timer."
            ),
        ),
        ColumnSpec(
            name="data_available_at",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description=(
                "UTC timestamp when this snapshot was captured — computed post-hoc from "
                "``kickoff + timer_seconds``. Nullable because pre-match snapshots "
                "(timer_seconds=0) may not have a stable kickoff reference."
            ),
        ),
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
)


# ============================================================================
# Registry side-effects (Families A, C, D only)
# ============================================================================

# Family A
CONTRACT_REGISTRY[("sports", "reference", "leagues")] = SPORTS_LEAGUES
CONTRACT_REGISTRY[("sports", "reference", "teams")] = SPORTS_TEAMS
CONTRACT_REGISTRY[("sports", "reference", "venues")] = SPORTS_VENUES
CONTRACT_REGISTRY[("sports", "league", "standings")] = SPORTS_STANDINGS
# Family C — TRANSFERMARKT_LEAGUES retired 2026-05-05 (catalog mapping in UAC).
CONTRACT_REGISTRY[("sports", "player", "player_values")] = SPORTS_PLAYER_VALUES
# Family D — SFI_LEAGUES retired 2026-05-05 (same reason).
CONTRACT_REGISTRY[("sports", "match", "sfi_progressive_stats")] = SPORTS_SFI_PROGRESSIVE_STATS


__all__ = [
    "SPORTS_LEAGUES",
    "SPORTS_PLAYER_VALUES",
    "SPORTS_SFI_PROGRESSIVE_STATS",
    "SPORTS_STANDINGS",
    "SPORTS_TEAMS",
    "SPORTS_VENUES",
]
