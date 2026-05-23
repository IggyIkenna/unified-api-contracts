"""Risk-rule enums — closed-set identifiers, scopes, and consequences."""

from __future__ import annotations

from enum import StrEnum


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
    ORACLE_OUTAGE_HALT = "ORACLE_OUTAGE_HALT"
    CROSS_CLOUD_EGRESS_HALT = "CROSS_CLOUD_EGRESS_HALT"
    CUSTODY_ENDPOINT_HALT = "CUSTODY_ENDPOINT_HALT"

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


__all__ = ["RiskRuleConsequence", "RiskRuleId", "RiskRuleScope"]
