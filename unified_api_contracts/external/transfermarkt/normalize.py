"""Transfermarkt normalizers — sports reference domain.

Converts Transfermarkt* schemas to CanonicalPlayer, CanonicalTeam using
normalize_utils._helpers. Transfermarkt has no official API; data is scraped.

Per-player market values extracted from squad rosters; emitted at (team, player,
season, fetch_day) granularity rather than team-level aggregates.
"""

from __future__ import annotations

from typing import NamedTuple

from unified_api_contracts.canonical.domain import CanonicalPlayer, CanonicalTeam

from .schemas import (
    TransfermarktLeagueTable,
    TransfermarktPlayer,
    TransfermarktTeamSquad,
)


class PlayerValue(NamedTuple):
    """Per-player market value snapshot."""

    player_id: str
    player_name: str | None
    position: str | None
    age: int | None
    market_value_eur: float | None
    contract_until: str | None
    current_club_id: str
    nationality_iso: str | None
    team_id: str
    league_id: str


def _safe_str(val: str | int | None) -> str:
    return str(val) if val is not None else ""


def normalize_transfermarkt_player(
    raw: TransfermarktPlayer,
    venue: str = "transfermarkt",
) -> CanonicalPlayer:
    """Convert TransfermarktPlayer to CanonicalPlayer."""
    return CanonicalPlayer(
        player_id=_safe_str(raw.id),
        name=_safe_str(raw.name),
        first_name=None,
        last_name=None,
        nationality=_safe_str(raw.nationality),
        position=_safe_str(raw.position) or None,
        date_of_birth=None,
        height_cm=None,
        weight_kg=None,
    )


def normalize_transfermarkt_team_from_squad(
    raw: TransfermarktTeamSquad,
    venue: str = "transfermarkt",
) -> CanonicalTeam:
    """Convert TransfermarktTeamSquad to CanonicalTeam."""
    return CanonicalTeam(
        team_id=_safe_str(raw.team_id),
        name=_safe_str(raw.team_name),
        short_name=None,
        country=None,
        founded=None,
        logo_url=None,
        venue=None,
    )


def normalize_transfermarkt_team_from_table(
    raw: TransfermarktLeagueTable,
    venue: str = "transfermarkt",
) -> CanonicalTeam:
    """Convert TransfermarktLeagueTable row to CanonicalTeam."""
    return CanonicalTeam(
        team_id=_safe_str(raw.team_id),
        name=_safe_str(raw.team),
        short_name=None,
        country=None,
        founded=None,
        logo_url=None,
        venue=None,
    )


def normalize_player_values(
    raw: TransfermarktTeamSquad,
    league_id: str,
) -> list[PlayerValue]:
    """Emit per-player market value rows from squad roster.

    Converts team-squad snapshot to per-(team, player, season, fetch_day) granularity.
    Each player is one row with market_value_eur + position/age/contract details.

    Args:
        raw: TransfermarktTeamSquad with players list.
        league_id: Canonical league_id (e.g. 'EPL') for this squad.

    Returns:
        List of PlayerValue rows (empty if no players in squad).
    """
    if not raw.players:
        return []

    team_id = _safe_str(raw.team_id)
    rows: list[PlayerValue] = []

    for player in raw.players:
        rows.append(
            PlayerValue(
                player_id=_safe_str(player.id),
                player_name=player.name,
                position=player.position,
                age=player.age,
                market_value_eur=player.market_value_eur,
                contract_until=player.contract_until,
                current_club_id=team_id,
                nationality_iso=player.nationality,
                team_id=team_id,
                league_id=league_id,
            )
        )

    return rows


__all__ = [
    "PlayerValue",
    "normalize_player_values",
    "normalize_transfermarkt_player",
    "normalize_transfermarkt_team_from_squad",
    "normalize_transfermarkt_team_from_table",
]
