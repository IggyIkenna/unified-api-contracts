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

from .codes import ALERT_CODES, AlertChannel, AlertCode, AlertSeverity
from .thresholds import ALERT_THRESHOLDS


class UnknownAlertCodeError(ValueError):
    """Raised when an :class:`AlertRule` pattern matches no :class:`AlertCode`."""


class UnknownThresholdKeyError(ValueError):
    """Raised when an :class:`AlertRule.threshold_key` is not in :data:`ALERT_THRESHOLDS`."""


class AlertRule(BaseModel):
    """A single routing rule — pattern → severity + channels (+ optional kill-switch).

    The ``pattern`` is fnmatch-style (e.g. ``"KILL_SWITCH_*"``) and is matched
    against incoming event names. At least one :class:`AlertCode` member must
    match the pattern, otherwise the rule is dead and a stale risk —
    :meth:`_validate_pattern_matches_codes` catches this at construction.

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

    pattern: str
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

    description: str = Field(default="")
    """One-line operator-facing description; rendered alongside the badge
    in DART. Keep concise."""

    @field_validator("pattern")
    @classmethod
    def _pattern_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("AlertRule.pattern must be a non-empty fnmatch pattern")
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
    def _validate_pattern_matches_codes(self) -> AlertRule:
        if self.pattern == "*":
            # Catch-all is allowed and intentional — matches every code.
            return self
        matched = [c for c in ALERT_CODES if fnmatch.fnmatchcase(c, self.pattern)]
        if not matched:
            raise UnknownAlertCodeError(
                f"AlertRule.pattern={self.pattern!r} matches no AlertCode member (closed set: {sorted(ALERT_CODES)})"
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

    def to_routing_dict(self) -> dict[str, object]:
        """Render to the legacy routing-rule shape consumed by alerting-service.

        Bridge for Phase 2 migration: ``alerting-service/config.py``'s
        ``_default_routing_rules`` factory becomes
        ``[rule.to_routing_dict() for rule in LIVE_ALERT_RULES]`` —
        byte-equivalent output, single SSOT.
        """
        return {
            "event_pattern": self.pattern,
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


_RUNBOOK_BASE: Final[str] = "unified-trading-pm/codex/14-playbooks/alerting"


def _runbook(slug: str) -> str:
    return f"{_RUNBOOK_BASE}/{slug}.md"


LIVE_ALERT_RULES: Final[tuple[AlertRule, ...]] = (
    # ── T1 CRITICAL — page now, kill-switch-fire family ─────────────────────
    # Single wildcard rule preserves byte-equivalence with the legacy
    # `KILL_SWITCH_*` routing entry. The ``code`` field anchors at the
    # liquidation-risk variant for runbook + threshold deep-link; the
    # AlertCode enum still enumerates all three KILL_SWITCH_* codes for
    # type-safe emitter use.
    AlertRule(
        code=AlertCode.KILL_SWITCH_DEFI_LIQUIDATION_RISK,
        pattern="KILL_SWITCH_*",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("kill_switch"),
        threshold_key="defi_health_factor_critical",
        triggers_kill_switch=True,
        description=(
            "Kill-switch family — DEFI_LIQUIDATION_RISK / PORTFOLIO_DRAWDOWN /"
            " VENUE_DISCONNECT all halt downstream subscribers + page on-call."
        ),
    ),
    # ── T1 CRITICAL — circuit + multi-leg ───────────────────────────────────
    AlertRule(
        code=AlertCode.CIRCUIT_BREAKER_OPEN,
        pattern="CIRCUIT_BREAKER_OPEN",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("circuit_breaker_open"),
        description="Per-(service,venue) circuit transitioned to OPEN — venue health degraded.",
    ),
    AlertRule(
        code=AlertCode.UNHEDGED_POSITION_ALERT,
        pattern="UNHEDGED_POSITION_ALERT",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("unhedged_position_alert"),
        description="Multi-leg partial fill — unhedged position detected.",
    ),
    AlertRule(
        code=AlertCode.MULTI_LEG_COMPENSATION_FAILED,
        pattern="MULTI_LEG_COMPENSATION_FAILED",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("multi_leg_compensation_failed"),
        description="Compensation trade failed — unhedged + circuit breaker fired.",
    ),
    AlertRule(
        code=AlertCode.DUAL_FAILURE_DETECTED,
        pattern="DUAL_FAILURE_DETECTED",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("dual_failure_detected"),
        description="Dual failure — can't reconcile AND can't execute.",
    ),
    AlertRule(
        code=AlertCode.ORDER_RECOVERY_FAILED,
        pattern="ORDER_RECOVERY_FAILED",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("order_recovery_failed"),
        description="Orphaned orders unresolvable — manual operator intervention required.",
    ),
    AlertRule(
        code=AlertCode.SERVICE_ERROR_CRITICAL,
        pattern="SERVICE_ERROR_CRITICAL",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("service_error_critical"),
        description="Service-level critical error — page on-call.",
    ),
    # ── T1 CRITICAL — DeFi P0 ──────────────────────────────────────────────
    AlertRule(
        code=AlertCode.DEFI_HEALTH_FACTOR_CRITICAL,
        pattern="DEFI_HEALTH_FACTOR_CRITICAL",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("defi_health_factor_critical"),
        threshold_key="defi_health_factor_critical",
        description="Aave health factor approaching liquidation — page on-call + auto-deleverage candidate.",
    ),
    AlertRule(
        code=AlertCode.DEFI_WEETH_DEPEG,
        pattern="DEFI_WEETH_DEPEG",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("defi_weeth_depeg"),
        threshold_key="defi_weeth_depeg_bps",
        description="weETH/ETH peg deviation exceeds tolerance — page + reduce LST exposure.",
    ),
    AlertRule(
        code=AlertCode.DEFI_POSITION_LIQUIDATED,
        pattern="DEFI_POSITION_LIQUIDATED",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("defi_position_liquidated"),
        description="Confirmed on-chain liquidation event — page + post-mortem trigger.",
    ),
    AlertRule(
        code=AlertCode.DEFI_RATE_DEVIATION,
        pattern="DEFI_RATE_DEVIATION",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("defi_rate_deviation"),
        description="Oracle/DEX rate divergence — page; possible MEV / oracle stale.",
    ),
    # ── T1 CRITICAL — margin ────────────────────────────────────────────────
    AlertRule(
        code=AlertCode.MARGIN_LIQUIDATION,
        pattern="MARGIN_LIQUIDATION",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("margin_liquidation"),
        description="Margin liquidation event from PBM canonical ladder.",
    ),
    AlertRule(
        code=AlertCode.MARGIN_CRITICAL,
        pattern="MARGIN_CRITICAL",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("margin_critical"),
        description="Margin critical band — page on-call.",
    ),
    # ── T2 HIGH — Telegram + PagerDuty P2 ───────────────────────────────────
    AlertRule(
        code=AlertCode.CIRCUIT_BREAKER_BACKOFF_ESCALATING,
        pattern="CIRCUIT_BREAKER_BACKOFF_*",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("circuit_breaker_backoff"),
        description="Repeated recovery failure — backoff schedule escalating.",
    ),
    AlertRule(
        code=AlertCode.ORDER_ORPHANED,
        pattern="ORDER_ORPHANED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("order_orphaned"),
        description="Orphaned order found during startup recovery.",
    ),
    AlertRule(
        code=AlertCode.POSITION_DRIFT_DETECTED,
        pattern="POSITION_DRIFT_DETECTED",
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
        pattern="RECON_DEGRADED_*",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("recon_degraded"),
        description="Closing positions without verified reconciliation state.",
    ),
    AlertRule(
        code=AlertCode.POSITION_CRITICAL_DISCREPANCY,
        pattern="POSITION_CRITICAL_DISCREPANCY",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("position_critical_discrepancy"),
        description="Position discrepancy large enough to escalate.",
    ),
    AlertRule(
        code=AlertCode.MARGIN_WARNING,
        pattern="MARGIN_WARNING",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("margin_warning"),
        description="Margin warning band — on-call sees drift before critical.",
    ),
    AlertRule(
        code=AlertCode.MARGIN_THRESHOLD_BREACH,
        pattern="MARGIN_THRESHOLD_BREACH",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("margin_threshold_breach"),
        threshold_key="margin_threshold_breach_bps",
        description="Within initial-margin-call buffer — pre-emptive notify.",
    ),
    AlertRule(
        code=AlertCode.CROSS_CLOUD_EGRESS_DETECTED,
        pattern="CROSS_CLOUD_EGRESS_DETECTED",
        severity=AlertSeverity.HIGH,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        runbook_doc=_runbook("cross_cloud_egress_detected"),
        threshold_key="cross_cloud_egress_bytes_per_request",
        description=(
            "Data-locality bug — UI/API in cloud A reading data from cloud B"
            " above per-request budget. Audit 2026-05-07 dual-cloud-active policy."
        ),
    ),
    # ── T3 WARN — Telegram only ─────────────────────────────────────────────
    AlertRule(
        code=AlertCode.CIRCUIT_BREAKER_DEGRADED,
        pattern="CIRCUIT_BREAKER_DEGRADED",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("circuit_breaker_degraded"),
        description="Circuit breaker throttling — venue health declining.",
    ),
    AlertRule(
        code=AlertCode.CIRCUIT_BREAKER_CLOSED,
        pattern="CIRCUIT_BREAKER_CLOSED",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("circuit_breaker_closed"),
        description="Circuit breaker recovered.",
    ),
    AlertRule(
        code=AlertCode.SERVICE_ERROR,
        pattern="SERVICE_ERROR",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("service_error"),
        description="Service-level non-critical error.",
    ),
    AlertRule(
        code=AlertCode.PREFLIGHT_FAILED,
        pattern="PREFLIGHT_FAILED",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("preflight_failed"),
        description="Preflight check failed — order rejected before submission.",
    ),
    AlertRule(
        code=AlertCode.SERVICE_DEGRADED,
        pattern="SERVICE_DEGRADED",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("service_degraded"),
        description="Service running but degraded mode active.",
    ),
    AlertRule(
        code=AlertCode.POSITION_CORRECTION_DISPATCHED,
        pattern="POSITION_CORRECTION_*",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("position_correction"),
        description="Auto-correction dispatched by reconciliation.",
    ),
    AlertRule(
        code=AlertCode.PORTFOLIO_REBALANCE_TRIGGERED,
        pattern="PORTFOLIO_REBALANCE_*",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("portfolio_rebalance"),
        description="Portfolio rebalancing triggered by drift.",
    ),
    AlertRule(
        code=AlertCode.ORDER_RECOVERY_INITIATED,
        pattern="ORDER_RECOVERY_*",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("order_recovery"),
        description="Order recovery lifecycle (initiated, completed).",
    ),
    AlertRule(
        code=AlertCode.DEFI_AAVE_UTILIZATION_SPIKE,
        pattern="DEFI_AAVE_UTILIZATION_SPIKE",
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
        pattern="DEFI_FUNDING_RATE_FLIP",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("defi_funding_rate_flip"),
        threshold_key="defi_funding_rate_flip_bps_5m",
        description="Perp funding rate flipped sign — possible regime change.",
    ),
    AlertRule(
        code=AlertCode.DEFI_FEATURE_STALE,
        pattern="DEFI_FEATURE_STALE",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("defi_feature_stale"),
        threshold_key="defi_feature_stale_minutes",
        description="DeFi LST yield read freshness exceeded SLA.",
    ),
    AlertRule(
        code=AlertCode.DEFI_TX_SIMULATION_FAILED,
        pattern="DEFI_TX_SIMULATION_FAILED",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("defi_tx_simulation_failed"),
        description="Tenderly tx simulation rejected — order would revert on chain.",
    ),
    AlertRule(
        code=AlertCode.BALANCE_DRIFT,
        pattern="BALANCE_DRIFT",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("balance_drift"),
        threshold_key="balance_drift_usd",
        description="Wallet balance drift vs expected ledger state.",
    ),
    AlertRule(
        code=AlertCode.ORDER_REJECTION_SPIKE,
        pattern="ORDER_REJECTION_SPIKE",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("order_rejection_spike"),
        threshold_key="order_rejection_spike_per_min",
        description="Sustained spike in order rejects — venue health degraded.",
    ),
    AlertRule(
        code=AlertCode.POSITION_DRIFT,
        pattern="POSITION_DRIFT",
        severity=AlertSeverity.WARN,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("position_drift"),
        threshold_key="position_drift_bps",
        description="Position drift from target exceeds rebalance threshold.",
    ),
    # ── T4 INFO — catch-all so nothing fires silently ──────────────────────
    AlertRule(
        code=AlertCode.SERVICE_DEGRADED,  # Catch-all uses SERVICE_DEGRADED as anchor code.
        pattern="*",
        severity=AlertSeverity.INFO,
        channels=(AlertChannel.TELEGRAM,),
        runbook_doc=_runbook("service_degraded"),
        description=(
            "Catch-all for events not matched above. Nothing is silent — every event reaches at least Telegram."
        ),
    ),
)
