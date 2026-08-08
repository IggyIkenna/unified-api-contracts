"""Schedule/outcome split for canonical fixtures (fixture-schedule-split epic).

ADDITIVE foundation for the fixture-schedule-split (operator decision
"code-now, walk-after"). These types live ALONGSIDE the legacy
``CanonicalFixture`` (in this package's ``__init__``) — they do NOT replace it.

**The writer cutover has SHIPPED (2026-07-14+, no legacy dual-write)** —
``instruments-service``'s FIXTURES writer now writes ONLY
``entity=fixtures_schedule``/``entity=fixtures_outcomes`` for every date on/after
the cutover; ``entity=fixtures`` no longer receives new data
(``sports_fixtures_schema_split_completion_2026_06_20.md``,
``plans/active/issues/features_sports_fixtures_split_reader_gap_2026_07_15.md``).
``gcs_paths.SPORTS_DATA_TYPE_TO_FOLDER`` now registers both split entity-type
strings AND ``candidate_parquet_paths("FIXTURES", ...)`` auto-appends
``FIXTURES_SCHEDULE`` candidates so existing "FIXTURES" callers keep resolving
rows across the cutover.

Split rationale (lookahead-bias avoidance — Q1/Q3 of the source issue):
``CanonicalFixtureSchedule`` carries pre-match / in-play timing that is known
at ``announced_at``; ``CanonicalFixtureOutcomes`` carries the result, only
known at ``match_end_time``. Keeping them separate lets each entity carry its
own ``available_at`` floor so feature compute can't read an outcome before it
existed.

All timestamps are tz-aware UTC (``AwareDatetime``). ET/PEN timestamps are
nullable — regular matches never reach extra time or penalties.

The legacy ``FIXTURES`` data_type is NOT removed (no historical dual-write ever
existed, so pre-cutover dates still only have ``entity=fixtures``) — see
``gcs_paths.SPORTS_DATA_TYPE_TO_FOLDER`` for the legacy ``FIXTURES`` →
``fixtures`` folder mapping alongside the two split entities.

SSOT: ``plans/epics/sports_master.md`` § "Match HT/ET/PEN timestamps +
score-distinction columns" (Q5 + Q6 + Q7) +
``codex/02-data/sports-fixtures-lifecycle.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict

from .fixture_status import MatchStatus

# ---------------------------------------------------------------------------
# New entity-type / data_type constants — ADDITIVE alongside the live FIXTURES.
# The single ``FIXTURES`` data_type is still the emitted entity today (see
# gcs_paths.SPORTS_DATA_TYPE_TO_FOLDER["fixtures"]). These two are wired into
# the writer + GCS folders ONLY at the gated split — defining the constants now
# lets UTL/IS build the migration against a stable name.
#
# Vocabulary lowercased 2026-08-08 (sports_taxonomy_p1_capture_and_contracts):
# all IS data_type tokens are now canonical lowercase.
# ---------------------------------------------------------------------------
FIXTURES_SCHEDULE: str = "fixtures_schedule"
"""Canonical data_type for the pre-match / scheduling half of a fixture.

GCS sub-folder: ``entity=fixtures_schedule``. Per-row
``available_at`` floor = ``announced_at``."""

FIXTURES_OUTCOMES: str = "fixtures_outcomes"
"""Canonical data_type for the result half of a fixture.

GCS sub-folder: ``entity=fixtures_outcomes``. Per-row
``available_at`` floor = ``match_end_time``."""


class MatchResult(StrEnum):
    """Closed-set canonical match result, distinguishing HOW the result arose.

    Penalty-shootout / extra-time wins are kept distinct from regulation
    results so downstream feature/strategy code can condition on the path to
    the result (a penalty win is not a draw, but it is not a regulation win
    either).
    """

    HOME_WIN = "home_win"
    """Home team won within regulation (90' + stoppage)."""

    AWAY_WIN = "away_win"
    """Away team won within regulation (90' + stoppage)."""

    DRAW_REGULATION = "draw_regulation"
    """Drawn after regulation — terminal for league fixtures (no ET/pens)."""

    HOME_WIN_AFTER_ET = "home_win_after_et"
    """Home team won in extra time (no penalty shootout)."""

    AWAY_WIN_AFTER_ET = "away_win_after_et"
    """Away team won in extra time (no penalty shootout)."""

    HOME_WIN_AFTER_PENS = "home_win_after_pens"
    """Home team won the penalty shootout."""

    AWAY_WIN_AFTER_PENS = "away_win_after_pens"
    """Away team won the penalty shootout."""


class CanonicalFixtureSchedule(BaseModel):
    """Pre-match / scheduling half of a fixture (split from ``CanonicalFixture``).

    Known at ``announced_at`` — carries the kickoff, participants, venue,
    status, and the (mostly nullable) phase timestamps. ET/PEN timestamps are
    nullable because regular matches never reach those phases.

    Canonical ``fixture_id`` format matches ``CanonicalFixture``:
    ``{api_football_fixture_id}`` as string.
    """

    model_config = ConfigDict(frozen=True)

    fixture_id: str
    kickoff_time: AwareDatetime
    league_id: str
    home_team_id: str
    away_team_id: str
    venue: str | None = None
    status: MatchStatus

    # --- Phase timestamps (Q5) — all tz-aware UTC. Regulation halves are
    # usually present for played matches; ET/PEN only for knockout overruns. ---
    halftime_start_time: AwareDatetime | None = None
    halftime_end_time: AwareDatetime | None = None
    extra_time_first_half_start_time: AwareDatetime | None = None
    extra_time_first_half_end_time: AwareDatetime | None = None
    extra_time_second_half_start_time: AwareDatetime | None = None
    extra_time_second_half_end_time: AwareDatetime | None = None
    penalty_shootout_start_time: AwareDatetime | None = None
    penalty_shootout_end_time: AwareDatetime | None = None
    whistle_full_time_at: AwareDatetime | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        return cls.model_validate(data)


class CanonicalFixtureOutcomes(BaseModel):
    """Result half of a fixture (split from ``CanonicalFixture``).

    Known only at ``match_end_time`` — carries the score distinctions and the
    typed ``match_result``. Penalty-shootout scores are NEVER collapsed into a
    single field: ``home_score_after_penalty_shootout`` is the aggregate
    (regulation + ET + the decisive pen) while ``home_penalty_shootout_score``
    is the shootout tally alone.
    """

    model_config = ConfigDict(frozen=True)

    fixture_id: str

    # --- Score distinction (Q6). All nullable: outcomes may be unknown
    # pre-result, and ET/PEN columns stay null for matches that ended in
    # regulation. ---
    home_score_regulation: int | None = None
    away_score_regulation: int | None = None
    home_score_after_extra_time: int | None = None
    away_score_after_extra_time: int | None = None
    home_score_after_penalty_shootout: int | None = None
    away_score_after_penalty_shootout: int | None = None
    home_penalty_shootout_score: int | None = None
    away_penalty_shootout_score: int | None = None

    went_to_extra_time: bool = False
    went_to_penalties: bool = False

    match_end_time: AwareDatetime | None = None
    match_result: MatchResult | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        return cls.model_validate(data)


@dataclass(frozen=True)
class MatchLifecycle:
    """Typed return for ``unified_trading_library.fixtures.extract_match_lifecycle``.

    Bundles the schedule (HT/ET/PEN phase timestamps) and the outcome
    (score-distinction columns + ``match_result``) for a single fixture so the
    UTL write-time helper returns ONE typed object. The IS FIXTURES adapter
    splits this into the two canonical entities at the gated writer cutover;
    until then it is purely the helper's transport type.

    This is a thin composition of the two canonical models rather than a third
    flat schema — it reuses their fields verbatim so there is no parallel
    field-set to keep in sync (the score / timestamp fields stay defined once
    on ``CanonicalFixtureSchedule`` / ``CanonicalFixtureOutcomes``).
    """

    schedule: CanonicalFixtureSchedule
    outcomes: CanonicalFixtureOutcomes
