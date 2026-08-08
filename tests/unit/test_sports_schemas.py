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

from unified_api_contracts import (
    EXPECTED_COVERAGE_BY_ASSET_GROUP,
    SPORTS_VENUES,
    VENUE_CATEGORY_MAP,
    VENUE_TO_ASSET_GROUP,
    VENUES_BY_ASSET_GROUP,
)

pytestmark = pytest.mark.unit


def test_sports_venues_constant() -> None:
    """SPORTS_VENUES must include canonical sports data and execution venues."""
    assert "API_FOOTBALL" in SPORTS_VENUES
    assert "BETFAIR_EX_UK" in SPORTS_VENUES  # bare BETFAIR is operator-group parent, not data-axis
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


def test_venues_by_asset_group_sports_and_prediction_are_disjoint() -> None:
    """`VENUES_BY_ASSET_GROUP["sports"]` and `["prediction"]` must never share a venue.

    This is the enumerator-level guard for the cross-AG bleed
    `sports_taxonomy_p1_capture_and_contracts_2026_08_08.md` ("Purge the cross-AG bleed
    from the sports denominator") closes: `VENUES_BY_ASSET_GROUP` is the live SSOT that
    `VENUE_TO_ASSET_GROUP` and every expected-universe enumerator that reads it directly
    are derived from — a future hand-edit re-adding KALSHI/POLYMARKET (or any other
    prediction-market venue) to the sports list would silently reopen the bleed
    `SPORTS_VENUE_ACCEPTED_CROSS_AG_BLEED` exists to suppress the panel badge for. Both
    lists are hand-authored (not derived from a shared source), so nothing else enforces
    this.
    """
    overlap = set(VENUES_BY_ASSET_GROUP["sports"]) & set(VENUES_BY_ASSET_GROUP["prediction"])
    assert not overlap, f"venue(s) declared in BOTH sports and prediction: {sorted(overlap)}"


def test_prediction_venues_resolve_to_prediction_not_sports() -> None:
    """Every declared prediction venue resolves to asset_group "prediction" via the live
    SSOT (`VENUE_TO_ASSET_GROUP`, mechanically derived from `VENUES_BY_ASSET_GROUP`) — the
    same contradiction `cross_ag_prediction_rows_bleed_into_sports_instruments_index_
    2026_07_20.md` root-caused for the DIFFERENT, execution-context `VENUE_CATEGORY_MAP`
    registry in `venue_constants.py` (covered by `test_sports_venue_category_map` above).
    """
    for venue in VENUES_BY_ASSET_GROUP["prediction"]:
        assert VENUE_TO_ASSET_GROUP.get(venue) == "prediction"


def test_expected_coverage_sports_and_prediction_are_disjoint() -> None:
    """`EXPECTED_COVERAGE_BY_ASSET_GROUP["sports"]`/`["prediction"]` keys must never
    overlap — this feeds `is_expected`/`get_expected_data_types_for_venue_in_scope`, the
    MTDS batch pre-flight's could-exist denominator, a second independent enumerator from
    `VENUES_BY_ASSET_GROUP` that must not re-seed a prediction-market venue into sports
    either.
    """
    sports_keys = set(EXPECTED_COVERAGE_BY_ASSET_GROUP["sports"])
    prediction_keys = set(EXPECTED_COVERAGE_BY_ASSET_GROUP["prediction"])
    overlap = sports_keys & prediction_keys
    assert not overlap, f"venue(s) declared in BOTH sports and prediction expected coverage: {sorted(overlap)}"


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
