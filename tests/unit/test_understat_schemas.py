"""Unit tests for raw US* Understat schemas (Stream B3 migration)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.unified_api_contracts_external.sports.sources.understat.schemas import (
    USMatchRaw,
    USMatchRosterRaw,
    USMatchShotRaw,
    USPlayerMatchRaw,
    USPlayerRaw,
    USPlayerSeasonRaw,
    USPlayerShotRaw,
    USTeamHistoryRaw,
    USTeamRaw,
)

# ---------------------------------------------------------------------------
# USTeamRaw
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUSTeamRaw:
    def test_construct_minimal(self) -> None:
        t = USTeamRaw(us_team_id=89, team_name="Arsenal", league="EPL", season="2024")
        assert t.us_team_id == 89
        assert t.team_name == "Arsenal"
        assert t.matches_fetched is None
        assert t.roster_fetched is None

    def test_construct_full(self) -> None:
        t = USTeamRaw(
            us_team_id=89,
            team_name="Arsenal",
            league="EPL",
            season="2024",
            matches_fetched=True,
            roster_fetched=False,
        )
        assert t.matches_fetched is True
        assert t.roster_fetched is False

    def test_from_raw(self) -> None:
        t = USTeamRaw.from_raw({"us_team_id": 89, "team_name": "Arsenal", "league": "EPL", "season": "2024"})
        assert t.us_team_id == 89

    def test_frozen(self) -> None:
        t = USTeamRaw(us_team_id=89, team_name="Arsenal", league="EPL", season="2024")
        with pytest.raises(ValidationError):
            t.team_name = "Chelsea"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        t = USTeamRaw(us_team_id=89, team_name="Arsenal", league="EPL", season="2024")
        t2 = USTeamRaw.model_validate(t.model_dump())
        assert t == t2

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            USTeamRaw(us_team_id=89, team_name="Arsenal", league="EPL")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# USTeamHistoryRaw
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUSTeamHistoryRaw:
    def test_construct_minimal(self) -> None:
        th = USTeamHistoryRaw(us_team_id=89, league="EPL", season="2024", match_date="2024-09-15")
        assert th.us_team_id == 89
        assert th.xg is None
        assert th.ppda_att is None

    def test_construct_full(self) -> None:
        th = USTeamHistoryRaw(
            us_team_id=89,
            league="EPL",
            season="2024",
            match_date="2024-09-15",
            xg=1.8,
            xga=0.6,
            npxg=1.5,
            npxga=0.4,
            npxgd=1.1,
            scored=2,
            missed=0,
            pts=3,
            xpts=2.7,
            ppda_att=320.0,
            ppda_def=42.0,
            ppda_allowed_att=280.0,
            ppda_allowed_def=38.0,
            deep=8,
            deep_allowed=3,
        )
        assert th.npxgd == 1.1
        assert th.deep == 8

    def test_from_raw(self) -> None:
        th = USTeamHistoryRaw.from_raw(
            {
                "us_team_id": 89,
                "league": "EPL",
                "season": "2024",
                "match_date": "2024-09-15",
                "xg": 1.8,
                "scored": 2,
            }
        )
        assert th.xg == 1.8

    def test_round_trip(self) -> None:
        th = USTeamHistoryRaw(us_team_id=89, league="EPL", season="2024", match_date="2024-09-15")
        th2 = USTeamHistoryRaw.model_validate(th.model_dump())
        assert th == th2


# ---------------------------------------------------------------------------
# USMatchRaw
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUSMatchRaw:
    def test_construct_minimal(self) -> None:
        m = USMatchRaw(
            us_fixture_id=12345,
            home_team="Arsenal",
            away_team="Chelsea",
            league="EPL",
            season="2024",
        )
        assert m.us_fixture_id == 12345
        assert m.home_goals is None
        assert m.forecast_home is None

    def test_construct_full(self) -> None:
        m = USMatchRaw(
            us_fixture_id=12345,
            home_team="Arsenal",
            away_team="Chelsea",
            home_goals=3,
            away_goals=1,
            home_xg=2.5,
            away_xg=0.8,
            forecast_home=0.65,
            forecast_draw=0.20,
            forecast_away=0.15,
            league="EPL",
            season="2024",
        )
        assert m.home_xg == 2.5
        assert m.forecast_away == 0.15

    def test_from_raw(self) -> None:
        m = USMatchRaw.from_raw(
            {
                "us_fixture_id": 12345,
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "league": "EPL",
                "season": "2024",
                "home_goals": 3,
            }
        )
        assert m.home_goals == 3

    def test_round_trip(self) -> None:
        m = USMatchRaw(
            us_fixture_id=1,
            home_team="A",
            away_team="B",
            league="EPL",
            season="2024",
        )
        m2 = USMatchRaw.model_validate(m.model_dump())
        assert m == m2


# ---------------------------------------------------------------------------
# USPlayerRaw
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUSPlayerRaw:
    def test_construct_minimal(self) -> None:
        p = USPlayerRaw(us_player_id=882, team_name="Arsenal")
        assert p.us_player_id == 882
        assert p.position is None
        assert p.xg is None

    def test_construct_full(self) -> None:
        p = USPlayerRaw(
            us_player_id=882,
            team_name="Arsenal",
            position="FW",
            games=30,
            minutes=2500,
            goals=18,
            assists=7,
            shots=90,
            key_passes=40,
            yellow_cards=3,
            red_cards=0,
            xg=16.5,
            xa=6.2,
            npg=15.0,
            npxg=14.8,
            xg_chain=20.1,
            xg_buildup=8.3,
        )
        assert p.goals == 18
        assert p.npxg == 14.8

    def test_from_raw(self) -> None:
        p = USPlayerRaw.from_raw({"us_player_id": 882, "team_name": "Arsenal", "goals": 18})
        assert p.goals == 18

    def test_round_trip(self) -> None:
        p = USPlayerRaw(us_player_id=882, team_name="Arsenal")
        p2 = USPlayerRaw.model_validate(p.model_dump())
        assert p == p2


# ---------------------------------------------------------------------------
# USMatchShotRaw
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUSMatchShotRaw:
    def test_construct_minimal(self) -> None:
        s = USMatchShotRaw(
            us_fixture_id=12345,
            us_shot_id=99001,
            minute=23,
            result="Goal",
            x=0.88,
            y=0.45,
        )
        assert s.us_shot_id == 99001
        assert s.xg is None
        assert s.team is None

    def test_construct_full(self) -> None:
        s = USMatchShotRaw(
            us_fixture_id=12345,
            us_shot_id=99001,
            minute=23,
            result="Goal",
            x=0.88,
            y=0.45,
            xg=0.76,
            player_name="Saka",
            situation="OpenPlay",
            shot_type="RightFoot",
            last_action="Pass",
            team="Arsenal",
        )
        assert s.xg == 0.76
        assert s.shot_type == "RightFoot"

    def test_from_raw(self) -> None:
        s = USMatchShotRaw.from_raw(
            {
                "us_fixture_id": 12345,
                "us_shot_id": 99001,
                "minute": 23,
                "result": "Goal",
                "x": 0.88,
                "y": 0.45,
                "xg": 0.76,
            }
        )
        assert s.xg == 0.76

    def test_round_trip(self) -> None:
        s = USMatchShotRaw(us_fixture_id=1, us_shot_id=1, minute=10, result="Saved", x=0.5, y=0.5)
        s2 = USMatchShotRaw.model_validate(s.model_dump())
        assert s == s2


# ---------------------------------------------------------------------------
# USMatchRosterRaw
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUSMatchRosterRaw:
    def test_construct_minimal(self) -> None:
        r = USMatchRosterRaw(us_fixture_id=12345, us_player_id=882)
        assert r.position is None
        assert r.sub_in is None

    def test_construct_full(self) -> None:
        r = USMatchRosterRaw(
            us_fixture_id=12345,
            us_player_id=882,
            position="FW",
            minutes=78,
            goals=1,
            assists=1,
            shots=4,
            key_passes=2,
            yellow_cards=0,
            red_cards=0,
            xg=0.85,
            xa=0.42,
            xg_chain=1.2,
            xg_buildup=0.6,
            sub_in=65,
            sub_out=None,
        )
        assert r.minutes == 78
        assert r.xg_chain == 1.2

    def test_from_raw(self) -> None:
        r = USMatchRosterRaw.from_raw({"us_fixture_id": 12345, "us_player_id": 882, "minutes": 90})
        assert r.minutes == 90

    def test_round_trip(self) -> None:
        r = USMatchRosterRaw(us_fixture_id=1, us_player_id=1)
        r2 = USMatchRosterRaw.model_validate(r.model_dump())
        assert r == r2


# ---------------------------------------------------------------------------
# USPlayerShotRaw
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUSPlayerShotRaw:
    def test_construct_minimal(self) -> None:
        s = USPlayerShotRaw(
            us_player_id=882,
            us_shot_id=99001,
            us_fixture_id=12345,
            minute=23,
            result="Goal",
            x=0.88,
            y=0.45,
        )
        assert s.us_player_id == 882
        assert s.xg is None
        assert s.season is None

    def test_construct_full(self) -> None:
        s = USPlayerShotRaw(
            us_player_id=882,
            us_shot_id=99001,
            us_fixture_id=12345,
            minute=23,
            result="Goal",
            x=0.88,
            y=0.45,
            xg=0.76,
            situation="OpenPlay",
            shot_type="RightFoot",
            season="2024",
        )
        assert s.situation == "OpenPlay"

    def test_from_raw(self) -> None:
        s = USPlayerShotRaw.from_raw(
            {
                "us_player_id": 882,
                "us_shot_id": 99001,
                "us_fixture_id": 12345,
                "minute": 23,
                "result": "Saved",
                "x": 0.5,
                "y": 0.5,
            }
        )
        assert s.result == "Saved"

    def test_round_trip(self) -> None:
        s = USPlayerShotRaw(us_player_id=1, us_shot_id=1, us_fixture_id=1, minute=1, result="Goal", x=0.5, y=0.5)
        s2 = USPlayerShotRaw.model_validate(s.model_dump())
        assert s == s2


# ---------------------------------------------------------------------------
# USPlayerMatchRaw
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUSPlayerMatchRaw:
    def test_construct_minimal(self) -> None:
        pm = USPlayerMatchRaw(us_player_id=882, us_fixture_id=12345)
        assert pm.goals is None
        assert pm.xg is None

    def test_construct_full(self) -> None:
        pm = USPlayerMatchRaw(
            us_player_id=882,
            us_fixture_id=12345,
            position="FW",
            games=1,
            minutes=90,
            goals=2,
            assists=1,
            shots=5,
            key_passes=3,
            yellow_cards=0,
            red_cards=0,
            xg=1.5,
            xa=0.8,
            npg=2.0,
            npxg=1.3,
            xg_chain=2.0,
            xg_buildup=1.1,
        )
        assert pm.goals == 2
        assert pm.npxg == 1.3

    def test_from_raw(self) -> None:
        pm = USPlayerMatchRaw.from_raw({"us_player_id": 882, "us_fixture_id": 12345, "goals": 2, "xg": 1.5})
        assert pm.xg == 1.5

    def test_round_trip(self) -> None:
        pm = USPlayerMatchRaw(us_player_id=1, us_fixture_id=1)
        pm2 = USPlayerMatchRaw.model_validate(pm.model_dump())
        assert pm == pm2


# ---------------------------------------------------------------------------
# USPlayerSeasonRaw
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUSPlayerSeasonRaw:
    def test_construct_minimal(self) -> None:
        ps = USPlayerSeasonRaw(us_player_id=882, season="2024", league="EPL")
        assert ps.team is None
        assert ps.xg is None

    def test_construct_full(self) -> None:
        ps = USPlayerSeasonRaw(
            us_player_id=882,
            season="2024",
            league="EPL",
            team="Arsenal",
            games=30,
            minutes=2500,
            goals=18,
            assists=7,
            shots=90,
            key_passes=40,
            yellow_cards=3,
            red_cards=0,
            xg=16.5,
            xa=6.2,
            npg=15.0,
            npxg=14.8,
            xg_chain=20.1,
            xg_buildup=8.3,
        )
        assert ps.team == "Arsenal"
        assert ps.xg_buildup == 8.3

    def test_from_raw(self) -> None:
        ps = USPlayerSeasonRaw.from_raw({"us_player_id": 882, "season": "2024", "league": "EPL", "team": "Arsenal"})
        assert ps.team == "Arsenal"

    def test_round_trip(self) -> None:
        ps = USPlayerSeasonRaw(us_player_id=1, season="2024", league="EPL")
        ps2 = USPlayerSeasonRaw.model_validate(ps.model_dump())
        assert ps == ps2

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            USPlayerSeasonRaw(us_player_id=882, season="2024")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Cross-cutting: __init__.py re-exports
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInitExports:
    """Verify all Raw schemas are importable from the package __init__."""

    def test_import_from_package(self) -> None:
        from unified_api_contracts.unified_api_contracts_external.sports.sources.understat import (
            USMatchRaw as _USMatchRaw,
        )
        from unified_api_contracts.unified_api_contracts_external.sports.sources.understat import (
            USMatchRosterRaw as _USMatchRosterRaw,
        )
        from unified_api_contracts.unified_api_contracts_external.sports.sources.understat import (
            USMatchShotRaw as _USMatchShotRaw,
        )
        from unified_api_contracts.unified_api_contracts_external.sports.sources.understat import (
            USPlayerMatchRaw as _USPlayerMatchRaw,
        )
        from unified_api_contracts.unified_api_contracts_external.sports.sources.understat import (
            USPlayerRaw as _USPlayerRaw,
        )
        from unified_api_contracts.unified_api_contracts_external.sports.sources.understat import (
            USPlayerSeasonRaw as _USPlayerSeasonRaw,
        )
        from unified_api_contracts.unified_api_contracts_external.sports.sources.understat import (
            USPlayerShotRaw as _USPlayerShotRaw,
        )
        from unified_api_contracts.unified_api_contracts_external.sports.sources.understat import (
            USTeamHistoryRaw as _USTeamHistoryRaw,
        )
        from unified_api_contracts.unified_api_contracts_external.sports.sources.understat import (
            USTeamRaw as _USTeamRaw,
        )

        # Verify they are the same classes
        assert _USTeamRaw is USTeamRaw
        assert _USMatchRaw is USMatchRaw
        assert _USPlayerRaw is USPlayerRaw
        assert _USMatchShotRaw is USMatchShotRaw
        assert _USMatchRosterRaw is USMatchRosterRaw
        assert _USPlayerShotRaw is USPlayerShotRaw
        assert _USPlayerMatchRaw is USPlayerMatchRaw
        assert _USPlayerSeasonRaw is USPlayerSeasonRaw
        assert _USTeamHistoryRaw is USTeamHistoryRaw
