"""Transfermarkt normalizers — sports reference domain.

Converts Transfermarkt* schemas to CanonicalPlayer, CanonicalTeam using
normalize_utils._helpers. Transfermarkt has no official API; data is scraped.
"""

from __future__ import annotations

from unified_api_contracts.canonical.domain import CanonicalPlayer, CanonicalTeam

from .schemas import (
    TransfermarktLeagueTable,
    TransfermarktPlayer,
    TransfermarktTeamSquad,
)


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


__all__ = [
    "normalize_transfermarkt_player",
    "normalize_transfermarkt_team_from_squad",
    "normalize_transfermarkt_team_from_table",
]
