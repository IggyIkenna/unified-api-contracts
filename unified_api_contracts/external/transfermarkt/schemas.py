"""Transfermarkt data schemas (stub).

NOTE: Transfermarkt has no official public API. Data is scraped via unofficial
wrappers (e.g. transfermarkt-scraper, mplsoccer). Market values are updated
weekly. Use at your own risk; respect robots.txt and rate limits.
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from pydantic import BaseModel

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction


class TransfermarktPlayer(BaseModel):
    """Player from Transfermarkt (scraped)."""

    id: str | int | None = None
    name: str | None = None
    position: str | None = None
    nationality: str | None = None
    market_value_eur: float | None = None
    market_value_currency: str | None = None
    club: str | None = None
    age: int | None = None
    contract_until: str | None = None
    player_image_url: str | None = None


class TransfermarktTransfer(BaseModel):
    """Transfer record from Transfermarkt (scraped)."""

    player_id: str | int | None = None
    player_name: str | None = None
    from_club: str | None = None
    to_club: str | None = None
    fee_eur: float | None = None
    fee_currency: str | None = None
    transfer_date: str | None = None
    season: str | None = None
    transfer_type: str | None = None  # loan, permanent, free


class TransfermarktTeamSquad(BaseModel):
    """Team squad from Transfermarkt (scraped)."""

    team_id: str | int | None = None
    team_name: str | None = None
    squad_size: int | None = None
    average_age: float | None = None
    foreigners_number: int | None = None
    total_market_value_eur: float | None = None
    players: list[TransfermarktPlayer] | None = None


class TransfermarktLeagueTable(BaseModel):
    """League table from Transfermarkt (scraped)."""

    position: int | None = None
    team: str | None = None
    team_id: str | int | None = None
    played: int | None = None
    wins: int | None = None
    draws: int | None = None
    losses: int | None = None
    goals_for: int | None = None
    goals_against: int | None = None
    points: int | None = None


class TransfermarktError(BaseModel):
    """Transfermarkt/scraper error."""

    error: str | None = None
    message: str | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map Transfermarkt error to retry action."""
        if code == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY
        if code is not None and code >= 500:
            return ErrorAction.RETRY
        return ErrorAction.FAIL
