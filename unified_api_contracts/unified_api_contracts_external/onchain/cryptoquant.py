"""Pydantic schemas for CryptoQuant on-chain analytics API.

Source: https://docs.cryptoquant.com/
Paid API key required. Rate limits: 300 requests/minute (standard tier).

Used by unified-market-interface for exchange flow data, miner metrics, and on-chain indicators.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from unified_api_contracts.shared import ErrorAction

# API Constants
CRYPTOQUANT_BASE_URL = "https://api.cryptoquant.com/v1"
CRYPTOQUANT_RATE_LIMIT_STANDARD = 300  # requests per minute
CRYPTOQUANT_RATE_LIMIT_PREMIUM = 1000  # requests per minute


class CryptoQuantExchangeFlow(BaseModel):
    """Exchange inflow/outflow data point."""

    timestamp_utc: datetime = Field(..., alias="datetime", description="Data point timestamp (UTC)")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    value: float = Field(..., description="Flow value in BTC or native asset")
    exchange: str | None = Field(None, description="Exchange name (e.g., binance, coinbase)")
    symbol: str = Field(..., description="Asset symbol (e.g., BTC, ETH)")
    flow_type: str = Field(..., description="Flow direction: inflow, outflow, netflow")


class CryptoQuantExchangeFlowResponse(BaseModel):
    """Response from /exchange-flows endpoint."""

    status: dict[str, int] = Field(..., description="Status metadata (code, elapsed_time)")
    result: dict[str, list[CryptoQuantExchangeFlow]] = Field(..., description="Flow data by exchange")


class CryptoQuantMinerMetrics(BaseModel):
    """Miner activity metrics."""

    timestamp_utc: datetime = Field(..., alias="datetime", description="Data point timestamp (UTC)")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    miner_revenue: float | None = Field(None, description="Total miner revenue in USD")
    miner_revenue_btc: float | None = Field(None, description="Total miner revenue in BTC")
    hash_rate: float | None = Field(None, description="Network hash rate (TH/s)")
    difficulty: float | None = Field(None, description="Mining difficulty")
    miner_position_index: float | None = Field(None, description="Miner Position Index (MPI): miner outflow / 1y MA")
    puell_multiple: float | None = Field(None, description="Puell Multiple: daily issuance / 365d MA issuance")


class CryptoQuantMinerMetricsResponse(BaseModel):
    """Response from /miner-metrics endpoint."""

    status: dict[str, int] = Field(..., description="Status metadata")
    result: dict[str, list[CryptoQuantMinerMetrics]] = Field(..., description="Miner metrics data")


class CryptoQuantReserveMetrics(BaseModel):
    """Exchange reserve metrics."""

    timestamp_utc: datetime = Field(..., alias="datetime", description="Data point timestamp (UTC)")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    reserve: float = Field(..., description="Total exchange reserve in BTC or native asset")
    exchange: str | None = Field(None, description="Exchange name")
    symbol: str = Field(..., description="Asset symbol")
    reserve_change_1d: float | None = Field(None, description="1-day reserve change")
    reserve_change_7d: float | None = Field(None, description="7-day reserve change")
    reserve_change_30d: float | None = Field(None, description="30-day reserve change")


class CryptoQuantReserveMetricsResponse(BaseModel):
    """Response from /exchange-reserves endpoint."""

    status: dict[str, int] = Field(..., description="Status metadata")
    result: dict[str, list[CryptoQuantReserveMetrics]] = Field(..., description="Reserve data by exchange")


class CryptoQuantWhaleMetrics(BaseModel):
    """Whale wallet activity metrics."""

    timestamp_utc: datetime = Field(..., alias="datetime", description="Data point timestamp (UTC)")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    whale_count: int | None = Field(None, description="Number of whale addresses (>1000 BTC)")
    whale_balance: float | None = Field(None, description="Total whale balance in BTC")
    whale_ratio: float | None = Field(None, description="Whale balance / circulating supply")
    large_transactions: int | None = Field(None, description="Number of large transactions (>$100k)")
    large_transaction_volume: float | None = Field(None, description="Volume of large transactions in USD")


class CryptoQuantWhaleMetricsResponse(BaseModel):
    """Response from /whale-metrics endpoint."""

    status: dict[str, int] = Field(..., description="Status metadata")
    result: dict[str, list[CryptoQuantWhaleMetrics]] = Field(..., description="Whale metrics data")


class CryptoQuantStablecoinMetrics(BaseModel):
    """Stablecoin supply and flow metrics."""

    timestamp_utc: datetime = Field(..., alias="datetime", description="Data point timestamp (UTC)")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    total_supply: float = Field(..., description="Total stablecoin supply in USD")
    supply_change_1d: float | None = Field(None, description="1-day supply change in USD")
    supply_change_7d: float | None = Field(None, description="7-day supply change in USD")
    supply_ratio: float | None = Field(None, description="Stablecoin supply / BTC market cap (liquidity indicator)")
    stablecoin: str = Field(..., description="Stablecoin symbol (e.g., USDT, USDC)")


class CryptoQuantStablecoinMetricsResponse(BaseModel):
    """Response from /stablecoin-metrics endpoint."""

    status: dict[str, int] = Field(..., description="Status metadata")
    result: dict[str, list[CryptoQuantStablecoinMetrics]] = Field(..., description="Stablecoin data")


class CryptoQuantError(BaseModel):
    """CryptoQuant API error."""

    message: str | None = Field(None, description="Error message")
    status_code: int | None = Field(None, description="HTTP status code")
    error_code: str | None = Field(None, description="CryptoQuant error code")

    @classmethod
    def classify(cls, status_code: int | None = None, error_code: str | None = None) -> ErrorAction:
        """Map CryptoQuant error to retry action."""
        if status_code == 429:
            return ErrorAction.RETRY_WITH_BACKOFF
        if status_code is not None and status_code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if status_code == 401:
            return ErrorAction.FAIL_HARD  # Invalid API key
        if status_code == 403:
            return ErrorAction.FAIL_HARD  # Forbidden / subscription required
        if error_code == "RATE_LIMIT_EXCEEDED":
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD


class CryptoQuantRequestParams(BaseModel):
    """Request parameters for CryptoQuant API endpoints."""

    window: str = Field(default="day", description="Time window: hour, day, week, month")
    from_: int | None = Field(None, alias="from", description="Start timestamp (Unix seconds)")
    to: int | None = Field(None, description="End timestamp (Unix seconds)")
    exchange: str | None = Field(None, description="Exchange slug (e.g., binance, coinbase)")
    symbol: str = Field(default="BTC", description="Asset symbol")
    limit: int | None = Field(None, ge=1, le=10000, description="Number of data points to return")

    model_config = {"populate_by_name": True}


# On-chain indicator thresholds
EXCHANGE_NETFLOW_BULLISH = -1000.0  # BTC netflow < -1000 = bullish (outflow from exchanges)
EXCHANGE_NETFLOW_BEARISH = 1000.0  # BTC netflow > 1000 = bearish (inflow to exchanges)
MINER_POSITION_INDEX_SELL_PRESSURE = 2.0  # MPI > 2.0 = high miner sell pressure
PUELL_MULTIPLE_BOTTOM = 0.5  # Puell < 0.5 = historically bullish entry
PUELL_MULTIPLE_TOP = 4.0  # Puell > 4.0 = historically bearish exit
WHALE_RATIO_ACCUMULATION = 0.45  # Whale ratio > 45% = accumulation phase
STABLECOIN_SUPPLY_RATIO_HIGH = 0.15  # Stablecoin/BTC cap > 15% = high liquidity (bullish)
