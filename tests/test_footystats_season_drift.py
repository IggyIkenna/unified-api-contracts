"""Tests for scripts/check_footystats_season_drift.py.

Uses mock API responses to verify drift detection logic without live network calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import check_footystats_season_drift as drift_module
import pytest
from check_footystats_season_drift import _canonical_from_name, check_drift

from unified_api_contracts.canonical.domain.sports.provider_league_ids import FOOTYSTATS_SEASON_IDS


def _make_mock_response(items: list[dict[str, object]]) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {"data": items}
    return mock


def _current_items() -> list[dict[str, object]]:
    """Return mock API items matching the current FOOTYSTATS_SEASON_IDS exactly (no drift)."""
    return [{"id": sid, "name": f"League {canon}"} for canon, sid in FOOTYSTATS_SEASON_IDS.items()]


def test_no_drift_when_season_ids_match() -> None:
    """check_drift returns empty drifted list when all API season_ids match the hardcoded dict."""
    items = _current_items()
    with patch.object(drift_module.requests, "get", return_value=_make_mock_response(items)):
        result = check_drift("fake-key")

    assert result["drifted"] == []
    assert result["missing_from_api"] == []


def test_drift_detected_for_new_season_id() -> None:
    """check_drift flags leagues whose season_id differs from FOOTYSTATS_SEASON_IDS."""
    items = _current_items()
    # Replace EPL's current season_id with a new one (simulating season rollover)
    epl_old = FOOTYSTATS_SEASON_IDS["EPL"]
    epl_new = epl_old + 10000
    items = [{"id": epl_new, "name": "Premier League"} if item["id"] == epl_old else item for item in items]

    with patch.object(drift_module.requests, "get", return_value=_make_mock_response(items)):
        result = check_drift("fake-key")

    drifted = result["drifted"]
    assert isinstance(drifted, list)
    drifted_leagues = {d["league"] for d in drifted}
    assert "EPL" in drifted_leagues
    epl_entry = next(d for d in drifted if d["league"] == "EPL")
    assert epl_entry["old_id"] == epl_old
    assert epl_entry["new_id"] == epl_new


def test_no_false_positive_for_unchanged_leagues() -> None:
    """Leagues whose season_id hasn't changed do not appear in drifted."""
    items = _current_items()
    epl_old = FOOTYSTATS_SEASON_IDS["EPL"]
    items = [{"id": epl_old + 10000, "name": "Premier League"} if item["id"] == epl_old else item for item in items]

    with patch.object(drift_module.requests, "get", return_value=_make_mock_response(items)):
        result = check_drift("fake-key")

    drifted_leagues = {d["league"] for d in result["drifted"]}
    unchanged = set(FOOTYSTATS_SEASON_IDS.keys()) - {"EPL"}
    assert not drifted_leagues.intersection(unchanged), f"False positives: {drifted_leagues & unchanged}"


def test_new_unknown_season_flagged_in_new_seasons() -> None:
    """Items whose season_id is absent from FOOTYSTATS_HISTORICAL_SEASON_IDS appear in new_seasons."""
    mystery_id = 99999999
    items = [*_current_items(), {"id": mystery_id, "name": "Unknown New League XYZ"}]

    with patch.object(drift_module.requests, "get", return_value=_make_mock_response(items)):
        result = check_drift("fake-key")

    new_ids = {s["season_id"] for s in result["new_seasons"]}
    assert mystery_id in new_ids


def test_unknown_name_gets_no_canonical_guess() -> None:
    """Items with completely unrecognised names get canonical_guess=None."""
    mystery_id = 99999998
    items = [*_current_items(), {"id": mystery_id, "name": "Totally Unknown League"}]

    with patch.object(drift_module.requests, "get", return_value=_make_mock_response(items)):
        result = check_drift("fake-key")

    unknown = next((s for s in result["new_seasons"] if s["season_id"] == mystery_id), None)
    assert unknown is not None
    assert unknown["canonical_guess"] is None


def test_known_name_gets_canonical_guess_and_historical_addition() -> None:
    """New season IDs with recognisable names get canonical_guess populated and appear in historical_additions."""
    bundesliga_new_id = 99999997
    items = _current_items()
    # Remove current Bundesliga entry and replace with a new season ID
    bundesliga_old = FOOTYSTATS_SEASON_IDS["BUNDESLIGA"]
    items = [i for i in items if i["id"] != bundesliga_old]
    items.append({"id": bundesliga_new_id, "name": "Bundesliga"})

    with patch.object(drift_module.requests, "get", return_value=_make_mock_response(items)):
        result = check_drift("fake-key")

    new_season = next((s for s in result["new_seasons"] if s["season_id"] == bundesliga_new_id), None)
    assert new_season is not None
    assert new_season["canonical_guess"] == "BUNDESLIGA"

    additions = {a["season_id"]: a["canonical"] for a in result["historical_additions"]}
    assert additions.get(bundesliga_new_id) == "BUNDESLIGA"


def test_missing_from_api_reported() -> None:
    """Leagues in FOOTYSTATS_SEASON_IDS that don't appear in the API response are flagged."""
    items = [i for i in _current_items() if i["id"] != FOOTYSTATS_SEASON_IDS["EPL"]]

    with patch.object(drift_module.requests, "get", return_value=_make_mock_response(items)):
        result = check_drift("fake-key")

    assert "EPL" in result["missing_from_api"]


@pytest.mark.parametrize(
    "name,expected_canonical",
    [
        ("Premier League", "EPL"),
        ("England Premier League", "EPL"),
        ("Bundesliga", "BUNDESLIGA"),
        ("2. Bundesliga", "BUNDESLIGA_2"),
        ("Serie A", "SERIE_A"),
        ("Ligue 1", "LIGUE_1"),
        ("La Liga", "LA_LIGA"),
        ("Danish Superliga", "DANISH_SUPERLIGA"),
        ("Eliteserien", "ELITESERIEN"),
        ("Allsvenskan", "ALLSVENSKAN"),
        ("J1 League", "J1_LEAGUE"),
        ("K League 1", "K_LEAGUE_1"),
        ("Completely Unknown League", None),
    ],
)
def test_canonical_from_name(name: str, expected_canonical: str | None) -> None:
    assert _canonical_from_name(name) == expected_canonical
