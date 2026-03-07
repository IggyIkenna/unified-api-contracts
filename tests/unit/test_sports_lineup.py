"""Unit tests for CanonicalLineup and LineupPlayer schemas.

Validates construction, from_raw with nested dicts, and frozen immutability.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.unified_api_contracts_external.sports.canonical.lineup import (
    CanonicalLineup,
    LineupPlayer,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# LineupPlayer
# ---------------------------------------------------------------------------


def test_lineup_player_minimal() -> None:
    """LineupPlayer constructs with only player_id (all other fields optional)."""
    player = LineupPlayer(player_id="p-101")
    assert player.player_id == "p-101"
    assert player.player_name is None
    assert player.shirt_number is None
    assert player.position is None
    assert player.grid_position is None
    assert player.is_substitute is False


def test_lineup_player_full() -> None:
    """LineupPlayer constructs with all fields populated."""
    player = LineupPlayer(
        player_id="p-101",
        player_name="Mohamed Salah",
        shirt_number=11,
        position="F",
        grid_position="1:4",
        is_substitute=False,
    )
    assert player.player_id == "p-101"
    assert player.player_name == "Mohamed Salah"
    assert player.shirt_number == 11
    assert player.position == "F"
    assert player.grid_position == "1:4"
    assert player.is_substitute is False


def test_lineup_player_from_raw() -> None:
    """LineupPlayer.from_raw constructs from a flat dictionary."""
    raw = {
        "player_id": "p-200",
        "player_name": "Virgil van Dijk",
        "shirt_number": 4,
        "position": "D",
        "grid_position": "2:2",
        "is_substitute": False,
    }
    player = LineupPlayer.from_raw(raw)
    assert player.player_id == "p-200"
    assert player.player_name == "Virgil van Dijk"
    assert player.shirt_number == 4


def test_lineup_player_frozen() -> None:
    """LineupPlayer must be immutable (frozen)."""
    player = LineupPlayer(player_id="p-101")
    with pytest.raises(Exception):  # noqa: B017
        player.player_id = "p-999"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CanonicalLineup
# ---------------------------------------------------------------------------


def test_canonical_lineup_minimal() -> None:
    """CanonicalLineup constructs with only required fields."""
    lineup = CanonicalLineup(fixture_id="fix-1", team_id="t-10")
    assert lineup.fixture_id == "fix-1"
    assert lineup.team_id == "t-10"
    assert lineup.formation is None
    assert lineup.coach_name is None
    assert lineup.coach_id is None
    assert lineup.starting == ()
    assert lineup.substitutes == ()


def test_canonical_lineup_with_nested_players() -> None:
    """CanonicalLineup constructs with nested LineupPlayer instances."""
    starter = LineupPlayer(
        player_id="p-1",
        player_name="Alisson",
        shirt_number=1,
        position="G",
        grid_position="1:1",
    )
    sub = LineupPlayer(
        player_id="p-20",
        player_name="Diogo Jota",
        shirt_number=20,
        position="F",
        is_substitute=True,
    )
    lineup = CanonicalLineup(
        fixture_id="fix-100",
        team_id="t-40",
        formation="4-3-3",
        coach_name="Arne Slot",
        coach_id="c-55",
        starting=(starter,),
        substitutes=(sub,),
    )
    assert lineup.formation == "4-3-3"
    assert lineup.coach_name == "Arne Slot"
    assert lineup.coach_id == "c-55"
    assert len(lineup.starting) == 1
    assert lineup.starting[0].player_id == "p-1"
    assert len(lineup.substitutes) == 1
    assert lineup.substitutes[0].is_substitute is True


def test_canonical_lineup_from_raw_nested_dict() -> None:
    """CanonicalLineup.from_raw parses nested dicts into LineupPlayer tuples."""
    raw = {
        "fixture_id": "fix-200",
        "team_id": "t-50",
        "formation": "4-4-2",
        "coach_name": "Pep Guardiola",
        "coach_id": "c-10",
        "starting": [
            {"player_id": "p-7", "player_name": "Kevin De Bruyne", "shirt_number": 17},
            {"player_id": "p-9", "player_name": "Erling Haaland", "shirt_number": 9},
        ],
        "substitutes": [
            {
                "player_id": "p-47",
                "player_name": "Phil Foden",
                "shirt_number": 47,
                "is_substitute": True,
            },
        ],
    }
    lineup = CanonicalLineup.from_raw(raw)
    assert lineup.fixture_id == "fix-200"
    assert lineup.team_id == "t-50"
    assert lineup.formation == "4-4-2"
    assert lineup.coach_name == "Pep Guardiola"
    assert len(lineup.starting) == 2
    assert lineup.starting[0].player_name == "Kevin De Bruyne"
    assert lineup.starting[1].shirt_number == 9
    assert len(lineup.substitutes) == 1
    assert lineup.substitutes[0].is_substitute is True
    # Verify tuple type (not list)
    assert isinstance(lineup.starting, tuple)
    assert isinstance(lineup.substitutes, tuple)


def test_canonical_lineup_frozen() -> None:
    """CanonicalLineup must be immutable (frozen)."""
    lineup = CanonicalLineup(fixture_id="fix-1", team_id="t-10")
    with pytest.raises(Exception):  # noqa: B017
        lineup.fixture_id = "fix-999"  # type: ignore[misc]


def test_canonical_lineup_frozen_nested() -> None:
    """Cannot mutate nested tuples on a frozen CanonicalLineup."""
    starter = LineupPlayer(player_id="p-1")
    lineup = CanonicalLineup(
        fixture_id="fix-1",
        team_id="t-10",
        starting=(starter,),
    )
    with pytest.raises(Exception):  # noqa: B017
        lineup.starting = ()  # type: ignore[misc]
