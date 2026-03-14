"""1xBet bookmaker API response schemas.

Ref: 1xBet public pre-match odds API.
"""

from __future__ import annotations

__api_version__ = "v1"  # matches provider_api_versions.yaml


from pydantic import BaseModel


class OneXBetOutcome(BaseModel):
    """Outcome in a 1xBet market."""

    name: str | None = None
    price: float | None = None
    point: float | None = None


class OneXBetMarket(BaseModel):
    """Market from 1xBet API."""

    name: str | None = None
    outcomes: list[OneXBetOutcome] | None = None


class OneXBetOddsResponse(BaseModel):
    """Odds response from 1xBet API."""

    markets: list[OneXBetMarket] | None = None


class OneXBetEvent(BaseModel):
    """Event (match) from 1xBet API."""

    id: int | None = None
