"""LIVE_ALERT_RULES — workspace SSOT for production routing.

Replaces the inline ``_default_routing_rules`` in
``alerting-service/alerting_service/config.py``. Phase 2 of
``alerting_service_live_rules_2026_05_07`` swaps the default-factory body to
``[rule.to_routing_dict() for rule in LIVE_ALERT_RULES]`` so the service
config no longer holds a parallel SSOT.

Construction is fail-loud: an :class:`AlertRule` referencing an unknown
``AlertCode`` member raises :class:`UnknownAlertCodeError`; an unknown
``threshold_key`` raises :class:`UnknownThresholdKeyError`. The closed-set
sanity tests in ``tests/internal/unit/test_alerting_taxonomy.py`` enforce
these at CI time.
"""

from __future__ import annotations

import fnmatch
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .codes import ALERT_CODES, AlertChannel, AlertCode, AlertSeverity, KillSwitchScope
from .thresholds import ALERT_THRESHOLDS


class UnknownAlertCodeError(ValueError):
    """Raised when an :class:`AlertRule.event_pattern` matches no :class:`AlertCode`."""


class UnknownThresholdKeyError(ValueError):
    """Raised when an :class:`AlertRule.threshold_key` is not in :data:`ALERT_THRESHOLDS`."""


class AlertRule(BaseModel):
    """A single routing rule — event_pattern → severity + channels (+ optional kill-switch).

    The ``event_pattern`` is fnmatch-style (e.g. ``"KILL_SWITCH_*"``) and is matched
    against incoming event names. At least one :class:`AlertCode` member must
    match the pattern, otherwise the rule is dead and a stale risk —
    :meth:`_validate_event_pattern_matches_codes` catches this at construction.

    ``triggers_kill_switch`` is the kill-switch axis orthogonal to severity:
    a rule with ``triggers_kill_switch=True`` causes
    ``alerting-service/alerting_service/kill_switch_bus_subscriber.py`` to
    publish a ``KillSwitchEvent`` (consumed by execution-service) on top of
    the routing-channel dispatch. Defaults to ``False`` — rules must opt in.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: AlertCode
    """Canonical AlertCode this rule represents. Anchors operator playbook
    deep-link, threshold lookup, and rehearsal scope."""

    event_pattern: str
    """fnmatch pattern matched against incoming event names. Must match
    `code.value` (exact-match rules) OR a wildcard family containing `code`."""

    severity: AlertSeverity
    """Paging severity. CRITICAL → PagerDuty P1. HIGH → PagerDuty P2. WARN →
    Telegram only. INFO → log only."""

    channels: tuple[AlertChannel, ...]
    """Dispatch channels for this rule. Empty tuple == LOG_ONLY equivalent;
    prefer explicit ``(AlertChannel.LOG_ONLY,)`` for readability."""

    runbook_doc: str = Field(default="")
    """Path (relative to repo root) of the operator playbook md file. UI deep-
    links here from the alert detail modal. Empty string == not yet authored."""

    threshold_key: str | None = Field(default=None)
    """Optional :data:`ALERT_THRESHOLDS` key. Validated against the registry
    at construction. ``None`` for rules whose firing condition is qualitative
    (e.g. ``CIRCUIT_BREAKER_OPEN`` is binary, no threshold)."""

    triggers_kill_switch: bool = Field(default=False)
    """If True, alerting-service publishes a ``KillSwitchEvent`` when this
    rule fires. Reserved for the ``KILL_SWITCH_*`` family."""

    kill_switch_scope: KillSwitchScope | None = Field(default=None)
    """Scope of the kill-switch action: ``GLOBAL`` halts every venue/archetype,
    ``VENUE`` halts only the named venue's adapters, ``ARCHETYPE`` halts only
    the named strategy archetype, ``STRATEGY`` halts a single strategy ID.
    REQUIRED for KILL_SWITCH_* codes; MUST be ``None`` for non-kill-switch
    codes. Validated below."""

    description: str = Field(default="")
    """One-line operator-facing description; rendered alongside the badge
    in DART. Keep concise."""

    @field_validator("event_pattern")
    @classmethod
    def _event_pattern_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("AlertRule.event_pattern must be a non-empty fnmatch pattern")
        return value

    @field_validator("channels")
    @classmethod
    def _channels_non_empty(cls, value: tuple[AlertChannel, ...]) -> tuple[AlertChannel, ...]:
        if not value:
            raise ValueError(
                "AlertRule.channels must contain at least one AlertChannel; "
                "use (AlertChannel.LOG_ONLY,) for log-only behaviour"
            )
        return value

    @model_validator(mode="after")
    def _validate_threshold_key(self) -> AlertRule:
        if self.threshold_key is not None and self.threshold_key not in ALERT_THRESHOLDS:
            raise UnknownThresholdKeyError(
                f"AlertRule.threshold_key={self.threshold_key!r} not in "
                f"ALERT_THRESHOLDS (known: {sorted(ALERT_THRESHOLDS)})"
            )
        return self

    @model_validator(mode="after")
    def _validate_event_pattern_matches_codes(self) -> AlertRule:
        if self.event_pattern == "*":
            # Catch-all is allowed and intentional — matches every code.
            return self
        matched = [c for c in ALERT_CODES if fnmatch.fnmatchcase(c, self.event_pattern)]
        if not matched:
            raise UnknownAlertCodeError(
                f"AlertRule.event_pattern={self.event_pattern!r} matches no AlertCode member "
                f"(closed set: {sorted(ALERT_CODES)})"
            )
        return self

    @model_validator(mode="after")
    def _validate_kill_switch_only_for_kill_switch_family(self) -> AlertRule:
        if self.triggers_kill_switch and not self.code.value.startswith("KILL_SWITCH_"):
            raise ValueError(
                "AlertRule.triggers_kill_switch=True is only valid for "
                "KILL_SWITCH_* AlertCode members; got "
                f"{self.code.value!r}"
            )
        return self

    @model_validator(mode="after")
    def _validate_kill_switch_scope_matches_code_family(self) -> AlertRule:
        is_kill_switch = self.code.value.startswith("KILL_SWITCH_")
        if is_kill_switch and self.kill_switch_scope is None:
            raise ValueError(
                "AlertRule.kill_switch_scope is REQUIRED for KILL_SWITCH_* "
                f"AlertCode members; got code={self.code.value!r} with "
                f"kill_switch_scope=None. Choose one of {[s.value for s in KillSwitchScope]!r}."
            )
        if not is_kill_switch and self.kill_switch_scope is not None:
            raise ValueError(
                "AlertRule.kill_switch_scope MUST be None for non-KILL_SWITCH_* "
                f"AlertCode members; got code={self.code.value!r} with "
                f"kill_switch_scope={self.kill_switch_scope!r}."
            )
        return self

    def to_routing_dict(self) -> dict[str, object]:
        """Render to the legacy routing-rule shape consumed by alerting-service.

        Bridge for Phase 2 migration: ``alerting-service/config.py``'s
        ``_default_routing_rules`` factory becomes
        ``[rule.to_routing_dict() for rule in LIVE_ALERT_RULES]`` —
        byte-equivalent output, single SSOT.
        """
        return {
            "event_pattern": self.event_pattern,
            "channels": [ch.value for ch in self.channels if ch is not AlertChannel.LOG_ONLY],
            "severity_filter": self.severity.to_legacy_filter(),
        }


# ---------------------------------------------------------------------------
# LIVE_ALERT_RULES — production rule set.
#
# Order matters for fnmatch dispatch — first-match-wins. Catch-all ``*`` MUST
# be last. Atomic codes precede their wildcard family so a specific override
# (e.g. ``CIRCUIT_BREAKER_OPEN`` CRITICAL) wins over the family default.
# ---------------------------------------------------------------------------


_RUNBOOK_BASE: Final[str] = "unified-trading-pm/codex/15-runbooks/alerting"


def _runbook(slug: str) -> str:
    return f"{_RUNBOOK_BASE}/{slug}.md"


LIVE_ALERT_RULES: Final[tuple[AlertRule, ...]] = (
    # ── T1 CRITICAL — page now, kill-switch-fire family ─────────────────────
    # Atomic per-code rules so ``kill_switch_scope`` can carry the per-event
    # halt scope (GLOBAL / VENUE / ARCHETYPE). The legacy single-wildcard
    # ``KILL_SWITCH_*`` rule was split 2026-05-08 because one rule cannot
    # carry three different scopes. Routing equivalence is preserved.
    AlertRule(
        code=AlertCode.KILL_SWITCH_DEFI_LIQUIDATION_RISK,
        event_pattern="KILL_SWITCH_DEFI_LIQUIDATION_RISK",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("kill_switch_defi_liquidation_risk"),
        threshold_key="defi_health_factor_critical",
        triggers_kill_switch=True,
        kill_switch_scope=KillSwitchScope.GLOBAL,
        description=(
            "DeFi position approaching liquidation (Aave HF below buffer) —"
            " halt all venues + page on-call. GLOBAL scope: every adapter"
            " stops new orders until operator clears."
        ),
    ),
    AlertRule(
        code=AlertCode.KILL_SWITCH_PORTFOLIO_DRAWDOWN,
        event_pattern="KILL_SWITCH_PORTFOLIO_DRAWDOWN",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("kill_switch_portfolio_drawdown"),
        triggers_kill_switch=True,
        kill_switch_scope=KillSwitchScope.GLOBAL,
        description=(
            "Portfolio drawdown breached threshold — halt all venues +"
            " page on-call. GLOBAL scope: every adapter stops new orders"
            " until operator reviews positions."
        ),
    ),
    AlertRule(
        code=AlertCode.KILL_SWITCH_VENUE_DISCONNECT,
        event_pattern="KILL_SWITCH_VENUE_DISCONNECT",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("kill_switch_venue_disconnect"),
        triggers_kill_switch=True,
        kill_switch_scope=KillSwitchScope.VENUE,
        description=(
            "Venue connectivity lost — halt the affected venue's adapters"
            " until reconnect. VENUE scope: other venues continue trading."
            " Payload includes ``details['venue']`` for scope key."
        ),
    ),
    # ── T1 CRITICAL — circuit + multi-leg ───────────────────────────────────
    AlertRule(
        code=AlertCode.CIRCUIT_BREAKER_OPEN,
        event_pattern="CIRCUIT_BREAKER_OPEN",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("circuit_breaker_open"),
        description="Per-(service,venue) circuit transitioned to OPEN — venue health degraded.",
    ),
    AlertRule(
        code=AlertCode.UNHEDGED_POSITION_ALERT,
        event_pattern="UNHEDGED_POSITION_ALERT",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("unhedged_position_alert"),
        description="Multi-leg partial fill — unhedged position detected.",
    ),
    AlertRule(
        code=AlertCode.MULTI_LEG_COMPENSATION_FAILED,
        event_pattern="MULTI_LEG_COMPENSATION_FAILED",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("multi_leg_compensation_failed"),
        description="Compensation trade failed — unhedged + circuit breaker fired.",
    ),
    AlertRule(
        code=AlertCode.DUAL_FAILURE_DETECTED,
        event_pattern="DUAL_FAILURE_DETECTED",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("dual_failure_detected"),
        description="Dual failure — can't reconcile AND can't execute.",
    ),
    AlertRule(
        code=AlertCode.ORDER_RECOVERY_FAILED,
        event_pattern="ORDER_RECOVERY_FAILED",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("order_recovery_failed"),
        description="Orphaned orders unresolvable — manual operator intervention required.",
    ),
    AlertRule(
        code=AlertCode.SERVICE_ERROR_CRITICAL,
        event_pattern="SERVICE_ERROR_CRITICAL",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("service_error_critical"),
        description="Service-level critical error — page on-call.",
    ),
    # ── T1 CRITICAL — DeFi P0 ──────────────────────────────────────────────
    AlertRule(
        code=AlertCode.DEFI_HEALTH_FACTOR_CRITICAL,
        event_pattern="DEFI_HEALTH_FACTOR_CRITICAL",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("defi_health_factor_critical"),
        threshold_key="defi_health_factor_critical",
        description="Aave health factor approaching liquidation — page on-call + auto-deleverage candidate.",
    ),
    AlertRule(
        code=AlertCode.DEFI_WEETH_DEPEG,
        event_pattern="DEFI_WEETH_DEPEG",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("defi_weeth_depeg"),
        threshold_key="defi_weeth_depeg_bps",
        description="weETH/ETH peg deviation exceeds tolerance — page + reduce LST exposure.",
    ),
    AlertRule(
        code=AlertCode.DEFI_POSITION_LIQUIDATED,
        event_pattern="DEFI_POSITION_LIQUIDATED",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("defi_position_liquidated"),
        description="Confirmed on-chain liquidation event — page + post-mortem trigger.",
    ),
    AlertRule(
        code=AlertCode.DEFI_RATE_DEVIATION,
        event_pattern="DEFI_RATE_DEVIATION",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("defi_rate_deviation"),
        description="Oracle/DEX rate divergence — page; possible MEV / oracle stale.",
    ),
    # ── T1 CRITICAL — DeFi Family 1/2 recursive-borrow archetype (added 2026-05-12)
    AlertRule(
        code=AlertCode.DEFI_LIQUIDATION_IMMINENT,
        event_pattern="DEFI_LIQUIDATION_IMMINENT",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("defi_liquidation_imminent"),
        threshold_key="defi_health_factor_critical",
        description="HF < 1.05 (pre-liquidation). LiquidationProximityCircuit fires immediate flash-close.",
    ),
    AlertRule(
        code=AlertCode.DEFI_PERP_VENUE_OUTAGE,
        event_pattern="DEFI_PERP_VENUE_OUTAGE",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("defi_perp_venue_outage"),
        description="HL bridge halt / Bybit rate-limit / WS-disconnect sustained > 60s; failover decision tree.",
    ),
    AlertRule(
        code=AlertCode.DEFI_ORACLE_STALE_PAUSE,
        event_pattern="DEFI_ORACLE_STALE_PAUSE",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("defi_oracle_stale_pause"),
        description="Chainlink heartbeat > 24h on active feed; pause new opens; widen HF threshold +0.10.",
    ),
    AlertRule(
        code=AlertCode.DEFI_RECURSIVE_LOOP_GAS_BUDGET_EXCEEDED,
        event_pattern="DEFI_RECURSIVE_LOOP_GAS_BUDGET_EXCEEDED",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("defi_recursive_loop_gas_budget_exceeded"),
        description="Persistent driver halted mid-loop; partial-state recovery + mid-loop unwind.",
    ),
    AlertRule(
        code=AlertCode.DEFI_CROSS_VENUE_DELTA_DRIFT,
        event_pattern="DEFI_CROSS_VENUE_DELTA_DRIFT",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("defi_cross_venue_delta_drift"),
        description="PerpHedgeSizer band breach > 5% of E_actual; auto-rebalance + alert.",
    ),
    # ── T1 CRITICAL — margin ────────────────────────────────────────────────
    AlertRule(
        code=AlertCode.MARGIN_LIQUIDATION,
        event_pattern="MARGIN_LIQUIDATION",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("margin_liquidation"),
        description="Margin liquidation event from PBM canonical ladder.",
    ),
    AlertRule(
        code=AlertCode.MARGIN_CRITICAL,
        event_pattern="MARGIN_CRITICAL",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("margin_critical"),
        description="Margin critical band — page on-call.",
    ),
    # ── T2 HIGH — Telegram + PagerDuty P2 ───────────────────────────────────
    AlertRule(
        code=AlertCode.CIRCUIT_BREAKER_BACKOFF_ESCALATING,
        event_pattern="CIRCUIT_BREAKER_BACKOFF_*",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("circuit_breaker_backoff"),
        description="Repeated recovery failure — backoff schedule escalating.",
    ),
    AlertRule(
        code=AlertCode.ORDER_ORPHANED,
        event_pattern="ORDER_ORPHANED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("order_orphaned"),
        description="Orphaned order found during startup recovery.",
    ),
    AlertRule(
        code=AlertCode.POSITION_DRIFT_DETECTED,
        event_pattern="POSITION_DRIFT_DETECTED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("position_drift"),
        threshold_key="position_drift_bps",
        description="Position drift detected — could be WARNING or CRITICAL severity.",
    ),
    AlertRule(
        # Pattern preserves legacy `RECON_DEGRADED_*` byte-equivalence; the
        # bare atomic `RECON_DEGRADED` code anchors the rule + runbook.
        code=AlertCode.RECON_DEGRADED,
        event_pattern="RECON_DEGRADED_*",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("recon_degraded"),
        description="Closing positions without verified reconciliation state.",
    ),
    AlertRule(
        code=AlertCode.POSITION_CRITICAL_DISCREPANCY,
        event_pattern="POSITION_CRITICAL_DISCREPANCY",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("position_critical_discrepancy"),
        description="Position discrepancy large enough to escalate.",
    ),
    AlertRule(
        code=AlertCode.MARGIN_WARNING,
        event_pattern="MARGIN_WARNING",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("margin_warning"),
        description="Margin warning band — on-call sees drift before critical.",
    ),
    AlertRule(
        code=AlertCode.MARGIN_THRESHOLD_BREACH,
        event_pattern="MARGIN_THRESHOLD_BREACH",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("margin_threshold_breach"),
        threshold_key="margin_threshold_breach_bps",
        description="Within initial-margin-call buffer — pre-emptive notify.",
    ),
    AlertRule(
        code=AlertCode.MARGIN_INFO,
        event_pattern="MARGIN_INFO",
        severity=AlertSeverity.INFO,
        channels=(AlertChannel.LOG_ONLY,),
        runbook_doc=_runbook("margin_info"),
        description=(
            "Informational margin event from PBM canonical ladder — position within"
            " safe band; metric being tracked. Log-only, no page."
        ),
    ),
    AlertRule(
        code=AlertCode.CROSS_CLOUD_EGRESS_DETECTED,
        event_pattern="CROSS_CLOUD_EGRESS_DETECTED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("cross_cloud_egress_detected"),
        threshold_key="cross_cloud_egress_bytes_per_request",
        description=(
            "Data-locality bug — UI/API in cloud A reading data from cloud B"
            " above per-request budget. Audit 2026-05-07 dual-cloud-active policy."
        ),
    ),
    # ── ML lifecycle (2026-05-08, cefi_ml_may_23_2026.epic Tab 5 Item 6) ────
    # CRITICAL — model-version mismatch is zero-tolerance: any trade against
    # an unapproved artefact is a regulatory + risk problem.
    AlertRule(
        code=AlertCode.ML_MODEL_VERSION_MISMATCH,
        event_pattern="ML_MODEL_VERSION_MISMATCH",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("ml_model_version_mismatch"),
        threshold_key="ml_model_version_mismatch_minutes",
        description=(
            "Strategy executing against unexpected model version — page on-call"
            " immediately; halt archetype until artefact / promotion path resolved."
        ),
    ),
    # CRITICAL — kill-switch family extension: ML model server unreachable /
    # repeated inference failures. ARCHETYPE scope: halt only the affected
    # ML archetype, other archetypes keep trading. Payload includes
    # ``details['archetype']`` for scope key.
    AlertRule(
        code=AlertCode.KILL_SWITCH_ML_MODEL_FAILURE,
        event_pattern="KILL_SWITCH_ML_MODEL_FAILURE",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("kill_switch_ml_model_failure"),
        triggers_kill_switch=True,
        kill_switch_scope=KillSwitchScope.ARCHETYPE,
        description=(
            "ML model server unreachable / repeated inference failures — halt"
            " the affected archetype until model recovers or operator overrides."
        ),
    ),
    # HIGH — model-output drift vs training baseline (PSI ≥ threshold).
    AlertRule(
        code=AlertCode.ML_MODEL_DRIFT_DETECTED,
        event_pattern="ML_MODEL_DRIFT_DETECTED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("ml_model_drift_detected"),
        threshold_key="ml_model_drift_psi",
        description=(
            "ML output distribution drift vs training baseline (PSI threshold)."
            " Page — model may be stale or feature inputs may have shifted regime."
        ),
    ),
    # HIGH — strategy P&L deviation from expected baseline.
    AlertRule(
        code=AlertCode.ML_PNL_DEVIATION,
        event_pattern="ML_PNL_DEVIATION",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("ml_pnl_deviation"),
        threshold_key="ml_pnl_deviation_bps",
        description=(
            "Live strategy P&L deviates from expected baseline beyond bps"
            " threshold over 24h — model wrong or execution degraded; investigate."
        ),
    ),
    # ── T3 WARN — Telegram only ─────────────────────────────────────────────
    AlertRule(
        code=AlertCode.CIRCUIT_BREAKER_DEGRADED,
        event_pattern="CIRCUIT_BREAKER_DEGRADED",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("circuit_breaker_degraded"),
        description="Circuit breaker throttling — venue health declining.",
    ),
    AlertRule(
        code=AlertCode.CIRCUIT_BREAKER_CLOSED,
        event_pattern="CIRCUIT_BREAKER_CLOSED",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("circuit_breaker_closed"),
        description="Circuit breaker recovered.",
    ),
    AlertRule(
        code=AlertCode.SERVICE_ERROR,
        event_pattern="SERVICE_ERROR",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("service_error"),
        description="Service-level non-critical error.",
    ),
    AlertRule(
        code=AlertCode.PREFLIGHT_FAILED,
        event_pattern="PREFLIGHT_FAILED",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("preflight_failed"),
        description="Preflight check failed — order rejected before submission.",
    ),
    AlertRule(
        code=AlertCode.SERVICE_DEGRADED,
        event_pattern="SERVICE_DEGRADED",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("service_degraded"),
        description="Service running but degraded mode active.",
    ),
    AlertRule(
        code=AlertCode.POSITION_CORRECTION_DISPATCHED,
        event_pattern="POSITION_CORRECTION_*",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("position_correction"),
        description="Auto-correction dispatched by reconciliation.",
    ),
    AlertRule(
        code=AlertCode.PORTFOLIO_REBALANCE_TRIGGERED,
        event_pattern="PORTFOLIO_REBALANCE_*",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("portfolio_rebalance"),
        description="Portfolio rebalancing triggered by drift.",
    ),
    AlertRule(
        code=AlertCode.ORDER_RECOVERY_INITIATED,
        event_pattern="ORDER_RECOVERY_*",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("order_recovery"),
        description="Order recovery lifecycle (initiated, completed).",
    ),
    AlertRule(
        code=AlertCode.DEFI_AAVE_UTILIZATION_SPIKE,
        event_pattern="DEFI_AAVE_UTILIZATION_SPIKE",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("defi_aave_utilization_spike"),
        threshold_key="defi_aave_utilization_spike_bps",
        description=(
            "Aave pool utilization above the kink (default 95.00 % = 9500 bps_of_one)."
            " Carry strategy assumptions break above this point."
        ),
    ),
    AlertRule(
        code=AlertCode.DEFI_FUNDING_RATE_FLIP,
        event_pattern="DEFI_FUNDING_RATE_FLIP",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("defi_funding_rate_flip"),
        threshold_key="defi_funding_rate_flip_bps_5m",
        description="Perp funding rate flipped sign — possible regime change.",
    ),
    AlertRule(
        code=AlertCode.DEFI_FEATURE_STALE,
        event_pattern="DEFI_FEATURE_STALE",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("defi_feature_stale"),
        threshold_key="defi_feature_stale_minutes",
        description="DeFi LST yield read freshness exceeded SLA.",
    ),
    AlertRule(
        code=AlertCode.DEFI_TX_SIMULATION_FAILED,
        event_pattern="DEFI_TX_SIMULATION_FAILED",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("defi_tx_simulation_failed"),
        description="Tenderly tx simulation rejected — order would revert on chain.",
    ),
    AlertRule(
        code=AlertCode.BALANCE_DRIFT,
        event_pattern="BALANCE_DRIFT",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("balance_drift"),
        threshold_key="balance_drift_usd",
        description="Wallet balance drift vs expected ledger state.",
    ),
    AlertRule(
        code=AlertCode.ORDER_REJECTION_SPIKE,
        event_pattern="ORDER_REJECTION_SPIKE",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("order_rejection_spike"),
        threshold_key="order_rejection_spike_per_min",
        description="Sustained spike in order rejects — venue health degraded.",
    ),
    AlertRule(
        code=AlertCode.POSITION_DRIFT,
        event_pattern="POSITION_DRIFT",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("position_drift"),
        threshold_key="position_drift_bps",
        description="Position drift from target exceeds rebalance threshold.",
    ),
    # ── ML lifecycle WARN tier (2026-05-08) ─────────────────────────────────
    AlertRule(
        code=AlertCode.ML_SIGNAL_STALENESS,
        event_pattern="ML_SIGNAL_STALENESS",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM, AlertChannel.SLACK),
        runbook_doc=_runbook("ml_signal_staleness"),
        threshold_key="ml_signal_staleness_minutes",
        description=(
            "ML signal stale beyond freshness window — investigate before escalating"
            " to ML_MODEL_VERSION_MISMATCH or KILL_SWITCH_ML_MODEL_FAILURE."
        ),
    ),
    AlertRule(
        code=AlertCode.ML_INFERENCE_LATENCY_BREACH,
        event_pattern="ML_INFERENCE_LATENCY_BREACH",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.SLACK,),
        runbook_doc=_runbook("ml_inference_latency_breach"),
        threshold_key="ml_inference_latency_p99_ms",
        description=(
            "Inference p99 latency SLO breached — model server slower than expected;"
            " investigate before staleness escalation."
        ),
    ),
    # ── Risk-rule pre-flight decisions (2026-05-11, risk_simulations plan Phase 1.E) ──
    # Per § 7 SSOT reconciliation seam: BLOCK is HIGH (route to alerting, not page);
    # SCALE_DOWN is WARN; MONITOR + TEST_ONLY are INFO. RiskRuleConsequence cross-product
    # table in risk_simulations_limits_alerting_2026_05_10.md lines 50-58.
    AlertRule(
        code=AlertCode.RISK_RULE_BLOCKED,
        event_pattern="RISK_RULE_BLOCKED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("risk_rule_blocked"),
        description=(
            "Pre-flight risk rule BLOCKED an order — order never reached venue."
            " Operator reviews the rule fire + decides whether to override."
        ),
    ),
    AlertRule(
        code=AlertCode.RISK_RULE_SCALED_DOWN,
        event_pattern="RISK_RULE_SCALED_DOWN",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("risk_rule_scaled_down"),
        description=(
            "Pre-flight risk rule SCALED DOWN an order — order proceeded at reduced"
            " size. Logged for post-trade review; no operator action required."
        ),
    ),
    AlertRule(
        code=AlertCode.RISK_RULE_MONITOR_FIRED,
        event_pattern="RISK_RULE_MONITOR_FIRED",
        severity=AlertSeverity.INFO,
        channels=(AlertChannel.LOG_ONLY,),
        runbook_doc=_runbook("risk_rule_monitor_fired"),
        description=(
            "Advisory risk rule fired (MONITOR consequence) — instruction passed"
            " through unmodified. Recorded for analytics; no operator action."
        ),
    ),
    AlertRule(
        code=AlertCode.RISK_RULE_TEST_ONLY_ROUTED,
        event_pattern="RISK_RULE_TEST_ONLY_ROUTED",
        severity=AlertSeverity.INFO,
        channels=(AlertChannel.LOG_ONLY,),
        runbook_doc=_runbook("risk_rule_test_only_routed"),
        description=(
            "Risk rule routed instruction to the matching engine (TEST_ONLY"
            " consequence) instead of live venue. Logged for backtest analysis."
        ),
    ),
    # ── Kill-switch recovery events (2026-05-11, Q8 ratification) ───────────
    # Distinct alert events per Policy B (larger-set-wins). Code starts with
    # KILL_SWITCH_ so kill_switch_scope is required by validator; GLOBAL chosen
    # as default since recovery scope follows the original arm-event scope.
    AlertRule(
        code=AlertCode.KILL_SWITCH_AUTO_RECOVERED,
        event_pattern="KILL_SWITCH_AUTO_RECOVERED",
        severity=AlertSeverity.INFO,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("kill_switch_auto_recovered"),
        kill_switch_scope=KillSwitchScope.GLOBAL,
        description=(
            "Circuit breaker auto-recovered after cooldown — guard predicate green"
            " for N consecutive readings; positions/orders resumed automatically."
        ),
    ),
    AlertRule(
        code=AlertCode.KILL_SWITCH_MANUAL_UNKILLED,
        event_pattern="KILL_SWITCH_MANUAL_UNKILLED",
        severity=AlertSeverity.INFO,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("kill_switch_manual_unkilled"),
        kill_switch_scope=KillSwitchScope.GLOBAL,
        description=(
            "Operator manually disarmed a kill switch via deployment-UI or CLI."
            " Audit log carries unkilled_by_operator_id + original arm provenance."
        ),
    ),
    # ── Tick-staleness + connectivity-gap event taxonomy (2026-05-11) ──────
    # alerting_service_live_rules_2026_05_07 § "Tick-staleness +
    # connectivity-gap event taxonomy" — complementary signals from MDPS
    # (downstream-detected) + MTDS (upstream-detected). The 30s coalesce
    # window in ``alerting-service/notifiers/router.py`` merges concurrent
    # TICK_STALENESS + CONNECTIVITY_GAP_DETECTED fires for the same
    # (venue, instrument, time-window) into ONE operator alert. Recovery
    # events (CONNECTIVITY_RECOVERED / CONNECTIVITY_GAP_BACKFILLED) close
    # the loop on previously-fired gap alerts. Payload contracts documented
    # in AlertCode docstrings (codes.py).
    AlertRule(
        code=AlertCode.TICK_STALENESS,
        event_pattern="TICK_STALENESS",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("tick_staleness"),
        threshold_key="tick_staleness_seconds",
        description=(
            "MDPS downstream-detected tick staleness — last tick for"
            " (venue, instrument) older than tick_staleness_seconds (default"
            " 300s = 5min). PagerDuty P2 when actual_seconds > 5min."
            " Coalesced with concurrent CONNECTIVITY_GAP_DETECTED on the"
            " same (venue, instrument) within 30s at the router."
        ),
    ),
    AlertRule(
        code=AlertCode.CONNECTIVITY_GAP_DETECTED,
        event_pattern="CONNECTIVITY_GAP_DETECTED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("connectivity_gap_detected"),
        description=(
            "MTDS upstream-detected connectivity gap — websocket dropped /"
            " heartbeat staleness threshold crossed per-venue. PagerDuty P2."
            " Coalesced with concurrent TICK_STALENESS on the same"
            " (venue, instrument) within 30s at the router."
        ),
    ),
    AlertRule(
        code=AlertCode.CONNECTIVITY_RECOVERED,
        event_pattern="CONNECTIVITY_RECOVERED",
        severity=AlertSeverity.INFO,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("connectivity_recovered"),
        description=(
            "MTDS upstream connectivity restored — closes the loop on a"
            " previously-fired CONNECTIVITY_GAP_DETECTED. Telegram-only"
            " (no page); operators rely on this to clear gap-alert state."
        ),
    ),
    AlertRule(
        code=AlertCode.CONNECTIVITY_GAP_BACKFILLED,
        event_pattern="CONNECTIVITY_GAP_BACKFILLED",
        severity=AlertSeverity.INFO,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("connectivity_gap_backfilled"),
        description=(
            "MTDS replay/backfill closed the gap window with historical"
            " data (secondary source). Distinct from CONNECTIVITY_RECOVERED"
            " because gap is fully closed (no missing data) vs reconnected"
            " forward. Payload includes replayed_ticks_count."
        ),
    ),
    # ── Phase 1.E — venue / lending / market-data / gas / oracle kill-switch ─
    # Combined upstream + stash additions (2026-05-13):
    # Upstream: VENUE_HALTED, LENDING_POOL_PAUSED, LENDING_BORROW_CAP_REACHED,
    #   LENDING_UTILIZATION_HIGH, MARKET_DATA_STALE, GAS_PRICE_SPIKE,
    #   GAS_BUDGET_EXCEEDED, KILL_SWITCH_ORACLE_DIVERGENCE
    # Stash: adds LENDING_POOL_UNAVAILABLE, GAS_SURGE_50X, LENDING_RATE_SPIKE,
    #   GAS_MEMPOOL_CONGESTION — all codes present in codes.py closed set.
    AlertRule(
        code=AlertCode.KILL_SWITCH_ORACLE_DIVERGENCE,
        event_pattern="KILL_SWITCH_ORACLE_DIVERGENCE",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("kill_switch_oracle_divergence"),
        threshold_key="oracle_divergence_sigma",
        triggers_kill_switch=True,
        kill_switch_scope=KillSwitchScope.GLOBAL,
        description=(
            "Oracle price divergence >= 30 sigma from rolling mean (Chainlink / Pyth / TWAP)."
            " Position delta undefined at this level — GLOBAL halt until oracle recovers."
        ),
    ),
    AlertRule(
        code=AlertCode.LENDING_POOL_UNAVAILABLE,
        event_pattern="LENDING_POOL_UNAVAILABLE",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("lending_pool_unavailable"),
        threshold_key="lending_pool_outage_seconds",
        description=(
            "Chain RPC outage / network partition making lending venue unreachable"
            " for >= threshold seconds. Block all lending-venue operations."
        ),
    ),
    AlertRule(
        code=AlertCode.GAS_SURGE_50X,
        event_pattern="GAS_SURGE_50X",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("gas_surge_50x"),
        threshold_key="gas_surge_multiple",
        description=(
            "EVM gas price >= 50x rolling baseline — on-chain economics inverted."
            " Pause all tx submission; circuit-breaker KILL_ALL on-chain positions."
        ),
    ),
    AlertRule(
        code=AlertCode.VENUE_HALTED,
        event_pattern="VENUE_HALTED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("venue_halted"),
        description=(
            "Venue entered a maintenance halt or full trading suspension."
            " Operator must reroute open hedges. Distinct from"
            " VENUE_CIRCUIT_BREAKER_OPEN (execution-side) and"
            " CONNECTIVITY_GAP_DETECTED (network-level)."
        ),
    ),
    AlertRule(
        code=AlertCode.LENDING_POOL_PAUSED,
        event_pattern="LENDING_POOL_PAUSED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("lending_pool_paused"),
        description=(
            "Aave / lending pool paused by guardian or governance — new borrows"
            " and repayments blocked. Carry strategy cannot resize leverage."
        ),
    ),
    AlertRule(
        code=AlertCode.LENDING_BORROW_CAP_REACHED,
        event_pattern="LENDING_BORROW_CAP_REACHED",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("lending_borrow_cap_reached"),
        description=(
            "Lending pool borrow cap reached — no new borrows possible."
            " Repayments and liquidations still active. Pool may clear in one block."
        ),
    ),
    AlertRule(
        code=AlertCode.LENDING_UTILIZATION_HIGH,
        event_pattern="LENDING_UTILIZATION_HIGH",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("lending_utilization_high"),
        threshold_key="lending_utilization_high_bps",
        description=(
            "Lending pool utilization above threshold — early-warning before"
            " interest-rate kink at 95.00%. Complements CIRCUIT_BREAKER_OPEN."
        ),
    ),
    AlertRule(
        code=AlertCode.LENDING_RATE_SPIKE,
        event_pattern="LENDING_RATE_SPIKE",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("lending_rate_spike"),
        threshold_key="lending_rate_spike_sigma",
        description=(
            "Borrow rate >= 5 sigma from rolling mean — sudden demand surge or governance"
            " param change. Block new borrows; evaluate existing position viability."
        ),
    ),
    AlertRule(
        code=AlertCode.MARKET_DATA_STALE,
        event_pattern="MARKET_DATA_STALE",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("market_data_stale"),
        threshold_key="market_data_stale_seconds",
        description=(
            "Market-data feed stale at consuming-service layer. Broader than"
            " TICK_STALENESS (MDPS-specific); covers features-onchain / strategy"
            " detecting any stale upstream feed."
        ),
    ),
    AlertRule(
        code=AlertCode.FEED_UNHEALTHY,
        event_pattern="FEED_UNHEALTHY",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("feed_unhealthy"),
        description=(
            "Data feed health degraded — feed returning errors, stale responses,"
            " or unreachable. Criticality-tiered routing handled by"
            " alerting-service data_freshness_rules.py (critical: PD+Slack;"
            " important: Slack; informational: log only)."
        ),
    ),
    AlertRule(
        code=AlertCode.DATA_STALE,
        event_pattern="DATA_STALE",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("data_stale"),
        threshold_key="market_data_stale_seconds",
        description=(
            "Alerting-service data-staleness check failed — feed age exceeds SLA."
            " Criticality-tiered: critical/important → Slack; informational → log only."
            " Distinct from MARKET_DATA_STALE (consuming-service) and"
            " TICK_STALENESS (MDPS write-gate)."
        ),
    ),
    AlertRule(
        code=AlertCode.DATA_GAP_DETECTED,
        event_pattern="DATA_GAP_DETECTED",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("data_gap_detected"),
        description=(
            "Significant gap in a data feed — age > 2x expected cadence."
            " Distinct from CONNECTIVITY_GAP_DETECTED (MTDS upstream WS drop)."
            " Fires from alerting-service scheduled freshness check."
        ),
    ),
    AlertRule(
        code=AlertCode.GAS_PRICE_SPIKE,
        event_pattern="GAS_PRICE_SPIKE",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("gas_price_spike"),
        threshold_key="gas_price_spike_gwei",
        description=(
            "L1/L2 gas price spiked above threshold gwei — on-chain tx cost"
            " renders execution uneconomic. Strategy blocks new on-chain orders"
            " until gas falls below recovery level."
        ),
    ),
    AlertRule(
        code=AlertCode.GAS_BUDGET_EXCEEDED,
        event_pattern="GAS_BUDGET_EXCEEDED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("gas_budget_exceeded"),
        threshold_key="gas_budget_exceeded_eth",
        description=(
            "Cumulative gas spend exceeded session/daily budget — new on-chain"
            " txs blocked until operator extends budget or rotates wallet."
        ),
    ),
    AlertRule(
        code=AlertCode.GAS_MEMPOOL_CONGESTION,
        event_pattern="GAS_MEMPOOL_CONGESTION",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("gas_mempool_congestion"),
        threshold_key="gas_mempool_confirmation_delay_seconds",
        description=(
            "Tx confirmation latency p99 exceeds threshold (nonce queue backlog,"
            " blob competition). Throttle new tx submission; monitor queue drain."
        ),
    ),
    # ── Stablecoin depeg surveillance (2026-05-13, Phase D.5 + D.7) ──────────
    AlertRule(
        code=AlertCode.STABLECOIN_ISSUER_PAUSED,
        event_pattern="STABLECOIN_ISSUER_PAUSED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("stablecoin_issuer_paused"),
        description=(
            "Stablecoin issuer (Circle / Tether / MakerDAO) paused issuance/redemption."
            " Operator must evaluate depeg-ladder escalation. NOT auto-action."
        ),
    ),
    AlertRule(
        code=AlertCode.GOVERNANCE_INCIDENT_DETECTED,
        event_pattern="GOVERNANCE_INCIDENT_DETECTED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("governance_incident_detected"),
        description=(
            "Governance forum (Snapshot / Tally) posted a proposal tagged with depeg-risk keywords."
            " Operator-page only — NOT auto-action. Investigate before escalating."
        ),
    ),
    AlertRule(
        code=AlertCode.GOVERNANCE_PROPOSAL_LIVE,
        event_pattern="GOVERNANCE_PROPOSAL_LIVE",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("governance_proposal_live"),
        description=(
            "Snapshot.org governance proposal targeting DeFi protocol parameters"
            " (LTV / liquidation threshold / borrow-supply cap / IRM kink)"
            " opened in aavedao, comp-vote, or morpho space."
            " Operator-page only — NOT auto-action. Investigate before escalating."
        ),
    ),
    # ── QG / infra staleness (2026-05-15, B-018 Phase 4.A monitoring) ────────
    AlertRule(
        code=AlertCode.QG_SNAPSHOT_STALE,
        event_pattern="QG_SNAPSHOT_STALE",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("qg_snapshot_stale"),
        threshold_key="qg_snapshot_stale_days",
        description=(
            "Daily QG snapshot not written to GCS for 2+ consecutive days —"
            " qg-snapshot cron VM likely failed. Investigate"
            " deployment-service/scripts/vm/launch-qg-snapshot-vm.sh."
        ),
    ),
    # ── Batch-vs-live recon drift (batch_live_symmetry_2026_05_10 Tab 6) ────
    AlertRule(
        code=AlertCode.BATCH_VS_LIVE_RECON_DRIFTED,
        event_pattern="BATCH_VS_LIVE_RECON_DRIFTED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("batch_vs_live_recon_drifted"),
        description=(
            "T+1 batch-vs-live execution PnL delta exceeded RECON_GREEN_THRESHOLDS bps_delta_max."
            " Inspect stage3 execution recon report in the GCS recon bucket for the flagged date."
            " Emitter: batch-live-reconciliation-service post stage3."
        ),
    ),
    # ── Liquidation family (2026-05-23, drawdown_liquidation_policy Phase 4 P0.12) ──
    AlertRule(
        code=AlertCode.LIQUIDATION_RISK_IMMINENT,
        event_pattern="LIQUIDATION_RISK_IMMINENT",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM, AlertChannel.TWILIO_VOICE),
        runbook_doc=_runbook("liquidation_risk_imminent"),
        description=(
            "Predictive liquidation risk — HF / collateral ratio approaching"
            " liquidation threshold; estimated time-to-liquidation below threshold."
            " SEV0: page + voice call. Operator evaluates position reduction"
            " or collateral top-up."
        ),
    ),
    AlertRule(
        code=AlertCode.LIQUIDATION_EVENT_DETECTED,
        event_pattern="LIQUIDATION_EVENT_DETECTED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("liquidation_event_detected"),
        description=(
            "Position liquidated by venue or protocol — post-event telemetry."
            " SEV1: page + investigate. Triggers investigation report workflow."
            " Distinct from LIQUIDATION_RISK_IMMINENT (predictive) and"
            " DEFI_POSITION_LIQUIDATED (DeFi on-chain protocol-level event)."
        ),
    ),
    AlertRule(
        code=AlertCode.LIQUIDATION_INVESTIGATION_REPORT_WRITTEN,
        event_pattern="LIQUIDATION_INVESTIGATION_REPORT_WRITTEN",
        severity=AlertSeverity.INFO,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("liquidation_investigation_report_written"),
        description=(
            "Liquidation investigation report written to audit store — closes the"
            " investigation loop for a LIQUIDATION_EVENT_DETECTED. Telegram-only;"
            " operator reviews report in DART safety-ops tab."
        ),
    ),
    # ── Dependency health (2026-05-23, connectivity_dependency_buffer_policy Phase 3 P0.7) ──
    AlertRule(
        code=AlertCode.DEPENDENCY_DEGRADED,
        event_pattern="DEPENDENCY_DEGRADED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("dependency_degraded"),
        description=(
            "Dependency outage exceeded expected_recovery_time + warning_buffer."
            " Severity dynamically escalates per evaluate_dependency_health():"
            " HIGH when expected+warning exceeded; CRITICAL when"
            " hard_escalation_seconds breached or fallback_available=False."
            " Payload includes dependency_id, dependency_class, outage_seconds."
        ),
    ),
    AlertRule(
        code=AlertCode.DEPENDENCY_RECOVERED,
        event_pattern="DEPENDENCY_RECOVERED",
        severity=AlertSeverity.INFO,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("dependency_recovered"),
        description=(
            "Dependency restored after outage — closes the loop on a previously-fired"
            " DEPENDENCY_DEGRADED. Telegram-only; payload includes"
            " dependency_id, outage_seconds, recovered_at."
        ),
    ),
    # ── T4 INFO — catch-all so nothing fires silently ──────────────────────
    AlertRule(
        code=AlertCode.SERVICE_DEGRADED,  # Catch-all uses SERVICE_DEGRADED as anchor code.
        event_pattern="*",
        severity=AlertSeverity.INFO,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("service_degraded"),
        description=(
            "Catch-all for events not matched above. Nothing is silent — every event reaches at least Telegram."
        ),
    ),
)


# ---------------------------------------------------------------------------
# DATA_PIPELINE_ALERT_RULES — data-pipeline self-monitoring routing contract.
#
# Parallel to :data:`LIVE_ALERT_RULES`, but for the data-pipeline failure-mode
# registry (``codex/05-infrastructure/data-pipeline-alerts.registry.yaml``,
# ~40 DP-* modes across FETCH/COVERAGE/PATH/VM/RATE/ENV/ORDER/MANIFEST/CATALOG/
# WATCHER). The registry yaml is the HUMAN SSOT mirror; THIS tuple is the
# CONTRACT — the alerting-service router + the emitters share it (UAC does NOT
# read the yaml at runtime; the entries are transcribed here, with a closed-set
# sanity test asserting they stay in sync).
#
# The DP_* events are NOT :class:`AlertCode` members (they are a distinct,
# runtime-data-pipeline event family in UTL ``events/event_types.py``), so they
# CANNOT reuse :class:`AlertRule` (its validator requires an AlertCode-matching
# ``event_pattern``). :class:`DataPipelineAlertRule` mirrors AlertRule's field
# shape (``event_pattern → severity + channels``) and adds the registry's
# ``category`` + ``escalation`` axes.
#
# Routing (per the registry ``severity_routing`` block + the plan): every rule
# mirrors to the ``#data-pipeline-alerts`` Slack channel
# (:data:`AlertChannel.SLACK`); CRITICAL additionally pages via Telegram +
# PagerDuty (incident gateway). Plan:
# ``data_pipeline_hardening_self_monitoring_2026_06_22.md`` Phase 0.
# ---------------------------------------------------------------------------


class DataPipelineAlertCategory(StrEnum):
    """Closed set of data-pipeline failure-mode categories (registry ``category``)."""

    FETCH = "FETCH"
    COVERAGE = "COVERAGE"
    PATH = "PATH"
    VM = "VM"
    RATE = "RATE"
    ENV = "ENV"
    ORDER = "ORDER"
    MANIFEST = "MANIFEST"
    CATALOG = "CATALOG"
    WATCHER = "WATCHER"
    DIGEST = "DIGEST"


class DataPipelineEscalation(StrEnum):
    """Closed set of escalation tiers (registry ``escalation``), mirroring the
    CI-failure-watcher auto-recover-vs-escalate model."""

    AUTO_RECOVER = "auto_recover"
    FILE_ISSUE = "file_issue"
    PAGE_OPERATOR = "page_operator"


# The Slack channel token for #data-pipeline-alerts (SM webhook secret
# DATA_PIPELINE_ALERTS_SLACK_WEBHOOK). Mirrors the registry ``channel`` field.
DATA_PIPELINE_SLACK_CHANNEL: Final[str] = "data_pipeline_slack"


class DataPipelineAlertRule(BaseModel):
    """A single data-pipeline routing rule — ``event`` → severity + channels.

    Parallel to :class:`AlertRule` but for the DP-* event family, which is not
    in the closed :class:`AlertCode` set. Frozen + ``extra="forbid"`` for the
    same fail-loud discipline. ``channels`` always includes
    :data:`AlertChannel.SLACK` (the ``#data-pipeline-alerts`` mirror); CRITICAL
    rules also carry Telegram + PagerDuty per the registry severity-routing.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    registry_id: str
    """Stable ``DP-<CATEGORY>-<NNN>`` id from the registry yaml."""

    category: DataPipelineAlertCategory
    """Failure-mode category (registry ``category``)."""

    event: str
    """The DP_* event name emitters produce (registry ``event``); the router
    matches incoming event names against this exactly."""

    severity: AlertSeverity
    """CRITICAL / WARN / INFO (HIGH unused for data-pipeline)."""

    channels: tuple[AlertChannel, ...]
    """Dispatch channels. Always includes :data:`AlertChannel.SLACK` (the
    #data-pipeline-alerts mirror); CRITICAL adds Telegram + PagerDuty."""

    escalation: DataPipelineEscalation
    """Escalation tier (registry ``escalation``)."""

    @field_validator("event", "registry_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("DataPipelineAlertRule.event / registry_id must be non-empty")
        return value

    @field_validator("channels")
    @classmethod
    def _channels_include_slack(cls, value: tuple[AlertChannel, ...]) -> tuple[AlertChannel, ...]:
        if AlertChannel.SLACK not in value:
            raise ValueError(
                "DataPipelineAlertRule.channels MUST include AlertChannel.SLACK "
                "(the #data-pipeline-alerts mirror) for every rule"
            )
        return value

    @model_validator(mode="after")
    def _critical_pages(self) -> DataPipelineAlertRule:
        if self.severity is AlertSeverity.CRITICAL:
            missing = {AlertChannel.TELEGRAM, AlertChannel.PAGERDUTY} - set(self.channels)
            if missing:
                raise ValueError(
                    f"CRITICAL DataPipelineAlertRule {self.registry_id} must page "
                    f"(Telegram + PagerDuty); missing {sorted(c.value for c in missing)}"
                )
        return self


def _dp_channels(severity: AlertSeverity) -> tuple[AlertChannel, ...]:
    """Registry severity → channels: SLACK mirror always; CRITICAL also pages."""
    if severity is AlertSeverity.CRITICAL:
        return (AlertChannel.SLACK, AlertChannel.TELEGRAM, AlertChannel.PAGERDUTY)
    return (AlertChannel.SLACK,)


def _dp_rule(
    registry_id: str,
    category: DataPipelineAlertCategory,
    event: str,
    severity: AlertSeverity,
    escalation: DataPipelineEscalation,
) -> DataPipelineAlertRule:
    return DataPipelineAlertRule(
        registry_id=registry_id,
        category=category,
        event=event,
        severity=severity,
        channels=_dp_channels(severity),
        escalation=escalation,
    )


# Transcribed from data-pipeline-alerts.registry.yaml (version 1). One rule per
# `event:`. Keep IN SYNC with the yaml — the closed-set test asserts parity.
_C = DataPipelineAlertCategory
_S = AlertSeverity
_E = DataPipelineEscalation

DATA_PIPELINE_ALERT_RULES: Final[tuple[DataPipelineAlertRule, ...]] = (
    # ── DP-FETCH (class C1, keystone) ───────────────────────────────────────
    _dp_rule("DP-FETCH-001", _C.FETCH, "DP_UNPROVEN_HONEST_ABSENCE", _S.CRITICAL, _E.FILE_ISSUE),
    _dp_rule("DP-FETCH-002", _C.FETCH, "DP_AUTH_ERROR_NOT_FAILED", _S.CRITICAL, _E.FILE_ISSUE),
    _dp_rule("DP-FETCH-003", _C.FETCH, "DP_RATELIMIT_AS_EMPTY", _S.WARN, _E.AUTO_RECOVER),
    _dp_rule("DP-FETCH-004", _C.FETCH, "DP_SERVER_ERROR_AS_EMPTY", _S.CRITICAL, _E.FILE_ISSUE),
    _dp_rule("DP-FETCH-005", _C.FETCH, "DP_MISSING_CREDENTIAL", _S.CRITICAL, _E.PAGE_OPERATOR),
    _dp_rule("DP-FETCH-006", _C.FETCH, "DP_EMPTY_REPROBE_DISAGREEMENT", _S.WARN, _E.FILE_ISSUE),
    _dp_rule("DP-FETCH-007", _C.FETCH, "DP_RUN_MOSTLY_EMPTY", _S.CRITICAL, _E.PAGE_OPERATOR),
    _dp_rule("DP-FETCH-008", _C.FETCH, "DP_CATALOG_FRESH_ASSERT_FALSE", _S.CRITICAL, _E.FILE_ISSUE),
    # ── DP-COVERAGE (class C2) ──────────────────────────────────────────────
    _dp_rule("DP-COVERAGE-001", _C.COVERAGE, "DP_FAILED_BEFORE_GENESIS", _S.WARN, _E.FILE_ISSUE),
    _dp_rule("DP-COVERAGE-002", _C.COVERAGE, "DP_WRONG_ASSET_GROUP", _S.WARN, _E.FILE_ISSUE),
    _dp_rule("DP-COVERAGE-003", _C.COVERAGE, "DP_VENUE_NOT_IN_ORACLE", _S.INFO, _E.FILE_ISSUE),
    _dp_rule("DP-COVERAGE-004", _C.COVERAGE, "DP_EXPECTED_GRAIN_NONCANONICAL", _S.WARN, _E.AUTO_RECOVER),
    # ── DP-PATH (class C3) ──────────────────────────────────────────────────
    _dp_rule("DP-PATH-001", _C.PATH, "DP_NONCANONICAL_WRITE_PATH", _S.CRITICAL, _E.FILE_ISSUE),
    _dp_rule("DP-PATH-002", _C.PATH, "DP_NONCANONICAL_PATH_ON_DISK", _S.WARN, _E.FILE_ISSUE),
    _dp_rule("DP-PATH-003", _C.PATH, "DP_PIPELINE_MODE_DRIFT", _S.WARN, _E.FILE_ISSUE),
    _dp_rule("DP-PATH-004", _C.PATH, "DP_LEGACY_SPELLING", _S.WARN, _E.FILE_ISSUE),
    _dp_rule("DP-PATH-005", _C.PATH, "DP_WRONG_BUCKET", _S.CRITICAL, _E.PAGE_OPERATOR),
    # ── DP-VM (class C4) ────────────────────────────────────────────────────
    _dp_rule("DP-VM-001", _C.VM, "DP_VM_EXIT_NONZERO", _S.CRITICAL, _E.PAGE_OPERATOR),
    _dp_rule("DP-VM-002", _C.VM, "DP_VM_GONE_NO_CAPTURE", _S.CRITICAL, _E.PAGE_OPERATOR),
    _dp_rule("DP-VM-003", _C.VM, "DP_VM_STALL", _S.WARN, _E.AUTO_RECOVER),
    _dp_rule("DP-VM-004", _C.VM, "DP_EVENT_LOOP_STARVED", _S.WARN, _E.FILE_ISSUE),
    _dp_rule("DP-VM-005", _C.VM, "DP_NO_EARLY_PROGRESS", _S.INFO, _E.FILE_ISSUE),
    _dp_rule("DP-VM-006", _C.VM, "DP_GCS_429_THRASH", _S.CRITICAL, _E.AUTO_RECOVER),
    # DP-VM-007: Cloud Run job running image older than the latest Artifact Registry
    # build for its service (stale_cloud_run_image_alert_gap_2026_06_26). A job can
    # heartbeat healthily on old code with no existing alert — this closes the
    # static-property gap. WARN / FILE_ISSUE: not an immediate runtime crisis but
    # a deployment drift that must be resolved before the job is counted as "done".
    # Route: #data-pipeline-alerts (SLACK only, per WARN severity routing).
    _dp_rule("DP-VM-007", _C.VM, "DP_CLOUD_RUN_STALE_IMAGE", _S.WARN, _E.FILE_ISSUE),
    # ── DP-RATE (class C5) ──────────────────────────────────────────────────
    _dp_rule("DP-RATE-001", _C.RATE, "DP_SOURCE_RATE_LIMITED", _S.WARN, _E.AUTO_RECOVER),
    _dp_rule("DP-RATE-002", _C.RATE, "DP_KEY_POOL_EXHAUSTED", _S.CRITICAL, _E.PAGE_OPERATOR),
    # ── DP-ENV (class C6) ───────────────────────────────────────────────────
    _dp_rule("DP-ENV-001", _C.ENV, "DP_READER_WRITER_BUCKET_MISMATCH", _S.CRITICAL, _E.FILE_ISSUE),
    _dp_rule("DP-ENV-002", _C.ENV, "DP_STALENESS_BELOW_CADENCE", _S.WARN, _E.AUTO_RECOVER),
    # ── DP-ORDER (class C7) ─────────────────────────────────────────────────
    _dp_rule("DP-ORDER-001", _C.ORDER, "DP_DOWNSTREAM_BEFORE_UPSTREAM", _S.WARN, _E.FILE_ISSUE),
    _dp_rule("DP-ORDER-002", _C.ORDER, "DP_LIVE_BATCH_SCHEMA_SKEW", _S.CRITICAL, _E.FILE_ISSUE),
    _dp_rule("DP-ORDER-003", _C.ORDER, "DP_NULL_EMPTY_DOUBLE_COUNT", _S.WARN, _E.AUTO_RECOVER),
    # ── DP-MANIFEST / DP-CATALOG / DP-WATCHER (infra meta) ──────────────────
    _dp_rule("DP-MANIFEST-001", _C.MANIFEST, "CONSOLIDATOR_DOWN", _S.CRITICAL, _E.AUTO_RECOVER),
    _dp_rule("DP-MANIFEST-002", _C.MANIFEST, "DP_NOT_V9", _S.WARN, _E.FILE_ISSUE),
    _dp_rule("DP-MANIFEST-003", _C.MANIFEST, "DP_PHANTOM_ROWS", _S.WARN, _E.FILE_ISSUE),
    _dp_rule("DP-MANIFEST-004", _C.MANIFEST, "DP_DIVERGENT_EMPTY", _S.WARN, _E.FILE_ISSUE),
    _dp_rule("DP-MANIFEST-005", _C.MANIFEST, "DP_SHARD_PILLAR_FAIL", _S.WARN, _E.FILE_ISSUE),
    _dp_rule("DP-CATALOG-001", _C.CATALOG, "DP_CATALOG_NOT_RUNNING", _S.CRITICAL, _E.PAGE_OPERATOR),
    _dp_rule("DP-WATCHER-001", _C.WATCHER, "DP_ZOMBIE_WATCHDOG_DOWN", _S.CRITICAL, _E.PAGE_OPERATOR),
    _dp_rule("DP-WATCHER-002", _C.WATCHER, "DP_CRON_DID_NOT_FIRE", _S.CRITICAL, _E.PAGE_OPERATOR),
    # ── DP-DIGEST (daily summaries, INFO) ───────────────────────────────────
    _dp_rule("DP-DIGEST-001", _C.DIGEST, "DP_DAILY_DIGEST", _S.INFO, _E.FILE_ISSUE),
    _dp_rule("DP-DIGEST-002", _C.DIGEST, "DP_HYGIENE_SUMMARY", _S.INFO, _E.FILE_ISSUE),
)
