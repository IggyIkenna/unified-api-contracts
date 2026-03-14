"""Unit tests for CanonicalProgressiveStats and CanonicalProgressiveOdds.

Validates construction, from_raw, frozen immutability, and Decimal precision
for the 30-second interval time-series schemas.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.external.sports.canonical.progressive import (
    CanonicalProgressiveOdds,
    CanonicalProgressiveStats,
)

pytestmark = pytest.mark.unit


# ── CanonicalProgressiveStats ────────────────────────────────────────────


class TestCanonicalProgressiveStats:
    """Tests for the progressive stats model."""

    def test_valid_construction_minimal(self) -> None:
        """Required fields only — all optional fields default to None."""
        obj = CanonicalProgressiveStats(
            fixture_id="fix-001",
            timer_seconds=90,
            team="home",
        )
        assert obj.fixture_id == "fix-001"
        assert obj.timer_seconds == 90
        assert obj.team == "home"
        assert obj.goals is None
        assert obj.possession_pct is None
        assert obj.dangerous_attacks is None
        assert obj.dominance_pct is None

    def test_valid_construction_full(self) -> None:
        """All fields populated."""
        obj = CanonicalProgressiveStats(
            fixture_id="fix-002",
            timer_seconds=2700,
            team="away",
            goals=2,
            possession_pct=55.3,
            dangerous_attacks=18,
            attacks=42,
            shots_on_target=5,
            shots_off_target=3,
            corners=6,
            fouls=10,
            yellow_cards=2,
            red_cards=0,
            substitutions=1,
            dominance_pct=62.1,
        )
        assert obj.goals == 2
        assert obj.possession_pct == pytest.approx(55.3)
        assert obj.dangerous_attacks == 18
        assert obj.shots_on_target == 5
        assert obj.corners == 6
        assert obj.fouls == 10
        assert obj.yellow_cards == 2
        assert obj.red_cards == 0
        assert obj.substitutions == 1
        assert obj.dominance_pct == pytest.approx(62.1)

    def test_from_raw(self) -> None:
        """from_raw classmethod constructs from a flat dictionary."""
        raw: dict[str, str | int | float | bool | None] = {
            "fixture_id": "fix-003",
            "timer_seconds": 1800,
            "team": "home",
            "goals": 1,
            "possession_pct": 48.5,
            "corners": 3,
        }
        obj = CanonicalProgressiveStats.from_raw(raw)
        assert obj.fixture_id == "fix-003"
        assert obj.timer_seconds == 1800
        assert obj.goals == 1
        assert obj.possession_pct == pytest.approx(48.5)
        assert obj.corners == 3

    def test_frozen_immutability(self) -> None:
        """Frozen model rejects attribute mutation."""
        obj = CanonicalProgressiveStats(
            fixture_id="fix-004",
            timer_seconds=60,
            team="home",
        )
        with pytest.raises(ValidationError):
            obj.goals = 1  # type: ignore[misc]

    def test_missing_required_fields_raises(self) -> None:
        """Omitting required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            CanonicalProgressiveStats(fixture_id="fix-005", timer_seconds=0)  # type: ignore[call-arg]


# ── CanonicalProgressiveOdds ─────────────────────────────────────────────


class TestCanonicalProgressiveOdds:
    """Tests for the progressive odds model."""

    def test_valid_construction_minimal(self) -> None:
        """Required fields only — all optional fields default to None."""
        obj = CanonicalProgressiveOdds(
            fixture_id="fix-101",
            timer_seconds=0,
        )
        assert obj.fixture_id == "fix-101"
        assert obj.timer_seconds == 0
        assert obj.home_win_odds is None
        assert obj.draw_odds is None
        assert obj.away_win_odds is None
        assert obj.asian_handicap_line is None

    def test_valid_construction_full(self) -> None:
        """All fields populated with Decimal values."""
        obj = CanonicalProgressiveOdds(
            fixture_id="fix-102",
            timer_seconds=2700,
            home_win_odds=Decimal("1.85"),
            draw_odds=Decimal("3.40"),
            away_win_odds=Decimal("4.50"),
            over_2_5_odds=Decimal("2.10"),
            under_2_5_odds=Decimal("1.75"),
            asian_handicap_line=Decimal("-0.5"),
            asian_handicap_home_odds=Decimal("1.90"),
            asian_handicap_away_odds=Decimal("2.00"),
            first_half_home_odds=Decimal("2.50"),
            first_half_draw_odds=Decimal("2.20"),
            first_half_away_odds=Decimal("5.00"),
            first_half_over_odds=Decimal("2.30"),
            first_half_under_odds=Decimal("1.60"),
        )
        assert obj.home_win_odds == Decimal("1.85")
        assert obj.draw_odds == Decimal("3.40")
        assert obj.asian_handicap_line == Decimal("-0.5")
        assert obj.first_half_under_odds == Decimal("1.60")

    def test_from_raw(self) -> None:
        """from_raw classmethod constructs from a flat dictionary."""
        raw: dict[str, str | int | float | bool | None] = {
            "fixture_id": "fix-103",
            "timer_seconds": 900,
            "home_win_odds": "2.10",
            "draw_odds": "3.25",
            "away_win_odds": "3.80",
        }
        obj = CanonicalProgressiveOdds.from_raw(raw)
        assert obj.fixture_id == "fix-103"
        assert obj.timer_seconds == 900
        assert obj.home_win_odds == Decimal("2.10")
        assert obj.draw_odds == Decimal("3.25")

    def test_frozen_immutability(self) -> None:
        """Frozen model rejects attribute mutation."""
        obj = CanonicalProgressiveOdds(
            fixture_id="fix-104",
            timer_seconds=30,
        )
        with pytest.raises(ValidationError):
            obj.home_win_odds = Decimal("1.50")  # type: ignore[misc]

    def test_decimal_precision_preserved(self) -> None:
        """Decimal precision is maintained through construction and from_raw."""
        obj = CanonicalProgressiveOdds(
            fixture_id="fix-105",
            timer_seconds=60,
            home_win_odds=Decimal("1.234567890"),
            over_2_5_odds=Decimal("2.000"),
        )
        assert str(obj.home_win_odds) == "1.234567890"
        assert str(obj.over_2_5_odds) == "2.000"

        # Also via from_raw with string Decimal input
        raw: dict[str, str | int | float | bool | None] = {
            "fixture_id": "fix-106",
            "timer_seconds": 120,
            "draw_odds": "3.141592653",
        }
        obj2 = CanonicalProgressiveOdds.from_raw(raw)
        assert str(obj2.draw_odds) == "3.141592653"

    def test_missing_required_fields_raises(self) -> None:
        """Omitting required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            CanonicalProgressiveOdds(fixture_id="fix-107")  # type: ignore[call-arg]

    def test_from_raw_with_numeric_odds(self) -> None:
        """from_raw accepts float values and converts to Decimal."""
        raw: dict[str, str | int | float | bool | None] = {
            "fixture_id": "fix-108",
            "timer_seconds": 180,
            "home_win_odds": 1.95,
            "asian_handicap_line": -0.75,
        }
        obj = CanonicalProgressiveOdds.from_raw(raw)
        assert isinstance(obj.home_win_odds, Decimal)
        assert isinstance(obj.asian_handicap_line, Decimal)
