"""Unit tests for api_football flattening normalizers.

Covers ``normalize_api_football_fixture_stats``,
``normalize_api_football_fixture_event``,
``normalize_api_football_lineup``, and ``normalize_api_football_injury`` —
the four functions that explode nested API-Football payloads into flat
parquet-ready rows. Plan:
``unified-trading-pm/plans/active/api_football_minimal_flattening_removal_2026_05_07.plan.md``.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.external.api_football.normalize import (
    normalize_api_football_fixture_event,
    normalize_api_football_fixture_stats,
    normalize_api_football_injury,
    normalize_api_football_lineup,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# normalize_api_football_fixture_stats
# ---------------------------------------------------------------------------


class TestFixtureStatsFlattening:
    """Validate per-team fixture-statistics flattening."""

    def test_full_payload_returns_one_row_with_all_columns(self) -> None:
        """A complete /fixtures/statistics row returns one flat row with
        every closed-set column populated."""
        raw: dict[str, object] = {
            "team": {"id": 33, "name": "Manchester United", "logo": "logo.png"},
            "statistics": [
                {"type": "Shots on Goal", "value": 5},
                {"type": "Shots off Goal", "value": 3},
                {"type": "Total Shots", "value": 12},
                {"type": "Blocked Shots", "value": 2},
                {"type": "Shots insidebox", "value": 8},
                {"type": "Shots outsidebox", "value": 4},
                {"type": "Fouls", "value": 11},
                {"type": "Corner Kicks", "value": 6},
                {"type": "Offsides", "value": 1},
                {"type": "Ball Possession", "value": "55%"},
                {"type": "Yellow Cards", "value": 2},
                {"type": "Red Cards", "value": None},
                {"type": "Goalkeeper Saves", "value": 4},
                {"type": "Total passes", "value": 450},
                {"type": "Passes accurate", "value": 380},
                {"type": "Passes %", "value": "84%"},
                {"type": "expected_goals", "value": "1.85"},
                {"type": "goals_prevented", "value": "0.32"},
            ],
        }
        rows = normalize_api_football_fixture_stats(raw, fixture_id="123")
        assert isinstance(rows, list)
        assert len(rows) == 1
        row = rows[0]
        assert row["fixture_id"] == "123"
        assert row["team_id"] == 33
        assert row["team_name"] == "Manchester United"
        assert row["is_home"] is None  # Caller fills.
        assert row["shots_on_target"] == 5
        assert row["shots_off_target"] == 3
        assert row["shots_total"] == 12
        assert row["shots_blocked"] == 2
        assert row["shots_inside_box"] == 8
        assert row["shots_outside_box"] == 4
        assert row["fouls"] == 11
        assert row["corners"] == 6
        assert row["offsides"] == 1
        assert row["ball_possession_pct"] == 55
        assert row["yellow_cards"] == 2
        assert row["red_cards"] is None
        assert row["goalkeeper_saves"] == 4
        assert row["passes_total"] == 450
        assert row["passes_accurate"] == 380
        assert row["passes_pct"] == 84
        assert row["expected_goals"] == pytest.approx(1.85)
        assert row["goals_prevented"] == pytest.approx(0.32)

    def test_partial_payload_fills_missing_columns_with_none(self) -> None:
        """When the API omits some stat types, missing columns are None."""
        raw: dict[str, object] = {
            "team": {"id": 50, "name": "Arsenal"},
            "statistics": [
                {"type": "Shots on Goal", "value": 7},
                {"type": "Ball Possession", "value": "62%"},
            ],
        }
        rows = normalize_api_football_fixture_stats(raw, fixture_id="42")
        assert len(rows) == 1
        row = rows[0]
        assert row["shots_on_target"] == 7
        assert row["ball_possession_pct"] == 62
        # Missing types get None.
        assert row["shots_off_target"] is None
        assert row["expected_goals"] is None
        assert row["passes_pct"] is None

    def test_unknown_stat_type_silently_ignored(self) -> None:
        """A stat type not in the closed-set map is skipped."""
        raw: dict[str, object] = {
            "team": {"id": 1, "name": "Test FC"},
            "statistics": [
                {"type": "Shots on Goal", "value": 3},
                {"type": "Mystery Stat", "value": "anything"},
            ],
        }
        rows = normalize_api_football_fixture_stats(raw, fixture_id="1")
        assert len(rows) == 1
        assert rows[0]["shots_on_target"] == 3
        assert "Mystery Stat" not in rows[0]

    def test_malformed_input_returns_empty(self) -> None:
        assert normalize_api_football_fixture_stats(None, fixture_id="x") == []  # type: ignore[arg-type]
        assert normalize_api_football_fixture_stats("string", fixture_id="x") == []  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# normalize_api_football_fixture_event
# ---------------------------------------------------------------------------


class TestFixtureEventFlattening:
    """Validate per-event flattening."""

    def test_full_event_returns_one_flat_row(self) -> None:
        raw: dict[str, object] = {
            "time": {"elapsed": 78, "extra": 3},
            "team": {"id": 33, "name": "Manchester United"},
            "player": {"id": 909, "name": "M. Rashford"},
            "assist": {"id": 882, "name": "B. Fernandes"},
            "type": "Goal",
            "detail": "Normal Goal",
            "comments": None,
        }
        rows = normalize_api_football_fixture_event(raw, fixture_id="555")
        assert len(rows) == 1
        row = rows[0]
        assert row["fixture_id"] == "555"
        assert row["time_elapsed"] == 78
        assert row["time_extra"] == 3
        assert row["team_id"] == 33
        assert row["team_name"] == "Manchester United"
        assert row["player_id"] == 909
        assert row["player_name"] == "M. Rashford"
        assert row["assist_id"] == 882
        assert row["assist_name"] == "B. Fernandes"
        assert row["event_type"] == "Goal"
        assert row["event_detail"] == "Normal Goal"
        assert row["comments"] is None

    def test_event_without_assist(self) -> None:
        """Yellow cards / VAR have no assist — assist fields go null."""
        raw: dict[str, object] = {
            "time": {"elapsed": 35, "extra": None},
            "team": {"id": 50, "name": "Arsenal"},
            "player": {"id": 100, "name": "B. Saka"},
            "assist": {"id": None, "name": None},
            "type": "Card",
            "detail": "Yellow Card",
            "comments": "Foul",
        }
        rows = normalize_api_football_fixture_event(raw, fixture_id="42")
        assert len(rows) == 1
        row = rows[0]
        assert row["assist_id"] is None
        assert row["assist_name"] is None
        assert row["event_type"] == "Card"
        assert row["event_detail"] == "Yellow Card"
        assert row["time_extra"] is None

    def test_malformed_input_returns_empty(self) -> None:
        assert normalize_api_football_fixture_event(None, fixture_id="x") == []  # type: ignore[arg-type]
        assert normalize_api_football_fixture_event("invalid", fixture_id="x") == []  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# normalize_api_football_lineup
# ---------------------------------------------------------------------------


class TestLineupFlattening:
    """Validate per-(team, player) lineup flattening."""

    def test_full_lineup_explodes_starters_and_subs(self) -> None:
        """startXI + substitutes both produce per-player rows; coach is
        stamped on every row, not emitted as its own row."""
        raw: dict[str, object] = {
            "team": {"id": 33, "name": "Manchester United"},
            "coach": {"id": 100, "name": "Erik ten Hag"},
            "formation": "4-2-3-1",
            "startXI": [
                {"player": {"id": 1, "name": "GK", "number": 1, "pos": "G", "grid": "1:1"}},
                {"player": {"id": 2, "name": "LB", "number": 3, "pos": "D", "grid": "2:1"}},
                {"player": {"id": 3, "name": "CB1", "number": 4, "pos": "D", "grid": "2:2"}},
            ],
            "substitutes": [
                {"player": {"id": 20, "name": "Sub1", "number": 12, "pos": "M", "grid": None}},
                {"player": {"id": 21, "name": "Sub2", "number": 14, "pos": "F", "grid": None}},
            ],
        }
        rows = normalize_api_football_lineup(raw, fixture_id="555")
        assert len(rows) == 5  # 3 starters + 2 subs
        starters = [r for r in rows if r["is_starter"] is True]
        subs = [r for r in rows if r["is_starter"] is False]
        assert len(starters) == 3
        assert len(subs) == 2
        # Each row carries the team-level fields.
        for row in rows:
            assert row["fixture_id"] == "555"
            assert row["team_id"] == 33
            assert row["team_name"] == "Manchester United"
            assert row["formation"] == "4-2-3-1"
            assert row["coach_id"] == 100
            assert row["coach_name"] == "Erik ten Hag"
        # First starter shape.
        gk = starters[0]
        assert gk["player_id"] == 1
        assert gk["player_pos"] == "G"
        assert gk["player_grid"] == "1:1"
        assert gk["player_number"] == 1
        # Sub with null grid.
        sub = subs[0]
        assert sub["player_id"] == 20
        assert sub["player_grid"] is None

    def test_lineup_without_coach(self) -> None:
        """Lower-tier leagues sometimes omit coach — coach fields go null."""
        raw: dict[str, object] = {
            "team": {"id": 1, "name": "Test FC"},
            "coach": {"id": None, "name": None},
            "formation": "3-5-2",
            "startXI": [{"player": {"id": 99, "name": "P1", "number": 7, "pos": "M", "grid": "3:2"}}],
            "substitutes": [],
        }
        rows = normalize_api_football_lineup(raw, fixture_id="1")
        assert len(rows) == 1
        assert rows[0]["coach_id"] is None
        assert rows[0]["coach_name"] is None

    def test_malformed_input_returns_empty(self) -> None:
        assert normalize_api_football_lineup(None, fixture_id="x") == []  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# normalize_api_football_injury
# ---------------------------------------------------------------------------


class TestInjuryFlattening:
    """Validate single-injury flattening (4 nested struct cols → flat)."""

    def test_full_injury_flattens_every_struct(self) -> None:
        raw: dict[str, object] = {
            "player": {
                "id": 909,
                "name": "M. Rashford",
                "photo": "rashford.png",
                "type": "Missing Fixture",
                "reason": "Hamstring Injury",
            },
            "team": {"id": 33, "name": "Manchester United", "logo": "mu.png"},
            "fixture": {
                "id": 555,
                "date": "2026-04-01T15:00:00+00:00",
                "timestamp": 1735834800,
                "timezone": "UTC",
            },
            "league": {
                "id": 39,
                "name": "Premier League",
                "country": "England",
                "season": 2025,
                "logo": "epl.png",
                "flag": "england.png",
            },
        }
        out = normalize_api_football_injury(raw)
        assert isinstance(out, dict)
        assert out["player_id"] == 909
        assert out["player_name"] == "M. Rashford"
        assert out["player_photo"] == "rashford.png"
        assert out["player_type"] == "Missing Fixture"
        assert out["player_reason"] == "Hamstring Injury"
        assert out["team_id"] == 33
        assert out["team_name"] == "Manchester United"
        assert out["fixture_id"] == 555
        assert out["league_id"] == 39
        assert out["league_season"] == 2025

    def test_injury_without_fixture(self) -> None:
        """Generic player-status updates with no fixture context — fixture_id is None."""
        raw: dict[str, object] = {
            "player": {"id": 1, "name": "X", "photo": None, "type": "Questionable", "reason": "Knock"},
            "team": {"id": 2, "name": "Y", "logo": None},
            "fixture": {"id": None, "date": None, "timestamp": None, "timezone": None},
            "league": {"id": 100, "name": "Z", "country": "GB", "season": 2025, "logo": None, "flag": None},
        }
        out = normalize_api_football_injury(raw)
        assert out["fixture_id"] is None
        assert out["player_id"] == 1
        assert out["league_season"] == 2025

    def test_malformed_input_returns_empty_dict(self) -> None:
        assert normalize_api_football_injury(None) == {}  # type: ignore[arg-type]
        assert normalize_api_football_injury("string") == {}  # type: ignore[arg-type]
