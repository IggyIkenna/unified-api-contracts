"""Performance tracking schemas for client reporting.

Covers equity curves, monthly returns, and aggregate performance statistics
used by client-reporting-api to serve TradeLink-quality dashboards.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, Field


class EquityCurvePoint(BaseModel, frozen=True):
    """Single point on an equity curve (hourly or daily granularity)."""

    timestamp: AwareDatetime = Field(description="UTC timestamp of this data point")
    equity_usd: Decimal = Field(description="Total equity in USD at this timestamp")
    hwm_usd: Decimal = Field(description="High-water mark in USD at this timestamp")
    drawdown_pct: Decimal = Field(
        default=Decimal("0"),
        description="Current drawdown from HWM as decimal (e.g. -0.05 = -5%)",
    )


class MonthlyReturn(BaseModel, frozen=True):
    """Monthly return record for a single calendar month."""

    year: int = Field(description="Calendar year (e.g. 2026)")
    month: int = Field(ge=1, le=12, description="Calendar month (1-12)")
    return_pct: Decimal = Field(description="Return for this month as decimal (e.g. 0.08 = 8%)")
    pnl_usd: Decimal = Field(description="Absolute P&L in USD for this month")
    opening_equity: Decimal = Field(description="Equity at start of month in USD")
    closing_equity: Decimal = Field(description="Equity at end of month in USD")


class PerformanceStats(BaseModel, frozen=True):
    """Aggregate performance statistics over a given period."""

    total_return_pct: Decimal = Field(description="Cumulative return as decimal")
    annualized_return_pct: Decimal = Field(description="Annualized return as decimal")
    sharpe_ratio: Decimal = Field(description="Sharpe ratio (risk-free rate = 0)")
    sortino_ratio: Decimal = Field(description="Sortino ratio (downside deviation)")
    max_drawdown_pct: Decimal = Field(description="Maximum drawdown as decimal (negative)")
    calmar_ratio: Decimal = Field(description="Annualized return / max drawdown")
    volatility_pct: Decimal = Field(description="Annualized volatility as decimal")
    win_rate: Decimal = Field(description="Fraction of winning days/trades")
    profit_factor: Decimal = Field(description="Gross profit / gross loss")
    avg_win_pct: Decimal = Field(description="Average winning day/trade return")
    avg_loss_pct: Decimal = Field(description="Average losing day/trade return")
    best_month_pct: Decimal = Field(description="Best single-month return")
    worst_month_pct: Decimal = Field(description="Worst single-month return")
    total_trades: int = Field(default=0, description="Total number of trades in period")
    winning_days: int = Field(default=0, description="Number of profitable days")
    losing_days: int = Field(default=0, description="Number of losing days")
    tracking_days: int = Field(default=0, description="Total days tracked")


class PerformanceSummary(BaseModel, frozen=True):
    """Complete performance summary for a client account.

    Combines equity curve, monthly returns, and aggregate stats
    into a single response payload for the performance dashboard.
    """

    client_id: str = Field(description="Client identifier (e.g. 'PR', 'ET')")
    client_name: str = Field(default="", description="Human-readable client name")
    venue: str = Field(default="", description="Primary venue (e.g. 'binance', 'okx')")
    currency: str = Field(default="USD", description="Account denomination currency")
    period_label: str = Field(default="all", description="Period filter applied (30d, 90d, 1y, all)")
    current_equity_usd: Decimal = Field(description="Current total equity in USD")
    current_hwm_usd: Decimal = Field(description="Current high-water mark in USD")
    equity_curve: list[EquityCurvePoint] = Field(
        default_factory=list,
        description="Time-series equity data points",
    )
    monthly_returns: list[MonthlyReturn] = Field(
        default_factory=list,
        description="Monthly return breakdown",
    )
    stats: PerformanceStats = Field(description="Aggregate performance statistics")
