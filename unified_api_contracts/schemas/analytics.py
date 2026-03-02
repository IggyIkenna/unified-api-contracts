"""Advanced analytics schemas — factor attribution, correlation, alternative data signals."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class FactorType(StrEnum):
    MOMENTUM = "momentum"
    VALUE = "value"
    QUALITY = "quality"
    SIZE = "size"
    VOLATILITY = "volatility"
    CARRY = "carry"
    LIQUIDITY = "liquidity"
    MACRO = "macro"
    CRYPTO_BETA = "crypto_beta"
    DEFI_YIELD = "defi_yield"
    SENTIMENT = "sentiment"
    TECHNICAL = "technical"


class AlternativeDataType(StrEnum):
    SENTIMENT = "sentiment"
    SATELLITE = "satellite"
    OPTIONS_FLOW = "options_flow"
    DARK_POOL = "dark_pool"
    SOCIAL_MEDIA = "social_media"
    NEWS_FLOW = "news_flow"
    WEB_TRAFFIC = "web_traffic"
    BLOCKCHAIN_METRICS = "blockchain_metrics"
    INSIDER_TRANSACTIONS = "insider_transactions"


class CorrelationRegime(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRISIS = "crisis"


# ---------------------------------------------------------------------------
# Factor attribution
# ---------------------------------------------------------------------------


class FactorExposure(BaseModel):
    """Exposure of an instrument or portfolio to a single risk factor."""

    factor: FactorType
    beta: float = Field(description="factor loading / sensitivity")
    t_stat: float | None = Field(default=None, description="statistical significance")
    r_squared: float | None = Field(default=None, description="regression R^2")
    factor_return: float | None = Field(default=None, description="factor return over period")
    contribution: float | None = Field(default=None, description="beta * factor_return = P&L contribution")


class FactorAttributionRecord(BaseModel):
    """Daily factor attribution for a portfolio/instrument."""

    date: date
    instrument_id: str | None = None
    portfolio_id: str | None = None
    strategy_id: str | None = None
    total_return: float
    factor_exposures: list[FactorExposure] = Field(default_factory=list)
    factor_returns: dict[str, float] = Field(
        default_factory=dict,
        description="FactorType -> return for that factor on this date",
    )
    residual_return: float | None = Field(default=None, description="return unexplained by factors")
    explained_pct: float | None = Field(default=None, description="fraction of return explained by factors (R^2)")


class FactorAttributionModel(BaseModel):
    """Metadata about a factor model used for attribution."""

    model_id: str
    model_name: str
    factors: list[FactorType]
    estimation_window_days: int = 252
    rebalance_frequency: str = "monthly"
    last_calibrated: date | None = None
    universe: str | None = Field(default=None, description="e.g. crypto_large_cap, equity_us")
    r_squared_median: float | None = None


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------


class CrossAssetCorrelationMatrix(BaseModel):
    """Pairwise correlation matrix across assets/instruments."""

    computed_at: datetime
    window_days: int = Field(description="rolling window used for computation")
    instruments: list[str] = Field(description="ordered list of instruments")
    correlation_matrix: list[list[float]] = Field(description="N x N matrix indexed by instruments list")
    regime: CorrelationRegime = CorrelationRegime.NORMAL
    average_pairwise_correlation: float | None = None
    max_eigenvalue: float | None = Field(default=None, description="largest eigenvalue of corr matrix")


class CorrelationRegimeChange(BaseModel):
    """Detected change in correlation regime."""

    detected_at: datetime
    regime_before: CorrelationRegime
    regime_after: CorrelationRegime
    assets_affected: list[str]
    trigger: str | None = Field(default=None, description="e.g. macro_shock, deleveraging, risk_off")
    correlation_delta: float | None = Field(default=None, description="change in average pairwise correlation")
    confidence: float | None = None


# ---------------------------------------------------------------------------
# Alternative data
# ---------------------------------------------------------------------------


class SentimentScore(BaseModel):
    """Aggregated sentiment score for an asset from a data source."""

    signal_id: str
    source: str = Field(description="e.g. twitter, reddit, news_aggregator, fear_greed_index")
    asset: str
    score: float = Field(description="-1 (extreme bearish) to +1 (extreme bullish)")
    normalized_score: float | None = Field(default=None, description="0-100 scale if source-specific")
    confidence: float | None = Field(default=None, description="0-1")
    timestamp: datetime
    raw_signal_count: int | None = Field(default=None, description="number of raw signals aggregated")
    sample_period_hours: int | None = None
    sentiment_change: float | None = Field(default=None, description="change vs previous period")


class SatelliteObservation(BaseModel):
    """Observation from satellite imagery analysis."""

    observation_id: str
    provider: str = Field(description="e.g. Orbital Insight, SpaceKnow, RS Metrics")
    asset: str = Field(description="commodity or company being observed")
    location: str | None = Field(default=None, description="geohash or lat/lon string")
    observation_date: date
    metric_name: str = Field(description="e.g. oil_tank_fill_pct, parking_lot_cars, ship_count")
    metric_value: float
    confidence: float | None = None
    yoy_change_pct: float | None = None


class OptionsFlowRecord(BaseModel):
    """Unusual options flow detection record (dark pool / block trades)."""

    flow_id: str
    detected_at: datetime
    underlying: str
    expiry: date
    strike: Decimal
    option_type: str = Field(description="call or put")
    contract_count: int
    premium_usd: Decimal
    implied_volatility: float | None = None
    delta: float | None = None
    is_bullish: bool | None = None
    venue: str | None = None
    trade_type: str | None = Field(default=None, description="sweep | block | complex")


class DarkPoolPrintRecord(BaseModel):
    """Off-exchange / dark pool trade print."""

    print_id: str
    detected_at: datetime
    instrument_id: str
    quantity: Decimal
    price: Decimal
    notional_usd: Decimal | None = None
    venue: str = Field(description="e.g. IEX, FINRA ADF, LIQUIDNET")
    is_above_midpoint: bool | None = None
    trade_code: str | None = Field(default=None, description="FINRA trade condition code")


class AlternativeDataSignal(BaseModel):
    """Unified wrapper for any alternative data signal."""

    signal_id: str
    data_type: AlternativeDataType
    asset: str
    value: float
    raw_signal: str | None = Field(default=None, description="serialised source-specific payload")
    timestamp: datetime
    provider: str
    confidence: float | None = None
    lookback_hours: int | None = None
    sentiment: SentimentScore | None = None
    satellite: SatelliteObservation | None = None
    options_flow: OptionsFlowRecord | None = None
    dark_pool: DarkPoolPrintRecord | None = None
