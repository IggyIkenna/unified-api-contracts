"""Registry Completeness P1 — sports/betting enums, BTTS normalization, venue constants.

Covers:
1. All OddsType enum values (including 8 new members)
2. BetSide and CommissionModel enums
3. VenueExecutionProfile accepts CommissionModel
4. Sports venues present in INSTRUMENT_TYPES_BY_VENUE
5. BTTS normalization with Yes/No outcome mapping
6. SUPPORTED_MARKET_TYPES covers all sports venues
7. BTTS cassette loads and validates against schema
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import ClassVar

import pytest

from unified_api_contracts.canonical.domain.sports.betting import (
    BetSide,
    CommissionModel,
)
from unified_api_contracts.canonical.domain.sports.odds import (
    CanonicalBookmakerMarket,
    OddsType,
    OutcomeType,
)
from unified_api_contracts.canonical.domain.sports.venue_execution import (
    VenueExecutionProfile,
)
from unified_api_contracts.external.odds_api.normalize import (
    _BTTS_OUTCOME_MAP,
    _MARKET_KEY_MAP,
    normalize_btts_outcomes,
)
from unified_api_contracts.external.odds_api.schemas import (
    OddsApiBookmaker,
    OddsApiFixture,
    OddsApiMarket,
    OddsApiOutcome,
)
from unified_api_contracts.registry._sports_venue_constants import (
    SUPPORTED_MARKET_TYPES,
)
from unified_api_contracts.registry.venue_constants import (
    INSTRUMENT_TYPES_BY_VENUE,
    SPORTS_BET_PLACEMENT_VENUES,
    SPORTS_BOOKMAKER_API_VENUES,
    SPORTS_BOOKMAKER_WEB_VENUES,
    SPORTS_DFS_VENUES,
    SPORTS_EXCHANGE_VENUES,
    SPORTS_PREDICTION_MARKET_VENUES,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 1. OddsType enum — all expected members present
# ---------------------------------------------------------------------------


class TestOddsTypeEnum:
    """All OddsType values are valid and include the 8 new members."""

    EXPECTED_MEMBERS: ClassVar[set[str]] = {
        "H2H",
        "OVER_UNDER",
        "ASIAN_HANDICAP",
        "BOTH_TEAMS_SCORE",
        "CORRECT_SCORE",
        "OUTRIGHT",
        "HALF_TIME_RESULT",
        "FIRST_HALF_OVER_UNDER",
        "CORNERS",
        "CARDS",
        "PLAYER_PROPS",
        "DRAW_NO_BET",
        "DOUBLE_CHANCE",
        "GOAL_SCORER",
    }

    def test_all_expected_members_exist(self) -> None:
        actual = {m.name for m in OddsType}
        missing = self.EXPECTED_MEMBERS - actual
        assert not missing, f"OddsType missing members: {missing}"

    def test_new_members_values(self) -> None:
        assert OddsType.HALF_TIME_RESULT == "half_time_result"
        assert OddsType.FIRST_HALF_OVER_UNDER == "first_half_over_under"
        assert OddsType.CORNERS == "corners"
        assert OddsType.CARDS == "cards"
        assert OddsType.PLAYER_PROPS == "player_props"
        assert OddsType.DRAW_NO_BET == "draw_no_bet"
        assert OddsType.DOUBLE_CHANCE == "double_chance"
        assert OddsType.GOAL_SCORER == "goal_scorer"

    def test_original_members_values(self) -> None:
        assert OddsType.H2H == "h2h"
        assert OddsType.OVER_UNDER == "over_under"
        assert OddsType.ASIAN_HANDICAP == "asian_handicap"
        assert OddsType.BOTH_TEAMS_SCORE == "both_teams_score"
        assert OddsType.CORRECT_SCORE == "correct_score"
        assert OddsType.OUTRIGHT == "outright"

    def test_is_str_enum(self) -> None:
        from enum import StrEnum

        assert issubclass(OddsType, StrEnum)
        for member in OddsType:
            assert isinstance(member, str)


# ---------------------------------------------------------------------------
# 2. BetSide and CommissionModel enums
# ---------------------------------------------------------------------------


class TestBetSideEnum:
    """BetSide enum has expected members."""

    def test_back_and_lay(self) -> None:
        assert BetSide.BACK == "back"
        assert BetSide.LAY == "lay"

    def test_member_count(self) -> None:
        assert len(BetSide) == 2

    def test_is_str_enum(self) -> None:
        from enum import StrEnum

        assert issubclass(BetSide, StrEnum)


class TestCommissionModelEnum:
    """CommissionModel enum has all expected members."""

    def test_core_members(self) -> None:
        assert CommissionModel.NET_WINNINGS_PCT == "net_winnings_pct"
        assert CommissionModel.BUILT_INTO_ODDS == "built_into_odds"
        assert CommissionModel.NOTIONAL_PCT == "notional_pct"
        assert CommissionModel.FLAT_FEE == "flat_fee"

    def test_additional_members(self) -> None:
        assert CommissionModel.MAKER_TAKER == "maker_taker"
        assert CommissionModel.LOW_VIG_EXCHANGE == "low_vig_exchange"
        assert CommissionModel.EXCHANGE_COMMISSION == "exchange_commission"

    def test_is_str_enum(self) -> None:
        from enum import StrEnum

        assert issubclass(CommissionModel, StrEnum)


# ---------------------------------------------------------------------------
# 3. VenueExecutionProfile accepts CommissionModel
# ---------------------------------------------------------------------------


class TestVenueExecutionProfileCommission:
    """VenueExecutionProfile.commission_model field typed as CommissionModel."""

    def test_accepts_commission_model(self) -> None:
        profile = VenueExecutionProfile(
            venue_key="betfair",
            commission_model=CommissionModel.NET_WINNINGS_PCT,
            commission_rate=Decimal("0.05"),
        )
        assert profile.commission_model == CommissionModel.NET_WINNINGS_PCT

    def test_accepts_none(self) -> None:
        profile = VenueExecutionProfile(venue_key="test_venue")
        assert profile.commission_model is None

    def test_accepts_all_commission_models(self) -> None:
        for model in CommissionModel:
            profile = VenueExecutionProfile(
                venue_key=f"test_{model.value}",
                commission_model=model,
            )
            assert profile.commission_model == model


# ---------------------------------------------------------------------------
# 4. Sports venues in INSTRUMENT_TYPES_BY_VENUE
# ---------------------------------------------------------------------------


class TestSportsVenuesInInstrumentTypes:
    """All sports bet-placement venues have INSTRUMENT_TYPES_BY_VENUE entries."""

    def test_exchange_venues_mapped_to_exchange_odds(self) -> None:
        for venue in SPORTS_EXCHANGE_VENUES:
            assert venue in INSTRUMENT_TYPES_BY_VENUE, f"Missing: {venue}"
            assert "EXCHANGE_ODDS" in INSTRUMENT_TYPES_BY_VENUE[venue]

    def test_prediction_market_venues_mapped(self) -> None:
        for venue in SPORTS_PREDICTION_MARKET_VENUES:
            assert venue in INSTRUMENT_TYPES_BY_VENUE, f"Missing: {venue}"
            assert "PREDICTION_MARKET" in INSTRUMENT_TYPES_BY_VENUE[venue]

    def test_bookmaker_api_venues_mapped_to_fixed_odds(self) -> None:
        for venue in SPORTS_BOOKMAKER_API_VENUES:
            assert venue in INSTRUMENT_TYPES_BY_VENUE, f"Missing: {venue}"
            assert "FIXED_ODDS" in INSTRUMENT_TYPES_BY_VENUE[venue]

    def test_bookmaker_web_venues_mapped_to_fixed_odds(self) -> None:
        for venue in SPORTS_BOOKMAKER_WEB_VENUES:
            assert venue in INSTRUMENT_TYPES_BY_VENUE, f"Missing: {venue}"
            assert "FIXED_ODDS" in INSTRUMENT_TYPES_BY_VENUE[venue]

    def test_dfs_venues_mapped_to_prop(self) -> None:
        for venue in SPORTS_DFS_VENUES:
            assert venue in INSTRUMENT_TYPES_BY_VENUE, f"Missing: {venue}"
            assert "PROP" in INSTRUMENT_TYPES_BY_VENUE[venue]

    def test_all_bet_placement_venues_covered(self) -> None:
        for venue in SPORTS_BET_PLACEMENT_VENUES:
            assert venue in INSTRUMENT_TYPES_BY_VENUE, (
                f"Bet placement venue {venue} missing from INSTRUMENT_TYPES_BY_VENUE"
            )


# ---------------------------------------------------------------------------
# 5. BTTS normalization
# ---------------------------------------------------------------------------


class TestBttsNormalization:
    """BTTS market key mapping and Yes/No outcome normalization."""

    def test_market_key_map_contains_btts(self) -> None:
        assert "btts" in _MARKET_KEY_MAP
        assert _MARKET_KEY_MAP["btts"] == OddsType.BOTH_TEAMS_SCORE

    def test_market_key_map_draw_no_bet(self) -> None:
        assert "draw_no_bet" in _MARKET_KEY_MAP
        assert _MARKET_KEY_MAP["draw_no_bet"] == OddsType.DRAW_NO_BET

    def test_market_key_map_double_chance(self) -> None:
        assert "double_chance" in _MARKET_KEY_MAP
        assert _MARKET_KEY_MAP["double_chance"] == OddsType.DOUBLE_CHANCE

    def test_btts_outcome_map_yes_no(self) -> None:
        assert _BTTS_OUTCOME_MAP["Yes"] == OutcomeType.YES
        assert _BTTS_OUTCOME_MAP["No"] == OutcomeType.NO

    def test_normalize_btts_outcomes_from_bookmaker(self) -> None:
        bookmaker = OddsApiBookmaker(
            key="pinnacle",
            title="Pinnacle",
            markets=[
                OddsApiMarket(
                    key="btts",
                    outcomes=[
                        OddsApiOutcome(name="Yes", price=1.72),
                        OddsApiOutcome(name="No", price=2.05),
                    ],
                ),
            ],
        )
        results = normalize_btts_outcomes(bookmaker)
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, CanonicalBookmakerMarket)
        assert result.bookmaker_key == "pinnacle"
        assert result.market == OddsType.BOTH_TEAMS_SCORE
        assert result.outcomes[OutcomeType.YES] == Decimal("1.72")
        assert result.outcomes[OutcomeType.NO] == Decimal("2.05")

    def test_normalize_btts_skips_non_btts_markets(self) -> None:
        bookmaker = OddsApiBookmaker(
            key="bet365",
            title="Bet365",
            markets=[
                OddsApiMarket(
                    key="h2h",
                    outcomes=[
                        OddsApiOutcome(name="Home", price=1.50),
                        OddsApiOutcome(name="Draw", price=4.00),
                        OddsApiOutcome(name="Away", price=6.00),
                    ],
                ),
            ],
        )
        results = normalize_btts_outcomes(bookmaker)
        assert results == []

    def test_normalize_btts_empty_markets(self) -> None:
        bookmaker = OddsApiBookmaker(key="test", title="Test", markets=None)
        results = normalize_btts_outcomes(bookmaker)
        assert results == []


# ---------------------------------------------------------------------------
# 6. SUPPORTED_MARKET_TYPES covers all sports venues
# ---------------------------------------------------------------------------


class TestSupportedMarketTypes:
    """SUPPORTED_MARKET_TYPES dict covers all sports bet-placement and DFS venues."""

    def test_exchange_venues_covered(self) -> None:
        for venue in SPORTS_EXCHANGE_VENUES:
            assert venue in SUPPORTED_MARKET_TYPES, f"Exchange venue {venue} missing"
            types = SUPPORTED_MARKET_TYPES[venue]
            assert isinstance(types, frozenset)
            assert OddsType.H2H in types
            assert OddsType.BOTH_TEAMS_SCORE in types

    def test_prediction_market_venues_covered(self) -> None:
        for venue in SPORTS_PREDICTION_MARKET_VENUES:
            assert venue in SUPPORTED_MARKET_TYPES, f"Prediction market venue {venue} missing"
            types = SUPPORTED_MARKET_TYPES[venue]
            assert OddsType.H2H in types

    def test_bookmaker_api_venues_covered(self) -> None:
        for venue in SPORTS_BOOKMAKER_API_VENUES:
            assert venue in SUPPORTED_MARKET_TYPES, f"Bookmaker API venue {venue} missing"
            types = SUPPORTED_MARKET_TYPES[venue]
            assert OddsType.H2H in types
            assert OddsType.BOTH_TEAMS_SCORE in types

    def test_bookmaker_web_venues_covered(self) -> None:
        for venue in SPORTS_BOOKMAKER_WEB_VENUES:
            assert venue in SUPPORTED_MARKET_TYPES, f"Bookmaker web venue {venue} missing"
            types = SUPPORTED_MARKET_TYPES[venue]
            assert OddsType.H2H in types

    def test_dfs_venues_covered(self) -> None:
        for venue in SPORTS_DFS_VENUES:
            assert venue in SUPPORTED_MARKET_TYPES, f"DFS venue {venue} missing"
            types = SUPPORTED_MARKET_TYPES[venue]
            assert OddsType.PLAYER_PROPS in types

    def test_all_values_are_odds_type(self) -> None:
        for venue, types in SUPPORTED_MARKET_TYPES.items():
            for odds_type in types:
                assert isinstance(odds_type, OddsType), f"Venue {venue} has non-OddsType value: {odds_type}"

    def test_all_bet_placement_venues_covered(self) -> None:
        for venue in SPORTS_BET_PLACEMENT_VENUES:
            assert venue in SUPPORTED_MARKET_TYPES, f"Bet placement venue {venue} missing from SUPPORTED_MARKET_TYPES"


# ---------------------------------------------------------------------------
# 7. BTTS cassette loads and validates against schema
# ---------------------------------------------------------------------------


class TestBttsCassette:
    """BTTS mock cassette loads and has valid structure."""

    CASSETTE_PATH = (
        Path(__file__).resolve().parents[2]
        / "unified_api_contracts"
        / "external"
        / "odds_api"
        / "mocks"
        / "btts_soccer_epl_cassette.json"
    )

    def test_cassette_file_exists(self) -> None:
        assert self.CASSETTE_PATH.exists(), f"Cassette not found at {self.CASSETTE_PATH}"

    def test_cassette_loads_as_json(self) -> None:
        data = json.loads(self.CASSETTE_PATH.read_text())
        assert isinstance(data, list)
        assert len(data) > 0

    def test_cassette_has_required_fields(self) -> None:
        data = json.loads(self.CASSETTE_PATH.read_text())
        fixture = data[0]
        assert "id" in fixture
        assert "sportKey" in fixture
        assert "homeTeam" in fixture
        assert "awayTeam" in fixture
        assert "bookmakers" in fixture

    def test_cassette_bookmaker_has_btts_market(self) -> None:
        data = json.loads(self.CASSETTE_PATH.read_text())
        fixture = data[0]
        found_btts = False
        for bookmaker in fixture["bookmakers"]:
            for market in bookmaker["markets"]:
                if market["key"] == "btts":
                    found_btts = True
                    outcomes = market["outcomes"]
                    outcome_names = {o["name"] for o in outcomes}
                    assert "Yes" in outcome_names, "BTTS market missing 'Yes' outcome"
                    assert "No" in outcome_names, "BTTS market missing 'No' outcome"
                    for o in outcomes:
                        assert isinstance(o["price"], (int, float)), (
                            f"BTTS outcome price must be numeric, got {type(o['price'])}"
                        )
        assert found_btts, "No BTTS market found in cassette"

    def test_cassette_parses_as_odds_api_fixture(self) -> None:
        data = json.loads(self.CASSETTE_PATH.read_text())
        for entry in data:
            fixture = OddsApiFixture.model_validate(entry)
            assert fixture.id is not None
            assert fixture.home_team is not None

    def test_cassette_btts_normalization_integration(self) -> None:
        """Load cassette and run BTTS normalization on each bookmaker."""
        data = json.loads(self.CASSETTE_PATH.read_text())
        total_btts = 0
        for entry in data:
            OddsApiFixture.model_validate(entry)  # validates without assignment
            for raw_bookmaker in entry.get("bookmakers", []):
                bookmaker = OddsApiBookmaker.model_validate(raw_bookmaker)
                results = normalize_btts_outcomes(bookmaker)
                total_btts += len(results)
                for result in results:
                    assert result.market == OddsType.BOTH_TEAMS_SCORE
                    assert OutcomeType.YES in result.outcomes
                    assert OutcomeType.NO in result.outcomes
        assert total_btts > 0, "No BTTS outcomes normalized from cassette"
