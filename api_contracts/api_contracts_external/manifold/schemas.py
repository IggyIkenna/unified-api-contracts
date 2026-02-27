"""Pydantic schemas for Manifold REST API. Markets, prices, comments, trades.

Ref: https://docs.manifold.markets/api
Base URL: https://api.manifold.markets/v0/
"""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class ManifoldMarket(BaseModel):
    """Prediction market (contract) from Manifold API."""

    id: str | None = None
    question: str | None = None
    description: str | None = None
    creator_id: str | None = Field(None, alias="creatorId")
    outcome_type: str | None = Field(None, alias="outcomeType")  # BINARY | MULTIPLE_CHOICE | FREE_RESPONSE
    mechanism: str | None = None  # cpmm-1 | dpm-2
    probability: float | None = None
    volume: float | None = None
    volume_24_hours: float | None = Field(None, alias="volume24Hours")
    created_time: int | None = Field(None, alias="createdTime")
    close_time: int | None = Field(None, alias="closeTime")
    resolution_time: int | None = Field(None, alias="resolutionTime")
    resolution: str | None = None
    resolution_probability: float | None = Field(None, alias="resolutionProbability")
    slug: str | None = None
    url: str | None = None
    group_slug: str | None = Field(None, alias="groupSlug")

    model_config = {"populate_by_name": True}


class ManifoldPrice(BaseModel):
    """Price / probability for a market outcome."""

    contract_id: str | None = Field(None, alias="contractId")
    outcome: str | None = None  # YES | NO
    price: float | None = None
    probability: float | None = None

    model_config = {"populate_by_name": True}


class ManifoldTrade(BaseModel):
    """Trade (bet) on Manifold."""

    id: str | None = None
    contract_id: str | None = Field(None, alias="contractId")
    amount: float | None = None
    outcome: str | None = None  # YES | NO
    price: float | None = None
    created_time: int | None = Field(None, alias="createdTime")
    user_id: str | None = Field(None, alias="userId")

    model_config = {"populate_by_name": True}


class ManifoldComment(BaseModel):
    """Comment on a market."""

    id: str | None = None
    contract_id: str | None = Field(None, alias="contractId")
    user_id: str | None = Field(None, alias="userId")
    text: str | None = None
    created_time: int | None = Field(None, alias="createdTime")

    model_config = {"populate_by_name": True}


class ManifoldGroup(BaseModel):
    """Topic/group (tag) for markets."""

    id: str | None = None
    name: str | None = None
    slug: str | None = None
    created_time: int | None = Field(None, alias="createdTime")

    model_config = {"populate_by_name": True}


class ManifoldError(BaseModel):
    """Manifold API error response."""

    error: str | None = None
    message: str | None = None

    @classmethod
    def classify(cls, message: str | None = None) -> ErrorAction:
        """Map Manifold error to retry action."""
        if message and "rate" in (message or "").lower():
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD
