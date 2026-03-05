"""Betdaq API response schemas."""

from pydantic import BaseModel, Field


class BetdaqPriceLevel(BaseModel):
    """Single back/lay price level."""

    price: float | None = None
    amount: float | None = None


class BetdaqOdds(BaseModel):
    """Betdaq odds schema."""

    model_config = {"populate_by_name": True}

    selection_id: int | None = Field(None, alias="selectionId")
    price: float | None = None
    side: str | None = None
    back_prices: list[BetdaqPriceLevel] | None = Field(None, alias="backPrices")
    lay_prices: list[BetdaqPriceLevel] | None = Field(None, alias="layPrices")


class BetdaqMarket(BaseModel):
    """Betdaq market schema."""

    market_id: int | None = None
    name: str | None = None


class BetdaqEvent(BaseModel):
    """Betdaq event schema."""

    event_id: int | None = None
    name: str | None = None
