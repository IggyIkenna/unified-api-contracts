"""Closed-set AlertCode + AlertSeverity + AlertChannel taxonomy.

`AlertCode` is the workspace SSOT for what alert names emitters may produce.
Mirrors the `EmptyConfirmedReason` / `LifecycleEventType` / `PreflightSkipReason`
discipline — emitting a code outside the enum is a programming error caught at
type-check time (StrEnum) AND at runtime via `LIVE_ALERT_RULES` validation.

Severity is the orderable paging-tier axis; channel is the dispatch axis. Both
are orthogonal to AlertCode. The legacy `severity_filter` field in
`alerting-service/alerting_service/config.py` (`"critical"` / `"warning"` /
None) maps to AlertSeverity via `AlertSeverity.to_legacy_filter()` so the
notifier dispatchers don't need migrating in Phase 1.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class AlertCode(StrEnum):
    """Closed set of alert codes the alerting-service may route.

    Adding a new code requires (1) appending here, (2) adding an `AlertRule`
    in `live_rules.LIVE_ALERT_RULES`, (3) writing the operator playbook entry
    under `unified-trading-pm/codex/14-playbooks/alerting/`, and (4) including
    the code in the next quarterly rehearsal scope. The closed-set sanity
    test in `tests/internal/unit/test_alerting_taxonomy.py` enforces (1) ↔ (2).
    """

    # ── Kill-switch family (CRITICAL — page now + halt downstream subscribers)
    KILL_SWITCH_DEFI_LIQUIDATION_RISK = "KILL_SWITCH_DEFI_LIQUIDATION_RISK"
    KILL_SWITCH_PORTFOLIO_DRAWDOWN = "KILL_SWITCH_PORTFOLIO_DRAWDOWN"
    KILL_SWITCH_VENUE_DISCONNECT = "KILL_SWITCH_VENUE_DISCONNECT"

    # ── Circuit-breaker lifecycle
    CIRCUIT_BREAKER_OPEN = "CIRCUIT_BREAKER_OPEN"
    CIRCUIT_BREAKER_DEGRADED = "CIRCUIT_BREAKER_DEGRADED"
    CIRCUIT_BREAKER_CLOSED = "CIRCUIT_BREAKER_CLOSED"
    CIRCUIT_BREAKER_BACKOFF_ESCALATING = "CIRCUIT_BREAKER_BACKOFF_ESCALATING"

    # ── DeFi-specific (matches DefiAlertType for emitter parity)
    DEFI_HEALTH_FACTOR_CRITICAL = "DEFI_HEALTH_FACTOR_CRITICAL"
    DEFI_WEETH_DEPEG = "DEFI_WEETH_DEPEG"
    DEFI_AAVE_UTILIZATION_SPIKE = "DEFI_AAVE_UTILIZATION_SPIKE"
    DEFI_FUNDING_RATE_FLIP = "DEFI_FUNDING_RATE_FLIP"
    DEFI_FEATURE_STALE = "DEFI_FEATURE_STALE"
    DEFI_POSITION_LIQUIDATED = "DEFI_POSITION_LIQUIDATED"
    DEFI_RATE_DEVIATION = "DEFI_RATE_DEVIATION"
    DEFI_TX_SIMULATION_FAILED = "DEFI_TX_SIMULATION_FAILED"

    # ── Margin ladder (PBM-canonical, thresholds from UAC LIQUIDATION_PARAMS_REGISTRY)
    MARGIN_LIQUIDATION = "MARGIN_LIQUIDATION"
    MARGIN_CRITICAL = "MARGIN_CRITICAL"
    MARGIN_WARNING = "MARGIN_WARNING"
    MARGIN_THRESHOLD_BREACH = "MARGIN_THRESHOLD_BREACH"

    # ── Position / reconciliation
    POSITION_DRIFT = "POSITION_DRIFT"
    POSITION_DRIFT_DETECTED = "POSITION_DRIFT_DETECTED"
    POSITION_CRITICAL_DISCREPANCY = "POSITION_CRITICAL_DISCREPANCY"
    POSITION_CORRECTION_DISPATCHED = "POSITION_CORRECTION_DISPATCHED"
    PORTFOLIO_REBALANCE_TRIGGERED = "PORTFOLIO_REBALANCE_TRIGGERED"
    BALANCE_DRIFT = "BALANCE_DRIFT"
    RECON_DEGRADED = "RECON_DEGRADED"

    # ── Order / execution health
    ORDER_REJECTION_SPIKE = "ORDER_REJECTION_SPIKE"
    ORDER_ORPHANED = "ORDER_ORPHANED"
    ORDER_RECOVERY_INITIATED = "ORDER_RECOVERY_INITIATED"
    ORDER_RECOVERY_COMPLETED = "ORDER_RECOVERY_COMPLETED"
    ORDER_RECOVERY_FAILED = "ORDER_RECOVERY_FAILED"

    # ── Multi-leg execution risk
    UNHEDGED_POSITION_ALERT = "UNHEDGED_POSITION_ALERT"
    MULTI_LEG_COMPENSATION_FAILED = "MULTI_LEG_COMPENSATION_FAILED"
    DUAL_FAILURE_DETECTED = "DUAL_FAILURE_DETECTED"

    # ── Service health
    SERVICE_ERROR = "SERVICE_ERROR"
    SERVICE_ERROR_CRITICAL = "SERVICE_ERROR_CRITICAL"
    SERVICE_DEGRADED = "SERVICE_DEGRADED"
    PREFLIGHT_FAILED = "PREFLIGHT_FAILED"

    # ── Cross-cloud / data-locality safety net (audit 2026-05-07: dual-cloud
    # active policy means a UI in one cloud reading data from the other is a
    # bug; alerting catches it).
    CROSS_CLOUD_EGRESS_DETECTED = "CROSS_CLOUD_EGRESS_DETECTED"


ALERT_CODES: Final[frozenset[str]] = frozenset(member.value for member in AlertCode)
"""String-membership view of :class:`AlertCode` for fast O(1) validation.

Mirrors `EMPTY_CONFIRMED_REASONS`. Use enum members in new code; this set is
for the validation hot path only.
"""


class AlertSeverity(StrEnum):
    """Orderable severity tier — drives paging behaviour.

    - ``CRITICAL`` — page now (PagerDuty P1), 24/7 SLA.
    - ``HIGH`` — page within SLA (PagerDuty P2 / "warning"), business-hours OK.
    - ``WARN`` — notify (Telegram only), no page.
    - ``INFO`` — log only / dashboard signal.
    """

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    WARN = "WARN"
    INFO = "INFO"

    def to_legacy_filter(self) -> str | None:
        """Map to the legacy `severity_filter` field in alerting-service.

        Existing dispatchers consume the legacy string (`"critical"` /
        `"warning"` / None). Once Phase 5 (DART) ships and dispatchers move
        to typed `AlertSeverity` consumption, this helper can be deleted.
        """
        if self is AlertSeverity.CRITICAL:
            return "critical"
        if self is AlertSeverity.HIGH:
            return "warning"
        return None


class AlertChannel(StrEnum):
    """Dispatch channels available to AlertRule routing."""

    PAGERDUTY = "pagerduty"
    TELEGRAM = "telegram"
    SLACK = "slack"
    EMAIL = "email"
    LOG_ONLY = "log_only"
