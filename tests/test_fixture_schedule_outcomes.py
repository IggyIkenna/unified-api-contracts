"""Unit tests for the additive fixture schedule/outcome split (sports_master).

Covers ``CanonicalFixtureSchedule`` + ``CanonicalFixtureOutcomes`` +
``MatchResult`` + ``MatchLifecycle`` + the ``FIXTURES_SCHEDULE`` /
``FIXTURES_OUTCOMES`` entity-type constants. These are ADDITIVE — the legacy
``CanonicalFixture`` and ``FIXTURES`` data_type are untouched (asserted below).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError


def _utc(hour: int = 12) -> datetime:
    return datetime(2026, 1, 1, hour, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Facade import path works: from unified_api_contracts.sports import ...
# ---------------------------------------------------------------------------
def test_facade_import_path():
    from unified_api_contracts.sports import (
        CanonicalFixtureOutcomes,
        CanonicalFixtureSchedule,
        MatchResult,
    )

    assert CanonicalFixtureSchedule is not None
    assert CanonicalFixtureOutcomes is not None
    assert MatchResult is not None


def test_facade_exports_lifecycle_and_constants():
    from unified_api_contracts.sports import (
        FIXTURES_OUTCOMES,
        FIXTURES_SCHEDULE,
        MatchLifecycle,
    )

    assert FIXTURES_SCHEDULE == "FIXTURES_SCHEDULE"
    assert FIXTURES_OUTCOMES == "FIXTURES_OUTCOMES"
    assert MatchLifecycle is not None


def test_additive_legacy_fixture_and_data_type_untouched():
    """The split is ADDITIVE — legacy CanonicalFixture + FIXTURES survive."""
    from unified_api_contracts.sports import (
        SPORTS_DATA_TYPE_TO_FOLDER,
        CanonicalFixture,
    )

    assert CanonicalFixture is not None
    assert SPORTS_DATA_TYPE_TO_FOLDER["FIXTURES"] == "fixtures"


# ---------------------------------------------------------------------------
# MatchResult closed StrEnum membership
# ---------------------------------------------------------------------------
def test_match_result_closed_set():
    from unified_api_contracts.sports import MatchResult

    assert {m.value for m in MatchResult} == {
        "home_win",
        "away_win",
        "draw_regulation",
        "home_win_after_et",
        "away_win_after_et",
        "home_win_after_pens",
        "away_win_after_pens",
    }


def test_match_result_str_enum_value_access():
    from unified_api_contracts.sports import MatchResult

    assert MatchResult.HOME_WIN_AFTER_PENS == "home_win_after_pens"
    assert MatchResult("draw_regulation") is MatchResult.DRAW_REGULATION
    with pytest.raises(ValueError):
        MatchResult("draw_after_et")  # not a member — no such state


# ---------------------------------------------------------------------------
# CanonicalFixtureSchedule — construction, field types, nullability
# ---------------------------------------------------------------------------
def test_schedule_minimal_construction():
    from unified_api_contracts.sports import CanonicalFixtureSchedule, MatchStatus

    sched = CanonicalFixtureSchedule(
        fixture_id="1034567",
        kickoff_time=_utc(),
        league_id="EPL",
        home_team_id="LIVERPOOL",
        away_team_id="ARSENAL",
        status=MatchStatus.SCHEDULED,
    )
    assert sched.fixture_id == "1034567"
    assert sched.status is MatchStatus.SCHEDULED
    # ET/PEN + HT timestamps default null for a regular pre-match row.
    assert sched.halftime_start_time is None
    assert sched.extra_time_first_half_start_time is None
    assert sched.penalty_shootout_start_time is None
    assert sched.whistle_full_time_at is None
    assert sched.venue is None


def test_schedule_all_phase_timestamps_populated():
    from unified_api_contracts.sports import CanonicalFixtureSchedule, MatchStatus

    sched = CanonicalFixtureSchedule(
        fixture_id="1",
        kickoff_time=_utc(12),
        league_id="EPL",
        home_team_id="LIV",
        away_team_id="ARS",
        venue="ANFIELD",
        status=MatchStatus.FINISHED,
        halftime_start_time=_utc(12),
        halftime_end_time=_utc(13),
        extra_time_first_half_start_time=_utc(14),
        extra_time_first_half_end_time=_utc(15),
        extra_time_second_half_start_time=_utc(16),
        extra_time_second_half_end_time=_utc(17),
        penalty_shootout_start_time=_utc(18),
        penalty_shootout_end_time=_utc(19),
        whistle_full_time_at=_utc(19),
    )
    assert sched.penalty_shootout_end_time == _utc(19)
    assert sched.venue == "ANFIELD"


def test_schedule_requires_tz_aware_kickoff():
    from unified_api_contracts.sports import CanonicalFixtureSchedule, MatchStatus

    with pytest.raises(ValidationError):
        CanonicalFixtureSchedule(
            fixture_id="1",
            kickoff_time=datetime(2026, 1, 1, 12),  # naive — must be rejected
            league_id="EPL",
            home_team_id="LIV",
            away_team_id="ARS",
            status=MatchStatus.SCHEDULED,
        )


def test_schedule_is_frozen():
    from unified_api_contracts.sports import CanonicalFixtureSchedule, MatchStatus

    sched = CanonicalFixtureSchedule(
        fixture_id="1",
        kickoff_time=_utc(),
        league_id="EPL",
        home_team_id="LIV",
        away_team_id="ARS",
        status=MatchStatus.SCHEDULED,
    )
    with pytest.raises(ValidationError):
        sched.fixture_id = "2"  # frozen


# ---------------------------------------------------------------------------
# CanonicalFixtureOutcomes — construction, score distinction, nullability
# ---------------------------------------------------------------------------
def test_outcomes_minimal_defaults():
    from unified_api_contracts.sports import CanonicalFixtureOutcomes

    out = CanonicalFixtureOutcomes(fixture_id="1")
    assert out.home_score_regulation is None
    assert out.went_to_extra_time is False
    assert out.went_to_penalties is False
    assert out.match_result is None
    assert out.match_end_time is None


def test_outcomes_penalty_shootout_score_never_collapsed():
    """Aggregate post-shootout score and the shootout tally are distinct fields."""
    from unified_api_contracts.sports import CanonicalFixtureOutcomes, MatchResult

    out = CanonicalFixtureOutcomes(
        fixture_id="1",
        home_score_regulation=1,
        away_score_regulation=1,
        home_score_after_extra_time=1,
        away_score_after_extra_time=1,
        home_score_after_penalty_shootout=2,
        away_score_after_penalty_shootout=1,
        home_penalty_shootout_score=5,
        away_penalty_shootout_score=4,
        went_to_extra_time=True,
        went_to_penalties=True,
        match_end_time=_utc(20),
        match_result=MatchResult.HOME_WIN_AFTER_PENS,
    )
    # Shootout tally (5-4) is a separate field from the aggregate (2-1).
    assert out.home_penalty_shootout_score == 5
    assert out.away_penalty_shootout_score == 4
    assert out.home_score_after_penalty_shootout == 2
    assert out.match_result is MatchResult.HOME_WIN_AFTER_PENS


def test_outcomes_requires_tz_aware_match_end():
    from unified_api_contracts.sports import CanonicalFixtureOutcomes

    with pytest.raises(ValidationError):
        CanonicalFixtureOutcomes(
            fixture_id="1",
            match_end_time=datetime(2026, 1, 1, 20),  # naive — rejected
        )


def test_outcomes_is_frozen():
    from unified_api_contracts.sports import CanonicalFixtureOutcomes

    out = CanonicalFixtureOutcomes(fixture_id="1")
    with pytest.raises(ValidationError):
        out.home_score_regulation = 3  # frozen


# ---------------------------------------------------------------------------
# MatchLifecycle dataclass — bundles schedule + outcomes
# ---------------------------------------------------------------------------
def test_match_lifecycle_bundles_both_models():
    from unified_api_contracts.sports import (
        CanonicalFixtureOutcomes,
        CanonicalFixtureSchedule,
        MatchLifecycle,
        MatchResult,
        MatchStatus,
    )

    sched = CanonicalFixtureSchedule(
        fixture_id="1",
        kickoff_time=_utc(),
        league_id="EPL",
        home_team_id="LIV",
        away_team_id="ARS",
        status=MatchStatus.FINISHED,
    )
    out = CanonicalFixtureOutcomes(
        fixture_id="1",
        home_score_regulation=2,
        away_score_regulation=0,
        match_result=MatchResult.HOME_WIN,
    )
    lifecycle = MatchLifecycle(schedule=sched, outcomes=out)
    assert lifecycle.schedule.fixture_id == "1"
    assert lifecycle.outcomes.match_result is MatchResult.HOME_WIN


# ---------------------------------------------------------------------------
# from_raw round-trips
# ---------------------------------------------------------------------------
def test_schedule_from_raw():
    from unified_api_contracts.sports import CanonicalFixtureSchedule

    sched = CanonicalFixtureSchedule.from_raw(
        {
            "fixture_id": "9",
            "kickoff_time": "2026-01-01T12:00:00+00:00",
            "league_id": "BUN",
            "home_team_id": "BAYERN",
            "away_team_id": "DORTMUND",
            "status": "scheduled",
        }
    )
    assert sched.league_id == "BUN"
    assert sched.kickoff_time.tzinfo is not None


def test_outcomes_from_raw():
    from unified_api_contracts.sports import CanonicalFixtureOutcomes, MatchResult

    out = CanonicalFixtureOutcomes.from_raw(
        {
            "fixture_id": "9",
            "home_score_regulation": 0,
            "away_score_regulation": 1,
            "match_result": "away_win",
        }
    )
    assert out.match_result is MatchResult.AWAY_WIN
