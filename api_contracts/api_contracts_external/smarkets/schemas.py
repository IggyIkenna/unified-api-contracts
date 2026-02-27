"""Pydantic schemas for Smarkets REST + WebSocket streaming API. Odds, orderbook, bet placement.

Ref: https://docs.smarkets.com/
Smarkets offers streaming API for odds and orderbook; REST for bet placement.
"""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class SmarketsEvent(BaseModel):
    """Event (match) from Smarkets API."""

    id: str | None = None
    name: str | None = None
    slug: str | None = None
    start_date: str | None = Field(None, alias="startDate")
    state: str | None = None
    market_count: int | None = Field(None, alias="marketCount")

    model_config = {"populate_by_name": True}


class SmarketsMarket(BaseModel):
    """Market from Smarkets API."""

    id: str | None = None
    event_id: str | None = Field(None, alias="eventId")
    name: str | None = None
    market_type: str | None = Field(None, alias="marketType")
    state: str | None = None
    volume: float | None = None

    model_config = {"populate_by_name": True}


class SmarketsRunner(BaseModel):
    """Runner (selection) in a Smarkets market."""

    id: str | None = None
    name: str | None = None
    market_id: str | None = Field(None, alias="marketId")

    model_config = {"populate_by_name": True}


class SmarketsPriceLevel(BaseModel):
    """Single price level in orderbook."""

    price: float | None = None
    size: float | None = None


class SmarketsOrderBook(BaseModel):
    """Order book for a market/runner."""

    market_id: str | None = Field(None, alias="marketId")
    runner_id: str | None = Field(None, alias="runnerId")
    backs: list[SmarketsPriceLevel] | None = None
    lays: list[SmarketsPriceLevel] | None = None

    model_config = {"populate_by_name": True}


class SmarketsBetPlacement(BaseModel):
    """Bet placement request/response."""

    id: str | None = None
    market_id: str | None = Field(None, alias="marketId")
    runner_id: str | None = Field(None, alias="runnerId")
    side: str | None = None  # back | lay
    price: float | None = None
    size: float | None = None
    status: str | None = None

    model_config = {"populate_by_name": True}


class SmarketsWsMessage(BaseModel):
    """WebSocket streaming message envelope."""

    type: str | None = None
    payload: dict | None = None

    model_config = {"populate_by_name": True}


class SmarketsError(BaseModel):
    """Smarkets API error response."""

    error: str | None = None
    message: str | None = None
    code: int | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map Smarkets error to retry action."""
        if code == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if code is not None and code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD
