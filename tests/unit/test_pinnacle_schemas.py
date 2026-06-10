"""Tests for external/pinnacle/schemas.py — Pinnacle error classification + from_raw classmethods."""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction
from unified_api_contracts.external.pinnacle.schemas import (
    PinnacleError,
    PinnacleEventSource,
    PinnacleLine,
    PinnacleMatchup,
    PinnacleOdds,
)

# ---------------------------------------------------------------------------
# PinnacleError.classify — error action mapping
# ---------------------------------------------------------------------------


def test_classify_rate_limit_code_429() -> None:
    assert PinnacleError.classify(code=429) == ErrorAction.RETRY


def test_classify_rate_in_error_string() -> None:
    assert PinnacleError.classify(error="rate limit exceeded") == ErrorAction.RETRY
    assert PinnacleError.classify(error="RATE_LIMIT") == ErrorAction.RETRY


def test_classify_rate_error_overrides_no_code() -> None:
    assert PinnacleError.classify(code=None, error="rate limited") == ErrorAction.RETRY


def test_classify_server_error_5xx() -> None:
    assert PinnacleError.classify(code=500) == ErrorAction.RETRY
    assert PinnacleError.classify(code=503) == ErrorAction.RETRY
    assert PinnacleError.classify(code=599) == ErrorAction.RETRY


def test_classify_unauthorized_code_401() -> None:
    assert PinnacleError.classify(code=401) == ErrorAction.FAIL


def test_classify_unauthorized_in_error_string() -> None:
    assert PinnacleError.classify(error="unauthorized access") == ErrorAction.FAIL


def test_classify_default_no_match_is_fail() -> None:
    assert PinnacleError.classify(code=400) == ErrorAction.FAIL
    assert PinnacleError.classify(code=404) == ErrorAction.FAIL
    assert PinnacleError.classify() == ErrorAction.FAIL
    assert PinnacleError.classify(code=None, error=None) == ErrorAction.FAIL


def test_classify_error_none_does_not_crash() -> None:
    # Should not raise even when error=None
    result = PinnacleError.classify(code=429, error=None)
    assert result == ErrorAction.RETRY


# ---------------------------------------------------------------------------
# PinnacleEventSource.from_raw
# ---------------------------------------------------------------------------

_NOW_ISO = "2026-01-15T12:00:00"


def test_pinnacle_event_source_from_raw_valid() -> None:
    raw: dict[str, str | int | float | bool | None] = {
        "event_id": 12345,
        "sport_id": 29,
        "league_id": 1980,
        "starts": _NOW_ISO,
        "home": "Team A",
        "away": "Team B",
        "live_status": 0,
        "status": "I",
        "parent_id": None,
    }
    event = PinnacleEventSource.from_raw(raw)
    assert event.event_id == 12345
    assert event.home == "Team A"
    assert event.away == "Team B"
    assert event.sport_id == 29
    assert event.live_status == 0


def test_pinnacle_event_source_from_raw_optional_fields_none() -> None:
    raw: dict[str, str | int | float | bool | None] = {
        "event_id": 99,
        "sport_id": 1,
        "league_id": 2,
        "starts": _NOW_ISO,
        "home": "H",
        "away": "A",
    }
    event = PinnacleEventSource.from_raw(raw)
    assert event.live_status is None
    assert event.parent_id is None


# ---------------------------------------------------------------------------
# PinnacleLine.from_raw
# ---------------------------------------------------------------------------


def test_pinnacle_line_from_raw_basic() -> None:
    raw: dict[str, str | int | float | bool | None] = {
        "event_id": 1,
        "period_number": 0,
        "line_id": 42,
        "market_type": "moneyline",
        "home_odds": 1.95,
        "away_odds": 1.85,
    }
    line = PinnacleLine.from_raw(raw)
    assert line.event_id == 1
    assert line.market_type == "moneyline"
    assert line.home_odds == Decimal("1.95")
    assert line.away_odds == Decimal("1.85")
    assert line.draw_odds is None


def test_pinnacle_line_from_raw_with_spread() -> None:
    raw: dict[str, str | int | float | bool | None] = {
        "event_id": 2,
        "period_number": 0,
        "line_id": 55,
        "market_type": "spread",
        "handicap": -2.5,
        "home_odds": 1.90,
        "away_odds": 1.90,
        "max_bet": 5000.0,
    }
    line = PinnacleLine.from_raw(raw)
    assert line.handicap == Decimal("-2.5")
    assert line.max_bet == Decimal("5000.0")


# ---------------------------------------------------------------------------
# PinnacleMatchup.from_raw
# ---------------------------------------------------------------------------


def test_pinnacle_matchup_from_raw() -> None:
    raw: dict[str, str | int | float | bool | None] = {
        "event_id": 10,
        "starts": _NOW_ISO,
        "home": "Arsenal",
        "away": "Chelsea",
        "league_id": 100,
        "moneyline_home": 2.1,
        "moneyline_away": 3.0,
    }
    matchup = PinnacleMatchup.from_raw(raw)
    assert matchup.home == "Arsenal"
    assert matchup.moneyline_home == Decimal("2.1")
    assert matchup.moneyline_draw is None
    assert matchup.spread_home is None


# ---------------------------------------------------------------------------
# PinnacleOdds.from_raw
# ---------------------------------------------------------------------------


def test_pinnacle_odds_from_raw() -> None:
    raw: dict[str, str | int | float | bool | None] = {
        "event_id": 20,
        "home": "Lakers",
        "away": "Bulls",
        "starts": _NOW_ISO,
        "lines": [],
    }
    odds = PinnacleOdds.from_raw(raw)
    assert odds.event_id == 20
    assert odds.home == "Lakers"
    assert odds.lines == []
