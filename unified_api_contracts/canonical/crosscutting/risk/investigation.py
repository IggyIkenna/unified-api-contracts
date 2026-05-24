"""DrawdownInvestigationReport — 17-field report written when HUMAN_ESCALATION or higher
threshold breaches.

Codifies ``disaster_recovery.md`` §8.4. Stored at
``incidents/{YYYY-MM-DD}/{incident_key}/drawdown_investigation.json``.

Implementation plan: ``plans/active/drawdown_liquidation_policy_and_strategy_risk_config_2026_05_23.md``
Phase 3 P0.6.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DrawdownInvestigationReport(BaseModel):
    """17-field drawdown investigation report.

    Written by the agent whenever the strategy's drawdown_pct breaches the
    HUMAN_ESCALATION threshold (or higher). Stored to the audit GCS bucket so
    operators can review the full context before deciding on remediation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Identity
    strategy_id: str
    incident_key: str
    account_id: str | None = None
    venue: str | None = None

    # Drawdown financials
    drawdown_amount: Decimal
    """Absolute loss amount in USD (negative = loss)."""
    drawdown_pct: Decimal
    """Drawdown as a fraction of NAV (negative = loss, e.g. -0.03 = -3%)."""
    realised_pnl: Decimal
    unrealised_pnl: Decimal

    # Time window
    window_start: datetime
    window_end: datetime

    # Market context
    market_move_context: str
    """Free-text summary of concurrent market moves (e.g. 'BTC -8% in 2h')."""

    # Exposure snapshot
    exposure_before: Decimal
    """Gross notional exposure at window_start (USD)."""
    exposure_after: Decimal
    """Gross notional exposure at window_end (USD)."""

    # Order + position state
    open_orders_summary: str
    """JSON-serialised snapshot of open orders at window_end, or 'none'."""
    position_concentration_summary: str
    """Top-3 position concentration as percentage of NAV, serialised."""

    # Issue categories
    venue_specific_issues: list[str]
    """Closed-set identifiers for venue-level anomalies observed."""
    data_quality_issues: list[str]
    """Closed-set identifiers for data quality anomalies (e.g. stale prices)."""

    # Distribution checks
    expected_distribution_check: str
    """'in_distribution' | 'out_of_distribution' | 'insufficient_data'."""
    signal_sanity: str
    """'sane' | 'degraded' | 'conflicting' | 'stale'."""

    # Cost attribution
    slippage_contribution: Decimal
    """Estimated slippage loss in USD over time_window."""
    fees_funding_borrow_contribution: Decimal
    """Fees + funding + borrow costs in USD over time_window."""

    # Risk gate state
    risk_limit_breaches: list[str]
    """RiskRuleId values of any rules that fired during time_window."""

    # Recommended action
    recommended_action: str
    """Human-readable recommended action string (e.g. 'REDUCE_POSITION_50PCT')."""
