"""Unit tests for MatchStatus + AF_STATUS_SHORT_MAP + AF_COMPLETED_CODES."""

from __future__ import annotations

from unified_api_contracts.canonical.domain.sports.fixture_status import (
    AF_COMPLETED_CODES,
    AF_STATUS_SHORT_MAP,
    COMPLETED_STATUSES,
    FS_STATUS_MAP,
    IN_PROGRESS_STATUSES,
    PRE_MATCH_STATUSES,
    TERMINAL_STATUSES,
    MatchStatus,
)


def test_match_status_closed_set():
    """MatchStatus has exactly 9 canonical states."""
    expected = {
        "scheduled",
        "live",
        "halftime",
        "finished",
        "postponed",
        "cancelled",
        "abandoned",
        "suspended",
        "interrupted",
    }
    assert {s.value for s in MatchStatus} == expected


def test_af_status_short_map_covers_documented_codes():
    """All documented API-Football status.short codes map to MatchStatus."""
    documented = {
        "NS",
        "TBD",  # pre-match
        "1H",
        "2H",
        "ET",
        "BT",
        "P",
        "LIVE",  # in-play
        "HT",  # halftime
        "FT",
        "AET",
        "PEN",
        "AWD",
        "WO",  # finished
        "SUSP",
        "INT",  # interrupted
        "PST",
        "CANC",
        "ABD",  # terminal
    }
    assert set(AF_STATUS_SHORT_MAP.keys()) == documented


def test_from_af_short_handles_unknown_codes_with_fallback():
    """Unknown codes fall back to SCHEDULED (don't raise)."""
    assert MatchStatus.from_af_short("UNKNOWN") == MatchStatus.SCHEDULED
    assert MatchStatus.from_af_short("") == MatchStatus.SCHEDULED
    assert MatchStatus.from_af_short(None) == MatchStatus.SCHEDULED


def test_from_af_short_case_insensitive():
    """from_af_short() upper-cases the input — lowercase resolves."""
    assert MatchStatus.from_af_short("ft") == MatchStatus.FINISHED
    assert MatchStatus.from_af_short("Ht") == MatchStatus.HALFTIME


def test_af_completed_codes_includes_all_finished_mappings():
    """AF_COMPLETED_CODES MUST include every raw AF code that maps to FINISHED.

    Drift here would cause adapters using AF_COMPLETED_CODES to silently miss
    AWD / WO walkover-finished fixtures (which DO produce a result row).
    """
    finished_codes = {code for code, status in AF_STATUS_SHORT_MAP.items() if status == MatchStatus.FINISHED}
    assert finished_codes == AF_COMPLETED_CODES, (
        f"AF_COMPLETED_CODES drift: enum-maps {finished_codes} != "
        f"constant {AF_COMPLETED_CODES}. Update fixture_status.py."
    )


def test_completed_statuses_grouping():
    """COMPLETED_STATUSES = {FINISHED} only — distinct from terminal (PST/CANC/ABD)."""
    assert frozenset({MatchStatus.FINISHED}) == COMPLETED_STATUSES


def test_in_progress_statuses_grouping():
    """IN_PROGRESS includes LIVE + HALFTIME (halftime is in-play, not a separate state)."""
    assert frozenset({MatchStatus.LIVE, MatchStatus.HALFTIME}) == IN_PROGRESS_STATUSES


def test_terminal_statuses_grouping():
    """TERMINAL = POSTPONED + CANCELLED + ABANDONED — fixtures that won't produce a regulation result."""
    assert frozenset({MatchStatus.POSTPONED, MatchStatus.CANCELLED, MatchStatus.ABANDONED}) == TERMINAL_STATUSES


def test_pre_match_statuses_grouping():
    """PRE_MATCH = {SCHEDULED} only."""
    assert frozenset({MatchStatus.SCHEDULED}) == PRE_MATCH_STATUSES


def test_grouping_sets_partition_finished_in_progress_pre_match():
    """No overlap between PRE_MATCH / IN_PROGRESS / COMPLETED grouping sets."""
    assert PRE_MATCH_STATUSES.isdisjoint(IN_PROGRESS_STATUSES)
    assert PRE_MATCH_STATUSES.isdisjoint(COMPLETED_STATUSES)
    assert IN_PROGRESS_STATUSES.isdisjoint(COMPLETED_STATUSES)


def test_terminal_disjoint_from_completed():
    """TERMINAL fixtures didn't finish in regulation — disjoint from COMPLETED."""
    assert TERMINAL_STATUSES.isdisjoint(COMPLETED_STATUSES)


# ---------------------------------------------------------------------------
# FootyStats helper
# ---------------------------------------------------------------------------


def test_fs_status_map_covers_documented_codes():
    """FS_STATUS_MAP covers FootyStats's documented status strings + spelling variants."""
    documented = {
        "scheduled",
        "live",
        "complete",
        "finished",
        "cancelled",
        "canceled",
        "postponed",
        "suspended",
        "abandoned",
    }
    assert set(FS_STATUS_MAP.keys()) == documented


def test_from_footystats_status_happy_path():
    """Each FootyStats status string maps to expected MatchStatus."""
    assert MatchStatus.from_footystats_status("scheduled") == MatchStatus.SCHEDULED
    assert MatchStatus.from_footystats_status("live") == MatchStatus.LIVE
    assert MatchStatus.from_footystats_status("complete") == MatchStatus.FINISHED
    assert MatchStatus.from_footystats_status("cancelled") == MatchStatus.CANCELLED
    assert MatchStatus.from_footystats_status("postponed") == MatchStatus.POSTPONED


def test_from_footystats_status_case_and_whitespace_insensitive():
    """Strips whitespace + lowercases the input."""
    assert MatchStatus.from_footystats_status("  LIVE  ") == MatchStatus.LIVE
    assert MatchStatus.from_footystats_status("Complete") == MatchStatus.FINISHED


def test_from_footystats_status_handles_unknown_with_fallback():
    """Unknown / empty / None → SCHEDULED fallback (matches from_af_short pattern)."""
    assert MatchStatus.from_footystats_status("unknown") == MatchStatus.SCHEDULED
    assert MatchStatus.from_footystats_status("") == MatchStatus.SCHEDULED
    assert MatchStatus.from_footystats_status(None) == MatchStatus.SCHEDULED


def test_from_footystats_status_american_canceled():
    """American spelling 'canceled' (one L) maps the same as British 'cancelled'."""
    assert MatchStatus.from_footystats_status("canceled") == MatchStatus.CANCELLED


# ---------------------------------------------------------------------------
# SFI state-derivation helper
# ---------------------------------------------------------------------------


def test_from_sfi_state_no_row_yet():
    """timer_seconds=None → SCHEDULED (fixture not yet started in SFI feed)."""
    assert MatchStatus.from_sfi_state(timer_seconds=None) == MatchStatus.SCHEDULED


def test_from_sfi_state_frozen_signals_finished():
    """frozen=True → FINISHED regardless of timer_seconds value."""
    assert MatchStatus.from_sfi_state(timer_seconds=5400, frozen=True) == MatchStatus.FINISHED


def test_from_sfi_state_within_halftime_window():
    """timer_seconds within [ht_start, ht_end] → HALFTIME."""
    assert (
        MatchStatus.from_sfi_state(
            timer_seconds=2710,  # ~45:10
            ht_start_timer=2700,
            ht_end_timer=3600,
        )
        == MatchStatus.HALFTIME
    )


def test_from_sfi_state_outside_halftime_window_is_live():
    """timer_seconds outside HT bounds (but not frozen) → LIVE."""
    assert (
        MatchStatus.from_sfi_state(
            timer_seconds=1800,  # 30:00 — first half
            ht_start_timer=2700,
            ht_end_timer=3600,
        )
        == MatchStatus.LIVE
    )


def test_from_sfi_state_no_halftime_metadata_defaults_to_live():
    """Without HT bounds + not frozen + timer present → LIVE."""
    assert MatchStatus.from_sfi_state(timer_seconds=1800) == MatchStatus.LIVE


def test_from_sfi_state_frozen_beats_halftime_check():
    """frozen=True wins even if timer happens to be within HT window."""
    assert (
        MatchStatus.from_sfi_state(
            timer_seconds=2800,
            ht_start_timer=2700,
            ht_end_timer=3600,
            frozen=True,
        )
        == MatchStatus.FINISHED
    )
