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
                f"AlertRule.event_pattern={self.event_pattern!r} matches no AlertCode member (closed set: {sorted(ALERT_CODES)})"
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
