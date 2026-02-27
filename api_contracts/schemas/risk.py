"""Advanced quantitative risk schemas — VaR, CVaR, stress testing, P&L attribution, multi-asset margin.

Extends the basic risk coverage in api_contracts/internal/risk.py with
statistical and portfolio-level analytics.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class VaRMethod(StrEnum):
    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"
    FILTERED_HISTORICAL = "filtered_historical"


class VaRRequest(BaseModel):
    """Request to compute VaR for a portfolio."""

    portfolio_id: str
    confidence_level: float = Field(default=0.99, description="e.g. 0.99 for 99% VaR")
    horizon_days: int = Field(default=1, description="holding period in trading days")
    method: VaRMethod = VaRMethod.HISTORICAL
    lookback_days: int = Field(default=252, description="historical window for calibration")
    instruments: list[str] = Field(default_factory=list, description="override portfolio scope")
    as_of_date: date | None = None


class VaRResult(BaseModel):
    """Value at Risk computation result."""

    portfolio_id: str
    computed_at: datetime
    method: VaRMethod
    confidence_level: float
    horizon_days: int
    var_amount: Decimal = Field(description="VaR in base currency (positive = loss threshold)")
    cvar_amount: Decimal = Field(description="CVaR / Expected Shortfall (loss beyond VaR)")
    var_pct_of_nav: float | None = Field(default=None, description="VaR as % of NAV")
    scenario_count: int | None = Field(default=None, description="MC: number of simulations")
    lookback_days: int | None = None
    component_var: dict[str, Decimal] = Field(
        default_factory=dict, description="per-instrument marginal VaR contribution"
    )


class StressScenario(BaseModel):
    """Definition of a stress scenario with factor shocks."""

    name: str
    description: str
    regime: str | None = Field(default=None, description="e.g. 2008_gfc, covid_march_2020, crypto_may_2021")
    factor_shocks: dict[str, float] = Field(
        description="factor_name -> pct shock, e.g. {'btc_price': -0.40, 'eth_price': -0.45}"
    )
    correlation_stress: float | None = Field(default=None, description="correlation increase during stress (0-1)")
    horizon_days: int = 1


class StressTestResult(BaseModel):
    """Result of applying a stress scenario to a portfolio."""

    portfolio_id: str
    scenario: StressScenario
    computed_at: datetime
    pnl_impact: Decimal = Field(description="P&L impact in base currency (negative = loss)")
    pnl_impact_pct: float | None = None
    var_impact: Decimal | None = Field(default=None, description="change in VaR under stressed correlations")
    positions_breaching_limits: list[str] = Field(
        default_factory=list, description="instrument_ids that breach risk limits under scenario"
    )
    largest_loss_instrument: str | None = None
    liquidity_horizon_days: int | None = Field(default=None, description="days to liquidate under stressed markets")


class SpanMarginLeg(BaseModel):
    """SPAN margin for a single instrument leg."""

    instrument_id: str
    delta: Decimal
    scan_risk: Decimal
    inter_month_spread_charge: Decimal | None = None
    delivery_month_charge: Decimal | None = None


class MultiAssetMarginCalculation(BaseModel):
    """Cross-asset margin computation (SPAN-style for derivatives)."""

    portfolio_id: str
    computed_at: datetime
    initial_margin: Decimal
    maintenance_margin: Decimal
    cross_margin_offset: Decimal = Field(description="margin credit from correlated positions")
    span_credit: Decimal | None = Field(default=None, description="SPAN inter-commodity credit")
    net_margin_required: Decimal
    margin_by_asset: dict[str, Decimal] = Field(
        default_factory=dict, description="per-instrument_id margin requirement"
    )
    margin_by_venue: dict[str, Decimal] = Field(default_factory=dict)
    legs: list[SpanMarginLeg] = Field(default_factory=list)
    currency: str = "USD"


class PnLAttributionRecord(BaseModel):
    """Daily P&L attribution broken down by risk factor."""

    date: date
    strategy_id: str
    portfolio_id: str | None = None
    total_pnl: Decimal
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    delta_pnl: Decimal | None = None
    gamma_pnl: Decimal | None = None
    vega_pnl: Decimal | None = None
    theta_pnl: Decimal | None = None
    rho_pnl: Decimal | None = None
    price_move_pnl: Decimal | None = None
    fx_pnl: Decimal | None = None
    carry_pnl: Decimal | None = None
    fees: Decimal = Decimal("0")
    funding_costs: Decimal = Decimal("0")
    residual_pnl: Decimal | None = Field(default=None, description="unexplained P&L after factor attribution")


class RealTimePnLRecord(BaseModel):
    """Intraday real-time P&L snapshot."""

    timestamp: datetime
    strategy_id: str
    portfolio_id: str | None = None
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    total_pnl: Decimal
    daily_high_pnl: Decimal | None = None
    daily_low_pnl: Decimal | None = None
    delta: Decimal | None = None
    gamma: Decimal | None = None
    vega: Decimal | None = None
    theta_daily: Decimal | None = None


class RiskLimitBreach(BaseModel):
    """Emitted when a risk limit is breached."""

    breach_id: str
    strategy_id: str
    limit_type: str = Field(description="var_1d | concentration | drawdown | leverage | exposure")
    current_value: float
    limit_value: float
    breach_pct: float = Field(description="how far over the limit: (current - limit) / limit")
    timestamp: datetime
    recommended_action: str | None = None
    auto_halt_triggered: bool = False
