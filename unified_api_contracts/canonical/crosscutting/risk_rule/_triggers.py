"""Risk-rule trigger conditions — typed closed-union for rule evaluation.

All trigger condition classes that rules can use to evaluate against
runtime context.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class _TriggerBase(BaseModel):
    """Shared trigger-condition base.

    § 7 SSOT reconciliation
    -----------------------

    Trigger conditions are evaluated by ``risk/rule_evaluator.py`` (UTL Phase
    3.A) against a runtime ``context`` containing the proposed instruction +
    current position-balance state. The closed-union discriminator
    ``trigger_type`` makes Pydantic + basedpyright route to the correct
    sub-model. Adding a new trigger type means appending to this union AND
    teaching the evaluator. No string-typed runtime branching.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


class MaxPositionSizeTrigger(_TriggerBase):
    """Position-size cap. Units: USD-notional."""

    trigger_type: Literal["max_position_size"] = "max_position_size"
    cap_usd: Decimal


class MaxDrawdownTrigger(_TriggerBase):
    """Drawdown cap. Units: bps from peak NAV."""

    trigger_type: Literal["max_drawdown"] = "max_drawdown"
    cap_bps: int


class MaxLeverageTrigger(_TriggerBase):
    """Leverage cap. Units: dimensionless (gross-notional / equity)."""

    trigger_type: Literal["max_leverage"] = "max_leverage"
    cap_ratio: Decimal


class MaxConcentrationTrigger(_TriggerBase):
    """Concentration cap. Units: % of total portfolio NAV."""

    trigger_type: Literal["max_concentration"] = "max_concentration"
    cap_pct: Decimal


class MaxCorrelationTrigger(_TriggerBase):
    """Cross-position correlation cap. Units: Pearson rho on rolling returns."""

    trigger_type: Literal["max_correlation"] = "max_correlation"
    cap_rho: Decimal
    window_days: int


class SlippageBudgetTrigger(_TriggerBase):
    """Slippage budget. Units: bps over benchmark-arrival mid."""

    trigger_type: Literal["slippage_budget_exceeded"] = "slippage_budget_exceeded"
    budget_bps: int


class FundingCostCeilingTrigger(_TriggerBase):
    """Funding-cost annualised ceiling. Units: bps APR."""

    trigger_type: Literal["funding_cost_ceiling"] = "funding_cost_ceiling"
    ceiling_bps_apr: int


class GasBudgetTrigger(_TriggerBase):
    """Per-instruction gas budget. Units: USD-equivalent at current ETH/SOL price."""

    trigger_type: Literal["gas_budget_exceeded"] = "gas_budget_exceeded"
    budget_usd: Decimal


class CapitalAtRiskCeilingTrigger(_TriggerBase):
    """Capital-at-risk ceiling. Units: USD-notional at 95% VaR / equivalent."""

    trigger_type: Literal["capital_at_risk_ceiling"] = "capital_at_risk_ceiling"
    ceiling_usd: Decimal


class MaxOITrigger(_TriggerBase):
    """Per-venue per-instrument open-interest cap. Units: USD-notional."""

    trigger_type: Literal["max_oi"] = "max_oi"
    cap_usd: Decimal


class MaxGrossExposureTrigger(_TriggerBase):
    """Account-level gross exposure cap. Units: USD-notional."""

    trigger_type: Literal["max_gross_exposure"] = "max_gross_exposure"
    cap_usd: Decimal


class MaxNetExposureTrigger(_TriggerBase):
    """Account-level net exposure cap. Units: USD-notional."""

    trigger_type: Literal["max_net_exposure"] = "max_net_exposure"
    cap_usd: Decimal


class MaxDailyLossTrigger(_TriggerBase):
    """Per-account daily loss cap. Units: USD."""

    trigger_type: Literal["max_daily_loss"] = "max_daily_loss"
    cap_usd: Decimal


class CounterpartyRatioCapTrigger(_TriggerBase):
    """Cross-venue counterparty ratio cap.

    Caps notional on ``secondary_venue`` as a fraction of the live notional on
    ``reference_venue``. Evaluated at Layer 2 against runtime position-balance
    state. Designed for the Bybit-vs-Hyperliquid 30-day post-cutover
    constraint in ``CARRY_BASIS_PERP_INV``:

    ``bybit_notional <= cap_ratio_of_reference * hyperliquid_notional``

    Consequence must be ``BLOCK`` (not ``SCALE_DOWN``) — the ratio is a hard
    counterparty credit-risk constraint, not a sizing preference.

    Attributes:
        reference_venue: The reference-leg venue whose live notional sets the
            denominator (e.g. ``"HYPERLIQUID"``).
        cap_ratio_of_reference: Maximum permitted fraction of reference-venue
            notional (e.g. ``0.50`` = 50%).  Range ``(0, 1.0]``.
        secondary_venue: The venue whose proposed notional is checked against
            the cap (e.g. ``"BYBIT"``).
    """

    trigger_type: Literal["counterparty_ratio_cap"] = "counterparty_ratio_cap"
    reference_venue: str
    cap_ratio_of_reference: Decimal
    secondary_venue: str


class BinaryEventTrigger(_TriggerBase):
    """Binary event-driven halt trigger.

    Fires when the named infrastructure event is detected. Unlike metric
    triggers, there is no numeric threshold — the condition is boolean:
    the event is either present or absent. The evaluator in UTL
    ``risk/rule_evaluator.py`` checks ``event_source`` via the registered
    health-probe table on every order.

    Used for oracle-outage, cross-cloud-egress, and custody-endpoint-halt
    rules (``ORACLE_OUTAGE_HALT``, ``CROSS_CLOUD_EGRESS_HALT``,
    ``CUSTODY_ENDPOINT_HALT``) where the trigger is an infrastructure
    health boolean, not a rolling metric.

    Attributes:
        event_source: Probe key identifying the infrastructure health signal
            (e.g. ``"chainlink_oracle"``, ``"cross_cloud_egress"``,
            ``"copper_custody_endpoint"``).
    """

    trigger_type: Literal["binary_event"] = "binary_event"
    event_source: str


RiskRuleTrigger = Annotated[
    (
        MaxPositionSizeTrigger
        | MaxDrawdownTrigger
        | MaxLeverageTrigger
        | MaxConcentrationTrigger
        | MaxCorrelationTrigger
        | SlippageBudgetTrigger
        | FundingCostCeilingTrigger
        | GasBudgetTrigger
        | CapitalAtRiskCeilingTrigger
        | MaxOITrigger
        | MaxGrossExposureTrigger
        | MaxNetExposureTrigger
        | MaxDailyLossTrigger
        | CounterpartyRatioCapTrigger
        | BinaryEventTrigger
    ),
    Field(discriminator="trigger_type"),
]
"""Discriminated union of typed trigger conditions.

§ 7 SSOT reconciliation
-----------------------

Closed union — every condition the pre-flight rule engine can evaluate is
listed here. The evaluator in UTL ``risk/rule_evaluator.py`` (Phase 3.A)
dispatches on ``trigger.trigger_type``. Adding new trigger types means
appending to this union + teaching the evaluator. Composes with Phase 2's
per-axis registry — each registry entry sets ``trigger=<concrete subclass>``
with axis-appropriate fields.

Closed for now; archetype-specific extensions (e.g. ``StakingDepegTrigger``
for ``carry_staked_basis``) land in the closed-enum extension table of
this module as Phase 2 ships, NOT in a wildcard ``Any`` field.
"""


__all__ = [
    "BinaryEventTrigger",
    "CapitalAtRiskCeilingTrigger",
    "CounterpartyRatioCapTrigger",
    "FundingCostCeilingTrigger",
    "GasBudgetTrigger",
    "MaxConcentrationTrigger",
    "MaxCorrelationTrigger",
    "MaxDailyLossTrigger",
    "MaxDrawdownTrigger",
    "MaxGrossExposureTrigger",
    "MaxLeverageTrigger",
    "MaxNetExposureTrigger",
    "MaxOITrigger",
    "MaxPositionSizeTrigger",
    "RiskRuleTrigger",
    "SlippageBudgetTrigger",
]
