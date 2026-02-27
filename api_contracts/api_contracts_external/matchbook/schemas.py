"""Pydantic schemas for Matchbook REST JSON API. Odds, offers, order placement, markets.

Ref: https://developers.matchbook.com/
Matchbook provides REST API with JSON; base URL: https://api.matchbook.com/edge/rest/
"""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class MatchbookEvent(BaseModel):
    """Event (match) from Matchbook API."""

    id: int | None = None
    name: str | None = None
    start: str | None = None
    status: str | None = None
    category_id: int | None = Field(None, alias="categoryId")

    model_config = {"populate_by_name": True}


class MatchbookMarket(BaseModel):
    """Market from Matchbook API."""

    id: int | None = None
    event_id: int | None = Field(None, alias="eventId")
    name: str | None = None
    market_type: str | None = Field(None, alias="marketType")
    status: str | None = None
    runners: list[dict] | None = None

    model_config = {"populate_by_name": True}


class MatchbookRunner(BaseModel):
    """Runner (selection) in a Matchbook market."""

    id: int | None = None
    name: str | None = None
    market_id: int | None = Field(None, alias="marketId")
    status: str | None = None

    model_config = {"populate_by_name": True}


class MatchbookOffer(BaseModel):
    """Offer (order) on Matchbook. Submit/Edit/Cancel via REST."""

    id: int | None = None
    runner_id: int | None = Field(None, alias="runnerId")
    side: str | None = None  # back | lay
    odds: float | None = None
    stake: float | None = None
    status: str | None = None  # open, matched, cancelled, edited, flushed, failed, delayed

    model_config = {"populate_by_name": True}


class MatchbookOdds(BaseModel):
    """Odds/prices for a runner."""

    runner_id: int | None = Field(None, alias="runnerId")
    back_odds: list[dict] | None = Field(None, alias="backOdds")
    lay_odds: list[dict] | None = Field(None, alias="layOdds")

    model_config = {"populate_by_name": True}


class MatchbookError(BaseModel):
    """Matchbook API error response."""

    error: str | None = None
    message: str | None = None
    code: int | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map Matchbook error to retry action."""
        if code == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if code is not None and code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD
