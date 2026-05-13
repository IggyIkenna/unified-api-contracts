"""Unit tests for Transfermarkt normalizers.

Covers normalize_player_values() per-player flatten (C.4 sports_master) —
emits per-(team, player, season, fetch_day) rows from team-squad rosters.
"""

from __future__ import annotations

from unified_api_contracts.external.transfermarkt.normalize import (
    PlayerValue,
    normalize_player_values,
)
from unified_api_contracts.external.transfermarkt.schemas import (
    TransfermarktPlayer,
    TransfermarktTeamSquad,
)


def _make_player(
    pid: str = "p100",
    name: str = "Test Player",
    market_value_eur: float | None = 50_000_000.0,
) -> TransfermarktPlayer:
    return TransfermarktPlayer(
        id=pid,
        name=name,
        position="CM",
        nationality="ENG",
        market_value_eur=market_value_eur,
        age=25,
        contract_until="2027-06-30",
    )


def test_normalize_player_values_emits_per_player_rows():
    """One row per player in squad."""
    squad = TransfermarktTeamSquad(
        team_id="t10",
        team_name="Test FC",
        players=[
            _make_player("p1", "Player One"),
            _make_player("p2", "Player Two"),
            _make_player("p3", "Player Three"),
        ],
    )
    rows = normalize_player_values(squad, league_id="EPL")
    assert len(rows) == 3
    assert all(isinstance(r, PlayerValue) for r in rows)
    assert {r.player_name for r in rows} == {"Player One", "Player Two", "Player Three"}


def test_normalize_player_values_preserves_market_value():
    """market_value_eur passes through as primary signal."""
    squad = TransfermarktTeamSquad(
        team_id="t11",
        team_name="Big Club",
        players=[_make_player("p100", market_value_eur=120_000_000.0)],
    )
    rows = normalize_player_values(squad, league_id="LA_LIGA")
    assert rows[0].market_value_eur == 120_000_000.0


def test_normalize_player_values_handles_empty_squad():
    """Empty/None players list emits zero rows."""
    squad = TransfermarktTeamSquad(team_id="t12", team_name="Empty FC", players=None)
    assert normalize_player_values(squad, league_id="EPL") == []

    squad2 = TransfermarktTeamSquad(team_id="t12", team_name="Empty FC", players=[])
    assert normalize_player_values(squad2, league_id="EPL") == []


def test_normalize_player_values_propagates_team_and_league():
    """team_id, current_club_id, league_id stamped on every row."""
    squad = TransfermarktTeamSquad(
        team_id="t20",
        team_name="Source FC",
        players=[_make_player("p1"), _make_player("p2")],
    )
    rows = normalize_player_values(squad, league_id="BUNDESLIGA")
    for row in rows:
        assert row.team_id == "t20"
        assert row.current_club_id == "t20"
        assert row.league_id == "BUNDESLIGA"


def test_normalize_player_values_tolerates_null_market_value():
    """Players with no market value still emit rows (market_value_eur=None)."""
    squad = TransfermarktTeamSquad(
        team_id="t30",
        team_name="No Values FC",
        players=[_make_player("p1", market_value_eur=None)],
    )
    rows = normalize_player_values(squad, league_id="EPL")
    assert len(rows) == 1
    assert rows[0].market_value_eur is None
    assert rows[0].player_id == "p1"


def test_player_value_namedtuple_unpacking():
    """PlayerValue is a NamedTuple — supports unpacking + named access."""
    squad = TransfermarktTeamSquad(
        team_id="t40",
        team_name="NT Test",
        players=[_make_player("p1", name="Alice")],
    )
    rows = normalize_player_values(squad, league_id="EPL")
    row = rows[0]
    assert row.player_id == "p1"
    assert row.player_name == "Alice"
    assert row.position == "CM"
    assert row.age == 25
    assert row.contract_until == "2027-06-30"
    assert row.nationality_iso == "ENG"
