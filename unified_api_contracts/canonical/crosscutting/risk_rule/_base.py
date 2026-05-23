"""Risk-rule base types — enums, constants, and core RiskRule model.

This module contains the fundamental risk-rule taxonomy including the closed-set
identifiers, scopes, consequences, and the core RiskRule model.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict

from ..alerting import AlertSeverity
from ..alerting.codes import KillSwitchScope
from ._enums import RiskRuleConsequence, RiskRuleId, RiskRuleScope
from ._triggers import RiskRuleTrigger

RISK_RULE_IDS: Final[frozenset[str]] = frozenset(m.value for m in RiskRuleId)
"""String-membership view of :class:`RiskRuleId` for fast O(1) validation.

Mirrors ``ALERT_CODES``. Use enum members in new code; this set is for the
validation hot path only.
"""


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


__all__ = [
    "RISK_RULE_IDS",
    "RiskRule",
]
