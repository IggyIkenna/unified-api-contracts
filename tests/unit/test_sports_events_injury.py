"""Unit tests for CanonicalFixtureEvent and CanonicalInjury schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.unified_api_contracts_external.sports.canonical.events import CanonicalFixtureEvent
from unified_api_contracts.unified_api_contracts_external.sports.canonical.injury import CanonicalInjury

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# CanonicalFixtureEvent
# ---------------------------------------------------------------------------


class TestCanonicalFixtureEvent:
    """Tests for CanonicalFixtureEvent construction, from_raw, and immutability."""

    def test_valid_construction_minimal(self) -> None:
        """Construct with only required fields."""
        event = CanonicalFixtureEvent(
            fixture_id="123",
            team_id="456",
            minute=34,
            event_type="goal",
        )
        assert event.fixture_id == "123"
        assert event.team_id == "456"
        assert event.minute == 34
        assert event.event_type == "goal"
        assert event.player_id is None
        assert event.player_name is None
        assert event.extra_time is None
        assert event.detail is None
        assert event.comments is None

    def test_valid_construction_all_fields(self) -> None:
        """Construct with every field populated."""
        event = CanonicalFixtureEvent(
            fixture_id="100",
            team_id="200",
            player_id="300",
            player_name="M. Salah",
            minute=78,
            extra_time=3,
            event_type="goal",
            detail="Normal Goal",
            comments="Assisted by T. Alexander-Arnold",
        )
        assert event.player_id == "300"
        assert event.player_name == "M. Salah"
        assert event.extra_time == 3
        assert event.detail == "Normal Goal"
        assert event.comments == "Assisted by T. Alexander-Arnold"

    def test_from_raw_roundtrip(self) -> None:
        """from_raw should produce the same model as direct construction."""
        raw: dict[str, str | int | float | bool | None] = {
            "fixture_id": "10",
            "team_id": "20",
            "player_id": "30",
            "player_name": "K. De Bruyne",
            "minute": 45,
            "extra_time": 2,
            "event_type": "card",
            "detail": "Yellow Card",
            "comments": None,
        }
        event = CanonicalFixtureEvent.from_raw(raw)
        assert event.fixture_id == "10"
        assert event.minute == 45
        assert event.extra_time == 2
        assert event.event_type == "card"
        assert event.detail == "Yellow Card"

    def test_frozen_immutability(self) -> None:
        """Assigning to a field on a frozen model must raise."""
        event = CanonicalFixtureEvent(
            fixture_id="1",
            team_id="2",
            minute=10,
            event_type="substitution",
        )
        with pytest.raises(ValidationError):
            event.minute = 99  # type: ignore[misc]

    def test_missing_required_field_raises(self) -> None:
        """Omitting a required field must raise ValidationError."""
        with pytest.raises(ValidationError):
            CanonicalFixtureEvent(  # type: ignore[call-arg]
                fixture_id="1",
                team_id="2",
                # minute is missing
                event_type="goal",
            )


# ---------------------------------------------------------------------------
# CanonicalInjury
# ---------------------------------------------------------------------------


class TestCanonicalInjury:
    """Tests for CanonicalInjury construction, from_raw, and immutability."""

    def test_valid_construction_minimal(self) -> None:
        """Construct with only required fields."""
        injury = CanonicalInjury(
            fixture_id="100",
            team_id="200",
            player_id="300",
            player_name="V. van Dijk",
        )
        assert injury.fixture_id == "100"
        assert injury.team_id == "200"
        assert injury.player_id == "300"
        assert injury.player_name == "V. van Dijk"
        assert injury.reason is None
        assert injury.severity is None

    def test_valid_construction_all_fields(self) -> None:
        """Construct with every field populated."""
        injury = CanonicalInjury(
            fixture_id="100",
            team_id="200",
            player_id="300",
            player_name="V. van Dijk",
            reason="Knee Injury",
            severity="major",
        )
        assert injury.reason == "Knee Injury"
        assert injury.severity == "major"

    def test_from_raw_roundtrip(self) -> None:
        """from_raw should produce the same model as direct construction."""
        raw: dict[str, str | int | float | bool | None] = {
            "fixture_id": "50",
            "team_id": "60",
            "player_id": "70",
            "player_name": "N. Kante",
            "reason": "Hamstring",
            "severity": "minor",
        }
        injury = CanonicalInjury.from_raw(raw)
        assert injury.fixture_id == "50"
        assert injury.player_name == "N. Kante"
        assert injury.reason == "Hamstring"
        assert injury.severity == "minor"

    def test_frozen_immutability(self) -> None:
        """Assigning to a field on a frozen model must raise."""
        injury = CanonicalInjury(
            fixture_id="1",
            team_id="2",
            player_id="3",
            player_name="Test Player",
        )
        with pytest.raises(ValidationError):
            injury.reason = "Changed"  # type: ignore[misc]

    def test_missing_required_field_raises(self) -> None:
        """Omitting a required field must raise ValidationError."""
        with pytest.raises(ValidationError):
            CanonicalInjury(  # type: ignore[call-arg]
                fixture_id="1",
                team_id="2",
                # player_id is missing
                player_name="Test Player",
            )
