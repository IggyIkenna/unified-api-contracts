"""Internal risk schemas — metrics, alerts, exposure, pre-trade checks, account state."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class RiskStatus(StrEnum):
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertType(StrEnum):
    PRE_TRADE_REJECTION = "PRE_TRADE_REJECTION"
    RISK_WARNING = "RISK_WARNING"
    RISK_CRITICAL = "RISK_CRITICAL"
    EXPOSURE_BREACH = "EXPOSURE_BREACH"
    MARGIN_WARNING = "MARGIN_WARNING"
    LIQUIDATION_RISK = "LIQUIDATION_RISK"
    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT"
    CONCENTRATION_LIMIT = "CONCENTRATION_LIMIT"
    LEVERAGE_BREACH = "LEVERAGE_BREACH"
    """Per-leg actual_leverage drifted from target_leverage by more than the
    configured alert tightness multiplier on the leg's ``rebalance_trigger_bps``.
    Independent of the LeveragedLegController auto-rebalance — operator-visible
    safety overlay raised after the controller's chance to act has passed.
    Emitted by risk-and-exposure-service. SSOT for the LegPortfolioState risk
    overlay declared in
    ``unified-trading-pm/plans/active/leveraged_leg_controller_2026_05_01.plan.md``."""


class PositionSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"
    NEUTRAL = "NEUTRAL"  # Non-directional (lending, staking, LP)


class RiskPosition(BaseModel):
    """Position as tracked by risk-and-exposure-service."""

    client_id: str = Field(..., json_schema_extra={"pii": True})
    strategy_id: str | None = None
    venue: str
    instrument: str
    quantity: Decimal
    avg_price: Decimal
    position_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    last_updated: datetime


class RiskMetrics(BaseModel):
    """Computed risk metrics per client (output of risk engine)."""

    client_id: str = Field(..., json_schema_extra={"pii": True})
    timestamp: datetime
    leverage: Decimal
    margin_usage: Decimal
    concentration: Decimal
    drawdown: Decimal
    account_equity: Decimal
    total_position_value: Decimal
    cash_balance: Decimal
    leverage_status: RiskStatus
    concentration_status: RiskStatus
    drawdown_status: RiskStatus
    health_factor: Decimal | None = Field(default=None, description="DeFi lending health factor (collateral/debt)")
    health_factor_status: RiskStatus | None = None
    weighted_ltv: Decimal | None = Field(default=None, description="Weighted loan-to-value ratio across DeFi positions")
    delta_composite: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Net delta exposure per underlying asset (e.g. {'ETH': Decimal('-0.05')})",
    )
    share_class: str | None = Field(default=None, description="Base currency denomination (USDT, ETH, BTC)")
    account_equity_share_class: Decimal | None = Field(
        default=None, description="Account equity in share class currency"
    )
    account_id: str | None = Field(default=None, description="Account-level risk when specified")
    strategy_id: str | None = Field(default=None, description="Strategy-level risk when specified")
    var_1d: Decimal | None = None
    var_5d: Decimal | None = None
    expected_shortfall: Decimal | None = None
    beta: Decimal | None = None


class AlertContextData(BaseModel):
    client_id: str = Field(..., json_schema_extra={"pii": True})
    strategy_id: str | None = None
    metric_type: str | None = None
    venue: str | None = None
    instrument: str | None = None
    position_size: Decimal | None = None
    trade_id: str | None = None
    order_id: str | None = None
    extra: dict[str, str | float | int | bool | None] = Field(default_factory=dict)


class AlertMessage(BaseModel):
    """Risk alert published to risk consumers (Pub/Sub or GCS)."""

    alert_type: AlertType
    client_id: str = Field(..., json_schema_extra={"pii": True})
    metric: str
    current_value: Decimal
    threshold: Decimal
    timestamp: datetime
    recommended_action: str | None = None
    context: AlertContextData | None = None
    severity: str = "WARNING"


class LimitCheckResult(BaseModel):
    """Result of a single limit check."""

    passed: bool = Field(description="Whether the check passed")
    limit_type: str = Field(description="Type of limit checked")
    current_value: Decimal = Field(description="Current value")
    limit_value: Decimal = Field(description="Limit threshold")
    reason: str | None = Field(default=None, description="Failure reason if check failed")


class PreTradeCheckRequest(BaseModel):
    client_id: str = Field(..., json_schema_extra={"pii": True})
    strategy_id: str | None = None
    venue: str
    instrument: str
    side: str
    quantity: Decimal
    estimated_price: Decimal
    order_type: str | None = None
    is_inverse: bool = False
    contract_size: Decimal = Decimal("1")


class PreTradeCheckResponse(BaseModel):
    approved: bool
    client_id: str = Field(..., json_schema_extra={"pii": True})
    instrument: str
    reason: str = ""
    alerts: list[AlertMessage] = Field(default_factory=list)
    checks: dict[str, LimitCheckResult] = Field(default_factory=dict)
    request: PreTradeCheckRequest | None = None
    timestamp: datetime | None = None


class ExposureSummary(BaseModel):
    client_id: str = Field(..., json_schema_extra={"pii": True})
    timestamp: datetime
    gross_exposure: Decimal
    net_exposure: Decimal
    long_exposure: Decimal
    short_exposure: Decimal
    by_venue: dict[str, Decimal] = Field(default_factory=dict)
    by_instrument: dict[str, Decimal] = Field(default_factory=dict)
    total_positions: int = 0


class Balance(BaseModel):
    currency: str
    free: Decimal
    locked: Decimal
    total: Decimal


class MarginState(BaseModel):
    account_id: str = Field(..., json_schema_extra={"pii": True})
    venue: str
    timestamp: datetime
    margin_level: float  # margin-ratio: float-ok (used_margin / total_margin, unitless ratio)
    total_collateral: Decimal
    total_debt: Decimal
    available_margin: Decimal
    liquidation_price: Decimal | None = None
    margin_ratio: float | None = None  # margin-ratio: float-ok (debt / collateral, unitless ratio)
    is_margin_call: bool = False


class InternalPosition(BaseModel):
    """Position tracked by unified-trade-execution-interface / position-balance-monitor."""

    instrument_id: str
    side: PositionSide
    quantity: Decimal
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    leverage: float | None = None  # financial-ratio: float-ok (leverage multiplier, unitless)
    liquidation_price: Decimal | None = None
    realized_pnl: Decimal | None = None


class AccountState(BaseModel):
    """Snapshot of a venue account — published after each fill or periodic sync."""

    timestamp: datetime
    venue: str
    account_id: str = Field(..., json_schema_extra={"pii": True})
    client_id: str | None = Field(default=None, json_schema_extra={"pii": True})
    positions: list[InternalPosition] = Field(default_factory=list)
    balances: dict[str, Balance] = Field(default_factory=dict)
    margin: MarginState | None = None


class PnLBreakdown(BaseModel):
    """Full PnL breakdown per position or portfolio slice.

    Dimensions follow the standard attribution model:
    - delta_pnl: PnL attributable to directional price moves (delta x dS).
    - funding_pnl: Cumulative funding payments received / paid (perpetual swaps).
    - basis_pnl: Cash-futures or cash-perp basis convergence contribution.
    - interest_rate_pnl: PnL from interest-rate curve moves (bonds, rate swaps).
    - greeks_delta_pnl / greeks_gamma_pnl / greeks_theta_pnl / greeks_vega_pnl:
      Per-greek options PnL breakdown.
    - realized_pnl / unrealized_pnl: Closed vs open position PnL.
    - mark_to_market_pnl: Total MTM PnL — sum of all attribution dimensions
      plus any residual unexplained PnL.
    """

    instrument_id: str
    client_id: str = Field(default="", json_schema_extra={"pii": True})
    strategy_id: str | None = None
    timestamp: datetime | None = None
    instrument_type: str = ""
    underlying: str = ""
    asset_class: str = ""
    account_id: str = ""
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Closed position PnL")
    unrealized_pnl: Decimal = Field(default=Decimal("0"), description="Open position PnL")
    delta_pnl: Decimal | None = Field(default=None, description="Directional delta PnL")
    funding_pnl: Decimal = Field(default=Decimal("0"), description="Funding payment PnL")
    funding_rate_pnl: Decimal | None = Field(default=None, description="Funding rate PnL (alias)")
    basis_pnl: Decimal | None = Field(default=None, description="Cash-futures basis PnL")
    interest_rate_pnl: Decimal | None = Field(default=None, description="Interest-rate curve PnL")
    greeks_pnl: Decimal = Field(default=Decimal("0"), description="Aggregate options Greeks PnL")
    greeks_delta_pnl: Decimal | None = Field(default=None, description="Options delta PnL")
    greeks_gamma_pnl: Decimal | None = Field(default=None, description="Options gamma PnL")
    greeks_theta_pnl: Decimal | None = Field(default=None, description="Options theta PnL")
    greeks_vega_pnl: Decimal | None = Field(default=None, description="Options vega PnL")
    gas_cost_usd: Decimal | None = Field(default=None, description="Total gas cost in USD for this instrument")
    slippage_bps: int | None = Field(default=None, description="Execution slippage in basis points")
    residual_pnl: Decimal | None = Field(default=None, description="Unexplained PnL = total - sum(components)")
    mark_to_market_pnl: Decimal | None = Field(default=None, description="Total MTM PnL including residual")
    currency: str = "USD"
    share_class: str | None = Field(default=None, description="Base currency denomination (USDT, ETH, BTC)")
    share_class_pnl: Decimal | None = Field(default=None, description="P&L denominated in share class base currency")
    fx_attribution_pnl: Decimal | None = Field(
        default=None, description="P&L attributable to FX movement vs share class"
    )
    lst_yield_pnl: Decimal | None = Field(default=None, description="P&L from LST ratio appreciation (staking yield)")


class GreeksExposure(BaseModel):
    """Options Greeks exposure per position.

    All Greeks are expressed in the position's native currency unless noted:
    - delta: Rate of change of option price with respect to underlying price.
    - gamma: Rate of change of delta with respect to underlying price.
    - theta: Time decay — change in option price per calendar day.
    - vega: Sensitivity to a 1-percentage-point move in implied volatility.
    - rho: Sensitivity to a 1-percentage-point move in the risk-free rate.
    """

    instrument_id: str = ""
    client_id: str = Field(default="", json_schema_extra={"pii": True})
    strategy_id: str | None = None
    timestamp: datetime | None = None
    delta: Decimal = Field(
        default=Decimal("0"),
        description="Option delta (unitless, range -1 to +1 for vanilla options)",
    )
    gamma: Decimal = Field(default=Decimal("0"), description="Option gamma")
    theta: Decimal = Field(default=Decimal("0"), description="Daily theta (currency units per day)")
    vega: Decimal = Field(default=Decimal("0"), description="Vega per 1pp IV move")
    rho: Decimal = Field(default=Decimal("0"), description="Rho per 1pp rate move")
    underlying_price: Decimal = Field(default=Decimal("0"))
    position_quantity: Decimal | None = None


class CircuitBreakerEvent(BaseModel):
    """Runtime event emitted on circuit breaker state transitions.

    Distinct from ``CircuitBreakerEventMessage`` (the Pub/Sub envelope) — this
    schema represents the domain event captured by the monitoring pipeline and
    stored to GCS / forwarded to risk consumers.

    States follow the 3-state machine: CLOSED → OPEN → HALF_OPEN → CLOSED.
    """

    venue: str = Field(description="Venue slug where the breaker tripped (e.g. 'binance')")
    state: str = Field(description="New breaker state after transition: CLOSED, OPEN, or HALF_OPEN")
    triggered_at: datetime = Field(description="UTC wall-clock time of the state transition")
    error_count: int = Field(ge=0, description="Cumulative triggering-error count at time of transition")
    cooldown_until: datetime | None = Field(
        default=None,
        description="UTC time when the OPEN cooldown expires and HALF_OPEN probe is allowed",
    )
    reason: str | None = None
    service_name: str | None = None


class EODSettlementTrigger(BaseModel):
    """End-of-day settlement trigger published to the ``eod-settlement`` Pub/Sub topic.

    Consumed by pnl-attribution-service and risk-and-exposure-service to
    lock in daily PnL, settle positions, and archive daily snapshots.
    """

    settlement_date: date = Field(description="Calendar date being settled (YYYY-MM-DD)")
    venues: list[str] = Field(description="Ordered list of venue slugs included in this settlement batch")
    settlement_time: time = Field(description="Wall-clock UTC time at which settlement calculations should run")
    triggered_by: str = Field(
        default="scheduler",
        description="Source that fired the trigger: 'scheduler', 'manual', or 'cascade'",
    )
    correlation_id: str | None = None


class CorrelationEntry(BaseModel):
    """Pairwise correlation between underlyings for risk group netting."""

    underlying_a: str
    underlying_b: str
    correlation: Decimal
    lookback_days: int
    last_updated: datetime
    source: str = "empirical"


# ---------------------------------------------------------------------------
# VaR / Stress Testing (moved from UAC — internal computation, not external data)
# ---------------------------------------------------------------------------


class VaRMethod(StrEnum):
    """Supported VaR computation methods."""

    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"
    FILTERED_HISTORICAL = "filtered_historical"


class StressScenarioType(StrEnum):
    """Named stress scenarios with predefined crisis multipliers."""

    GFC_2008 = "GFC_2008"
    COVID_2020 = "COVID_2020"
    CRYPTO_BLACK_THURSDAY_2020 = "CRYPTO_BLACK_THURSDAY_2020"


class VaRRequest(BaseModel):
    """Request to compute VaR for a portfolio."""

    portfolio_id: str
    confidence_level: Decimal = Field(default=Decimal("0.99"), description="e.g. 0.99 for 99% VaR")
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
    confidence_level: Decimal
    horizon_days: int
    var_amount: Decimal = Field(description="VaR in base currency (positive = loss threshold)")
    cvar_amount: Decimal = Field(description="CVaR / Expected Shortfall")
    var_pct_of_nav: Decimal | None = Field(default=None, description="VaR as % of NAV")
    scenario_count: int | None = Field(default=None, description="MC: number of simulations")
    lookback_days: int | None = None
    component_var: dict[str, Decimal] = Field(default_factory=dict, description="per-instrument marginal VaR")


class StressScenario(BaseModel):
    """Definition of a stress scenario with factor shocks."""

    name: str
    description: str
    scenario_type: StressScenarioType | None = None
    factor_shocks: dict[str, Decimal] = Field(description="factor_name -> pct shock")
    correlation_stress: Decimal | None = None
    horizon_days: int = 1


class StressTestResult(BaseModel):
    """Result of applying a stress scenario to a portfolio."""

    portfolio_id: str
    scenario: StressScenario
    computed_at: datetime
    pnl_impact: Decimal = Field(description="P&L impact in base currency (negative = loss)")
    pnl_impact_pct: Decimal | None = None
    var_impact: Decimal | None = None
    positions_breaching_limits: list[str] = Field(default_factory=list)
    largest_loss_instrument: str | None = None


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
    funding_pnl: Decimal | None = None
    basis_pnl: Decimal | None = None
    fx_pnl: Decimal | None = None
    carry_pnl: Decimal | None = None
    fees: Decimal = Decimal("0")
    residual_pnl: Decimal | None = Field(default=None, description="unexplained P&L")


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


# ---------------------------------------------------------------------------
# Strategy-risk subscription — strategies declare which risks apply to them
# ---------------------------------------------------------------------------


class StrategyRiskProfile(BaseModel):
    """Which risk types a strategy subscribes to. Unsubscribed = zero in matrix."""

    strategy_type: str
    subscribed_risks: list[str] = Field(description="RiskType.value strings from UAC risk_taxonomy")
    custom_risk_ids: list[str] = Field(default_factory=list, description="user-defined custom risk IDs")


# ---------------------------------------------------------------------------
# Risk aggregation hierarchy
# ---------------------------------------------------------------------------


class RiskAggregationLevel(StrEnum):
    """Levels in the Company->Client->Account->Strategy->Underlying->Instrument tree."""

    COMPANY = "company"
    CLIENT = "client"
    ACCOUNT = "account"
    STRATEGY = "strategy"
    UNDERLYING = "underlying"
    INSTRUMENT = "instrument"


class RiskPnLNode(BaseModel):
    """Single node in the aggregation tree. Used at every level."""

    level: RiskAggregationLevel
    level_id: str
    risk_by_type: dict[str, Decimal] = Field(default_factory=dict, description="RiskType.value -> exposure")
    pnl_by_type: dict[str, Decimal] = Field(default_factory=dict, description="RiskType.value -> P&L")
    var_by_type: dict[str, Decimal] = Field(default_factory=dict, description="RiskType.value -> marginal VaR")
    children: list[RiskPnLNode] = Field(default_factory=list)
    subscribed_risks: list[str] = Field(default_factory=list, description="from StrategyRiskProfile")


class DurationBucket(StrEnum):
    """Term structure maturity buckets for duration risk."""

    OVERNIGHT = "overnight"
    ONE_WEEK = "1w"
    ONE_MONTH = "1m"
    THREE_MONTH = "3m"
    SIX_MONTH = "6m"
    ONE_YEAR = "1y"
    TWO_YEAR_PLUS = "2y+"


class TermStructureExposure(BaseModel):
    """Duration risk decomposed by maturity bucket."""

    underlying: str
    exposures_by_bucket: dict[str, Decimal] = Field(description="DurationBucket.value -> exposure")


# ---------------------------------------------------------------------------
# Extended P&L attribution (dict-based — no schema change for new risk types)
# ---------------------------------------------------------------------------


class ExtendedPnLAttribution(BaseModel):
    """P&L attributed to each RiskType. Dict-based for extensibility."""

    client_id: str
    strategy_id: str | None = None
    underlying: str | None = None
    instrument_id: str | None = None
    level: str = Field(description="RiskAggregationLevel.value")
    timestamp: datetime
    pnl_by_risk_type: dict[str, Decimal] = Field(description="RiskType.value → P&L")
    total_pnl: Decimal
    residual_pnl: Decimal = Field(description="unexplained — large residual = missing risk factor")
    fees: Decimal = Decimal("0")


# ---------------------------------------------------------------------------
# Custom risk types — strategy-specific, user-defined risks
# ---------------------------------------------------------------------------


class CustomRiskEvaluationMethod(StrEnum):
    """How to evaluate a custom risk scenario."""

    RATE_SENSITIVITY = "rate_sensitivity"
    SCENARIO_PNL = "scenario_pnl"
    THRESHOLD_BREACH = "threshold_breach"


class CustomRiskTypeDefinition(BaseModel):
    """Definition of a custom risk type. Fixed schema — restart to add new types."""

    risk_id: str = Field(description="e.g. eth_borrow_rate_sensitivity")
    display_name: str = Field(description="e.g. ETH Borrow Rate Sensitivity")
    evaluation_method: CustomRiskEvaluationMethod
    applicable_strategies: list[str] = Field(description="strategy types this applies to")
    description: str


# ---------------------------------------------------------------------------
# Emergency exit playbooks — per-strategy position unwinding
# ---------------------------------------------------------------------------


class EmergencyExitType(StrEnum):
    """Type of emergency position exit procedure."""

    MARKET_CLOSE = "market_close"
    ATOMIC_UNWIND = "atomic_unwind"
    DELEVERAGE_SEQUENCE = "deleverage_sequence"
    DELTA_HEDGE = "delta_hedge"
    STOP_NEW_ONLY = "stop_new_only"
    HEDGE_CROSS_VENUE = "hedge_cross_venue"
    FAST_UNWIND = "fast_unwind"
    SLOW_UNWIND = "slow_unwind"
    HYBRID_UNWIND = "hybrid_unwind"


class EmergencyExitStep(BaseModel):
    """Single step in an emergency exit sequence."""

    order: int = Field(description="execution sequence — same order = simultaneous")
    action: str = Field(description="close_perp, sell_spot, repay_debt, withdraw_collateral")
    instrument_filter: str | None = Field(default=None, description="which instrument/leg")
    urgency: str = Field(default="immediate", description="immediate | best_effort | queued")
    max_slippage_bps: int = Field(default=50)
    timeout_seconds: int = Field(default=300)


class EmergencyExitPlaybook(BaseModel):
    """Per-strategy emergency exit procedure."""

    strategy_type: str
    exit_type: EmergencyExitType
    steps: list[EmergencyExitStep]
    description: str = Field(description="human-readable: e.g. unwind both legs of basis trade")


class ClientRiskTolerance(BaseModel):
    """Per-client risk tolerance thresholds. Loaded from GCS."""

    client_id: str
    max_drawdown_pct: Decimal = Field(description="kill switch trigger: e.g. 10.0 = -10%")
    max_var_breach_pct: Decimal = Field(default=Decimal("150"), description="e.g. 150 = 1.5x VaR limit")
    auto_kill_switch_timeout_minutes: int = Field(default=30)
    emergency_exit_override: str | None = Field(default=None, description="close_all | hedge_only | stop_new_only")


# ---------------------------------------------------------------------------
# Scoped kill switch — composable by entity + dimension
# ---------------------------------------------------------------------------


class ScopedKillSwitchSpec(BaseModel):
    """Composable kill switch scope spec. Combines entity (who) + dimension (what)."""

    entity_type: str = Field(description="company | client | account")
    entity_id: str | None = Field(default=None, description="None = all (company-wide)")
    strategy_type: str | None = Field(default=None, description="None = all strategies")
    venue: str | None = Field(default=None, description="None = all venues")
    instrument_id: str | None = Field(default=None, description="None = all instruments")
    auto_deactivate_after_minutes: int | None = None
    exit_playbook_override: str | None = Field(default=None, description="override default playbook")


class ScopedKillSwitchState(BaseModel):
    """State of an active scoped kill switch."""

    scope: ScopedKillSwitchSpec
    is_active: bool
    activated_at: datetime
    activated_by: str
    reason: str
    auto_deactivate_at: datetime | None = None
    exit_progress: dict[str, str] = Field(default_factory=dict, description="step_id → status")


# ---------------------------------------------------------------------------
# Margin health time-series — unified across CeFi/DeFi/TradFi
# ---------------------------------------------------------------------------


class MarginHealthSnapshot(BaseModel):
    """Per-candle margin health snapshot. Written alongside PnL snapshots."""

    strategy_id: str
    timestamp: datetime
    venue: str
    venue_type: str = Field(description="cefi | defi | tradfi")
    position_type: str = Field(description="A_TOKEN | DEBT_TOKEN | PERPETUAL | SPOT | FUTURE | OPTION")
    health_factor: Decimal | None = Field(default=None, description="DeFi: Aave HF = collateral * liq_threshold / debt")
    ltv_ratio: Decimal | None = Field(default=None, description="debt / collateral")
    collateral_usd: Decimal = Decimal("0")
    debt_usd: Decimal = Decimal("0")
    margin_usage_pct: Decimal | None = Field(default=None, description="CeFi: used_margin / total_margin * 100")
    liquidation_price: Decimal | None = None
    distance_to_liquidation_pct: Decimal | None = Field(
        default=None, description="(current - liq_price) / current * 100"
    )
    client_id: str | None = None
    account_id: str | None = None


# ---------------------------------------------------------------------------
# Margin model registry (P2.1a — workspace audit 2026-05-01)
# ---------------------------------------------------------------------------


class MarginModel(StrEnum):
    """Canonical margin/liquidation model identifier per venue or protocol.

    The UTL ``margin_and_liquidation`` engine dispatches on this enum; UAC
    ``LiquidationParams`` table is keyed by this enum. Single SSOT for
    "what's the margin model for X?" queries across services.

    EXPOSURE_CAP is the soft analog used by sports/prediction venues — there's
    no hard liquidation, just position-size caps enforced by the bookmaker
    or the exchange contract.
    """

    AAVE_V3 = "AAVE_V3"
    COMPOUND_V3 = "COMPOUND_V3"
    MORPHO_BLUE = "MORPHO_BLUE"
    FLUID = "FLUID"
    EULER_V2 = "EULER_V2"
    RADIANT = "RADIANT"
    VENUS = "VENUS"
    BENQI = "BENQI"
    BINANCE_CROSS = "BINANCE_CROSS"
    BINANCE_ISOLATED = "BINANCE_ISOLATED"
    BYBIT = "BYBIT"
    OKX = "OKX"
    DYDX_V4 = "DYDX_V4"
    HYPERLIQUID = "HYPERLIQUID"
    FUTURES_SPAN = "FUTURES_SPAN"
    EXPOSURE_CAP = "EXPOSURE_CAP"


class LiquidationParams(BaseModel):
    """Per-margin-model threshold tuple — single SSOT for HF/LTV cutoffs.

    Reconciles the previously-conflicting Aave HF thresholds: risk-and-exposure
    (1.5/1.3/1.1), alerting (1.2), strategy (1.2 default). After P2.1 ships,
    every service consumes this table; no service inlines threshold numbers.

    Semantics:
    - ``health_factor_warning``: emit MarginEvent severity=warning at or below.
    - ``health_factor_critical``: emit severity=critical; strategy pauses.
    - ``health_factor_severe``: deleverage executor takes auto-action.
    - ``health_factor_liquidation``: protocol liquidation imminent (HF < 1.0
      typically).
    - ``ltv_max_borrow``: hard cap for new borrowing (consumed by pre-trade).
    - ``mmr_warning_pct`` / ``mmr_critical_pct``: CeFi margin-ratio analogs.
    """

    margin_model: MarginModel
    health_factor_warning: Decimal | None = None
    health_factor_critical: Decimal | None = None
    health_factor_severe: Decimal | None = None
    health_factor_liquidation: Decimal | None = None
    ltv_max_borrow: Decimal | None = None
    mmr_warning_pct: Decimal | None = Field(default=None, description="CeFi: margin_usage_pct above this -> warning")
    mmr_critical_pct: Decimal | None = Field(default=None, description="CeFi: margin_usage_pct above this -> critical")
    description: str = ""


LIQUIDATION_PARAMS_REGISTRY: dict[MarginModel, LiquidationParams] = {
    # ── DeFi: HF-based ──────────────────────────────────────────────────
    MarginModel.AAVE_V3: LiquidationParams(
        margin_model=MarginModel.AAVE_V3,
        health_factor_warning=Decimal("1.30"),
        health_factor_critical=Decimal("1.15"),
        health_factor_severe=Decimal("1.05"),
        health_factor_liquidation=Decimal("1.00"),
        ltv_max_borrow=Decimal("0.825"),
        description=(
            "Reconciled from prior 1.5/1.3/1.1 (risk) and 1.2 (alerting/strategy) — "
            "tighter warning at 1.30 catches drift earlier; severe at 1.05 gives "
            "the deleverage executor headroom before 1.00 liq trigger."
        ),
    ),
    MarginModel.COMPOUND_V3: LiquidationParams(
        margin_model=MarginModel.COMPOUND_V3,
        health_factor_warning=Decimal("1.30"),
        health_factor_critical=Decimal("1.15"),
        health_factor_severe=Decimal("1.05"),
        health_factor_liquidation=Decimal("1.00"),
        ltv_max_borrow=Decimal("0.85"),
        description="Mirrors Aave V3 thresholds; per-asset overrides via collateral factor.",
    ),
    MarginModel.MORPHO_BLUE: LiquidationParams(
        margin_model=MarginModel.MORPHO_BLUE,
        health_factor_warning=Decimal("1.30"),
        health_factor_critical=Decimal("1.15"),
        health_factor_severe=Decimal("1.05"),
        health_factor_liquidation=Decimal("1.00"),
        ltv_max_borrow=Decimal("0.86"),
        description="Per-market lltv set at deployment; defaults track Aave shape.",
    ),
    # Defi pipeline extension Phase 6.2 — additional lending protocols
    MarginModel.FLUID: LiquidationParams(
        margin_model=MarginModel.FLUID,
        health_factor_warning=Decimal("1.30"),
        health_factor_critical=Decimal("1.15"),
        health_factor_severe=Decimal("1.05"),
        health_factor_liquidation=Decimal("1.00"),
        ltv_max_borrow=Decimal("0.85"),
        description="Fluid (formerly Instadapp Lite); HF semantics mirror Aave.",
    ),
    MarginModel.EULER_V2: LiquidationParams(
        margin_model=MarginModel.EULER_V2,
        health_factor_warning=Decimal("1.30"),
        health_factor_critical=Decimal("1.15"),
        health_factor_severe=Decimal("1.05"),
        health_factor_liquidation=Decimal("1.00"),
        ltv_max_borrow=Decimal("0.83"),
        description="Euler V2 EVK vaults; per-vault LTV set at deployment, conservative default.",
    ),
    MarginModel.RADIANT: LiquidationParams(
        margin_model=MarginModel.RADIANT,
        health_factor_warning=Decimal("1.30"),
        health_factor_critical=Decimal("1.15"),
        health_factor_severe=Decimal("1.05"),
        health_factor_liquidation=Decimal("1.00"),
        ltv_max_borrow=Decimal("0.80"),
        description="Radiant Capital cross-chain lending; HF semantics mirror Aave V3.",
    ),
    MarginModel.VENUS: LiquidationParams(
        margin_model=MarginModel.VENUS,
        health_factor_warning=Decimal("1.30"),
        health_factor_critical=Decimal("1.15"),
        health_factor_severe=Decimal("1.05"),
        health_factor_liquidation=Decimal("1.00"),
        ltv_max_borrow=Decimal("0.80"),
        description="Venus Protocol (BSC); Compound-fork HF semantics.",
    ),
    MarginModel.BENQI: LiquidationParams(
        margin_model=MarginModel.BENQI,
        health_factor_warning=Decimal("1.30"),
        health_factor_critical=Decimal("1.15"),
        health_factor_severe=Decimal("1.05"),
        health_factor_liquidation=Decimal("1.00"),
        ltv_max_borrow=Decimal("0.80"),
        description="Benqi (Avalanche); Compound-fork HF semantics.",
    ),
    # ── CeFi: MMR-based ─────────────────────────────────────────────────
    MarginModel.BINANCE_CROSS: LiquidationParams(
        margin_model=MarginModel.BINANCE_CROSS,
        mmr_warning_pct=Decimal("70"),
        mmr_critical_pct=Decimal("85"),
        description="Cross margin: warn at 70% used, critical at 85%. Tier-aware MMR via cefi_margin_tiers.",
    ),
    MarginModel.BINANCE_ISOLATED: LiquidationParams(
        margin_model=MarginModel.BINANCE_ISOLATED,
        mmr_warning_pct=Decimal("70"),
        mmr_critical_pct=Decimal("85"),
        description="Isolated margin: per-position loss capped at posted margin.",
    ),
    MarginModel.BYBIT: LiquidationParams(
        margin_model=MarginModel.BYBIT,
        mmr_warning_pct=Decimal("70"),
        mmr_critical_pct=Decimal("85"),
        description="Bybit unified margin; tier-aware MMR via cefi_margin_tiers.",
    ),
    MarginModel.OKX: LiquidationParams(
        margin_model=MarginModel.OKX,
        mmr_warning_pct=Decimal("70"),
        mmr_critical_pct=Decimal("85"),
        description="OKX tiered margin; tier-aware MMR via cefi_margin_tiers.",
    ),
    MarginModel.DYDX_V4: LiquidationParams(
        margin_model=MarginModel.DYDX_V4,
        mmr_warning_pct=Decimal("70"),
        mmr_critical_pct=Decimal("85"),
        description="dYdX v4 perpetual margin; isolated by default.",
    ),
    MarginModel.HYPERLIQUID: LiquidationParams(
        margin_model=MarginModel.HYPERLIQUID,
        mmr_warning_pct=Decimal("70"),
        mmr_critical_pct=Decimal("85"),
        description="Hyperliquid cross margin with auto-deleverage on insolvency.",
    ),
    # ── TradFi: SPAN-based ──────────────────────────────────────────────
    MarginModel.FUTURES_SPAN: LiquidationParams(
        margin_model=MarginModel.FUTURES_SPAN,
        mmr_warning_pct=Decimal("75"),
        mmr_critical_pct=Decimal("90"),
        description="SPAN-style scenario margin; venue computes IM/MM via portfolio risk array.",
    ),
    # ── Sports / prediction: soft caps ──────────────────────────────────
    MarginModel.EXPOSURE_CAP: LiquidationParams(
        margin_model=MarginModel.EXPOSURE_CAP,
        description=(
            "No hard liquidation. Bookmaker / exchange contract enforces "
            "position-size caps; risk-service tracks exposure but no margin call."
        ),
    ),
}


def get_liquidation_params(margin_model: MarginModel) -> LiquidationParams:
    """Lookup helper. Always succeeds — every margin model has a row."""
    return LIQUIDATION_PARAMS_REGISTRY[margin_model]


class HealthFactor(BaseModel):
    """Standalone health-factor snapshot for a single account/protocol pair.

    Distinct from the ``health_factor: Decimal | None`` field on ``RiskMetrics``
    and ``MarginHealthSnapshot`` — this is a rich type that bundles the value
    with its computed status against the registered thresholds. Used as the
    return type from UTL's ``LiquidationMonitor.assess()``.
    """

    margin_model: MarginModel
    value: Decimal
    status: RiskStatus
    severity_breach: str = Field(
        default="none",
        description="none | warning | critical | severe | liquidation",
    )
    timestamp: datetime
    client_id: str | None = Field(default=None, json_schema_extra={"pii": True})
    account_id: str | None = None
    venue: str | None = None
    distance_to_warning_pct: Decimal | None = None
    distance_to_liquidation_pct: Decimal | None = None
