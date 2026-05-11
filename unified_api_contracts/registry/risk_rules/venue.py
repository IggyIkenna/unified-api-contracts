"""Per-venue risk-rule registry — cutover-archetype venues (Phase 2.B).

§ 7 SSOT reconciliation
=======================

This module seeds the per-venue axis of the per-axis risk-rule registry
introduced by ``plans/active/risk_simulations_limits_alerting_2026_05_10.md``
Phase 2.B. Each ``RiskRule`` here is evaluated at Layer 2 of the 4-layer
risk-gates model (``codex/09-strategy/architecture-v2/cross-cutting/risk-gates.md``)
against per-venue context (open-interest, single-instrument size, total
cross-instrument exposure on the venue).

Composes with the 5 canonical SSOTs per the seam diagram in the plan body:

* **Risk-gates Layer 2** — pre-flight evaluator picks the venue's rule set by
  matching ``rule.applies_to == venue_name``.
* **Kill-switch SSOT** — ``rule.kill_switch_scope()`` returns
  ``KillSwitchScope.VENUE`` for every entry here (per the orthogonality
  declaration in ``RiskRuleScope`` docstring).
* **Alerting** — ``rule.alerting_severity`` drives the ``RISK_RULE_BLOCKED`` /
  ``RISK_RULE_SCALED_DOWN`` / ``RISK_RULE_MONITOR_FIRED`` /
  ``RISK_RULE_TEST_ONLY_ROUTED`` dispatch per ``CONSEQUENCE_ALERT_CODES``.
* **Circuit-breaker** — aggregated BLOCK rate ≥ threshold on a venue may
  transition that venue's breaker (CLOSED → DEGRADED → OPEN) per the
  ``alerting_service_live_rules`` cascade.

Cutover-archetype venues (6 perp venues + Solana DeFi protocols per the
2026-05-23 master plan):

* **CeFi perps**: ``bybit``, ``deribit``, ``binance``, ``okx``, ``hyperliquid``,
  ``aster``.
* **Solana DeFi (carry_staked_basis LST yields)**: ``marinade``, ``jito``,
  ``sanctum``.

Each venue carries ≥3 rules (MaxOI, max single-instrument size, max
cross-instrument size on the venue). Total ≥27 rules at registry seed.
"""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.alerting import AlertSeverity
from unified_api_contracts.canonical.crosscutting.risk_rule import (
    MaxConcentrationTrigger,
    MaxOITrigger,
    MaxPositionSizeTrigger,
    RiskRule,
    RiskRuleConsequence,
    RiskRuleId,
    RiskRuleScope,
)

# ---------------------------------------------------------------------------
# CeFi perp venues — 6 venues × 3 rules = 18 rules
# ---------------------------------------------------------------------------

_BYBIT_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_OI_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="bybit",
        trigger=MaxOITrigger(cap_usd=Decimal("5000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Bybit per-instrument open-interest cap (USD-notional).",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="bybit",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("1000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Bybit max single-instrument USD-notional position size.",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="bybit",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("10000000")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="Bybit max cross-instrument USD-notional total exposure on venue.",
    ),
)

_DERIBIT_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_OI_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="deribit",
        trigger=MaxOITrigger(cap_usd=Decimal("3000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Deribit per-instrument open-interest cap (USD-notional).",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="deribit",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("750000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Deribit max single-instrument USD-notional position size.",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="deribit",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("7500000")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="Deribit max cross-instrument USD-notional total exposure on venue.",
    ),
)

_BINANCE_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_OI_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="binance",
        trigger=MaxOITrigger(cap_usd=Decimal("10000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Binance per-instrument open-interest cap (USD-notional).",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="binance",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("2000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Binance max single-instrument USD-notional position size.",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="binance",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("20000000")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="Binance max cross-instrument USD-notional total exposure on venue.",
    ),
)

_OKX_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_OI_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="okx",
        trigger=MaxOITrigger(cap_usd=Decimal("4000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="OKX per-instrument open-interest cap (USD-notional).",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="okx",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("800000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="OKX max single-instrument USD-notional position size.",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="okx",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("8000000")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="OKX max cross-instrument USD-notional total exposure on venue.",
    ),
)

_HYPERLIQUID_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_OI_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="hyperliquid",
        trigger=MaxOITrigger(cap_usd=Decimal("2000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Hyperliquid per-instrument open-interest cap (USD-notional).",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="hyperliquid",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("500000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Hyperliquid max single-instrument USD-notional position size.",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="hyperliquid",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("4000000")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="Hyperliquid max cross-instrument USD-notional total exposure on venue.",
    ),
)

_ASTER_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_OI_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="aster",
        trigger=MaxOITrigger(cap_usd=Decimal("1000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Aster per-instrument open-interest cap (USD-notional).",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="aster",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("250000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Aster max single-instrument USD-notional position size.",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="aster",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("2000000")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="Aster max cross-instrument USD-notional total exposure on venue.",
    ),
)

# ---------------------------------------------------------------------------
# Solana DeFi protocols (LST yields for carry_staked_basis) — 3 × 3 = 9 rules
# ---------------------------------------------------------------------------

_MARINADE_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_OI_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="marinade",
        trigger=MaxOITrigger(cap_usd=Decimal("500000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Marinade mSOL TVL deployment cap (USD-notional).",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="marinade",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("200000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Marinade max single-stake USD-notional mSOL position.",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_CONCENTRATION_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="marinade",
        trigger=MaxConcentrationTrigger(cap_pct=Decimal("0.30")),
        consequence=RiskRuleConsequence.MONITOR,
        alerting_severity=AlertSeverity.WARN,
        description="Marinade mSOL concentration cap as % of total LST portfolio.",
    ),
)

_JITO_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_OI_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="jito",
        trigger=MaxOITrigger(cap_usd=Decimal("750000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Jito jitoSOL TVL deployment cap (USD-notional).",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="jito",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("250000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Jito max single-stake USD-notional jitoSOL position.",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_CONCENTRATION_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="jito",
        trigger=MaxConcentrationTrigger(cap_pct=Decimal("0.40")),
        consequence=RiskRuleConsequence.MONITOR,
        alerting_severity=AlertSeverity.WARN,
        description="Jito jitoSOL concentration cap as % of total LST portfolio.",
    ),
)

_SANCTUM_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_OI_PER_VENUE,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="sanctum",
        trigger=MaxOITrigger(cap_usd=Decimal("250000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Sanctum bSOL/INF TVL deployment cap (USD-notional).",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="sanctum",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("100000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Sanctum max single-stake USD-notional bSOL/INF position.",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_CONCENTRATION_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_VENUE,
        applies_to="sanctum",
        trigger=MaxConcentrationTrigger(cap_pct=Decimal("0.20")),
        consequence=RiskRuleConsequence.MONITOR,
        alerting_severity=AlertSeverity.WARN,
        description="Sanctum bSOL/INF concentration cap as % of total LST portfolio.",
    ),
)

# ---------------------------------------------------------------------------
# Public registry tuple — flattened across all venues.
# ---------------------------------------------------------------------------

VENUE_RULES: tuple[RiskRule, ...] = (
    *_BYBIT_RULES,
    *_DERIBIT_RULES,
    *_BINANCE_RULES,
    *_OKX_RULES,
    *_HYPERLIQUID_RULES,
    *_ASTER_RULES,
    *_MARINADE_RULES,
    *_JITO_RULES,
    *_SANCTUM_RULES,
)
"""Per-venue rules registry seed.

≥3 rules per venue across 9 cutover-archetype venues (6 CeFi perps + 3 Solana
DeFi protocols). All entries have ``scope=PER_VENUE``;
``rule.kill_switch_scope()`` returns ``KillSwitchScope.VENUE`` per the seam
orthogonality declaration.
"""


__all__ = ["VENUE_RULES"]
