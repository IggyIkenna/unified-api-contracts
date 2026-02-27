"""Pydantic schemas for PredictIt REST API. Markets, prices, bids/asks.

Ref: https://www.predictit.org/api/marketdata/
Non-commercial use only; 60s refresh rate. No auth required.
"""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class PredictItContract(BaseModel):
    """Contract (outcome) in a PredictIt market."""

    id: int | None = None
    name: str | None = None
    short_name: str | None = Field(None, alias="shortName")
    image: str | None = None
    url: str | None = None
    best_buy_yes_cost: float | None = Field(None, alias="bestBuyYesCost")
    best_buy_no_cost: float | None = Field(None, alias="bestBuyNoCost")
    best_sell_yes_cost: float | None = Field(None, alias="bestSellYesCost")
    best_sell_no_cost: float | None = Field(None, alias="bestSellNoCost")
    last_close_price: float | None = Field(None, alias="lastClosePrice")
    last_trade_price: float | None = Field(None, alias="lastTradePrice")
    volume: int | None = None
    date_end: str | None = Field(None, alias="dateEnd")

    model_config = {"populate_by_name": True}


class PredictItMarket(BaseModel):
    """Market from PredictIt API."""

    id: int | None = None
    name: str | None = None
    short_name: str | None = Field(None, alias="shortName")
    image: str | None = None
    url: str | None = None
    contracts: list[PredictItContract] | None = None
    volume: int | None = None
    status: str | None = None
    category: str | None = None
    subcategory: str | None = None
    date_end: str | None = Field(None, alias="dateEnd")
    time_stamp: str | None = Field(None, alias="timeStamp")

    model_config = {"populate_by_name": True}


class PredictItAllMarkets(BaseModel):
    """Response from /api/marketdata/all/ — all active markets."""

    markets: list[PredictItMarket] | None = None


class PredictItError(BaseModel):
    """PredictIt API error response."""

    error: str | None = None
    message: str | None = None

    @classmethod
    def classify(cls, message: str | None = None) -> ErrorAction:
        """Map PredictIt error to retry action."""
        if message and "rate" in (message or "").lower():
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD
