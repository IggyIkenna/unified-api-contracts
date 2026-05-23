"""Risk-rule events and constants — fired events and seam-diagram conformance."""

from __future__ import annotations

from datetime import datetime
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from ..alerting import AlertSeverity
from ..alerting.codes import AlertCode, KillSwitchScope
from ._enums import RiskRuleConsequence, RiskRuleId, RiskRuleScope


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
    rule,  # RiskRule - avoiding import cycle
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
    "RiskRuleFiredEvent",
    "risk_rule_fired_event",
]
