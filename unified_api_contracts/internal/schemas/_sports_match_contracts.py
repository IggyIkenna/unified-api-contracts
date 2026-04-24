"""SPORTS Family B — API-Football match-fact SchemaContracts.

Extracted from ``_sports_contracts.py`` to keep each module under the
codex 900-line limit. See SSOT plan:
``plans/active/sports_uac_schema_contracts_registration_2026_04_24.plan.md``.

Contracts registered:

- FIXTURES — master fixtures parquet (``af_`` prefixed IDs)
- FIXTURE_EVENTS — per-fixture goal / card / sub events
- FIXTURE_STATS — per-fixture team-level stats (currently minimal on disk)
- FIXTURE_LINEUPS — per-fixture team formations
- PLAYER_STATS — per-fixture per-player stats
- INJURIES — daily injury report (nested structs serialised as string)
"""

from __future__ import annotations

from unified_api_contracts.internal.schemas._sports_shared import DATA_AVAILABLE_AT as _DATA_AVAILABLE_AT
from unified_api_contracts.internal.schemas.contracts import (
    CONTRACT_REGISTRY,
    ColumnSpec,
    SchemaContract,
)

# ============================================================================
# Family B — API-Football FACT
# ============================================================================


SPORTS_FIXTURES = SchemaContract(
    category="sports",
    instrument_type="match",
    data_type="fixtures",
    columns=[
        ColumnSpec(
            name="af_fixture_id",
            dtype="int64",
            nullable=False,
            description="API-Football numeric fixture ID — canonical row identifier.",
        ),
        ColumnSpec(
            name="referee_name",
            dtype="string",
            nullable=True,
            description="Match referee's name; null when not assigned.",
        ),
        ColumnSpec(
            name="date",
            dtype="string",
            nullable=False,
            description="Kickoff date (ISO ``YYYY-MM-DD`` in league local timezone).",
        ),
        ColumnSpec(
            name="timestamp",
            dtype="string",
            nullable=False,
            description="Kickoff ISO datetime (UTC); string-typed on disk for provider round-trip fidelity.",
        ),
        ColumnSpec(
            name="periods_first",
            dtype="string",
            nullable=True,
            description="First-half start epoch (seconds as string); null pre-match.",
        ),
        ColumnSpec(
            name="periods_second",
            dtype="string",
            nullable=True,
            description="Second-half start epoch (seconds as string); null pre-match.",
        ),
        ColumnSpec(
            name="venue_id",
            dtype="float64",
            nullable=True,
            description="API-Football numeric venue ID for this match; float to allow nulls.",
        ),
        ColumnSpec(
            name="venue_name",
            dtype="string",
            nullable=True,
            description="Venue name for this match (may differ from home team's declared venue).",
        ),
        ColumnSpec(
            name="venue_city",
            dtype="string",
            nullable=True,
            description="City of the venue.",
        ),
        ColumnSpec(
            name="status_long",
            dtype="string",
            nullable=False,
            description="Human status label (e.g. 'Match Finished', 'Not Started', 'In Play').",
        ),
        ColumnSpec(
            name="status_short",
            dtype="string",
            nullable=False,
            description="API-Football status code: 'NS' | 'FT' | 'AET' | 'PEN' | 'HT' | 'LIVE' | 'PST' | 'CANC' | …",
        ),
        ColumnSpec(
            name="status_elapsed_time",
            dtype="float64",
            nullable=True,
            description="Minutes elapsed in live match (0-90 regulation, 90-120 ET); null pre-match and post-match.",
        ),
        ColumnSpec(
            name="af_league_id",
            dtype="int64",
            nullable=False,
            description="API-Football numeric league ID this fixture belongs to.",
        ),
        ColumnSpec(
            name="season",
            dtype="int64",
            nullable=False,
            description="Season year (e.g. 2024 for 2024-25 season).",
        ),
        ColumnSpec(
            name="round",
            dtype="string",
            nullable=False,
            description="Round / matchday label (e.g. 'Regular Season - 28', 'Round of 16').",
        ),
        ColumnSpec(
            name="af_home_id",
            dtype="int64",
            nullable=False,
            description="API-Football numeric ID of the home team.",
        ),
        ColumnSpec(
            name="af_away_id",
            dtype="int64",
            nullable=False,
            description="API-Football numeric ID of the away team.",
        ),
        ColumnSpec(
            name="af_winner_id",
            dtype="float64",
            nullable=True,
            description="API-Football team ID of the winner; null for draws and unplayed matches.",
        ),
        ColumnSpec(
            name="af_home_name",
            dtype="string",
            nullable=False,
            description="Home team name as published by API-Football.",
        ),
        ColumnSpec(
            name="af_away_name",
            dtype="string",
            nullable=False,
            description="Away team name as published by API-Football.",
        ),
        ColumnSpec(
            name="home_score",
            dtype="float64",
            nullable=True,
            description="Final home goals; null pre-match. Mirror aggregate across all phases.",
        ),
        ColumnSpec(
            name="away_score",
            dtype="float64",
            nullable=True,
            description="Final away goals; null pre-match.",
        ),
        ColumnSpec(
            name="home_score_halftime",
            dtype="float64",
            nullable=True,
            description="Home goals at halftime.",
        ),
        ColumnSpec(
            name="away_score_halftime",
            dtype="float64",
            nullable=True,
            description="Away goals at halftime.",
        ),
        ColumnSpec(
            name="home_score_fulltime",
            dtype="float64",
            nullable=True,
            description="Home goals at fulltime (90 min) — equals home_score unless match went to ET/pens.",
        ),
        ColumnSpec(
            name="away_score_fulltime",
            dtype="float64",
            nullable=True,
            description="Away goals at fulltime (90 min).",
        ),
        ColumnSpec(
            name="home_score_extratime",
            dtype="float64",
            nullable=True,
            description="Home goals at end of extra time; null if ET not played.",
        ),
        ColumnSpec(
            name="away_score_extratime",
            dtype="float64",
            nullable=True,
            description="Away goals at end of extra time.",
        ),
        ColumnSpec(
            name="home_score_penalty",
            dtype="float64",
            nullable=True,
            description="Home penalty-shootout goals; null if no shootout.",
        ),
        ColumnSpec(
            name="away_score_penalty",
            dtype="float64",
            nullable=True,
            description="Away penalty-shootout goals.",
        ),
        ColumnSpec(
            name="day",
            dtype="string",
            nullable=False,
            description="Partition date (``YYYY-MM-DD``) — matches GCS ``day=`` partition value.",
        ),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="af_fixture_id",
    required_row_count_min=1,
)


SPORTS_FIXTURE_EVENTS = SchemaContract(
    category="sports",
    instrument_type="match",
    data_type="fixture_events",
    columns=[
        ColumnSpec(
            name="type",
            dtype="string",
            nullable=False,
            description="Event category: 'Goal' | 'Card' | 'subst' | 'Var'. API-Football top-level ``type``.",
        ),
        ColumnSpec(
            name="detail",
            dtype="string",
            nullable=True,
            description=(
                "Event sub-type (e.g. 'Normal Goal', 'Penalty', 'Yellow Card', "
                "'Substitution 1'). Pairs with ``type`` for full event classification."
            ),
        ),
        ColumnSpec(
            name="comments",
            dtype="string",
            nullable=True,
            description="Free-text VAR / referee commentary; null for routine events.",
        ),
        ColumnSpec(
            name="fixture_id",
            dtype="string",
            nullable=False,
            description=(
                "Stringified ``af_fixture_id`` — note: FIXTURE_EVENTS uses the legacy "
                "``fixture_id`` column name (not ``af_fixture_id``). Join key back to FIXTURES."
            ),
        ),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
)


SPORTS_FIXTURE_STATS = SchemaContract(
    category="sports",
    instrument_type="match",
    data_type="fixture_stats",
    columns=[
        ColumnSpec(
            name="fixture_id",
            dtype="string",
            nullable=False,
            description="Stringified ``af_fixture_id`` — join key back to FIXTURES.",
        ),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
    # Note: current FIXTURE_STATS adapter output is minimal (only fixture_id +
    # data_available_at). Team-level statistics (possession, shots, etc.) are
    # not currently flattened into columns. Schema reflects current on-disk
    # reality; broader stat columns are a follow-up plan.
)


SPORTS_FIXTURE_LINEUPS = SchemaContract(
    category="sports",
    instrument_type="match",
    data_type="fixture_lineups",
    columns=[
        ColumnSpec(
            name="formation",
            dtype="string",
            nullable=True,
            description="Team formation string (e.g. '4-3-3', '3-5-2'); null pre-match until lineup published.",
        ),
        ColumnSpec(
            name="fixture_id",
            dtype="string",
            nullable=False,
            description="Stringified ``af_fixture_id`` — join key.",
        ),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
)


SPORTS_PLAYER_STATS = SchemaContract(
    category="sports",
    instrument_type="match",
    data_type="player_stats",
    columns=[
        ColumnSpec(
            name="fixture_id", dtype="string", nullable=False, description="Stringified ``af_fixture_id`` — join key."
        ),
        ColumnSpec(name="team_id", dtype="string", nullable=False, description="Stringified API-Football team ID."),
        ColumnSpec(name="team_name", dtype="string", nullable=False, description="Team name at time of match."),
        ColumnSpec(
            name="player_id",
            dtype="string",
            nullable=False,
            description="API-Football player ID — row identifier within (fixture, team).",
        ),
        ColumnSpec(name="player_name", dtype="string", nullable=False, description="Player name as published."),
        ColumnSpec(
            name="minutes_played",
            dtype="float64",
            nullable=True,
            description="Minutes played in this match (0 = did not play / unused sub).",
        ),
        ColumnSpec(name="position", dtype="string", nullable=True, description="Position code (G / D / M / F)."),
        ColumnSpec(
            name="rating",
            dtype="float64",
            nullable=True,
            description="API-Football player rating (0-10 float); null for players without enough actions.",
        ),
        ColumnSpec(
            name="captain", dtype="bool", nullable=False, description="True if player wore the captain's armband."
        ),
        ColumnSpec(
            name="substitute", dtype="bool", nullable=False, description="True if player came on as a substitute."
        ),
        ColumnSpec(name="offsides", dtype="float64", nullable=True, description="Offside infractions by this player."),
        ColumnSpec(name="shots_total", dtype="float64", nullable=True, description="Total shots attempted."),
        ColumnSpec(name="shots_on", dtype="float64", nullable=True, description="Shots on target."),
        ColumnSpec(name="goals_total", dtype="float64", nullable=True, description="Goals scored."),
        ColumnSpec(
            name="goals_conceded",
            dtype="int64",
            nullable=False,
            description="Goals conceded while on the pitch (GK-focused metric).",
        ),
        ColumnSpec(name="assists", dtype="float64", nullable=True, description="Goal assists credited."),
        ColumnSpec(
            name="saves", dtype="float64", nullable=True, description="Goalkeeper saves; null / 0 for outfield players."
        ),
        ColumnSpec(name="passes_total", dtype="float64", nullable=True, description="Total passes attempted."),
        ColumnSpec(
            name="passes_key", dtype="float64", nullable=True, description="Key passes (pass that leads to a shot)."
        ),
        ColumnSpec(name="passes_accuracy", dtype="float64", nullable=True, description="Pass completion % (0-100)."),
        ColumnSpec(name="tackles_total", dtype="float64", nullable=True, description="Tackles made."),
        ColumnSpec(name="blocks", dtype="float64", nullable=True, description="Blocks made (shots / crosses blocked)."),
        ColumnSpec(name="interceptions", dtype="float64", nullable=True, description="Interceptions made."),
        ColumnSpec(name="duels_total", dtype="float64", nullable=True, description="Ground/aerial duels contested."),
        ColumnSpec(name="duels_won", dtype="float64", nullable=True, description="Duels won."),
        ColumnSpec(name="dribbles_attempts", dtype="float64", nullable=True, description="Dribble attempts."),
        ColumnSpec(name="dribbles_success", dtype="float64", nullable=True, description="Successful dribbles."),
        ColumnSpec(
            name="dribbles_past",
            dtype="float64",
            nullable=True,
            description="Times this player was dribbled past by an opponent.",
        ),
        ColumnSpec(
            name="fouls_drawn", dtype="float64", nullable=True, description="Fouls drawn (times fouled by opponent)."
        ),
        ColumnSpec(name="fouls_committed", dtype="float64", nullable=True, description="Fouls committed."),
        ColumnSpec(
            name="yellow_cards",
            dtype="int64",
            nullable=False,
            description="Yellow cards received (0 or 1 in a single match unless red-for-two-yellows, in which case 2).",
        ),
        ColumnSpec(name="red_cards", dtype="int64", nullable=False, description="Red cards received (0 or 1)."),
        ColumnSpec(
            name="penalty_won", dtype="float64", nullable=True, description="Penalties won (drawn a PK for team)."
        ),
        ColumnSpec(
            name="penalty_committed",
            dtype="float64",
            nullable=True,
            description="Penalties conceded (committed the foul).",
        ),
        ColumnSpec(name="penalty_scored", dtype="int64", nullable=False, description="Penalties scored."),
        ColumnSpec(
            name="penalty_missed", dtype="int64", nullable=False, description="Penalties missed (saved / off-target)."
        ),
        ColumnSpec(name="penalty_saved", dtype="float64", nullable=True, description="Penalties saved (GK)."),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="player_id",
    required_row_count_min=0,
)


SPORTS_INJURIES = SchemaContract(
    category="sports",
    instrument_type="match",
    data_type="injuries",
    columns=[
        ColumnSpec(
            name="player",
            dtype="string",
            nullable=False,
            description=(
                "Nested player struct serialised as string on disk: "
                "``{id, name, photo, reason, type}``. Flatten-to-columns is a follow-up."
            ),
        ),
        ColumnSpec(
            name="team",
            dtype="string",
            nullable=False,
            description="Nested team struct serialised as string: ``{id, logo, name}``.",
        ),
        ColumnSpec(
            name="fixture",
            dtype="string",
            nullable=True,
            description=(
                "Nested fixture struct serialised as string: ``{date, id, timestamp, timezone}``. "
                "May be null for injuries not tied to a specific fixture."
            ),
        ),
        ColumnSpec(
            name="league",
            dtype="string",
            nullable=False,
            description="Nested league struct serialised as string: ``{country, flag, id, logo, name, season}``.",
        ),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="player",
    required_row_count_min=0,
)


# ============================================================================
# Registry side-effects
# ============================================================================

CONTRACT_REGISTRY[("sports", "match", "fixtures")] = SPORTS_FIXTURES
CONTRACT_REGISTRY[("sports", "match", "fixture_events")] = SPORTS_FIXTURE_EVENTS
CONTRACT_REGISTRY[("sports", "match", "fixture_stats")] = SPORTS_FIXTURE_STATS
CONTRACT_REGISTRY[("sports", "match", "fixture_lineups")] = SPORTS_FIXTURE_LINEUPS
CONTRACT_REGISTRY[("sports", "match", "player_stats")] = SPORTS_PLAYER_STATS
CONTRACT_REGISTRY[("sports", "match", "injuries")] = SPORTS_INJURIES


__all__ = [
    "SPORTS_FIXTURES",
    "SPORTS_FIXTURE_EVENTS",
    "SPORTS_FIXTURE_LINEUPS",
    "SPORTS_FIXTURE_STATS",
    "SPORTS_INJURIES",
    "SPORTS_PLAYER_STATS",
]
