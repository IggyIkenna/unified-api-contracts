"""LiquidationInvestigationReport — 16-field liquidation investigation schema.

Codifies ``disaster_recovery.md`` §9.4. Written when ``LIQUIDATION_EVENT_DETECTED``
fires and any of the 7 closed-set SEV0 escalation predicates are true.

Implementation plan:
``plans/active/drawdown_liquidation_policy_and_strategy_risk_config_2026_05_23.md``
Phase 4 P0.11.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class LiquidationInvestigationReport(BaseModel):
    """16-field liquidation investigation report (§9.4 of target model).

    Written by the LiquidationEventDetector when an actual liquidation is
    confirmed. Linked to the parent incident via ``incident_key``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Identity
    venue: str
    account_id: str
    strategy_id: str
    incident_key: str
    instrument_id: str | None = None

    # Liquidation event details
    liquidated_quantity: Decimal
    """Quantity of the instrument that was liquidated (positive = absolute)."""
    liquidation_price: Decimal
    """Price at which the position was liquidated."""
    mark_index_price_path: list[Decimal]
    """Time-ordered list of mark/index prices leading up to liquidation."""

    # Margin state
    margin_mode: str
    """'cross' | 'isolated' | 'portfolio' — per venue nomenclature."""
    collateral_balances_before: dict[str, Decimal]
    """Asset → balance mapping immediately before the liquidation event."""
    collateral_balances_after: dict[str, Decimal]
    """Asset → balance mapping immediately after the liquidation event."""

    # Orders and risk
    open_orders_before_liquidation: list[str]
    """Order-IDs (or order-JSON strings) of open orders before liquidation."""
    risk_limits_in_force: list[str]
    """RiskRuleId values that were active at liquidation time."""
    alerts_fired_before_liquidation: list[str]
    """AlertCode values that fired in the hour before liquidation."""

    # Strategy state
    strategy_expected_risk: str
    """Free-form: was this within the strategy's expected risk envelope? ('yes'|'no'|'unknown')"""
    close_reduce_logic_failed: bool
    """True if close/reduce logic ran but failed to prevent liquidation."""
    venue_api_data_stale: bool
    """True if venue API data was stale when the liquidation happened."""

    # Escalation
    human_escalation_triggered: bool
    detected_at: datetime

    # Remediation
    remediation_recommendations: list[str]
    """Closed-set action identifiers the agent recommends (e.g. 'REVIEW_CLOSE_ALL_LOGIC')."""
