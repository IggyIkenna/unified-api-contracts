"""Unit tests for CanonicalFixtureStatsDetail and CanonicalFixture extended fields."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.unified_api_contracts_external.sports.canonical.fixture import (
    CanonicalFixture,
    CanonicalLeague,
    CanonicalTeam,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.fixture_stats import (
    CanonicalFixtureStatsDetail,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_fixture_kwargs() -> dict[str, str | int | float | bool | None | CanonicalTeam | CanonicalLeague]:
    """Return the minimum required fields for a CanonicalFixture."""
    return {
        "fixture_id": "fix-1",
        "home_team": CanonicalTeam(team_id="t1", name="Home FC"),
        "away_team": CanonicalTeam(team_id="t2", name="Away FC"),
        "league": CanonicalLeague(league_id="lg1", name="Test League", country="GB"),
        "kickoff_utc": "2025-06-01T15:00:00Z",
        "season": "2024-25",
        "source": "api_football",
    }


# ---------------------------------------------------------------------------
# CanonicalFixtureStatsDetail — construction
# ---------------------------------------------------------------------------


class TestCanonicalFixtureStatsDetailConstruction:
    """Validate CanonicalFixtureStatsDetail construction from direct kwargs."""

    def test_minimal_required_fields(self) -> None:
        """Only fixture_id and team_id are required; all stats default to None."""
        obj = CanonicalFixtureStatsDetail(fixture_id="fix-1", team_id="t-42")
        assert obj.fixture_id == "fix-1"
        assert obj.team_id == "t-42"
        assert obj.shots_on_target is None
        assert obj.expected_goals is None
        assert obj.goals_prevented is None

    def test_full_construction(self) -> None:
        """All 20 fields populated — verify every value round-trips."""
        obj = CanonicalFixtureStatsDetail(
            fixture_id="fix-99",
            team_id="t-7",
            shots_on_target=5,
            shots_off_target=3,
            shots_total=8,
            shots_blocked=2,
            shots_inside_box=6,
            shots_outside_box=2,
            fouls=12,
            corners=7,
            offsides=3,
            possession_pct=55,
            yellow_cards=2,
            red_cards=0,
            goalkeeper_saves=4,
            passes_total=450,
            passes_accurate=380,
            passes_accuracy_pct=84,
            expected_goals=1.85,
            goals_prevented=0.32,
        )
        assert obj.shots_on_target == 5
        assert obj.shots_total == 8
        assert obj.possession_pct == 55
        assert obj.passes_total == 450
        assert obj.passes_accuracy_pct == 84
        assert obj.expected_goals == pytest.approx(1.85)
        assert obj.goals_prevented == pytest.approx(0.32)

    def test_missing_fixture_id_raises(self) -> None:
        """fixture_id is required — omitting it must raise ValidationError."""
        with pytest.raises(ValidationError):
            CanonicalFixtureStatsDetail(team_id="t-1")  # type: ignore[call-arg]

    def test_missing_team_id_raises(self) -> None:
        """team_id is required — omitting it must raise ValidationError."""
        with pytest.raises(ValidationError):
            CanonicalFixtureStatsDetail(fixture_id="fix-1")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# CanonicalFixtureStatsDetail — from_raw
# ---------------------------------------------------------------------------


class TestCanonicalFixtureStatsDetailFromRaw:
    """Validate the from_raw classmethod."""

    def test_from_raw_minimal(self) -> None:
        """from_raw with only required fields."""
        raw: dict[str, str | int | float | bool | None] = {
            "fixture_id": "fix-10",
            "team_id": "t-20",
        }
        obj = CanonicalFixtureStatsDetail.from_raw(raw)
        assert obj.fixture_id == "fix-10"
        assert obj.team_id == "t-20"
        assert obj.shots_on_target is None

    def test_from_raw_full(self) -> None:
        """from_raw with all fields populated."""
        raw: dict[str, str | int | float | bool | None] = {
            "fixture_id": "fix-50",
            "team_id": "t-88",
            "shots_on_target": 4,
            "shots_off_target": 6,
            "shots_total": 10,
            "shots_blocked": 3,
            "shots_inside_box": 7,
            "shots_outside_box": 3,
            "fouls": 14,
            "corners": 5,
            "offsides": 2,
            "possession_pct": 48,
            "yellow_cards": 3,
            "red_cards": 1,
            "goalkeeper_saves": 5,
            "passes_total": 320,
            "passes_accurate": 260,
            "passes_accuracy_pct": 81,
            "expected_goals": 2.1,
            "goals_prevented": 0.5,
        }
        obj = CanonicalFixtureStatsDetail.from_raw(raw)
        assert obj.fixture_id == "fix-50"
        assert obj.corners == 5
        assert obj.expected_goals == pytest.approx(2.1)

    def test_from_raw_extra_fields_ignored(self) -> None:
        """Unknown keys in the raw dict should be silently ignored."""
        raw: dict[str, str | int | float | bool | None] = {
            "fixture_id": "fix-1",
            "team_id": "t-1",
            "nonexistent_field": 999,
        }
        # Pydantic v2 ignores extras by default — should not raise
        obj = CanonicalFixtureStatsDetail.from_raw(raw)
        assert obj.fixture_id == "fix-1"


# ---------------------------------------------------------------------------
# CanonicalFixtureStatsDetail — frozen
# ---------------------------------------------------------------------------


class TestCanonicalFixtureStatsDetailFrozen:
    """The model must be immutable (ConfigDict frozen=True)."""

    def test_cannot_mutate_field(self) -> None:
        """Assigning to a field on a frozen model must raise ValidationError."""
        obj = CanonicalFixtureStatsDetail(fixture_id="fix-1", team_id="t-1")
        with pytest.raises(ValidationError):
            obj.fixture_id = "changed"  # type: ignore[misc]

    def test_cannot_mutate_optional_field(self) -> None:
        """Even optional fields must be frozen."""
        obj = CanonicalFixtureStatsDetail(
            fixture_id="fix-1",
            team_id="t-1",
            shots_on_target=5,
        )
        with pytest.raises(ValidationError):
            obj.shots_on_target = 10  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CanonicalFixture — optional fields for schema evolution
# ---------------------------------------------------------------------------


class TestCanonicalFixtureExtendedFields:
    """Verify the 8 new fields added to CanonicalFixture."""

    def test_old_construction_still_works(self) -> None:
        """Constructing CanonicalFixture without the new fields must succeed."""
        obj = CanonicalFixture(**_minimal_fixture_kwargs())
        assert obj.fixture_id == "fix-1"
        # New fields default to None
        assert obj.home_shots_blocked is None
        assert obj.away_shots_blocked is None
        assert obj.home_offsides is None
        assert obj.away_offsides is None
        assert obj.home_passes_total is None
        assert obj.away_passes_total is None
        assert obj.home_passes_accuracy is None
        assert obj.away_passes_accuracy is None

    def test_new_fields_populated(self) -> None:
        """Constructing CanonicalFixture with the new fields must work."""
        kwargs = _minimal_fixture_kwargs()
        kwargs["home_shots_blocked"] = 4
        kwargs["away_shots_blocked"] = 2
        kwargs["home_offsides"] = 3
        kwargs["away_offsides"] = 1
        kwargs["home_passes_total"] = 500
        kwargs["away_passes_total"] = 420
        kwargs["home_passes_accuracy"] = 88
        kwargs["away_passes_accuracy"] = 79
        obj = CanonicalFixture(**kwargs)  # type: ignore[arg-type]
        assert obj.home_shots_blocked == 4
        assert obj.away_shots_blocked == 2
        assert obj.home_offsides == 3
        assert obj.away_offsides == 1
        assert obj.home_passes_total == 500
        assert obj.away_passes_total == 420
        assert obj.home_passes_accuracy == 88
        assert obj.away_passes_accuracy == 79

    def test_fixture_frozen(self) -> None:
        """CanonicalFixture must remain frozen after adding new fields."""
        obj = CanonicalFixture(**_minimal_fixture_kwargs())
        with pytest.raises(ValidationError):
            obj.home_shots_blocked = 5  # type: ignore[misc]
