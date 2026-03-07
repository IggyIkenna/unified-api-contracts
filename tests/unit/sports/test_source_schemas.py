"""Verify source schemas: construction, from_raw(), round-trip serialisation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from unified_api_contracts.unified_api_contracts_external.sports.sources.api_football.schemas import (
    APIFootballEvent,
    APIFootballFixture,
    APIFootballLeague,
    APIFootballLineup,
    APIFootballOdds,
    APIFootballPlayer,
    APIFootballReferee,
    APIFootballStats,
    APIFootballTeam,
    APIFootballVenue,
)
from unified_api_contracts.unified_api_contracts_external.sports.sources.betfair.schemas import (
    BetfairExchangeOdds,
    BetfairMarket,
    BetfairMarketStatus,
    BetfairOrder,
    BetfairPrice,
    BetfairRunner,
)
from unified_api_contracts.unified_api_contracts_external.sports.sources.footystats.schemas import (
    FootyStatsBTTS,
    FootyStatsLeague,
    FootyStatsMatch,
    FootyStatsOdds,
    FootyStatsOverUnder,
    FootyStatsPlayer,
    FootyStatsReferee,
    FootyStatsTeam,
)
from unified_api_contracts.unified_api_contracts_external.sports.sources.odds_api.schemas import (
    OddsApiBookmaker,
    OddsApiEvent,
    OddsApiMarket,
    OddsApiOutcome,
)
from unified_api_contracts.unified_api_contracts_external.sports.sources.open_meteo.schemas import (
    OpenMeteoForecast,
    OpenMeteoWeather,
    WeatherAtKickoff,
    WeatherCondition,
)
from unified_api_contracts.unified_api_contracts_external.sports.sources.pinnacle.schemas import (
    PinnacleEvent,
    PinnacleLine,
    PinnacleMatchup,
    PinnacleOdds,
)
from unified_api_contracts.unified_api_contracts_external.sports.sources.soccer_football_info.schemas import (
    SFILeague,
    SFIMatch,
    SFIMatchDominance,
    SFIMatchProgressiveOdds,
    SFIMatchProgressiveStats,
    SFITeam,
)
from unified_api_contracts.unified_api_contracts_external.sports.sources.understat.schemas import (
    UnderstatMatch,
    UnderstatPlayerSeason,
    UnderstatShot,
    UnderstatTeamHistory,
    UnderstatXGData,
)

NOW = datetime.now(tz=UTC)


@pytest.mark.unit
class TestAPIFootballSchemas:
    def test_venue_from_raw(self) -> None:
        v = APIFootballVenue.from_raw({"venue_id": 1, "name": "Old Trafford"})
        assert v.venue_id == 1

    def test_fixture_construct(self) -> None:
        f = APIFootballFixture(
            fixture_id=123,
            date=NOW,
            league_id=39,
            league_name="PL",
            league_country="England",
            season=2024,
            home_team_id=33,
            home_team_name="Man Utd",
            away_team_id=34,
            away_team_name="Newcastle",
        )
        assert f.fixture_id == 123

    def test_fixture_round_trip(self) -> None:
        f = APIFootballFixture(
            fixture_id=1,
            date=NOW,
            league_id=39,
            league_name="PL",
            league_country="GB",
            season=2024,
            home_team_id=1,
            home_team_name="A",
            away_team_id=2,
            away_team_name="B",
        )
        data = f.model_dump()
        f2 = APIFootballFixture.model_validate(data)
        assert f == f2

    def test_team_from_raw(self) -> None:
        t = APIFootballTeam.from_raw({"team_id": 33, "name": "Man Utd"})
        assert t.name == "Man Utd"

    def test_player_from_raw(self) -> None:
        p = APIFootballPlayer.from_raw({"player_id": 1, "name": "Test"})
        assert p.player_id == 1

    def test_stats_from_raw(self) -> None:
        s = APIFootballStats.from_raw({"team_id": 1, "fixture_id": 1})
        assert s.shots_on_goal is None

    def test_lineup_from_raw(self) -> None:
        ln = APIFootballLineup.from_raw({"fixture_id": 1, "team_id": 1})
        assert ln.substitute is False

    def test_event_from_raw(self) -> None:
        e = APIFootballEvent.from_raw({"fixture_id": 1, "event_type": "Goal"})
        assert e.event_type == "Goal"

    def test_odds_from_raw(self) -> None:
        o = APIFootballOdds.from_raw(
            {
                "fixture_id": 1,
                "league_id": 39,
                "bookmaker_id": 1,
                "bookmaker_name": "bet365",
                "market_name": "Match Winner",
                "value_name": "Home",
                "odd": "1.50",
            }
        )
        assert o.odd == "1.50"

    def test_referee_from_raw(self) -> None:
        r = APIFootballReferee.from_raw({"name": "Michael Oliver"})
        assert r.name == "Michael Oliver"

    def test_league_from_raw(self) -> None:
        lg = APIFootballLeague.from_raw({"league_id": 39, "name": "PL", "country": "GB", "season": 2024})
        assert lg.season == 2024


@pytest.mark.unit
class TestFootyStatsSchemas:
    def test_match_from_raw(self) -> None:
        m = FootyStatsMatch.from_raw(
            {
                "match_id": 1,
                "date_unix": 1700000000,
                "competition_id": 1,
                "season": "2024",
                "home_id": 1,
                "away_id": 2,
                "home_name": "A",
                "away_name": "B",
            }
        )
        assert m.match_id == 1

    def test_match_round_trip(self) -> None:
        m = FootyStatsMatch(
            match_id=1,
            date_unix=1700000000,
            competition_id=1,
            season="2024",
            home_id=1,
            away_id=2,
            home_name="A",
            away_name="B",
        )
        data = m.model_dump()
        m2 = FootyStatsMatch.model_validate(data)
        assert m == m2

    def test_team_construct(self) -> None:
        t = FootyStatsTeam(team_id=1, name="Test")
        assert t.clean_name is None

    def test_league_construct(self) -> None:
        lg = FootyStatsLeague(league_id=1, name="PL", season="2024")
        assert lg.total_matches is None

    def test_player_construct(self) -> None:
        p = FootyStatsPlayer(player_id=1, full_name="Test Player")
        assert p.position is None

    def test_referee_construct(self) -> None:
        r = FootyStatsReferee(referee_id=1, full_name="Ref")
        assert r.cards_per_match_overall is None

    def test_btts_construct(self) -> None:
        b = FootyStatsBTTS(match_id=1, btts=True)
        assert b.btts is True

    def test_over_under_construct(self) -> None:
        ou = FootyStatsOverUnder(match_id=1)
        assert ou.over25 is None

    def test_odds_construct(self) -> None:
        o = FootyStatsOdds(
            match_id=1,
            market_type="FT Result",
            market_option="1",
            bookmaker="bet365",
            odds_value=1.5,
        )
        assert o.odds_value == 1.5


@pytest.mark.unit
class TestUnderstatSchemas:
    def test_match_from_raw(self) -> None:
        m = UnderstatMatch.from_raw(
            {
                "fixture_id": 1,
                "date": NOW.isoformat(),
                "league": "EPL",
                "season": 2024,
                "is_result": True,
                "home_team_id": 1,
                "home_team_name": "A",
                "away_team_id": 2,
                "away_team_name": "B",
            }
        )
        assert m.league == "EPL"

    def test_shot_construct(self) -> None:
        s = UnderstatShot(
            shot_id=1,
            fixture_id=1,
            player_id=1,
            player_name="Test",
            minute=45,
            result="Goal",
            x=0.8,
            y=0.5,
            xg=0.35,
        )
        assert s.xg == 0.35

    def test_player_season_construct(self) -> None:
        ps = UnderstatPlayerSeason(player_id=1, season=2024, league="EPL")
        assert ps.xg is None

    def test_team_history_construct(self) -> None:
        th = UnderstatTeamHistory(
            team_id=1,
            team_name="A",
            league="EPL",
            season=2024,
            match_date=NOW,
            home_away="h",
            xg=1.5,
            xga=0.8,
            scored=2,
            conceded=1,
            result="w",
            pts=3,
        )
        assert th.pts == 3

    def test_xg_data_construct(self) -> None:
        xg = UnderstatXGData(fixture_id=1, home_xg=1.5, away_xg=0.8)
        assert xg.home_npxg is None


@pytest.mark.unit
class TestSFISchemas:
    def test_match_from_raw(self) -> None:
        m = SFIMatch.from_raw(
            {
                "match_id": "abc123",
                "date": NOW.isoformat(),
                "home_team_id": "h1",
                "home_team_name": "A",
                "away_team_id": "a1",
                "away_team_name": "B",
            }
        )
        assert m.match_id == "abc123"

    def test_league_construct(self) -> None:
        lg = SFILeague(league_id="l1", season_id="s1", league_name="PL")
        assert lg.country_code is None

    def test_team_construct(self) -> None:
        t = SFITeam(team_id="t1", team_name="FC", league_id="l1", season_id="s1")
        assert t.position is None

    def test_dominance_construct(self) -> None:
        d = SFIMatchDominance(match_id="m1", timer="45:00", home_dominance=12.5, away_dominance=7.5)
        assert d.home_dominance == 12.5

    def test_progressive_stats_construct(self) -> None:
        ps = SFIMatchProgressiveStats(match_id="m1", timer="30:00", team="A")
        assert ps.goals is None

    def test_progressive_odds_construct(self) -> None:
        po = SFIMatchProgressiveOdds(match_id="m1", timer="30:00")
        assert po.odds_home is None


@pytest.mark.unit
class TestOpenMeteoSchemas:
    def test_weather_construct(self) -> None:
        w = OpenMeteoWeather(
            latitude=51.5,
            longitude=-0.1,
            temperature_celsius=15.0,
            observation_time_utc=NOW,
        )
        assert w.temperature_celsius == 15.0

    def test_forecast_construct(self) -> None:
        f = OpenMeteoForecast(
            latitude=51.5,
            longitude=-0.1,
            forecast_time_utc=NOW,
            temperature_celsius=16.0,
        )
        assert f.precipitation_mm is None

    def test_weather_at_kickoff_construct(self) -> None:
        wk = WeatherAtKickoff(
            fixture_id="af:1",
            venue_latitude=51.5,
            venue_longitude=-0.1,
            kickoff_utc=NOW,
            temperature_celsius=14.0,
            data_source="open_meteo",
        )
        assert wk.data_source == "open_meteo"

    def test_weather_condition_enum(self) -> None:
        assert WeatherCondition.RAIN == "rain"


@pytest.mark.unit
class TestBetfairSchemas:
    def test_price_construct(self) -> None:
        p = BetfairPrice(price=Decimal("2.50"), size=Decimal("100.00"))
        assert p.price == Decimal("2.50")

    def test_runner_construct(self) -> None:
        r = BetfairRunner(selection_id=12345, runner_name="Man Utd")
        assert r.back_prices == []

    def test_market_construct(self) -> None:
        m = BetfairMarket(market_id="1.234", market_name="Match Odds")
        assert m.runners == []

    def test_order_construct(self) -> None:
        o = BetfairOrder(
            bet_id="b1",
            market_id="1.234",
            selection_id=12345,
            side="BACK",
            price=Decimal("2.50"),
            size=Decimal("50.00"),
            status="EXECUTABLE",
        )
        assert o.side == "BACK"

    def test_exchange_odds_construct(self) -> None:
        eo = BetfairExchangeOdds(
            market_id="1.234",
            selection_id=12345,
            runner_name="Man Utd",
            timestamp_utc=NOW,
        )
        assert eo.best_back_price is None

    def test_market_status_enum(self) -> None:
        assert BetfairMarketStatus.OPEN == "OPEN"


@pytest.mark.unit
class TestPinnacleSchemas:
    def test_event_construct(self) -> None:
        e = PinnacleEvent(event_id=1, sport_id=29, league_id=1, starts=NOW, home="A", away="B")
        assert e.event_id == 1

    def test_line_construct(self) -> None:
        ln = PinnacleLine(event_id=1, period_number=0, line_id=1, market_type="moneyline")
        assert ln.home_odds is None

    def test_matchup_construct(self) -> None:
        m = PinnacleMatchup(event_id=1, starts=NOW, home="A", away="B", league_id=1)
        assert m.moneyline_home is None

    def test_odds_construct(self) -> None:
        o = PinnacleOdds(event_id=1, home="A", away="B", starts=NOW, lines=[])
        assert o.lines == []


@pytest.mark.unit
class TestOddsApiSchemas:
    def test_outcome_construct(self) -> None:
        o = OddsApiOutcome(name="Man Utd", price=2.50)
        assert o.point is None

    def test_market_construct(self) -> None:
        m = OddsApiMarket(
            key="h2h",
            last_update=NOW,
            outcomes=[OddsApiOutcome(name="A", price=1.5)],
        )
        assert len(m.outcomes) == 1

    def test_bookmaker_construct(self) -> None:
        b = OddsApiBookmaker(key="pinnacle", title="Pinnacle", last_update=NOW, markets=[])
        assert b.markets == []

    def test_event_construct(self) -> None:
        e = OddsApiEvent(
            event_id="evt1",
            sport_key="soccer_epl",
            sport_title="EPL",
            commence_time=NOW,
            home_team="A",
            away_team="B",
            bookmakers=[],
        )
        assert e.sport_key == "soccer_epl"

    def test_event_round_trip(self) -> None:
        e = OddsApiEvent(
            event_id="evt1",
            sport_key="soccer_epl",
            sport_title="EPL",
            commence_time=NOW,
            home_team="A",
            away_team="B",
            bookmakers=[],
        )
        data = e.model_dump()
        e2 = OddsApiEvent.model_validate(data)
        assert e == e2
