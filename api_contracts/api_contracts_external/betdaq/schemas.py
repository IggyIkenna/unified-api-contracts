"""Pydantic schemas for Betdaq SOAP/REST API. Odds, markets, events, order placement, PnL.

Ref: https://api.betdaq.com/v2.0/Docs/
Betdaq uses SOAP-based API; responses can be modeled as JSON-like structures.
"""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class BetdaqEvent(BaseModel):
    """Event (match/race) from Betdaq API."""

    event_id: int | None = Field(None, alias="eventId")
    event_name: str | None = Field(None, alias="eventName")
    event_type_id: int | None = Field(None, alias="eventTypeId")
    start_time: str | None = Field(None, alias="startTime")
    venue: str | None = None
    market_count: int | None = Field(None, alias="marketCount")

    model_config = {"populate_by_name": True}


class BetdaqMarket(BaseModel):
    """Market from Betdaq API."""

    market_id: int | None = Field(None, alias="marketId")
    market_name: str | None = Field(None, alias="marketName")
    event_id: int | None = Field(None, alias="eventId")
    market_type: str | None = Field(None, alias="marketType")
    status: str | None = None
    selection_count: int | None = Field(None, alias="selectionCount")

    model_config = {"populate_by_name": True}


class BetdaqSelection(BaseModel):
    """Selection (runner) in a Betdaq market."""

    selection_id: int | None = Field(None, alias="selectionId")
    selection_name: str | None = Field(None, alias="selectionName")
    market_id: int | None = Field(None, alias="marketId")
    reset_sequence_number: int | None = Field(None, alias="resetSequenceNumber")
    withdrawal_sequence_number: int | None = Field(None, alias="withdrawalSequenceNumber")

    model_config = {"populate_by_name": True}


class BetdaqPrice(BaseModel):
    """Price level (back/lay) for a selection."""

    price: float | None = None
    amount: float | None = None
    polarity: str | None = None  # Back | Lay


class BetdaqOdds(BaseModel):
    """Odds/prices for a selection."""

    selection_id: int | None = Field(None, alias="selectionId")
    back_prices: list[BetdaqPrice] | None = Field(None, alias="backPrices")
    lay_prices: list[BetdaqPrice] | None = Field(None, alias="layPrices")

    model_config = {"populate_by_name": True}


class BetdaqOrderPlacement(BaseModel):
    """Order placement request/response."""

    order_handle: str | None = Field(None, alias="orderHandle")
    selection_id: int | None = Field(None, alias="selectionId")
    polarity: str | None = None  # Back | Lay
    price: float | None = None
    stake: float | None = None
    status: str | None = None

    model_config = {"populate_by_name": True}


class BetdaqPnL(BaseModel):
    """P&L / settlement data."""

    market_id: int | None = Field(None, alias="marketId")
    selection_id: int | None = Field(None, alias="selectionId")
    profit_loss: float | None = Field(None, alias="profitLoss")
    currency: str | None = None

    model_config = {"populate_by_name": True}


class BetdaqError(BaseModel):
    """Betdaq API error response."""

    code: int | str | None = None
    message: str | None = None

    @classmethod
    def classify(cls, code: int | str | None = None, message: str | None = None) -> ErrorAction:
        """Map Betdaq error to retry action."""
        if code == 429 or (message and "rate" in (message or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if isinstance(code, int) and code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code == 401 or (message and "unauthorized" in (message or "").lower()):
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD
