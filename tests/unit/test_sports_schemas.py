"""Unit tests for sports-related API contract schemas (no external API calls).

Validates that Api-Football, Odds API, Betfair, Pinnacle, Open-Meteo, FootyStats,
and Soccer Football Info schemas parse minimal payloads correctly.
"""

from __future__ import annotations

import pytest
from unified_api_contracts.api_football.schemas import (
    ApiFootballFixture,
    ApiFootballLeague,
    ApiFootballTeam,
)
from unified_api_contracts.betfair.schemas import BetfairMarketCatalogue
from unified_api_contracts.footystats.schemas import FootystatsMatch
from unified_api_contracts.odds_api.schemas import OddsApiFixture
from unified_api_contracts.open_meteo.schemas import OpenMeteoRequest
from unified_api_contracts.pinnacle.schemas import PinnacleLeague
from unified_api_contracts.soccer_football_info.schemas import SoccerFootballMatch as SfiMatch

from unified_api_contracts import SPORTS_VENUES, VENUE_CATEGORY_MAP

pytestmark = pytest.mark.unit


def test_sports_venues_constant() -> None:
    """SPORTS_VENUES must include canonical sports data and execution venues."""
    assert "API_FOOTBALL" in SPORTS_VENUES
    assert "BETFAIR_EX_UK" in SPORTS_VENUES  # bare BETFAIR removed 2026-08-08: operator-group parent, not data-axis
    assert "PINNACLE" in SPORTS_VENUES
    assert "ODDS_API" in SPORTS_VENUES
    assert "FOOTYSTATS" in SPORTS_VENUES
    assert "OPEN_METEO" in SPORTS_VENUES


def test_sports_venue_category_map() -> None:
    """All SPORTS_VENUES map to category 'sports' EXCEPT the two deliberate prediction-market
    exceptions (KALSHI/POLYMARKET) — members of SPORTS_VENUES via SPORTS_PREDICTION_MARKET_VENUES
    (they DO offer sports contracts, a routing fact) but their asset_group is "prediction", not
    "sports" (VENUE_CATEGORY_MAP override, root-caused 2026-07-24 as a live SSOT contradiction with
    market_data_categories.VENUE_TO_ASSET_GROUP — this test previously encoded the wrong side of
    that contradiction as the expected behavior). See
    cross_ag_prediction_rows_bleed_into_sports_instruments_index_2026_07_20.md.
    """
    prediction_exceptions = {"KALSHI", "POLYMARKET"}
    for venue in SPORTS_VENUES:
        expected = "prediction" if venue in prediction_exceptions else "sports"
        assert VENUE_CATEGORY_MAP.get(venue) == expected


def test_api_football_fixture_minimal() -> None:
    """ApiFootballFixture parses minimal valid payload (all fields optional)."""
    obj = ApiFootballFixture.model_validate({"id": 1, "date": "2024-06-01T15:00:00+00:00"})
    assert obj.id == 1
    assert obj.date is not None


def test_api_football_fixture_goals_null_before_kickoff() -> None:
    """Unplayed fixtures (NS) return null home/away goals — must parse without validation errors."""
    obj = ApiFootballFixture.model_validate(
        {
            "id": 1,
            "goals": {"home": None, "away": None},
        }
    )
    assert obj.goals is not None
    assert obj.goals.home is None
    assert obj.goals.away is None


def test_api_football_team_minimal() -> None:
    """ApiFootballTeam parses minimal payload."""
    obj = ApiFootballTeam.model_validate({"id": 1, "name": "Team A"})
    assert obj.id == 1
    assert obj.name == "Team A"


def test_api_football_league_minimal() -> None:
    """ApiFootballLeague parses minimal payload."""
    obj = ApiFootballLeague.model_validate({"id": 1, "name": "Premier League", "season": 2024})
    assert obj.id == 1
    assert obj.season == 2024


def test_odds_api_fixture_minimal() -> None:
    """OddsApiFixture parses minimal payload."""
    payload = {
        "id": "evt-1",
        "sportKey": "soccer_epl",
        "commenceTime": "2024-06-01T15:00:00Z",
        "homeTeam": "Home",
        "awayTeam": "Away",
    }
    obj = OddsApiFixture.model_validate(payload)
    assert obj.id == "evt-1"
    assert obj.home_team == "Home"


def test_betfair_market_catalogue_minimal() -> None:
    """BetfairMarketCatalogue parses minimal payload."""
    payload = {"marketId": "1.123", "marketName": "Match Odds"}
    obj = BetfairMarketCatalogue.model_validate(payload)
    assert obj.market_id == "1.123"


def test_pinnacle_league_minimal() -> None:
    """PinnacleLeague parses minimal payload."""
    obj = PinnacleLeague.model_validate({"id": 1, "name": "Soccer"})
    assert obj.id == 1


def test_open_meteo_request_minimal() -> None:
    """OpenMeteoRequest parses minimal payload (used for weather in sports pipeline)."""
    obj = OpenMeteoRequest.model_validate({"latitude": 51.5, "longitude": -0.1})
    assert obj.latitude == 51.5


def test_footystats_match_minimal() -> None:
    """FootystatsMatch parses minimal payload."""
    obj = FootystatsMatch.model_validate({"id": 1})
    assert obj.id == 1


def test_soccer_football_info_match_minimal() -> None:
    """Soccer Football Info match schema parses minimal payload (id is str)."""
    obj = SfiMatch.model_validate({"id": "1"})
    assert obj.id == "1"
