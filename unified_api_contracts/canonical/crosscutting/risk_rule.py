"""Risk-rule taxonomy SSOT — closed-set rule-id, scope, consequence, trigger conditions.

This module is the workspace SSOT for **pre-flight risk-rule decisions** evaluated
at Layer 2 of the 4-layer risk-gates model (see
``codex/09-strategy/architecture-v2/cross-cutting/risk-gates.md``). It introduces
``RiskRuleConsequence`` as a NEW pre-flight rule-decision abstraction — distinct
from + composing with the 5 canonical workspace risk SSOTs (risk-gates layers,
8-event lifecycle, kill-switch trigger set, circuit-breaker action set, strategy
kill-switch behaviour set).

§ 7 SSOT reconciliation
=======================

Per ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` § "§ 7 SSOT
reconciliation seam (Framing 1)" — picked by operator 2026-05-10. The seam
diagram + cross-product table in that plan body is the canonical reconciliation
between ``RiskRuleConsequence`` and the 5 canonical SSOTs:

* **Risk-gates 4 layers** — ``codex/09-strategy/architecture-v2/cross-cutting/risk-gates.md``.
  ``RiskRuleConsequence`` evaluates at Layer 2 (strategy-service/risk pre-flight);
  ``ErrorAction`` taxonomy classifies Layer 4 (venue-side) errors.
  They don't overlap.
* **8-event lifecycle SSOT** — every fire emits ``RiskRuleFiredEvent`` plus
  the corresponding instruction-lifecycle event (BLOCK → ``INSTRUCTION_REJECTED_RISK``;
  others → ``INSTRUCTION_ACCEPTED_PREFLIGHT`` with annotations).
* **Kill-switch trigger set** — ``codex/04-architecture/kill-switch-circuit-breaker.md``.
  ``RiskRule.kill_switch_scope()`` maps ``RiskRuleScope`` →
  ``KillSwitchScope`` for the orthogonal axis (rule applicability vs kill-switch
  blast radius).
* **Circuit-breaker action set** — ``plans/active/alerting_service_live_rules_2026_05_07.md``.
  Aggregated BLOCK rate ≥ threshold triggers circuit-breaker state transitions
  (CLOSED → DEGRADED → OPEN); SCALE_DOWN / MONITOR / TEST_ONLY do not.
* **Strategy kill-switch behaviour 4-set** — ``STOP_NEW_ONLY`` / ``FAST_UNWIND``
  / ``SLOW_UNWIND`` / ``DELTA_HEDGE`` — engaged downstream when a BLOCK rule's
  ``triggers_kill_switch`` evaluates true.

Reviewers reject Phase 1+ contributors that bypass this seam (e.g. inlining
risk-rule logic in execution-service instead of routing through Layer 2).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from .alerting import AlertSeverity
from .alerting.codes import AlertCode, KillSwitchScope


class RiskRuleId(StrEnum):
    """Closed-set rule identifiers for the per-axis risk-rule registry.

    § 7 SSOT reconciliation
    -----------------------

    Each rule-id maps 1:1 to a ``RiskRule`` instance in the per-axis registry
    (``registry/risk_rules/{archetype,venue,account,client,asset_group,global}.py``
    seeded in Phase 2 of ``risk_simulations_limits_alerting_2026_05_10``). The
    closed-set discipline mirrors ``AlertCode`` /
    ``EmptyConfirmedReason`` / ``LifecycleEventType`` — emitting a rule-id
    outside the enum is a programming error caught at type-check time.

    Composes with the 5 canonical SSOTs per the seam diagram in
    ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` § "§ 7
    SSOT reconciliation seam (Framing 1)":

    * ``codex/09-strategy/architecture-v2/cross-cutting/risk-gates.md`` — Layer
      2 evaluation point.
    * 8-event lifecycle SSOT — fire emits ``RiskRuleFiredEvent``.
    * ``codex/04-architecture/kill-switch-circuit-breaker.md`` — kill-switch
      scope mapping via ``RiskRule.kill_switch_scope()``.
    * ``plans/active/alerting_service_live_rules_2026_05_07.md`` — alerting
      routing via ``RiskRule.alerting_severity`` + AlertCodes
      ``RISK_RULE_BLOCKED`` / ``RISK_RULE_SCALED_DOWN`` /
      ``RISK_RULE_MONITOR_FIRED`` / ``RISK_RULE_TEST_ONLY_ROUTED``.
    * Strategy kill-switch behaviour 4-set — engaged when BLOCK rule's
      ``triggers_kill_switch`` is true.

    Closed members below seed the Phase 2 registry. Phase 2.A-F sub-agents
    extend this enum with additional archetype-specific / venue-specific
    rule-ids — every new member MUST also seed a ``RiskRule`` in the
    appropriate per-axis registry.
    """

    # ── Position-sizing axis (per-archetype + per-venue) ────────────────────
    MAX_POSITION_SIZE_PER_ARCHETYPE = "MAX_POSITION_SIZE_PER_ARCHETYPE"
    MAX_POSITION_SIZE_PER_VENUE = "MAX_POSITION_SIZE_PER_VENUE"
    MAX_POSITION_SIZE_PER_INSTRUMENT = "MAX_POSITION_SIZE_PER_INSTRUMENT"
    MAX_OI_PER_VENUE = "MAX_OI_PER_VENUE"

    # ── Drawdown axis (per-archetype + per-account + per-client) ────────────
    MAX_DRAWDOWN_PER_ARCHETYPE = "MAX_DRAWDOWN_PER_ARCHETYPE"
    MAX_DRAWDOWN_PER_ACCOUNT = "MAX_DRAWDOWN_PER_ACCOUNT"
    MAX_DRAWDOWN_PER_CLIENT = "MAX_DRAWDOWN_PER_CLIENT"
    MAX_DAILY_LOSS_PER_ACCOUNT = "MAX_DAILY_LOSS_PER_ACCOUNT"

    # ── Leverage + concentration axis ───────────────────────────────────────
    MAX_LEVERAGE_PER_ARCHETYPE = "MAX_LEVERAGE_PER_ARCHETYPE"
    MAX_LEVERAGE_PER_ACCOUNT = "MAX_LEVERAGE_PER_ACCOUNT"
    MAX_CONCENTRATION_PER_INSTRUMENT = "MAX_CONCENTRATION_PER_INSTRUMENT"
    MAX_CONCENTRATION_PER_ASSET_GROUP = "MAX_CONCENTRATION_PER_ASSET_GROUP"

    # ── Cost-budget axis ────────────────────────────────────────────────────
    SLIPPAGE_BUDGET_PER_ARCHETYPE = "SLIPPAGE_BUDGET_PER_ARCHETYPE"
    FUNDING_COST_CEILING_PER_ARCHETYPE = "FUNDING_COST_CEILING_PER_ARCHETYPE"
    GAS_BUDGET_PER_ARCHETYPE = "GAS_BUDGET_PER_ARCHETYPE"

    # ── Cross-instrument / cross-venue axis ─────────────────────────────────
    MAX_CORRELATION_PER_ARCHETYPE = "MAX_CORRELATION_PER_ARCHETYPE"
    MAX_GROSS_EXPOSURE_PER_ACCOUNT = "MAX_GROSS_EXPOSURE_PER_ACCOUNT"
    MAX_NET_EXPOSURE_PER_ACCOUNT = "MAX_NET_EXPOSURE_PER_ACCOUNT"
    CAPITAL_AT_RISK_CEILING_PER_ARCHETYPE = "CAPITAL_AT_RISK_CEILING_PER_ARCHETYPE"

    # ── Global kill-conditions axis ─────────────────────────────────────────
    GLOBAL_PORTFOLIO_DRAWDOWN_HALT = "GLOBAL_PORTFOLIO_DRAWDOWN_HALT"
    GLOBAL_DATA_STALENESS_HALT = "GLOBAL_DATA_STALENESS_HALT"

    # ── Strategy-family aggregate axis (Phase 2.H) ──────────────────────────
    # § 7 SSOT reconciliation — strategy-family rules aggregate per-archetype
    # state into per-family caps. See
    # ``registry/risk_rules/strategy_family.py`` for the seed registry.
    FAMILY_GROSS_EXPOSURE_CAP = "FAMILY_GROSS_EXPOSURE_CAP"
    FAMILY_NET_EXPOSURE_CAP = "FAMILY_NET_EXPOSURE_CAP"
    FAMILY_DRAWDOWN_CAP = "FAMILY_DRAWDOWN_CAP"
    FAMILY_CAPITAL_AT_RISK_CEILING = "FAMILY_CAPITAL_AT_RISK_CEILING"
    FAMILY_CONCENTRATION_PER_VENUE = "FAMILY_CONCENTRATION_PER_VENUE"
    FAMILY_CORRELATION_WITH_OTHER_FAMILY = "FAMILY_CORRELATION_WITH_OTHER_FAMILY"

    # ── Counterparty ratio axis (cross-venue safety constraint) ─────────────
    # § 7 SSOT reconciliation — Bybit notional must not exceed a fraction of
    # the Hyperliquid leg for the first 30 days post-cutover, per
    # ``plans/active/defi_recursive_borrow_archetypes_2026_05_10.md``
    # "Bybit counterparty cap policy". Evaluated at Layer 2 against the live
    # HL notional read from position-balance state.
    COUNTERPARTY_RATIO_CAP = "COUNTERPARTY_RATIO_CAP"


RISK_RULE_IDS: Final[frozenset[str]] = frozenset(m.value for m in RiskRuleId)
"""String-membership view of :class:`RiskRuleId` for fast O(1) validation.

Mirrors ``ALERT_CODES``. Use enum members in new code; this set is for the
validation hot path only.
"""


class RiskRuleScope(StrEnum):
    """Scope axis — which dimension the rule applies along.

    § 7 SSOT reconciliation
    -----------------------

    ``RiskRuleScope`` is **orthogonal to ``KillSwitchScope``** per the seam
    diagram cross-product table in
    ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` § "§ 7 SSOT
    reconciliation seam":

    * ``RiskRuleScope`` = the rule-applicability axis (which entities the rule
      should evaluate against).
    * ``KillSwitchScope`` (per
      ``codex/04-architecture/kill-switch-circuit-breaker.md``) = the
      kill-switch-blast-radius axis (when armed, what gets halted).

    ``RiskRule.kill_switch_scope()`` (Phase 1.C) maps Scope → KillSwitchScope
    when the rule's BLOCK consequence is paired with
    ``triggers_kill_switch=True``:

    * ``PER_VENUE`` → ``KillSwitchScope.VENUE``
    * ``PER_ARCHETYPE`` → ``KillSwitchScope.ARCHETYPE``
    * ``PER_CLIENT`` → ``KillSwitchScope.CLIENT``
    * ``GLOBAL`` → ``KillSwitchScope.GLOBAL``
    * ``PER_ACCOUNT`` / ``PER_ASSET_GROUP`` / ``PER_STRATEGY_FAMILY`` →
      ``None`` (not directly kill-switch-applicable; affect portfolio
      aggregates instead — family-aggregate caps escalate via the
      circuit-breaker BLOCK-rate path, not the kill-switch).
    """

    PER_ARCHETYPE = "PER_ARCHETYPE"
    PER_VENUE = "PER_VENUE"
    PER_ACCOUNT = "PER_ACCOUNT"
    PER_ASSET_GROUP = "PER_ASSET_GROUP"
    PER_CLIENT = "PER_CLIENT"
    PER_STRATEGY_FAMILY = "PER_STRATEGY_FAMILY"
    GLOBAL = "GLOBAL"


class RiskRuleConsequence(StrEnum):
    """Pre-flight rule decision — closed set of 4 actions a fired rule can take.

    § 7 SSOT reconciliation
    -----------------------

    ``RiskRuleConsequence`` is a NEW abstraction at a NEW layer — **per-rule
    per-instruction pre-flight decision** evaluated at Layer 2 of the 4-layer
    risk-gates model
    (``codex/09-strategy/architecture-v2/cross-cutting/risk-gates.md``). It
    does NOT replace any existing canonical SSOT; it COMPOSES with all 5 per
    the cross-product table in
    ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` § "§ 7 SSOT
    reconciliation seam":

    * **BLOCK**: emits ``INSTRUCTION_REJECTED_RISK`` + ``RiskRuleFiredEvent``
      (HIGH/CRITICAL) + AlertCode ``RISK_RULE_BLOCKED``. May trigger
      kill-switch when paired with ``triggers_kill_switch=True``. Aggregated
      BLOCK rate ≥ threshold may transition the venue circuit-breaker per
      ``alerting_service_live_rules`` cascade.
    * **SCALE_DOWN**: emits ``INSTRUCTION_ACCEPTED_PREFLIGHT`` (size_adjusted)
      + ``RESIZED_EXECUTION`` at Layer 3 + ``RiskRuleFiredEvent`` (WARN) +
      AlertCode ``RISK_RULE_SCALED_DOWN``. Does NOT trigger kill-switch or
      breaker.
    * **MONITOR**: emits ``INSTRUCTION_ACCEPTED_PREFLIGHT`` + advisory
      ``RiskRuleFiredEvent`` (INFO/WARN) + AlertCode
      ``RISK_RULE_MONITOR_FIRED``. Passthrough; no instruction modification.
    * **TEST_ONLY**: tags instruction ``mode=TEST`` → Layer 3 routes to the
      matching engine instead of live venue. Emits
      ``INSTRUCTION_ACCEPTED_PREFLIGHT`` (mode=TEST) +
      ``RiskRuleFiredEvent`` (INFO) + AlertCode
      ``RISK_RULE_TEST_ONLY_ROUTED``.

    Orthogonal to ``ErrorAction`` (RETRY / RECONNECT / SKIP / FAIL per
    ``codex/04-architecture/autonomous-recovery-matrix.md``) — that's the
    Layer 4 post-venue-error classification. Layer 2 may BLOCK (instruction
    never reaches venue → no ErrorAction); Layer 2 may approve (any
    non-BLOCK) → Layer 4 may then classify a venue rejection.
    """

    BLOCK = "BLOCK"
    SCALE_DOWN = "SCALE_DOWN"
    MONITOR = "MONITOR"
    TEST_ONLY = "TEST_ONLY"


# ---------------------------------------------------------------------------
# Trigger conditions — typed closed-union (discriminated by ``trigger_type``).
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# RiskRule — the per-rule contract.
# ---------------------------------------------------------------------------


class RiskRule(BaseModel):
    """Single risk-rule contract — one row in the per-axis registry.

    § 7 SSOT reconciliation
    -----------------------

    ``RiskRule`` is the fundamental contract every per-axis registry entry
    instantiates. Composes with all 5 canonical SSOTs per the seam diagram in
    ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` § "§ 7
    SSOT reconciliation seam (Framing 1)":

    * **Risk-gates Layer 2** — evaluated by
      ``risk/rule_evaluator.py`` (UTL Phase 3.A) against runtime context.
    * **8-event lifecycle SSOT** — every fire emits ``RiskRuleFiredEvent``
      with this rule's ``rule_id`` + ``alerting_severity``.
    * **Kill-switch trigger set** — ``kill_switch_scope()`` maps ``scope`` →
      ``KillSwitchScope``; downstream kill-switch fires when consequence is
      ``BLOCK`` + caller declares ``triggers_kill_switch=True``.
    * **Circuit-breaker action set** — aggregated BLOCK rate ≥ threshold may
      transition the breaker per
      ``RISK_TO_BREAKER_ESCALATION_MAP`` (declared separately in
      ``circuit_breaker.py`` by Sub-C; see plan body
      ``risk_simulations_limits_alerting`` Phase 7.E).
    * **Strategy kill-switch behaviour 4-set** — Layer 3 strategy engine
      consumes the BLOCK + kill-switch-engaged combination + dispatches
      ``STOP_NEW_ONLY`` / ``FAST_UNWIND`` / ``SLOW_UNWIND`` / ``DELTA_HEDGE``
      per per-archetype config.

    The ``applies_to`` field is a free-form string keyed by ``scope``:

    * ``PER_ARCHETYPE`` → ``StrategyArchetype.value`` (e.g.
      ``"CARRY_STAKED_BASIS"``).
    * ``PER_VENUE`` → venue short-name (e.g. ``"bybit"`` / ``"deribit"``).
    * ``PER_ACCOUNT`` → account-id string (e.g. ``"paper-1"`` / ``"live-1"``).
    * ``PER_ASSET_GROUP`` → ``"cefi"`` / ``"defi"`` / ``"tradfi"`` /
      ``"sports"`` / ``"prediction"``.
    * ``PER_CLIENT`` → client-id string.
    * ``PER_STRATEGY_FAMILY`` → ``StrategyFamilyId.value`` (e.g.
      ``"LST_LEVERAGE_FAMILY"`` / ``"FUNDING_ARB_FAMILY"``) per
      ``canonical/crosscutting/strategy_family.py``.
    * ``GLOBAL`` → ``"*"`` (sentinel).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: RiskRuleId
    """Closed-set rule identifier — keys the per-axis registry."""

    scope: RiskRuleScope
    """Applicability axis — drives ``kill_switch_scope()`` mapping."""

    applies_to: str
    """Free-form string keyed by ``scope`` — see class docstring for the
    per-scope key shape. Empty string is rejected by Pydantic."""

    trigger: RiskRuleTrigger
    """Typed trigger condition — closed-union discriminated by
    ``trigger_type``. Evaluator dispatches on this field."""

    consequence: RiskRuleConsequence
    """Pre-flight rule decision — closed set of 4 actions
    (BLOCK / SCALE_DOWN / MONITOR / TEST_ONLY)."""

    alerting_severity: AlertSeverity
    """Severity to stamp on the emitted ``RiskRuleFiredEvent`` — drives
    paging behaviour per ``alerting_service_live_rules``. CRITICAL +
    HIGH typically pair with BLOCK; WARN with SCALE_DOWN; INFO with
    MONITOR + TEST_ONLY."""

    description: str
    """Operator-facing rule description. Rendered in the deployment-UI Risk
    tab (Phase 6 of risk plan)."""

    triggers_kill_switch: bool = False
    """Whether a BLOCK consequence engages the kill-switch via
    ``kill_switch_scope()``. Only meaningful when ``consequence == BLOCK``.
    SCALE_DOWN / MONITOR / TEST_ONLY ignore this field per the seam diagram
    orthogonality declarations."""

    def kill_switch_scope(self) -> KillSwitchScope | None:
        """Map ``self.scope`` → ``KillSwitchScope`` per the seam diagram.

        § 7 SSOT reconciliation
        -----------------------

        Composes with the kill-switch SSOT
        (``codex/04-architecture/kill-switch-circuit-breaker.md``). Returns
        ``None`` for scopes that aren't directly kill-switch-applicable
        (``PER_ACCOUNT`` + ``PER_ASSET_GROUP`` affect portfolio aggregates,
        not blast-radius halts). Callers MUST only use the return value when
        ``self.consequence == RiskRuleConsequence.BLOCK`` AND
        ``self.triggers_kill_switch`` is True — otherwise the orthogonality
        declaration says the kill-switch does not fire even when scope is
        mappable.
        """
        if self.scope is RiskRuleScope.PER_VENUE:
            return KillSwitchScope.VENUE
        if self.scope is RiskRuleScope.PER_ARCHETYPE:
            return KillSwitchScope.ARCHETYPE
        if self.scope is RiskRuleScope.PER_CLIENT:
            return KillSwitchScope.CLIENT
        if self.scope is RiskRuleScope.GLOBAL:
            return KillSwitchScope.GLOBAL
        # PER_ACCOUNT + PER_ASSET_GROUP + PER_STRATEGY_FAMILY — not directly
        # kill-switch-applicable per the seam diagram cross-product table.
        # Family-aggregate rules escalate via the circuit-breaker BLOCK-rate
        # path (aggregate BLOCK rate ≥ threshold → breaker transition) rather
        # than the kill-switch's per-blast-radius halt mechanism.
        return None


class RiskRuleFiredEvent(BaseModel):
    """Emitted every time a ``RiskRule`` fires during pre-flight evaluation.

    The 8-event-lifecycle SSOT entry for the risk-rule layer: a single
    ``RiskRuleFiredEvent`` accompanies every consequence (BLOCK / SCALE_DOWN /
    MONITOR / TEST_ONLY) plus the corresponding instruction-lifecycle event
    (see ``CONSEQUENCE_EVENTS_EMITTED``). The alerting-service consumes this
    event + routes by ``alert_code`` and ``alerting_severity`` per
    ``LIVE_ALERT_RULES``.

    § 7 SSOT reconciliation
    -----------------------

    Composes with the 5 canonical SSOTs per
    ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` § "§ 7 SSOT
    reconciliation seam (Framing 1)":

    * **8-event lifecycle SSOT** — this IS the risk-layer lifecycle event;
      ``CONSEQUENCE_EVENTS_EMITTED`` declares which instruction-lifecycle
      events fire alongside it per ``consequence``.
    * **AlertCode + AlertSeverity + AlertChannel SSOT** — ``alert_code`` is a
      member of the closed ``AlertCode`` set (one of the four
      ``RISK_RULE_*`` codes added in risk plan Phase 1.E); ``alerting_severity``
      is the rule's declared ``AlertSeverity``; ``AlertChannel`` routing is
      resolved downstream by the matching ``LIVE_ALERT_RULES`` entry.
    * **Kill-switch trigger set** — ``triggers_kill_switch`` + ``kill_switch_scope``
      carry forward the rule's ``kill_switch_scope()`` mapping so the alerting /
      kill-switch consumer can arm a switch without re-looking-up the rule. Only
      meaningful when ``consequence == BLOCK`` AND ``triggers_kill_switch`` per
      the seam-diagram orthogonality declarations.

    Producers: ``risk/preflight.py`` (UTL Phase 3.B) builds one per fired rule
    from ``risk_preflight()``; strategy-service/risk / execution-service /
    strategy-service emit them on their pre-flight call sites (risk plan Phase
    4). Use :func:`risk_rule_fired_event` to construct one from a ``RiskRule``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: RiskRuleId
    """The fired rule's closed-set identifier."""

    scope: RiskRuleScope
    """The fired rule's applicability axis (mirrors ``RiskRule.scope``)."""

    applies_to: str
    """The fired rule's ``applies_to`` key — per-scope shape per
    ``RiskRule`` docstring. Empty string rejected by Pydantic."""

    consequence: RiskRuleConsequence
    """The decision the fired rule took — BLOCK / SCALE_DOWN / MONITOR /
    TEST_ONLY."""

    alerting_severity: AlertSeverity
    """Severity to route the alert at — copied from ``RiskRule.alerting_severity``."""

    alert_code: AlertCode
    """Closed-set alert code — one of ``RISK_RULE_BLOCKED`` /
    ``RISK_RULE_SCALED_DOWN`` / ``RISK_RULE_MONITOR_FIRED`` /
    ``RISK_RULE_TEST_ONLY_ROUTED`` per ``CONSEQUENCE_ALERT_CODES``."""

    fired_at: datetime
    """UTC instant the rule fired (pre-flight evaluation time)."""

    instruction_id: str = ""
    """Order / instruction id the pre-flight ran for; empty for portfolio-level
    monitor fires that aren't tied to a single instruction."""

    triggers_kill_switch: bool = False
    """Whether a kill-switch should be armed — only true for BLOCK rules with
    ``RiskRule.triggers_kill_switch`` set."""

    kill_switch_scope: KillSwitchScope | None = None
    """``RiskRule.kill_switch_scope()`` carried forward — the blast radius of
    the kill-switch to arm when ``triggers_kill_switch`` is true; ``None`` for
    scopes that don't map (PER_ACCOUNT / PER_ASSET_GROUP / PER_STRATEGY_FAMILY)
    or when no kill-switch fires."""

    trigger_detail: dict[str, str] = Field(default_factory=dict)
    """Stringified observed-vs-threshold values for the alert body (e.g.
    ``{"observed": "1100", "threshold": "1000", "units": "bps"}``). Optional;
    alerting renders it verbatim."""

    metadata: dict[str, str] = Field(default_factory=dict)
    """Free-form context (correlation id, archetype, venue, source service)."""


# ---------------------------------------------------------------------------
# Seam-diagram conformance — declarative cross-product for tests.
# ---------------------------------------------------------------------------

CONSEQUENCE_EVENTS_EMITTED: Final[dict[RiskRuleConsequence, tuple[str, ...]]] = {
    RiskRuleConsequence.BLOCK: (
        "INSTRUCTION_REJECTED_RISK",
        "RiskRuleFiredEvent",
    ),
    RiskRuleConsequence.SCALE_DOWN: (
        "INSTRUCTION_ACCEPTED_PREFLIGHT",
        "RESIZED_EXECUTION",
        "RiskRuleFiredEvent",
    ),
    RiskRuleConsequence.MONITOR: (
        "INSTRUCTION_ACCEPTED_PREFLIGHT",
        "RiskRuleFiredEvent",
    ),
    RiskRuleConsequence.TEST_ONLY: (
        "INSTRUCTION_ACCEPTED_PREFLIGHT",
        "ORDER_SUBMITTED",
        "RiskRuleFiredEvent",
    ),
}
"""Declarative cross-product from the § 7 seam diagram.

§ 7 SSOT reconciliation
-----------------------

Constant SSOT of "which lifecycle events fire per ``RiskRuleConsequence``"
per the cross-product table in
``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` § "§ 7 SSOT
reconciliation seam". Phase 1.D unit tests assert this matches the seam
diagram; downstream service emitters cite this dict at runtime to verify
their own emission shape.

Each ``ORDER_SUBMITTED`` for ``TEST_ONLY`` targets the matching engine, not
the live venue — Layer 3 routing semantics per the seam diagram.
"""


CONSEQUENCE_ALERT_CODES: Final[dict[RiskRuleConsequence, str]] = {
    RiskRuleConsequence.BLOCK: "RISK_RULE_BLOCKED",
    RiskRuleConsequence.SCALE_DOWN: "RISK_RULE_SCALED_DOWN",
    RiskRuleConsequence.MONITOR: "RISK_RULE_MONITOR_FIRED",
    RiskRuleConsequence.TEST_ONLY: "RISK_RULE_TEST_ONLY_ROUTED",
}
"""Per-consequence AlertCode mapping per the § 7 seam diagram.

§ 7 SSOT reconciliation
-----------------------

The 4 AlertCodes were added to ``AlertCode`` closed-set in Phase 1.E
(2026-05-10 risk plan + Q6 Policy B "larger-set-wins" ratification). The
strings here MUST match ``AlertCode.<MEMBER>.value``; the unit test in
``tests/internal/unit/test_risk_rule_taxonomy.py`` asserts the keys cover
the full ``RiskRuleConsequence`` closed set and that every value resolves
through ``AlertCode``.
"""


def risk_rule_fired_event(
    rule: RiskRule,
    *,
    fired_at: datetime,
    instruction_id: str = "",
    trigger_detail: dict[str, str] | None = None,
    metadata: dict[str, str] | None = None,
) -> RiskRuleFiredEvent:
    """Build a :class:`RiskRuleFiredEvent` from a fired ``RiskRule``.

    Derives ``alert_code`` from ``CONSEQUENCE_ALERT_CODES`` and the kill-switch
    fields from ``rule.kill_switch_scope()`` + ``rule.triggers_kill_switch``
    (kill-switch only carried forward for a BLOCK consequence per the
    seam-diagram orthogonality). Callers supply ``fired_at`` (UTC) +
    optional ``instruction_id`` / ``trigger_detail`` / ``metadata``.

    This is the SSOT constructor — strategy-service/risk, execution-service
    and ``risk/preflight.py`` (UTL) all build the event through here so the
    ``consequence → alert_code`` and kill-switch derivations stay single-source.
    """
    arms_kill_switch = rule.consequence is RiskRuleConsequence.BLOCK and rule.triggers_kill_switch
    return RiskRuleFiredEvent(
        rule_id=rule.rule_id,
        scope=rule.scope,
        applies_to=rule.applies_to,
        consequence=rule.consequence,
        alerting_severity=rule.alerting_severity,
        alert_code=AlertCode(CONSEQUENCE_ALERT_CODES[rule.consequence]),
        fired_at=fired_at,
        instruction_id=instruction_id,
        triggers_kill_switch=arms_kill_switch,
        kill_switch_scope=rule.kill_switch_scope() if arms_kill_switch else None,
        trigger_detail=dict(trigger_detail or {}),
        metadata=dict(metadata or {}),
    )


__all__ = [
    "CONSEQUENCE_ALERT_CODES",
    "CONSEQUENCE_EVENTS_EMITTED",
    "RISK_RULE_IDS",
    "CapitalAtRiskCeilingTrigger",
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
    "RiskRule",
    "RiskRuleConsequence",
    "RiskRuleFiredEvent",
    "RiskRuleId",
    "RiskRuleScope",
    "RiskRuleTrigger",
    "SlippageBudgetTrigger",
    "risk_rule_fired_event",
]
