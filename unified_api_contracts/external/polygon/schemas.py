"""Polygon.io API response schemas — used by instruments-service TradFi reference data adapter.

Note: The MTDS Polygon.io market-data handler was removed (defunct provider cleanup 2026-05-22).
These schemas remain because instruments-service still uses Polygon.io for TradFi reference
data (instrument metadata: tickers, options chains, expiry calendars).
"""

from pydantic import BaseModel, Field


class PolygonTicker(BaseModel):
    ticker: str | None = None
    name: str | None = None
    market: str | None = None
    locale: str | None = None
    primary_exchange: str | None = Field(None, alias="primary_exchange")
    type: str | None = None
    active: bool | None = None
    currency_name: str | None = Field(None, alias="currency_name")
    cik: str | None = None
    composite_figi: str | None = Field(None, alias="composite_figi")
    share_class_figi: str | None = Field(None, alias="share_class_figi")
    last_updated_utc: str | None = Field(None, alias="last_updated_utc")
    description: str | None = None


class PolygonTickersResponse(BaseModel):
    results: list[PolygonTicker] | None = None
    status: str | None = None
    request_id: str | None = Field(None, alias="request_id")
    count: int | None = None
    next_url: str | None = Field(None, alias="next_url")


class PolygonOptionContract(BaseModel):
    ticker: str | None = None
    underlying_ticker: str | None = Field(None, alias="underlying_ticker")
    contract_type: str | None = Field(None, alias="contract_type")
    exercise_style: str | None = Field(None, alias="exercise_style")
    expiration_date: str | None = Field(None, alias="expiration_date")
    strike_price: float | None = Field(None, alias="strike_price")
    shares_per_contract: int | None = Field(None, alias="shares_per_contract")
    primary_exchange: str | None = Field(None, alias="primary_exchange")
    additional_underlyings: list[dict[str, object]] | None = Field(None, alias="additional_underlyings")
    cfi: str | None = None


class PolygonOptionContractsResponse(BaseModel):
    results: list[PolygonOptionContract] | None = None
    status: str | None = None
    request_id: str | None = Field(None, alias="request_id")
    next_url: str | None = Field(None, alias="next_url")
