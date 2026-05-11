"""Unit tests for the sports per-source coverage SSOTs (Wave 3.X Track B).

Covers the helpers the ``unified_trading_library.legacy_reason_classifier``
sports classifier consumes to flip an ``empty_confirmed`` shard from the
catch-all ``SOURCE_RETURNED_ZERO`` to a typed reason:

* ``UNDERSTAT_COVERED_LEAGUES`` / ``does_understat_cover`` — Understat covers
  only 5 European leagues; everything else is ``EXPECTED_SOURCE_DOES_NOT_COVER_LEAGUE``.
* ``is_within_transfer_window`` — country-code-keyed transfer-window membership
  (transfermarkt shards outside the window → ``EXPECTED_OUTSIDE_TRANSFER_WINDOW``).
* ``get_footystats_season_bounds`` / ``is_within_footystats_season`` /
  ``footystats_season_status_for_day`` — FootyStats season bounds derived from
  the league registry's ``season_months`` (pre/post-season gaps →
  ``EXPECTED_PRE_SEASON`` / ``EXPECTED_POST_SEASON``).

All five are re-exported from the ``unified_api_contracts.sports`` facade.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from unified_api_contracts import EMPTY_CONFIRMED_REASONS
from unified_api_contracts.sports import (
    UNDERSTAT_COVERED_LEAGUES,
    UNDERSTAT_NAMES,
    does_understat_cover,
    footystats_season_status_for_day,
    get_footystats_season_bounds,
    get_season_boundary,
    is_within_footystats_season,
    is_within_transfer_window,
)

# ── Understat coverage ──────────────────────────────────────────────────────


def test_understat_covered_leagues_is_the_five_european_leagues() -> None:
    assert frozenset({"BUNDESLIGA", "EPL", "LA_LIGA", "LIGUE_1", "SERIE_A"}) == UNDERSTAT_COVERED_LEAGUES
    # Single SSOT: the set is exactly the keys of UNDERSTAT_NAMES, not a copy.
    assert frozenset(UNDERSTAT_NAMES.keys()) == UNDERSTAT_COVERED_LEAGUES


@pytest.mark.parametrize(
    ("league_id", "expected"),
    [
        ("EPL", True),
        ("epl", True),  # case-insensitive
        ("LA_LIGA", True),
        ("BUNDESLIGA", True),
        ("LIGUE_1", True),
        ("SERIE_A", True),
        ("MLS", False),
        ("J1_LEAGUE", False),
        ("ENG_CHAMPIONSHIP", False),  # 2nd tier — Understat doesn't cover it
        ("ELITESERIEN", False),
    ],
)
def test_does_understat_cover(league_id: str, expected: bool) -> None:
    assert does_understat_cover(league_id) is expected


# ── Transfer windows by country code ────────────────────────────────────────


def test_is_within_transfer_window_open_during_eng_summer_window() -> None:
    # England summer window (default) ≈ Jun 14 - Aug 30 — mid-July must be open.
    assert is_within_transfer_window("ENG", date(2025, 7, 15)) is True


def test_is_within_transfer_window_closed_in_october() -> None:
    # No transfer window is open in October for England.
    assert is_within_transfer_window("ENG", date(2025, 10, 15)) is False


def test_is_within_transfer_window_open_during_winter_window() -> None:
    # Most European FAs run a January winter window.
    assert is_within_transfer_window("ESP", date(2025, 1, 15)) is True


def test_is_within_transfer_window_unknown_country_uses_generic_pattern() -> None:
    # Unknown country → generic European dual-window pattern (summer ~Jun 10-Aug 31).
    assert is_within_transfer_window("ZZZ", date(2025, 7, 1)) is True
    assert is_within_transfer_window("ZZZ", date(2025, 10, 1)) is False


# ── FootyStats season bounds ────────────────────────────────────────────────


def test_get_footystats_season_bounds_matches_season_boundary() -> None:
    b = get_season_boundary("EPL", 2025)
    assert get_footystats_season_bounds("EPL", 2025) == (b.start_date, b.end_date)
    start, end = get_footystats_season_bounds("EPL", 2025)
    assert start < end  # season runs forward in time


def test_is_within_footystats_season_inclusive_of_bounds() -> None:
    start, end = get_footystats_season_bounds("EPL", 2025)
    assert is_within_footystats_season("EPL", 2025, start) is True
    assert is_within_footystats_season("EPL", 2025, end) is True
    assert is_within_footystats_season("EPL", 2025, start + timedelta(days=30)) is True
    assert is_within_footystats_season("EPL", 2025, start - timedelta(days=1)) is False
    assert is_within_footystats_season("EPL", 2025, end + timedelta(days=1)) is False


def test_footystats_season_status_in_season_is_none() -> None:
    start = get_footystats_season_bounds("EPL", 2025)[0]
    assert footystats_season_status_for_day("EPL", start + timedelta(days=30)) is None


def test_footystats_season_status_post_season_just_after_season_end() -> None:
    end_2024 = get_footystats_season_bounds("EPL", 2024)[1]
    # A day two days after the 2024-25 season ended (≈ late May 2025) is in the
    # off-season gap and closer to the just-ended season than the next one.
    status = footystats_season_status_for_day("EPL", end_2024 + timedelta(days=2))
    assert status == "EXPECTED_POST_SEASON"


def test_footystats_season_status_pre_season_just_before_season_start() -> None:
    start_2025 = get_footystats_season_bounds("EPL", 2025)[0]
    # A day two days before the 2025-26 season starts (≈ late July 2025) is in
    # the off-season gap and closer to the upcoming season than the prior one.
    status = footystats_season_status_for_day("EPL", start_2025 - timedelta(days=2))
    assert status == "EXPECTED_PRE_SEASON"


def test_footystats_season_status_returns_typed_reason_strings() -> None:
    # Whatever non-None value comes back must be a member of the closed
    # EmptyConfirmedReason set (so the classifier can stamp it directly).
    for probe in (
        get_footystats_season_bounds("EPL", 2025)[0] - timedelta(days=2),
        get_footystats_season_bounds("EPL", 2024)[1] + timedelta(days=2),
    ):
        status = footystats_season_status_for_day("EPL", probe)
        assert status in ("EXPECTED_PRE_SEASON", "EXPECTED_POST_SEASON")
        assert status in EMPTY_CONFIRMED_REASONS


def test_footystats_season_status_calendar_year_league_in_season() -> None:
    # Calendar-year league (Allsvenskan, Sweden) — a mid-season day must be in-season.
    start, end = get_footystats_season_bounds("ALLSVENSKAN", 2025)
    mid = start + (end - start) // 2
    assert footystats_season_status_for_day("ALLSVENSKAN", mid) is None
    assert is_within_footystats_season("ALLSVENSKAN", 2025, mid) is True
