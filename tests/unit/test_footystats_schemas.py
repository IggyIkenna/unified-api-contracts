"""Verify FT*Raw source schemas: minimal construction, full construction, round-trip, frozen."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.sports.sources.footystats.schemas import (
    FTLeagueStatsRaw,
    FTLineupEventRaw,
    FTLineupRaw,
    FTMatchRaw,
    FTOddsRaw,
    FTPlayerRaw,
    FTRefereeRaw,
    FTTeamRaw,
    FTWeatherRaw,
)


@pytest.mark.unit
class TestFTTeamRaw:
    def test_minimal(self) -> None:
        t = FTTeamRaw(ft_team_id=100)
        assert t.ft_team_id == 100
        assert t.name is None
        assert t.clean_name is None

    def test_full(self) -> None:
        t = FTTeamRaw(
            ft_team_id=100,
            name="Arsenal",
            clean_name="Arsenal",
            english_name="Arsenal FC",
            short_hand="ARS",
            full_name="Arsenal Football Club",
            country="England",
            continent="Europe",
            founded="1886",
            image="https://example.com/arsenal.png",
            competition_id=1625,
            season="2024/2025",
            season_clean="2024/2025",
            table_position=1,
            performance_rank=3,
            risk=45,
            url="/arsenal",
        )
        assert t.name == "Arsenal"
        assert t.table_position == 1
        assert t.country == "England"

    def test_round_trip(self) -> None:
        t = FTTeamRaw(ft_team_id=200, name="Chelsea", country="England")
        data = t.model_dump()
        t2 = FTTeamRaw.model_validate(data)
        assert t == t2

    def test_frozen(self) -> None:
        t = FTTeamRaw(ft_team_id=1)
        with pytest.raises(ValidationError):
            t.name = "Mutated"  # type: ignore[misc]


@pytest.mark.unit
class TestFTMatchRaw:
    def test_minimal(self) -> None:
        m = FTMatchRaw(ft_match_id=999)
        assert m.ft_match_id == 999
        assert m.competition_id is None
        assert m.home_goal_count is None

    def test_full(self) -> None:
        m = FTMatchRaw(
            ft_match_id=999,
            date_unix=1700000000,
            competition_id=1625,
            season="2024/2025",
            status="complete",
            round_id=1,
            game_week=10,
            revised_game_week=10,
            home_id=100,
            away_id=200,
            home_name="Arsenal",
            away_name="Chelsea",
            winning_team=100,
            referee_id=50,
            stadium_name="Emirates",
            attendance=60000,
            # Goals
            home_goal_count=2,
            away_goal_count=1,
            total_goal_count=3,
            ht_goals_team_a=1,
            ht_goals_team_b=0,
            goals_2hg_team_a=1,
            goals_2hg_team_b=1,
            ht_goal_count=1,
            goal_count_2hg=2,
            # Possession
            team_a_possession=58,
            team_b_possession=42,
            # Shots
            team_a_shots=15,
            team_b_shots=8,
            team_a_shots_on_target=6,
            team_b_shots_on_target=3,
            team_a_shots_off_target=9,
            team_b_shots_off_target=5,
            # Corners
            team_a_corners=7,
            team_b_corners=4,
            total_corner_count=11,
            team_a_fh_corners=4,
            team_b_fh_corners=2,
            team_a_2h_corners=3,
            team_b_2h_corners=2,
            # Cards
            team_a_yellow_cards=2,
            team_b_yellow_cards=3,
            team_a_red_cards=0,
            team_b_red_cards=0,
            team_a_cards_num=2,
            team_b_cards_num=3,
            # Fouls
            team_a_fouls=10,
            team_b_fouls=14,
            # xG
            team_a_xg=2.1,
            team_b_xg=0.9,
            total_xg=3.0,
            team_a_xg_prematch=1.8,
            team_b_xg_prematch=1.2,
            total_xg_prematch=3.0,
            # PPG
            home_ppg=2.5,
            away_ppg=1.8,
            pre_match_home_ppg=2.4,
            pre_match_away_ppg=1.7,
            pre_match_team_a_overall_ppg=2.3,
            pre_match_team_b_overall_ppg=1.9,
            # BTTS & potentials
            btts=True,
            btts_potential=72,
            btts_fhg_potential=40,
            btts_2hg_potential=55,
            o25_potential=80,
            o35_potential=45,
            o45_potential=20,
            u25_potential=20,
            avg_potential=60,
            corners_potential=70,
            cards_potential=55,
            offsides_potential=40,
            # Over/under flags
            over25=True,
            over35=False,
            # Odds
            odds_ft_1=1.80,
            odds_ft_x=3.40,
            odds_ft_2=4.50,
            odds_ft_over25=1.70,
            odds_ft_under25=2.10,
            odds_btts_yes=1.65,
            odds_btts_no=2.15,
            odds_doublechance_1x=1.25,
            odds_dnb_1=1.40,
            odds_dnb_2=2.80,
            # Attacks
            team_a_dangerous_attacks=55,
            team_b_dangerous_attacks=38,
            team_a_attacks=120,
            team_b_attacks=95,
            # Offsides
            team_a_offsides=3,
            team_b_offsides=2,
            # Goal timings
            home_goals_timings="[12, 78]",
            away_goals_timings="[55]",
        )
        assert m.home_goal_count == 2
        assert m.team_a_xg == 2.1
        assert m.btts is True
        assert m.odds_ft_1 == 1.80

    def test_round_trip(self) -> None:
        m = FTMatchRaw(ft_match_id=1, competition_id=10, home_id=1, away_id=2)
        data = m.model_dump()
        m2 = FTMatchRaw.model_validate(data)
        assert m == m2

    def test_frozen(self) -> None:
        m = FTMatchRaw(ft_match_id=1)
        with pytest.raises(ValidationError):
            m.home_goal_count = 5  # type: ignore[misc]


@pytest.mark.unit
class TestFTRefereeRaw:
    def test_minimal(self) -> None:
        r = FTRefereeRaw(ft_referee_id=50)
        assert r.ft_referee_id == 50
        assert r.full_name is None
        assert r.cards_per_match_overall is None

    def test_full(self) -> None:
        r = FTRefereeRaw(
            ft_referee_id=50,
            competition_id=1625,
            season="2024/2025",
            full_name="Michael Oliver",
            known_as="M. Oliver",
            nationality="England",
            age=39,
            league="Premier League",
            appearances_overall=20,
            wins_home=8,
            wins_away=6,
            draws_overall=6,
            btts_overall=12,
            btts_percentage=60,
            goals_per_match_overall=2.8,
            cards_overall=80,
            cards_per_match_overall=4.0,
            yellow_cards_overall=74,
            red_cards_overall=6,
            penalties_given_overall=3,
            min_per_card_overall=22,
        )
        assert r.full_name == "Michael Oliver"
        assert r.cards_per_match_overall == 4.0

    def test_round_trip(self) -> None:
        r = FTRefereeRaw(ft_referee_id=1, full_name="Test Ref")
        data = r.model_dump()
        r2 = FTRefereeRaw.model_validate(data)
        assert r == r2


@pytest.mark.unit
class TestFTLeagueStatsRaw:
    def test_minimal(self) -> None:
        ls = FTLeagueStatsRaw(ft_league_id=1625)
        assert ls.ft_league_id == 1625
        assert ls.season is None
        assert ls.xg_avg is None

    def test_full(self) -> None:
        ls = FTLeagueStatsRaw(
            ft_league_id=1625,
            season="2024/2025",
            name="Premier League",
            english_name="Premier League",
            country="England",
            division=1,
            status="active",
            total_matches=380,
            matches_completed=200,
            club_num=20,
            total_goals=520,
            season_avg_overall=2.6,
            season_avg_home=1.5,
            season_avg_away=1.1,
            btts_matches=110,
            season_btts_percentage=55,
            season_cs_percentage=25,
            season_over15_percentage_overall=75,
            season_over25_percentage_overall=55,
            season_over35_percentage_overall=30,
            corners_avg_overall=10.5,
            corners_avg_home=5.8,
            corners_avg_away=4.7,
            corners_total_overall=2100,
            cards_avg_overall=3.8,
            cards_avg_home=2.0,
            cards_avg_away=1.8,
            cards_total_overall=760,
            shots_avg_overall=24.0,
            shots_total_overall=4800,
            fouls_avg_overall=22.0,
            fouls_total_overall=4400,
            home_wins=85,
            draws=55,
            away_wins=60,
            home_win_percentage=43,
            draw_percentage=27,
            away_win_percentage=30,
            xg_avg=2.5,
        )
        assert ls.season_avg_overall == 2.6
        assert ls.corners_avg_overall == 10.5
        assert ls.home_wins == 85

    def test_round_trip(self) -> None:
        ls = FTLeagueStatsRaw(ft_league_id=1, season="2024")
        data = ls.model_dump()
        ls2 = FTLeagueStatsRaw.model_validate(data)
        assert ls == ls2


@pytest.mark.unit
class TestFTWeatherRaw:
    def test_minimal(self) -> None:
        w = FTWeatherRaw(ft_match_id=999)
        assert w.ft_match_id == 999
        assert w.wind_speed is None

    def test_full(self) -> None:
        w = FTWeatherRaw(
            ft_match_id=999,
            wind_speed="11.5 m/s",
            wind_degree=220,
            lat=51.5,
            lon=-0.1,
            weather_type="few clouds",
            weather_code="clouds",
            temp_fahrenheit=59.0,
            temp_celsius=15.0,
            pressure=1013,
            clouds="20%",
            humidity="55%",
        )
        assert w.temp_celsius == 15.0
        assert w.weather_type == "few clouds"

    def test_round_trip(self) -> None:
        w = FTWeatherRaw(ft_match_id=1, temp_celsius=20.0, humidity="60%")
        data = w.model_dump()
        w2 = FTWeatherRaw.model_validate(data)
        assert w == w2


@pytest.mark.unit
class TestFTOddsRaw:
    def test_minimal(self) -> None:
        o = FTOddsRaw(ft_match_id=999)
        assert o.ft_match_id == 999
        assert o.odds_value is None

    def test_full(self) -> None:
        o = FTOddsRaw(
            ft_match_id=999,
            market_type="FT Result",
            market_option="1",
            bookmaker="bet365",
            odds_value=Decimal("1.85"),
        )
        assert o.odds_value == Decimal("1.85")
        assert o.bookmaker == "bet365"

    def test_round_trip(self) -> None:
        o = FTOddsRaw(
            ft_match_id=1,
            market_type="Over/Under",
            market_option="Over 2.5",
            bookmaker="Unibet",
            odds_value=Decimal("1.70"),
        )
        data = o.model_dump()
        o2 = FTOddsRaw.model_validate(data)
        assert o == o2


@pytest.mark.unit
class TestFTPlayerRaw:
    def test_minimal(self) -> None:
        p = FTPlayerRaw(ft_player_id=1001)
        assert p.ft_player_id == 1001
        assert p.full_name is None
        assert p.goals_overall is None

    def test_full(self) -> None:
        p = FTPlayerRaw(
            ft_player_id=1001,
            competition_id=1625,
            season="2024/2025",
            full_name="Bukayo Saka",
            known_as="Saka",
            position="Forward",
            nationality="England",
            age=23,
            club_team_id=100,
            appearances_overall=25,
            appearances_home=13,
            appearances_away=12,
            minutes_played_overall=2100,
            goals_overall=10,
            goals_home=6,
            goals_away=4,
            goals_per_90_overall=0.43,
            assists_overall=8,
            assists_per_90_overall=0.34,
            goals_involved_per_90_overall=0.77,
            clean_sheets_overall=8,
            conceded_overall=18,
            conceded_per_90_overall=0.77,
            cards_overall=3,
            yellow_cards_overall=3,
            red_cards_overall=0,
            cards_per_90_overall=0.13,
            penalty_goals=2,
            penalty_misses=0,
            rank_in_league_top_attackers=5,
            rank_in_club_top_scorer=2,
        )
        assert p.full_name == "Bukayo Saka"
        assert p.goals_per_90_overall == 0.43
        assert p.rank_in_club_top_scorer == 2

    def test_round_trip(self) -> None:
        p = FTPlayerRaw(ft_player_id=1, full_name="Test", position="Midfielder")
        data = p.model_dump()
        p2 = FTPlayerRaw.model_validate(data)
        assert p == p2


@pytest.mark.unit
class TestFTLineupRaw:
    def test_minimal(self) -> None:
        ln = FTLineupRaw(ft_match_id=999)
        assert ln.ft_match_id == 999
        assert ln.ft_team_id is None
        assert ln.is_starting is None

    def test_full(self) -> None:
        ln = FTLineupRaw(
            ft_match_id=999,
            ft_team_id=100,
            ft_player_id=1001,
            shirt_number=7,
            is_starting=True,
            ft_player_out_id=None,
            player_out_time=None,
        )
        assert ln.is_starting is True
        assert ln.shirt_number == 7

    def test_substitute(self) -> None:
        ln = FTLineupRaw(
            ft_match_id=999,
            ft_team_id=100,
            ft_player_id=1002,
            shirt_number=14,
            is_starting=False,
            ft_player_out_id=1001,
            player_out_time="70'",
        )
        assert ln.is_starting is False
        assert ln.ft_player_out_id == 1001
        assert ln.player_out_time == "70'"

    def test_round_trip(self) -> None:
        ln = FTLineupRaw(ft_match_id=1, ft_team_id=10, ft_player_id=100, is_starting=True)
        data = ln.model_dump()
        ln2 = FTLineupRaw.model_validate(data)
        assert ln == ln2


@pytest.mark.unit
class TestFTLineupEventRaw:
    def test_minimal(self) -> None:
        e = FTLineupEventRaw(ft_match_id=999)
        assert e.ft_match_id == 999
        assert e.event_type is None

    def test_full(self) -> None:
        e = FTLineupEventRaw(
            ft_match_id=999,
            ft_team_id=100,
            ft_player_id=1001,
            event_type="Goal",
            event_time="45",
        )
        assert e.event_type == "Goal"
        assert e.event_time == "45"

    def test_card_event(self) -> None:
        e = FTLineupEventRaw(
            ft_match_id=999,
            ft_team_id=200,
            ft_player_id=2001,
            event_type="Yellow",
            event_time="28",
        )
        assert e.event_type == "Yellow"

    def test_round_trip(self) -> None:
        e = FTLineupEventRaw(ft_match_id=1, event_type="Red", event_time="90+4'")
        data = e.model_dump()
        e2 = FTLineupEventRaw.model_validate(data)
        assert e == e2
