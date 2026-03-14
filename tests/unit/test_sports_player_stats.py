"""Unit tests for CanonicalPlayerMatchStats schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.external.sports.canonical.player_stats import (
    CanonicalPlayerMatchStats,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _full_payload() -> dict[str, str | int | float | bool | None]:
    """Return a fully-populated raw payload for CanonicalPlayerMatchStats."""
    return {
        "fixture_id": "fix-123",
        "team_id": "team-456",
        "player_id": "player-789",
        "player_name": "Mohamed Salah",
        "minutes_played": 90,
        "rating": 8.2,
        "is_captain": False,
        "is_substitute": False,
        "shots_total": 5,
        "shots_on_target": 3,
        "goals_total": 1,
        "goals_conceded": 0,
        "assists": 1,
        "saves": 0,
        "passes_total": 42,
        "passes_key": 3,
        "passes_accuracy": 85,
        "tackles_total": 2,
        "tackles_blocks": 0,
        "tackles_interceptions": 1,
        "duels_total": 10,
        "duels_won": 6,
        "dribbles_attempts": 4,
        "dribbles_success": 3,
        "dribbles_past": 1,
        "fouls_drawn": 2,
        "fouls_committed": 1,
        "cards_yellow": 0,
        "cards_red": 0,
        "penalty_won": 0,
        "penalty_committed": 0,
        "penalty_scored": 0,
        "penalty_missed": 0,
        "penalty_saved": 0,
    }


# ---------------------------------------------------------------------------
# Valid construction
# ---------------------------------------------------------------------------


class TestValidConstruction:
    """CanonicalPlayerMatchStats must accept valid payloads."""

    def test_full_payload(self) -> None:
        """All 34 fields can be supplied and round-trip correctly."""
        data = _full_payload()
        stats = CanonicalPlayerMatchStats.model_validate(data)

        assert stats.fixture_id == "fix-123"
        assert stats.team_id == "team-456"
        assert stats.player_id == "player-789"
        assert stats.player_name == "Mohamed Salah"
        assert stats.minutes_played == 90
        assert stats.rating == 8.2
        assert stats.is_captain is False
        assert stats.is_substitute is False
        assert stats.shots_total == 5
        assert stats.shots_on_target == 3
        assert stats.goals_total == 1
        assert stats.goals_conceded == 0
        assert stats.assists == 1
        assert stats.saves == 0
        assert stats.passes_total == 42
        assert stats.passes_key == 3
        assert stats.passes_accuracy == 85
        assert stats.tackles_total == 2
        assert stats.tackles_blocks == 0
        assert stats.tackles_interceptions == 1
        assert stats.duels_total == 10
        assert stats.duels_won == 6
        assert stats.dribbles_attempts == 4
        assert stats.dribbles_success == 3
        assert stats.dribbles_past == 1
        assert stats.fouls_drawn == 2
        assert stats.fouls_committed == 1
        assert stats.cards_yellow == 0
        assert stats.cards_red == 0
        assert stats.penalty_won == 0
        assert stats.penalty_committed == 0
        assert stats.penalty_scored == 0
        assert stats.penalty_missed == 0
        assert stats.penalty_saved == 0

    def test_minimal_payload_only_required(self) -> None:
        """Only the three required ID fields are needed for construction."""
        stats = CanonicalPlayerMatchStats(
            fixture_id="f-1",
            team_id="t-1",
            player_id="p-1",
        )
        assert stats.fixture_id == "f-1"
        assert stats.team_id == "t-1"
        assert stats.player_id == "p-1"


# ---------------------------------------------------------------------------
# from_raw roundtrip
# ---------------------------------------------------------------------------


class TestFromRaw:
    """from_raw classmethod must produce identical instances to direct construction."""

    def test_from_raw_roundtrip(self) -> None:
        """from_raw(payload) -> model_dump() should equal the original payload."""
        data = _full_payload()
        stats = CanonicalPlayerMatchStats.from_raw(data)
        dumped = stats.model_dump()

        for key, value in data.items():
            assert dumped[key] == value, f"Mismatch on {key}: {dumped[key]} != {value}"

    def test_from_raw_minimal(self) -> None:
        """from_raw with only required fields fills defaults."""
        data: dict[str, str | int | float | bool | None] = {
            "fixture_id": "f-1",
            "team_id": "t-1",
            "player_id": "p-1",
        }
        stats = CanonicalPlayerMatchStats.from_raw(data)
        assert stats.fixture_id == "f-1"
        assert stats.player_name is None
        assert stats.is_captain is False


# ---------------------------------------------------------------------------
# Defaults are None for optional fields
# ---------------------------------------------------------------------------


class TestDefaults:
    """Optional stat fields must default to None; booleans to False."""

    def test_optional_int_fields_default_none(self) -> None:
        """All optional int stat fields default to None when omitted."""
        stats = CanonicalPlayerMatchStats(
            fixture_id="f-1",
            team_id="t-1",
            player_id="p-1",
        )
        optional_int_fields = [
            "minutes_played",
            "shots_total",
            "shots_on_target",
            "goals_total",
            "goals_conceded",
            "assists",
            "saves",
            "passes_total",
            "passes_key",
            "passes_accuracy",
            "tackles_total",
            "tackles_blocks",
            "tackles_interceptions",
            "duels_total",
            "duels_won",
            "dribbles_attempts",
            "dribbles_success",
            "dribbles_past",
            "fouls_drawn",
            "fouls_committed",
            "cards_yellow",
            "cards_red",
            "penalty_won",
            "penalty_committed",
            "penalty_scored",
            "penalty_missed",
            "penalty_saved",
        ]
        for field in optional_int_fields:
            assert getattr(stats, field) is None, f"{field} should default to None"

    def test_optional_float_field_default_none(self) -> None:
        """rating defaults to None."""
        stats = CanonicalPlayerMatchStats(
            fixture_id="f-1",
            team_id="t-1",
            player_id="p-1",
        )
        assert stats.rating is None

    def test_optional_str_field_default_none(self) -> None:
        """player_name defaults to None."""
        stats = CanonicalPlayerMatchStats(
            fixture_id="f-1",
            team_id="t-1",
            player_id="p-1",
        )
        assert stats.player_name is None

    def test_boolean_defaults(self) -> None:
        """is_captain and is_substitute default to False."""
        stats = CanonicalPlayerMatchStats(
            fixture_id="f-1",
            team_id="t-1",
            player_id="p-1",
        )
        assert stats.is_captain is False
        assert stats.is_substitute is False


# ---------------------------------------------------------------------------
# Frozen immutability
# ---------------------------------------------------------------------------


class TestFrozenImmutability:
    """CanonicalPlayerMatchStats must be immutable (frozen=True)."""

    def test_cannot_mutate_required_field(self) -> None:
        """Assigning to a required field raises ValidationError."""
        stats = CanonicalPlayerMatchStats(
            fixture_id="f-1",
            team_id="t-1",
            player_id="p-1",
        )
        with pytest.raises(ValidationError):
            stats.fixture_id = "f-2"  # type: ignore[misc]

    def test_cannot_mutate_optional_field(self) -> None:
        """Assigning to an optional field raises ValidationError."""
        stats = CanonicalPlayerMatchStats(
            fixture_id="f-1",
            team_id="t-1",
            player_id="p-1",
        )
        with pytest.raises(ValidationError):
            stats.goals_total = 5  # type: ignore[misc]

    def test_cannot_mutate_boolean_field(self) -> None:
        """Assigning to a boolean default field raises ValidationError."""
        stats = CanonicalPlayerMatchStats(
            fixture_id="f-1",
            team_id="t-1",
            player_id="p-1",
        )
        with pytest.raises(ValidationError):
            stats.is_captain = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    """Missing required fields must raise ValidationError."""

    def test_missing_fixture_id(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalPlayerMatchStats(
                team_id="t-1",
                player_id="p-1",
            )  # type: ignore[call-arg]

    def test_missing_team_id(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalPlayerMatchStats(
                fixture_id="f-1",
                player_id="p-1",
            )  # type: ignore[call-arg]

    def test_missing_player_id(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalPlayerMatchStats(
                fixture_id="f-1",
                team_id="t-1",
            )  # type: ignore[call-arg]
