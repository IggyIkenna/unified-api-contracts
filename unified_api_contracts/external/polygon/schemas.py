"""Polygon.io REST API schemas: tickers, option contracts, reference data.

Ref: https://polygon.io/docs/stocks/get_v3_reference_tickers
     https://polygon.io/docs/options/get_v3_reference_options_contracts

Auth: Authorization: Bearer {api_key}
Base URL: https://api.polygon.io
"""

__api_version__ = "v3"  # matches provider_api_versions.yaml

from pydantic import BaseModel, Field

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction


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


class PolygonAggregate(BaseModel):
    """Single OHLCV bar from GET /v3/aggs/ticker/{ticker}/range/...

    Ref: https://polygon.io/docs/stocks/get_v3_aggs_ticker__ticker__range
    """

    o: float | None = None  # open
    h: float | None = None  # high
    l: float | None = None  # low
    c: float | None = None  # close
    v: float | None = None  # volume
    vw: float | None = None  # vwap
    t: int | None = None  # timestamp (ms)
    n: int | None = None  # number of items in aggregate


class PolygonAggregatesResponse(BaseModel):
    """Response from GET /v3/aggs/ticker/{ticker}/range/..."""

    results: list[PolygonAggregate] | None = None
    status: str | None = None
    ticker: str | None = None
    query_count: int | None = Field(None, alias="queryCount")
    results_count: int | None = Field(None, alias="resultsCount")


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


class PolygonDividend(BaseModel):
    """Single dividend record from GET /v3/reference/dividends.

    Ref: https://polygon.io/docs/stocks/get_v3_reference_dividends
    """

    ticker: str | None = None
    ex_dividend_date: str | None = Field(None, alias="ex_dividend_date")
    pay_date: str | None = Field(None, alias="pay_date")
    record_date: str | None = Field(None, alias="record_date")
    declaration_date: str | None = Field(None, alias="declaration_date")
    cash_amount: float | None = Field(None, alias="cash_amount")
    currency: str | None = None
    dividend_type: str | None = Field(None, alias="dividend_type")  # CD, SC, LT, ST
    frequency: int | None = None  # 1=annual, 2=semi, 4=quarterly, 12=monthly


class PolygonSplit(BaseModel):
    """Single stock split record from GET /v3/reference/splits.

    Ref: https://polygon.io/docs/stocks/get_v3_reference_splits
    """

    ticker: str | None = None
    execution_date: str | None = Field(None, alias="execution_date")
    split_from: float | None = Field(None, alias="split_from")
    split_to: float | None = Field(None, alias="split_to")


class PolygonDividendsResponse(BaseModel):
    """Paginated response from GET /v3/reference/dividends."""

    results: list[PolygonDividend] | None = None
    status: str | None = None
    request_id: str | None = Field(None, alias="request_id")
    next_url: str | None = Field(None, alias="next_url")


class PolygonSplitsResponse(BaseModel):
    """Paginated response from GET /v3/reference/splits."""

    results: list[PolygonSplit] | None = None
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
            return ErrorAction.RETRY
        if status == "ERROR" and error and "auth" in (error or "").lower():
            return ErrorAction.FAIL
        return ErrorAction.FAIL
