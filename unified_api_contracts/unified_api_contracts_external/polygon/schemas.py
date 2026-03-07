"""Polygon.io REST API schemas: tickers, option contracts, reference data.

Ref: https://polygon.io/docs/stocks/get_v3_reference_tickers
     https://polygon.io/docs/options/get_v3_reference_options_contracts

Auth: Authorization: Bearer {api_key}
Base URL: https://api.polygon.io
"""

__api_version__ = "v3"  # matches provider_api_versions.yaml

from pydantic import BaseModel, Field

from unified_api_contracts import ErrorAction


class PolygonTicker(BaseModel):
    """Single ticker entry from GET /v3/reference/tickers.

    Covers equities, ETFs, indices. active=true filters out delisted securities.
    """

    ticker: str | None = None
    name: str | None = None
    market: str | None = None  # stocks, otc, crypto, fx
    locale: str | None = None  # us, global
    primary_exchange: str | None = Field(None, alias="primary_exchange")
    type: str | None = None  # CS=Common Stock, ETF, ADRC, etc.
    active: bool | None = None
    currency_name: str | None = Field(None, alias="currency_name")
    cik: str | None = None
    composite_figi: str | None = Field(None, alias="composite_figi")
    share_class_figi: str | None = Field(None, alias="share_class_figi")
    last_updated_utc: str | None = Field(None, alias="last_updated_utc")
    description: str | None = None


class PolygonTickersResponse(BaseModel):
    """Paginated response from GET /v3/reference/tickers."""

    results: list[PolygonTicker] | None = None
    status: str | None = None
    request_id: str | None = Field(None, alias="request_id")
    count: int | None = None
    next_url: str | None = Field(None, alias="next_url")


class PolygonOptionContract(BaseModel):
    """Single option contract from GET /v3/reference/options/contracts.

    Covers US equity options. expired=false filters active contracts.
    """

    ticker: str | None = None  # e.g. "O:AAPL230616C00150000"
    underlying_ticker: str | None = Field(None, alias="underlying_ticker")
    contract_type: str | None = Field(None, alias="contract_type")  # call | put
    exercise_style: str | None = Field(None, alias="exercise_style")  # american | european
    expiration_date: str | None = Field(None, alias="expiration_date")  # YYYY-MM-DD
    strike_price: float | None = Field(None, alias="strike_price")
    shares_per_contract: int | None = Field(None, alias="shares_per_contract")
    primary_exchange: str | None = Field(None, alias="primary_exchange")
    additional_underlyings: list[dict[str, object]] | None = Field(None, alias="additional_underlyings")
    cfi: str | None = None  # CFI code e.g. "OCASPS"


class PolygonOptionContractsResponse(BaseModel):
    """Paginated response from GET /v3/reference/options/contracts."""

    results: list[PolygonOptionContract] | None = None
    status: str | None = None
    request_id: str | None = Field(None, alias="request_id")
    next_url: str | None = Field(None, alias="next_url")


class PolygonError(BaseModel):
    """Polygon.io API error response."""

    status: str | None = None
    request_id: str | None = Field(None, alias="request_id")
    error: str | None = None
    message: str | None = None

    @classmethod
    def classify(cls, status: str | None = None, error: str | None = None) -> ErrorAction:
        """Map Polygon error to retry action."""
        if error and "too many" in (error or "").lower():
            return ErrorAction.RETRY_WITH_BACKOFF
        if status == "ERROR" and error and "auth" in (error or "").lower():
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD
