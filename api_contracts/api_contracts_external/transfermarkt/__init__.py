"""Transfermarkt data contracts (stub).

No official API; data from unofficial scrapers.
"""

from .schemas import (
    TransfermarktError,
    TransfermarktLeagueTable,
    TransfermarktPlayer,
    TransfermarktTeamSquad,
    TransfermarktTransfer,
)

__all__ = [
    "TransfermarktError",
    "TransfermarktLeagueTable",
    "TransfermarktPlayer",
    "TransfermarktTeamSquad",
    "TransfermarktTransfer",
]
