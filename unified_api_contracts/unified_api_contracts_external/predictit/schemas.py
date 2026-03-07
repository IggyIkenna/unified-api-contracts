"""PredictIt API response schemas."""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from pydantic import BaseModel, Field


class PredictItContract(BaseModel):
    """PredictIt contract schema."""

    model_config = {"populate_by_name": True}

    id: int | None = None
    name: str | None = None
    short_name: str | None = Field(None, alias="shortName")
    best_buy_yes_cost: float | None = Field(None, alias="bestBuyYesCost")
    best_buy_no_cost: float | None = Field(None, alias="bestBuyNoCost")
    best_sell_yes_cost: float | None = Field(None, alias="bestSellYesCost")
    best_sell_no_cost: float | None = Field(None, alias="bestSellNoCost")
    last_close_price: float | None = Field(None, alias="lastClosePrice")
    last_trade_price: float | None = Field(None, alias="lastTradePrice")
    volume: int | None = None
    date_end: str | None = Field(None, alias="dateEnd")


class PredictItMarket(BaseModel):
    """PredictIt market schema."""

    model_config = {"populate_by_name": True}

    id: int | None = None
    name: str | None = None
    short_name: str | None = Field(None, alias="shortName")
    volume: int | None = None
    status: str | None = None
    category: str | None = None
    subcategory: str | None = None
    date_end: str | None = Field(None, alias="dateEnd")
    contracts: list[PredictItContract] | None = None
