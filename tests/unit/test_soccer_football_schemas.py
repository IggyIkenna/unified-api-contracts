"""Unit tests for SF*Raw Soccer Football Info source schemas.

Validates construction, from_raw() parsing, frozen immutability, round-trip
serialisation, and Decimal precision for all seven raw models.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.external.sports.sources.soccer_football_info.schemas import (
    SFLeagueRaw,
    SFMatchDominanceRaw,
    SFMatchEventRaw,
    SFMatchProgressiveOddsRaw,
    SFMatchProgressiveStatsRaw,
    SFMatchRaw,
    SFTeamRaw,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# SFLeagueRaw
# ---------------------------------------------------------------------------


class TestSFLeagueRaw:
    def test_construct_required_only(self) -> None:
        lg = SFLeagueRaw(
            sf_league_id="eb57e70ef2e7077e",
            sf_season_id="c625dc22edd8645e",
            league_name="Premier League",
        )
        assert lg.sf_league_id == "eb57e70ef2e7077e"
        assert lg.country_code is None
        assert lg.teams_fetched is None

    def test_construct_full(self) -> None:
        lg = SFLeagueRaw(
            sf_league_id="eb57",
            sf_season_id="c625",
            league_name="PL",
            country_code="GB",
            has_image=True,
            important=True,
            af_league_id=39,
            af_season=2024,
            teams_fetched=True,
            matches_fetched=False,
        )
        assert lg.af_league_id == 39
        assert lg.teams_fetched is True
        assert lg.matches_fetched is False

    def test_from_raw(self) -> None:
        lg = SFLeagueRaw.from_raw(
            {
                "sf_league_id": "abc",
                "sf_season_id": "def",
                "league_name": "La Liga",
                "country_code": "ES",
                "af_league_id": 140,
            }
        )
        assert lg.league_name == "La Liga"
        assert lg.af_league_id == 140

    def test_frozen(self) -> None:
        lg = SFLeagueRaw(sf_league_id="a", sf_season_id="b", league_name="PL")
        with pytest.raises(ValidationError):
            lg.league_name = "Changed"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        lg = SFLeagueRaw(sf_league_id="a", sf_season_id="b", league_name="PL")
        data = lg.model_dump()
        lg2 = SFLeagueRaw.model_validate(data)
        assert lg == lg2


# ---------------------------------------------------------------------------
# SFTeamRaw
# ---------------------------------------------------------------------------


class TestSFTeamRaw:
    def test_construct_required_only(self) -> None:
        t = SFTeamRaw(
            sf_team_id="t1",
            sf_league_id="l1",
            sf_season_id="s1",
            team_name="Arsenal",
        )
        assert t.team_name == "Arsenal"
        assert t.wins is None
        assert t.af_team_id is None

    def test_construct_full(self) -> None:
        t = SFTeamRaw(
            sf_team_id="t1",
            sf_league_id="l1",
            sf_season_id="s1",
            team_name="Arsenal",
            wins=20,
            draws=5,
            losses=3,
            points=65,
            goals_scored=60,
            goals_conceded=25,
            af_team_id=42,
            position=1,
        )
        assert t.wins == 20
        assert t.points == 65
        assert t.position == 1

    def test_from_raw(self) -> None:
        t = SFTeamRaw.from_raw(
            {
                "sf_team_id": "t2",
                "sf_league_id": "l1",
                "sf_season_id": "s1",
                "team_name": "Chelsea",
                "wins": 15,
                "draws": 8,
                "losses": 5,
            }
        )
        assert t.team_name == "Chelsea"
        assert t.wins == 15

    def test_frozen(self) -> None:
        t = SFTeamRaw(sf_team_id="t1", sf_league_id="l1", sf_season_id="s1", team_name="X")
        with pytest.raises(ValidationError):
            t.team_name = "Y"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        t = SFTeamRaw(sf_team_id="t1", sf_league_id="l1", sf_season_id="s1", team_name="X")
        data = t.model_dump()
        t2 = SFTeamRaw.model_validate(data)
        assert t == t2


# ---------------------------------------------------------------------------
# SFMatchRaw
# ---------------------------------------------------------------------------


class TestSFMatchRaw:
    def test_construct_required_only(self) -> None:
        m = SFMatchRaw(
            sf_match_id="m1",
            date="2024-12-01T15:00:00",
            sf_home_id="h1",
            home_name="Arsenal",
            sf_away_id="a1",
            away_name="Chelsea",
        )
        assert m.sf_match_id == "m1"
        assert m.ft_home is None
        assert m.odds_start_home is None

    def test_construct_with_scores_and_stats(self) -> None:
        m = SFMatchRaw(
            sf_match_id="m2",
            date="2024-12-01T15:00:00",
            sf_home_id="h1",
            home_name="Arsenal",
            sf_away_id="a1",
            away_name="Chelsea",
            ft_home=2,
            ft_away=1,
            ht_home=1,
            ht_away=0,
            home_possession=55,
            away_possession=45,
            home_shots_on=6,
            away_shots_on=3,
            home_corners=7,
            away_corners=4,
            home_xg_kickoff=1.8,
            away_xg_kickoff=0.9,
        )
        assert m.ft_home == 2
        assert m.ft_away == 1
        assert m.home_possession == 55
        assert m.home_xg_kickoff == 1.8

    def test_construct_with_decimal_odds(self) -> None:
        m = SFMatchRaw(
            sf_match_id="m3",
            date="2024-12-01",
            sf_home_id="h1",
            home_name="A",
            sf_away_id="a1",
            away_name="B",
            odds_start_home=Decimal("1.85"),
            odds_start_draw=Decimal("3.50"),
            odds_start_away=Decimal("4.20"),
            odds_start_over=Decimal("1.90"),
            odds_start_under=Decimal("1.95"),
            odds_start_ou_line=Decimal("2.5"),
            odds_start_ah_home=Decimal("1.92"),
            odds_start_ah_away=Decimal("1.88"),
            odds_start_ah_line="-0.5",
            odds_kick_home=Decimal("1.80"),
            odds_kick_draw=Decimal("3.60"),
            odds_kick_away=Decimal("4.30"),
            odds_kick_over=Decimal("1.88"),
            odds_kick_under=Decimal("1.97"),
            odds_kick_ou_line=Decimal("2.5"),
            odds_kick_ah_home=Decimal("1.90"),
            odds_kick_ah_away=Decimal("1.90"),
            odds_kick_ah_line="-0.5",
        )
        assert m.odds_start_home == Decimal("1.85")
        assert m.odds_kick_draw == Decimal("3.60")
        assert m.odds_start_ah_line == "-0.5"

    def test_from_raw(self) -> None:
        m = SFMatchRaw.from_raw(
            {
                "sf_match_id": "m4",
                "date": "2024-12-01",
                "sf_home_id": "h1",
                "home_name": "Team A",
                "sf_away_id": "a1",
                "away_name": "Team B",
                "ft_home": 3,
                "ft_away": 0,
                "af_match_id": 12345,
            }
        )
        assert m.ft_home == 3
        assert m.af_match_id == 12345

    def test_frozen(self) -> None:
        m = SFMatchRaw(
            sf_match_id="m1",
            date="2024-12-01",
            sf_home_id="h1",
            home_name="A",
            sf_away_id="a1",
            away_name="B",
        )
        with pytest.raises(ValidationError):
            m.ft_home = 5  # type: ignore[misc]

    def test_round_trip(self) -> None:
        m = SFMatchRaw(
            sf_match_id="m1",
            date="2024-12-01",
            sf_home_id="h1",
            home_name="A",
            sf_away_id="a1",
            away_name="B",
            odds_start_home=Decimal("2.10"),
        )
        data = m.model_dump()
        m2 = SFMatchRaw.model_validate(data)
        assert m == m2

    def test_all_score_fields(self) -> None:
        m = SFMatchRaw(
            sf_match_id="m5",
            date="2024-12-01",
            sf_home_id="h1",
            home_name="A",
            sf_away_id="a1",
            away_name="B",
            ft_home=2,
            ft_away=2,
            ht_home=1,
            ht_away=1,
            ot_home=1,
            ot_away=0,
            pen_home=4,
            pen_away=3,
        )
        assert m.ot_home == 1
        assert m.pen_away == 3


# ---------------------------------------------------------------------------
# SFMatchEventRaw
# ---------------------------------------------------------------------------


class TestSFMatchEventRaw:
    def test_construct(self) -> None:
        e = SFMatchEventRaw(sf_match_id="m1", event_type="goal", timer="45+2", team="A")
        assert e.event_type == "goal"
        assert e.team == "A"

    def test_from_raw(self) -> None:
        e = SFMatchEventRaw.from_raw({"sf_match_id": "m1", "event_type": "yellow_card", "timer": "32", "team": "B"})
        assert e.event_type == "yellow_card"
        assert e.timer == "32"

    def test_frozen(self) -> None:
        e = SFMatchEventRaw(sf_match_id="m1", event_type="corner", timer="10", team="A")
        with pytest.raises(ValidationError):
            e.team = "B"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        e = SFMatchEventRaw(sf_match_id="m1", event_type="goal", timer="90", team="B")
        data = e.model_dump()
        e2 = SFMatchEventRaw.model_validate(data)
        assert e == e2


# ---------------------------------------------------------------------------
# SFMatchDominanceRaw
# ---------------------------------------------------------------------------


class TestSFMatchDominanceRaw:
    def test_construct(self) -> None:
        d = SFMatchDominanceRaw(sf_match_id="m1", timer="45:00", team_a_dominance=12.5, team_b_dominance=7.5)
        assert d.team_a_dominance == 12.5
        assert d.team_b_dominance == 7.5

    def test_from_raw(self) -> None:
        d = SFMatchDominanceRaw.from_raw(
            {
                "sf_match_id": "m1",
                "timer": "30:00",
                "team_a_dominance": 15.2,
                "team_b_dominance": 4.8,
            }
        )
        assert d.timer == "30:00"
        assert d.team_a_dominance == 15.2

    def test_frozen(self) -> None:
        d = SFMatchDominanceRaw(sf_match_id="m1", timer="10:00", team_a_dominance=10.0, team_b_dominance=10.0)
        with pytest.raises(ValidationError):
            d.team_a_dominance = 20.0  # type: ignore[misc]

    def test_round_trip(self) -> None:
        d = SFMatchDominanceRaw(sf_match_id="m1", timer="60:00", team_a_dominance=8.0, team_b_dominance=12.0)
        data = d.model_dump()
        d2 = SFMatchDominanceRaw.model_validate(data)
        assert d == d2


# ---------------------------------------------------------------------------
# SFMatchProgressiveStatsRaw
# ---------------------------------------------------------------------------


class TestSFMatchProgressiveStatsRaw:
    def test_construct_required_only(self) -> None:
        ps = SFMatchProgressiveStatsRaw(sf_match_id="m1", timer="30:00", team="A")
        assert ps.goals is None
        assert ps.possession is None
        assert ps.dominance is None

    def test_construct_full(self) -> None:
        ps = SFMatchProgressiveStatsRaw(
            sf_match_id="m1",
            timer="45:00",
            team="A",
            goals=1,
            possession=58,
            attacks=45,
            dangerous_attacks=12,
            shots_total=8,
            shots_on_target=4,
            shots_off_target=3,
            shots_goal_attempts=5,
            penalties=0,
            corners=4,
            fouls=7,
            yellow_cards=1,
            yellow_then_red=0,
            red_cards=0,
            substitutions=1,
            throwins=10,
            injuries=0,
            offsides=2,
            dominance=14.5,
            dominance_avg=13.2,
        )
        assert ps.goals == 1
        assert ps.possession == 58
        assert ps.dominance == 14.5
        assert ps.shots_goal_attempts == 5

    def test_from_raw(self) -> None:
        ps = SFMatchProgressiveStatsRaw.from_raw(
            {
                "sf_match_id": "m1",
                "timer": "60:00",
                "team": "B",
                "goals": 0,
                "possession": 42,
                "corners": 2,
                "fouls": 9,
            }
        )
        assert ps.team == "B"
        assert ps.possession == 42

    def test_frozen(self) -> None:
        ps = SFMatchProgressiveStatsRaw(sf_match_id="m1", timer="10:00", team="A")
        with pytest.raises(ValidationError):
            ps.goals = 1  # type: ignore[misc]

    def test_round_trip(self) -> None:
        ps = SFMatchProgressiveStatsRaw(sf_match_id="m1", timer="45:00", team="A", goals=2, corners=5)
        data = ps.model_dump()
        ps2 = SFMatchProgressiveStatsRaw.model_validate(data)
        assert ps == ps2


# ---------------------------------------------------------------------------
# SFMatchProgressiveOddsRaw
# ---------------------------------------------------------------------------


class TestSFMatchProgressiveOddsRaw:
    def test_construct_required_only(self) -> None:
        po = SFMatchProgressiveOddsRaw(sf_match_id="m1", timer="00:00")
        assert po.home_win is None
        assert po.draw is None
        assert po.away_win is None
        assert po.ah_home is None
        assert po.over is None

    def test_construct_full_time_odds(self) -> None:
        po = SFMatchProgressiveOddsRaw(
            sf_match_id="m1",
            timer="30:00",
            home_win=Decimal("1.85"),
            draw=Decimal("3.50"),
            away_win=Decimal("4.20"),
            ah_home=Decimal("1.92"),
            ah_away=Decimal("1.88"),
            ah_line=Decimal("-0.5"),
            over=Decimal("1.90"),
            under=Decimal("1.95"),
            ou_line=Decimal("2.5"),
        )
        assert po.home_win == Decimal("1.85")
        assert po.ah_line == Decimal("-0.5")
        assert po.ou_line == Decimal("2.5")

    def test_construct_first_half_odds(self) -> None:
        po = SFMatchProgressiveOddsRaw(
            sf_match_id="m1",
            timer="10:00",
            h1_home_win=Decimal("2.10"),
            h1_draw=Decimal("2.80"),
            h1_away_win=Decimal("3.50"),
            h1_ah_home=Decimal("1.95"),
            h1_ah_away=Decimal("1.85"),
            h1_ah_line=Decimal("-0.25"),
            h1_over=Decimal("2.20"),
            h1_under=Decimal("1.70"),
            h1_ou_line=Decimal("0.5"),
        )
        assert po.h1_home_win == Decimal("2.10")
        assert po.h1_ah_line == Decimal("-0.25")

    def test_construct_asian_corner(self) -> None:
        po = SFMatchProgressiveOddsRaw(
            sf_match_id="m1",
            timer="20:00",
            ac_over=Decimal("1.85"),
            ac_under=Decimal("1.95"),
            ac_line=Decimal("9.5"),
            h1_ac_over=Decimal("1.90"),
            h1_ac_under=Decimal("1.90"),
            h1_ac_line=Decimal("4.5"),
        )
        assert po.ac_line == Decimal("9.5")
        assert po.h1_ac_line == Decimal("4.5")

    def test_from_raw(self) -> None:
        po = SFMatchProgressiveOddsRaw.from_raw(
            {
                "sf_match_id": "m1",
                "timer": "45:00",
                "home_win": Decimal("2.00"),
                "draw": Decimal("3.20"),
                "away_win": Decimal("3.80"),
            }
        )
        assert po.home_win == Decimal("2.00")
        assert po.draw == Decimal("3.20")

    def test_from_raw_with_float_coercion(self) -> None:
        """Pydantic should coerce float input to Decimal."""
        po = SFMatchProgressiveOddsRaw.from_raw(
            {
                "sf_match_id": "m1",
                "timer": "60:00",
                "home_win": 2.0,
                "draw": 3.2,
            }
        )
        assert isinstance(po.home_win, Decimal)
        assert isinstance(po.draw, Decimal)

    def test_frozen(self) -> None:
        po = SFMatchProgressiveOddsRaw(sf_match_id="m1", timer="00:00")
        with pytest.raises(ValidationError):
            po.home_win = Decimal("1.50")  # type: ignore[misc]

    def test_round_trip(self) -> None:
        po = SFMatchProgressiveOddsRaw(
            sf_match_id="m1",
            timer="30:00",
            home_win=Decimal("1.85"),
            draw=Decimal("3.50"),
            over=Decimal("1.90"),
        )
        data = po.model_dump()
        po2 = SFMatchProgressiveOddsRaw.model_validate(data)
        assert po == po2

    def test_decimal_precision_preserved(self) -> None:
        """Verify Decimal precision is maintained through round-trip."""
        po = SFMatchProgressiveOddsRaw(
            sf_match_id="m1",
            timer="00:00",
            home_win=Decimal("1.333"),
            ah_line=Decimal("-0.25"),
        )
        dumped = po.model_dump()
        restored = SFMatchProgressiveOddsRaw.model_validate(dumped)
        assert restored.home_win == Decimal("1.333")
        assert restored.ah_line == Decimal("-0.25")


# ---------------------------------------------------------------------------
# Import smoke test — verifies __init__.py re-exports
# ---------------------------------------------------------------------------


class TestImportSmoke:
    def test_all_raw_models_importable_from_package(self) -> None:
        import unified_api_contracts.external.sports.sources.soccer_football_info as sfi_pkg

        # Verify package re-exports resolve to the same classes
        assert sfi_pkg.SFLeagueRaw is SFLeagueRaw
        assert sfi_pkg.SFMatchRaw is SFMatchRaw
        assert sfi_pkg.SFTeamRaw is SFTeamRaw
        assert sfi_pkg.SFMatchEventRaw is SFMatchEventRaw
        assert sfi_pkg.SFMatchDominanceRaw is SFMatchDominanceRaw
        assert sfi_pkg.SFMatchProgressiveStatsRaw is SFMatchProgressiveStatsRaw
        assert sfi_pkg.SFMatchProgressiveOddsRaw is SFMatchProgressiveOddsRaw

    def test_all_clean_models_importable_from_package(self) -> None:
        import unified_api_contracts.external.sports.sources.soccer_football_info as sfi_pkg

        assert sfi_pkg.SFILeague is not None
        assert sfi_pkg.SFIMatch is not None
        assert sfi_pkg.SFITeam is not None
        assert sfi_pkg.SFIMatchDominance is not None
        assert sfi_pkg.SFIMatchProgressiveStats is not None
        assert sfi_pkg.SFIMatchProgressiveOdds is not None
