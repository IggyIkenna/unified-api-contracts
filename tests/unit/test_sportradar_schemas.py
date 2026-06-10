"""Tests for external/sportradar/schemas.py — Sportradar model schemas and error classification."""

from __future__ import annotations

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction
from unified_api_contracts.external.sportradar.schemas import (
    SportradarCategory,
    SportradarCompetitor,
    SportradarError,
    SportradarSport,
    SportradarTournament,
)

# ---------------------------------------------------------------------------
# SportradarError.classify — error action mapping
# ---------------------------------------------------------------------------


def test_classify_429_is_retry() -> None:
    assert SportradarError.classify(code=429) == ErrorAction.RETRY


def test_classify_5xx_is_retry() -> None:
    assert SportradarError.classify(code=500) == ErrorAction.RETRY
    assert SportradarError.classify(code=503) == ErrorAction.RETRY


def test_classify_401_is_fail() -> None:
    assert SportradarError.classify(code=401) == ErrorAction.FAIL


def test_classify_403_is_fail() -> None:
    assert SportradarError.classify(code=403) == ErrorAction.FAIL


def test_classify_default_no_match_is_fail() -> None:
    assert SportradarError.classify(code=400) == ErrorAction.FAIL
    assert SportradarError.classify() == ErrorAction.FAIL
    assert SportradarError.classify(code=None, message=None) == ErrorAction.FAIL


# ---------------------------------------------------------------------------
# Model construction — verify fields and defaults
# ---------------------------------------------------------------------------


def test_sportradar_competitor_defaults() -> None:
    c = SportradarCompetitor()
    assert c.id is None
    assert c.name is None
    assert c.qualifier is None


def test_sportradar_competitor_with_values() -> None:
    c = SportradarCompetitor(id="sr:competitor:1", name="Arsenal", qualifier="home")
    assert c.id == "sr:competitor:1"
    assert c.name == "Arsenal"
    assert c.qualifier == "home"


def test_sportradar_sport_defaults() -> None:
    s = SportradarSport()
    assert s.id is None
    assert s.name is None


def test_sportradar_category_with_sport() -> None:
    sport = SportradarSport(id="sr:sport:1", name="Soccer")
    cat = SportradarCategory(id="sr:category:1", name="International", sport=sport)
    assert cat.sport is not None
    assert cat.sport.name == "Soccer"


def test_sportradar_tournament_defaults() -> None:
    t = SportradarTournament()
    assert t.id is None
    assert t.name is None
