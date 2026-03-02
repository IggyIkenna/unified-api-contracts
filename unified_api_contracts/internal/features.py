"""Internal feature schemas — delta-one features, vol surface, term structure, on-chain features."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DeltaOneFeatureRecord(BaseModel):
    """Output row from features-delta-one-service (subset of FEATURES_SCHEMA key groups).

    All feature columns are NOT NULL in the GCS parquet; None here indicates
    optional group presence depending on instrument type.
    """

    timestamp: datetime
    timestamp_out: datetime
    instrument_id: str

    # Technical indicators
    rsi_14: float | None = None
    rsi_7: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    adx: float | None = None

    # Moving averages
    sma_5: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_5: float | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None

    # Volatility realized
    rv_5: float | None = None
    rv_20: float | None = None
    rv_60: float | None = None
    parkinson_5: float | None = None
    garman_klass_5: float | None = None

    # Momentum
    momentum_5: float | None = None
    momentum_20: float | None = None
    roc_5: float | None = None
    roc_20: float | None = None

    # Volume
    volume_sma_20: float | None = None
    volume_ratio: float | None = None
    obv: float | None = None
    vwap_deviation: float | None = None

    # Market microstructure
    bid_ask_spread: float | None = None
    order_imbalance: float | None = None
    trade_intensity: float | None = None

    # Funding / OI (derivatives)
    funding_rate: float | None = None
    funding_rate_ma_8h: float | None = None
    open_interest: float | None = None
    open_interest_change_pct: float | None = None

    # Liquidations
    liquidation_buy_usd: float | None = None
    liquidation_sell_usd: float | None = None
    liquidation_ratio: float | None = None

    # Returns
    return_1h: float | None = None
    return_4h: float | None = None
    return_24h: float | None = None

    # Temporal
    hour_of_day: int | None = None
    day_of_week: int | None = None
    is_weekend: bool | None = None

    # Targets (labels for ML)
    target_direction: int | None = None
    target_return_1h: float | None = None


class OptionsIvRecord(BaseModel):
    """Output row from features-volatility-service (options_iv schema)."""

    timestamp: datetime
    timestamp_out: datetime
    venue: str
    underlying_symbol: str
    atm_iv: float | None = None
    call_25d_iv: float | None = None
    put_25d_iv: float | None = None
    skew_25d: float | None = None
    skew_25d_ratio: float | None = None
    risk_reversal_25d: float | None = None
    butterfly_25d: float | None = None
    term_slope: float | None = None
    term_curvature: float | None = None
    iv_at_90_moneyness: float | None = None
    iv_at_100_moneyness: float | None = None
    iv_at_110_moneyness: float | None = None
    implied_forward: float | None = None
    implied_rate: float | None = None
    total_options_volume: float | None = None
    put_call_volume_ratio: float | None = None
    atm_bid_ask_spread: float | None = None


class FuturesTermStructureRecord(BaseModel):
    """Output row from features-volatility-service (futures_term_structure schema)."""

    timestamp: datetime
    timestamp_out: datetime
    venue: str
    underlying_symbol: str
    spot_price: float
    front_month_price: float | None = None
    front_month_expiry_days: int | None = None
    basis: float | None = None
    basis_pct: float | None = None
    annualized_basis: float | None = None
    curve_slope: float | None = None
    curve_curvature: float | None = None
    roll_yield_1m: float | None = None
    roll_yield_3m: float | None = None


class FeatureSnapshotRequest(BaseModel):
    """Request to fetch a feature snapshot for ML inference."""

    instrument_id: str
    timestamp: datetime
    lookback_window: int = Field(description="Number of bars to include")
    feature_groups: list[str] = Field(default_factory=list, description="Empty = all groups")
    timeframe: str = "1h"
