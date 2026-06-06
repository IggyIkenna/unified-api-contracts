"""SPORTS Family B — API-Football match-fact SchemaContracts.

Extracted from ``_sports_contracts.py`` to keep each module under the
codex 900-line limit. See SSOT plan:
``plans/active/sports_uac_schema_contracts_registration_2026_04_24.md``.

Contracts registered:

- FIXTURES — master fixtures parquet (``af_`` prefixed IDs)
- FIXTURE_EVENTS — per-fixture goal / card / sub events (one row per event)
- FIXTURE_STATS — per-fixture per-team stats (one row per (fixture, team))
- FIXTURE_LINEUPS — per-fixture per-player lineups (one row per (fixture, team, player))
- PLAYER_STATS — per-fixture per-player stats
- INJURIES — daily injury report (one row per (player, team, fixture))

## Provider semantics — API-Football

API-Football is a JSON HTTP API; every endpoint returns nested objects
(player + team + fixture + league + statistics arrays). The instruments-service
adapter flattens these at the UAC normalizer layer (
``unified_api_contracts.external.api_football.normalize.normalize_api_football_*``)
into per-row dicts that match the contract column shape declared here.

Flattening shipped via plan
``plans/active/api_football_minimal_flattening_removal_2026_05_07.plan.md``
(2026-05-08) — prior to that ``fixture_events`` / ``fixture_stats`` /
``fixture_lineups`` only persisted ``fixture_id + available_at`` with
the nested arrays dropped, and ``injuries`` persisted four opaque
``struct<>`` columns. Reach the canonical column shape via the
post-flattening commits in UAC + instruments-service.

Status enumeration on FIXTURES (``status_short``):
- Pre-match: ``TBD`` (date confirmed, time TBC), ``NS`` (not started)
- In-play: ``1H`` (first half), ``HT`` (halftime), ``2H`` (second half),
  ``ET`` (extra time), ``BT`` (break time), ``P`` (penalty shootout),
  ``SUSP`` (suspended), ``INT`` (interrupted), ``LIVE`` (generic live)
- Post-match: ``FT`` (full time), ``AET`` (after extra time), ``PEN``
  (after penalties), ``PST`` (postponed), ``CANC`` (cancelled), ``ABD``
  (abandoned), ``AWD`` (awarded by federation), ``WO`` (walkover)
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
    asset_group="sports",
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
            name="match_end_time",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description=(
                "UTC timestamp when match concluded — computed at write-time via "
                "resolve_match_end_time() cascade (api_football native → SFI freeze → "
                "footystats/understat post-match → kickoff+120min fallback). Null pre-match "
                "and during live. SSOT: codex/02-data/match-end-time-cascade.md."
            ),
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
        # ------------------------------------------------------------------
        # Q5 — HT/ET/PEN phase timestamps (fixture-schedule-split Phase 3).
        # Populated at write-time from the api-football fixture response via
        # ``unified_trading_library.fixtures.extract_match_lifecycle``. ALL
        # nullable: regulation matches never reach ET/PEN, and the AF fixtures
        # endpoint only timestamps the two regulation half starts (HT derives
        # from ``periods.first + 45'``; ET/PEN have no native AF timestamp so
        # they stay null even when ``went_to_extra_time`` / ``went_to_penalties``
        # is true). All tz-aware UTC. SSOT: codex/02-data/sports-fixtures-lifecycle.md.
        # ------------------------------------------------------------------
        ColumnSpec(
            name="halftime_start_time",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description="UTC start of the halftime break (= first-half start + 45'); null pre-match / unplayed.",
        ),
        ColumnSpec(
            name="halftime_end_time",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description="UTC end of the halftime break (= second-half start); null pre-match / unplayed.",
        ),
        ColumnSpec(
            name="extra_time_first_half_start_time",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description="UTC start of ET first half; null unless ET played (AF emits no ET timestamp).",
        ),
        ColumnSpec(
            name="extra_time_first_half_end_time",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description="UTC end of ET first half; null unless ET was played.",
        ),
        ColumnSpec(
            name="extra_time_second_half_start_time",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description="UTC start of ET second half; null unless ET was played.",
        ),
        ColumnSpec(
            name="extra_time_second_half_end_time",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description="UTC end of ET second half; null unless ET was played.",
        ),
        ColumnSpec(
            name="penalty_shootout_start_time",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description="UTC start of the penalty shootout; null unless a shootout occurred.",
        ),
        ColumnSpec(
            name="penalty_shootout_end_time",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description="UTC end of the penalty shootout; null unless a shootout occurred.",
        ),
        ColumnSpec(
            name="whistle_full_time_at",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description="UTC regulation full-time whistle (2H start + 45' or kickoff + 90'); null abandoned/pre-match.",
        ),
        # ------------------------------------------------------------------
        # Q6 — score-distinction columns (fixture-schedule-split Phase 3).
        # Populated at write-time from the api-football ``score`` block. The
        # penalty-shootout score is NEVER collapsed: ``*_score_after_penalty_shootout``
        # is the post-shootout aggregate (AF ``goals``) while
        # ``*_penalty_shootout_score`` is the shootout tally alone (AF
        # ``score.penalty``). ALL nullable. ``went_to_*`` default False.
        # ------------------------------------------------------------------
        ColumnSpec(
            name="home_score_regulation",
            dtype="float64",
            nullable=True,
            description="Home goals at end of regulation (AF ``score.fulltime``); null pre-result.",
        ),
        ColumnSpec(
            name="away_score_regulation",
            dtype="float64",
            nullable=True,
            description="Away goals at end of regulation (AF ``score.fulltime``); null pre-result.",
        ),
        ColumnSpec(
            name="home_score_after_extra_time",
            dtype="float64",
            nullable=True,
            description="Home aggregate after extra time (AF ``score.extratime``); null unless ET played.",
        ),
        ColumnSpec(
            name="away_score_after_extra_time",
            dtype="float64",
            nullable=True,
            description="Away aggregate after extra time (AF ``score.extratime``); null unless ET played.",
        ),
        ColumnSpec(
            name="home_score_after_penalty_shootout",
            dtype="float64",
            nullable=True,
            description="Home post-shootout aggregate (AF ``goals``); null unless a shootout occurred.",
        ),
        ColumnSpec(
            name="away_score_after_penalty_shootout",
            dtype="float64",
            nullable=True,
            description="Away post-shootout aggregate; null unless a shootout occurred.",
        ),
        ColumnSpec(
            name="home_penalty_shootout_score",
            dtype="float64",
            nullable=True,
            description="Home shootout tally alone (AF ``score.penalty``); null unless a shootout occurred.",
        ),
        ColumnSpec(
            name="away_penalty_shootout_score",
            dtype="float64",
            nullable=True,
            description="Away shootout tally alone (AF ``score.penalty``); null unless a shootout occurred.",
        ),
        ColumnSpec(
            name="went_to_extra_time",
            dtype="bool",
            nullable=True,
            description="True if the match reached extra time (AF status AET/PEN or non-null ET/pen score).",
        ),
        ColumnSpec(
            name="went_to_penalties",
            dtype="bool",
            nullable=True,
            description="True if decided by a penalty shootout (AF status PEN or non-null penalty score).",
        ),
        ColumnSpec(
            name="match_result",
            dtype="string",
            nullable=True,
            description="Closed-set ``MatchResult`` (home_win / *_after_et / *_after_pens); null pre-result.",
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
    asset_group="sports",
    instrument_type="match",
    data_type="fixture_events",
    columns=[
        ColumnSpec(
            name="fixture_id",
            dtype="string",
            nullable=False,
            description=(
                "Stringified ``af_fixture_id`` — join key back to FIXTURES. "
                "Note this entity keeps the unprefixed ``fixture_id`` column "
                "name on disk (not ``af_fixture_id`` like the master FIXTURES "
                "parquet); the drilldown reader's schema-adaptive "
                "``_probe_fid_column`` helper handles the alias."
            ),
        ),
        ColumnSpec(
            name="time_elapsed",
            dtype="int64",
            nullable=True,
            description="Match minute (0-90 regulation, 90-120 ET) when the event occurred.",
        ),
        ColumnSpec(
            name="time_extra",
            dtype="int64",
            nullable=True,
            description="Stoppage-time minutes added on top of ``time_elapsed`` (e.g. 90+3 → elapsed=90, extra=3).",
        ),
        ColumnSpec(
            name="team_id",
            dtype="int64",
            nullable=True,
            description="API-Football team ID for the team the event belongs to.",
        ),
        ColumnSpec(
            name="team_name",
            dtype="string",
            nullable=True,
            description="Team name as published by API-Football.",
        ),
        ColumnSpec(
            name="player_id",
            dtype="int64",
            nullable=True,
            description="Primary player on the event — scorer / card recipient / sub-out.",
        ),
        ColumnSpec(
            name="player_name",
            dtype="string",
            nullable=True,
            description="Primary player name.",
        ),
        ColumnSpec(
            name="assist_id",
            dtype="int64",
            nullable=True,
            description="Assist player ID for goals; sub-in player ID for substitutions; null otherwise.",
        ),
        ColumnSpec(
            name="assist_name",
            dtype="string",
            nullable=True,
            description="Assist / sub-in player name.",
        ),
        ColumnSpec(
            name="event_type",
            dtype="string",
            nullable=False,
            description=(
                "Event category from API-Football: 'Goal' | 'Card' | 'subst' "
                "| 'Var'. Combined with ``event_detail`` (sub-type) gives the "
                "full event classification."
            ),
        ),
        ColumnSpec(
            name="event_detail",
            dtype="string",
            nullable=True,
            description=(
                "Event sub-type. For Goals: 'Normal Goal' | 'Own Goal' | "
                "'Penalty' | 'Missed Penalty'. For Cards: 'Yellow Card' | "
                "'Red Card' | 'Second Yellow card'. For substitutions: "
                "'Substitution 1' | 'Substitution 2' | … (numbered per team). "
                "For VAR: 'Goal Disallowed - Foul', 'Penalty awarded', etc."
            ),
        ),
        ColumnSpec(
            name="comments",
            dtype="string",
            nullable=True,
            description=(
                "Free-text VAR / referee commentary as published by "
                "API-Football. Null for routine events. Useful for narrative "
                "data products; not for filter / aggregation use."
            ),
        ),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
)


SPORTS_FIXTURE_STATS = SchemaContract(
    asset_group="sports",
    instrument_type="match",
    data_type="fixture_stats",
    columns=[
        ColumnSpec(
            name="fixture_id",
            dtype="string",
            nullable=False,
            description=(
                "Stringified ``af_fixture_id`` — join key back to FIXTURES. "
                "One row per (fixture, team) — typically two rows per fixture."
            ),
        ),
        ColumnSpec(
            name="team_id",
            dtype="int64",
            nullable=True,
            description="API-Football team ID — row identifier within the fixture.",
        ),
        ColumnSpec(
            name="team_name",
            dtype="string",
            nullable=True,
            description="Team name as published by API-Football.",
        ),
        ColumnSpec(
            name="is_home",
            dtype="bool",
            nullable=True,
            description=(
                "True if this row is the home team. Stamped by the orchestrator "
                "when it cross-references ``team_id`` against the fixture's "
                "``af_home_id``; null when home/away cannot be resolved at "
                "write time."
            ),
        ),
        ColumnSpec(
            name="shots_on_target",
            dtype="int64",
            nullable=True,
            description="Shots on target (provider 'Shots on Goal').",
        ),
        ColumnSpec(
            name="shots_off_target",
            dtype="int64",
            nullable=True,
            description="Shots off target (missed the goal frame).",
        ),
        ColumnSpec(
            name="shots_total",
            dtype="int64",
            nullable=True,
            description="All shots attempted by the team.",
        ),
        ColumnSpec(
            name="shots_blocked",
            dtype="int64",
            nullable=True,
            description="Shots blocked by opposition defenders before reaching the keeper.",
        ),
        ColumnSpec(
            name="shots_inside_box",
            dtype="int64",
            nullable=True,
            description="Shots taken from inside the penalty area.",
        ),
        ColumnSpec(
            name="shots_outside_box",
            dtype="int64",
            nullable=True,
            description="Shots taken from outside the penalty area.",
        ),
        ColumnSpec(
            name="fouls",
            dtype="int64",
            nullable=True,
            description="Fouls committed by the team.",
        ),
        ColumnSpec(
            name="corners",
            dtype="int64",
            nullable=True,
            description="Corner kicks taken by the team.",
        ),
        ColumnSpec(
            name="offsides",
            dtype="int64",
            nullable=True,
            description="Offside infractions by the team.",
        ),
        ColumnSpec(
            name="ball_possession_pct",
            dtype="int64",
            nullable=True,
            description="Possession percentage 0-100 (provider returns '55%' string; flattener strips the suffix).",
        ),
        ColumnSpec(
            name="yellow_cards",
            dtype="int64",
            nullable=True,
            description="Yellow cards received by the team.",
        ),
        ColumnSpec(
            name="red_cards",
            dtype="int64",
            nullable=True,
            description="Red cards received by the team.",
        ),
        ColumnSpec(
            name="goalkeeper_saves",
            dtype="int64",
            nullable=True,
            description="Saves made by the team's goalkeeper.",
        ),
        ColumnSpec(
            name="passes_total",
            dtype="int64",
            nullable=True,
            description="Total passes attempted by the team.",
        ),
        ColumnSpec(
            name="passes_accurate",
            dtype="int64",
            nullable=True,
            description="Accurate (completed) passes.",
        ),
        ColumnSpec(
            name="passes_pct",
            dtype="int64",
            nullable=True,
            description="Pass-completion percentage 0-100 (provider 'Passes %').",
        ),
        ColumnSpec(
            name="expected_goals",
            dtype="float64",
            nullable=True,
            description=(
                "Expected goals (xG) — model-derived attacking quality "
                "summed across all shots. Provider may return as a string."
            ),
        ),
        ColumnSpec(
            name="goals_prevented",
            dtype="float64",
            nullable=True,
            description="xG-suppression metric — opposition xG minus actual goals conceded.",
        ),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
)


SPORTS_FIXTURE_LINEUPS = SchemaContract(
    asset_group="sports",
    instrument_type="match",
    data_type="fixture_lineups",
    columns=[
        ColumnSpec(
            name="fixture_id",
            dtype="string",
            nullable=False,
            description="Stringified ``af_fixture_id`` — join key. One row per (fixture, team, player).",
        ),
        ColumnSpec(
            name="team_id",
            dtype="int64",
            nullable=True,
            description="API-Football team ID.",
        ),
        ColumnSpec(
            name="team_name",
            dtype="string",
            nullable=True,
            description="Team name as published by API-Football.",
        ),
        ColumnSpec(
            name="formation",
            dtype="string",
            nullable=True,
            description=(
                "Team formation string (e.g. '4-3-3', '3-5-2', '4-2-3-1'). "
                "Null pre-match until the team sheet is published (~1 hour "
                "before kickoff for major leagues, later for lower tiers). "
                "Stamped on every (team, player) row for the team."
            ),
        ),
        ColumnSpec(
            name="coach_id",
            dtype="int64",
            nullable=True,
            description="API-Football coach ID; stamped on every player row for the team.",
        ),
        ColumnSpec(
            name="coach_name",
            dtype="string",
            nullable=True,
            description="Coach name; stamped on every player row for the team.",
        ),
        ColumnSpec(
            name="player_id",
            dtype="int64",
            nullable=True,
            description="API-Football player ID — identifier for the (fixture, team, player) row.",
        ),
        ColumnSpec(
            name="player_name",
            dtype="string",
            nullable=True,
            description="Player name as published.",
        ),
        ColumnSpec(
            name="player_number",
            dtype="int64",
            nullable=True,
            description="Shirt number worn by the player in this match.",
        ),
        ColumnSpec(
            name="player_pos",
            dtype="string",
            nullable=True,
            description="Position code: 'G' (goalkeeper) | 'D' (defender) | 'M' (midfielder) | 'F' (forward).",
        ),
        ColumnSpec(
            name="player_grid",
            dtype="string",
            nullable=True,
            description=(
                "Grid coordinate string (e.g. '4:1' = back-line, leftmost). "
                "Null for substitutes (subs have no on-pitch grid until they "
                "come on)."
            ),
        ),
        ColumnSpec(
            name="is_starter",
            dtype="bool",
            nullable=False,
            description="True for the 11 starting XI rows; False for substitute bench rows.",
        ),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
)


SPORTS_PLAYER_STATS = SchemaContract(
    asset_group="sports",
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
    asset_group="sports",
    instrument_type="match",
    data_type="injuries",
    columns=[
        ColumnSpec(
            name="player_id",
            dtype="int64",
            nullable=True,
            description="API-Football player ID — row identifier within the (date, team) cell.",
        ),
        ColumnSpec(
            name="player_name",
            dtype="string",
            nullable=True,
            description="Player name as published.",
        ),
        ColumnSpec(
            name="player_photo",
            dtype="string",
            nullable=True,
            description="Provider-hosted player headshot PNG URL.",
        ),
        ColumnSpec(
            name="player_type",
            dtype="string",
            nullable=True,
            description=("Absence category: 'Missing Fixture' | 'Questionable' as published by API-Football."),
        ),
        ColumnSpec(
            name="player_reason",
            dtype="string",
            nullable=True,
            description=(
                "Free-text injury / absence reason (e.g. 'Hamstring Injury', "
                "'Suspended', 'COVID-19', 'National selection'). Useful for "
                "narrative context; not for filter / aggregation."
            ),
        ),
        ColumnSpec(
            name="team_id",
            dtype="int64",
            nullable=True,
            description="API-Football team ID — joins to TEAMS / FIXTURES team columns.",
        ),
        ColumnSpec(
            name="team_name",
            dtype="string",
            nullable=True,
            description="Team name as published.",
        ),
        ColumnSpec(
            name="fixture_id",
            dtype="int64",
            nullable=True,
            description=(
                "API-Football fixture ID for the upcoming match the player "
                "is missing. Null when the injury report is a generic "
                "player-status update not tied to a specific match."
            ),
        ),
        ColumnSpec(
            name="league_id",
            dtype="int64",
            nullable=True,
            description="API-Football league ID for the league the upcoming fixture belongs to.",
        ),
        ColumnSpec(
            name="league_season",
            dtype="int64",
            nullable=True,
            description="Season year (e.g. 2025 for the 2025-26 European season).",
        ),
        _DATA_AVAILABLE_AT,
    ],
    symbol_column="player_id",
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
