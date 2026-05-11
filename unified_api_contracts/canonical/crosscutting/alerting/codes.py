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
    under `unified-trading-pm/codex/15-runbooks/alerting/`, and (4) including
    the code in the next quarterly rehearsal scope. The closed-set sanity
    test in `tests/internal/unit/test_alerting_taxonomy.py` enforces (1) ↔ (2).
    """

    # ── Kill-switch family (CRITICAL — page now + halt downstream subscribers)
    KILL_SWITCH_DEFI_LIQUIDATION_RISK = "KILL_SWITCH_DEFI_LIQUIDATION_RISK"
    KILL_SWITCH_PORTFOLIO_DRAWDOWN = "KILL_SWITCH_PORTFOLIO_DRAWDOWN"
    KILL_SWITCH_VENUE_DISCONNECT = "KILL_SWITCH_VENUE_DISCONNECT"
    KILL_SWITCH_ML_MODEL_FAILURE = "KILL_SWITCH_ML_MODEL_FAILURE"
    """Kill-switch — model server unreachable / repeated inference failures /
    unrecoverable model-version mismatch. Halts the affected archetype until
    model server recovers or operator overrides. Added 2026-05-08 for
    `cefi_ml_may_23_2026.epic` ML kill-switch coverage."""

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
    RECON_DEGRADED_CLOSE = "RECON_DEGRADED_CLOSE"
    """Reconciliation degraded — closing positions without verified state.
    Mirrors the UTL ``RECON_DEGRADED_CLOSE`` lifecycle event emitted by
    position-balance-monitor + risk-and-exposure-service."""

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

    # ── ML lifecycle (2026-05-08, cefi_ml_may_23_2026.epic Tab 5 Item 6) ────
    # Live-ML signal staleness / drift / P&L deviation / inference latency /
    # model-version mismatch. Producers: ml-inference-service (signal +
    # latency + version); strategy-service (P&L deviation per archetype);
    # ml-training-service (drift via PSI vs training-baseline distributions).
    ML_SIGNAL_STALENESS = "ML_SIGNAL_STALENESS"
    """ML signal hasn't refreshed within the freshness window. Default 5min
    per `ml_signal_staleness_minutes`; per-archetype overrides allowed."""
    ML_MODEL_DRIFT_DETECTED = "ML_MODEL_DRIFT_DETECTED"
    """Model output distribution drifts from training baseline (Population
    Stability Index ≥ threshold). Page-worthy — model may be stale or
    feature inputs may have shifted regime."""
    ML_PNL_DEVIATION = "ML_PNL_DEVIATION"
    """Live strategy P&L deviates from expected by more than the bps
    threshold. Either model is wrong or execution is degraded; in either
    case, page on-call to investigate before drawdown compounds."""
    ML_INFERENCE_LATENCY_BREACH = "ML_INFERENCE_LATENCY_BREACH"
    """Inference SLO breached (p99 > threshold ms). WARN-level — model
    server still serving but slower than expected; investigate before it
    escalates to staleness."""
    ML_MODEL_VERSION_MISMATCH = "ML_MODEL_VERSION_MISMATCH"
    """Strategy executing against unexpected model version (artefact
    rollback / promotion race / hot-reload mis-fire). CRITICAL — every
    trade until resolved is on a model the operator did not approve."""

    # ── Risk-rule taxonomy (2026-05-10, risk_simulations_limits_alerting Phase
    # 1.E + cross-plan audit Q6 Policy B "larger-set-wins"). Each
    # ``RiskRuleConsequence`` value gets a dedicated AlertCode so the alerting
    # routing layer can apply per-consequence severity + per-consequence
    # channels (e.g. BLOCK pages; SCALE_DOWN dashboards; MONITOR + TEST_ONLY
    # log-only). The corresponding LIVE_ALERT_RULES entries are seeded by the
    # master coordinator after Sub-A's ``event_pattern`` rename lands
    # (UAC@0b61aec). Producers: risk-and-exposure-service ``rule_evaluator``.
    # SSOT seam: ``plans/active/risk_simulations_limits_alerting_2026_05_10.md``
    # § "§ 7 SSOT reconciliation seam (Framing 1)" cross-product table.
    RISK_RULE_BLOCKED = "RISK_RULE_BLOCKED"
    """A risk rule fired with ``RiskRuleConsequence.BLOCK`` — instruction
    rejected pre-flight before reaching the venue. Severity per
    ``RiskRule.alerting_severity`` (typically HIGH or CRITICAL). Distinct from
    generic ``PREFLIGHT_FAILED`` which fires for pre-flight checks NOT routed
    through the rule engine (e.g. instrument-not-listed, kill-switch already
    engaged). When N consecutive BLOCKs on the same ``(venue, asset_group)``
    accumulate, the breaker may escalate per
    ``RISK_TO_BREAKER_ESCALATION_MAP`` — that emits
    ``CIRCUIT_BREAKER_DEGRADED`` / ``CIRCUIT_BREAKER_OPEN`` separately."""
    RISK_RULE_SCALED_DOWN = "RISK_RULE_SCALED_DOWN"
    """A risk rule fired with ``RiskRuleConsequence.SCALE_DOWN`` — instruction
    accepted with a size-adjustment multiplier (e.g. position-size cap halves
    the order). Severity typically WARN. Does NOT trigger kill-switch or
    circuit-breaker — instruction proceeds at reduced size, downstream P&L
    reflects the scaled fill."""
    RISK_RULE_MONITOR_FIRED = "RISK_RULE_MONITOR_FIRED"
    """A risk rule fired with ``RiskRuleConsequence.MONITOR`` — instruction
    accepted unchanged; rule fire is advisory (dashboard signal / log entry).
    Severity typically INFO or WARN. Never triggers kill-switch or
    circuit-breaker. Used for tripwire rules where the team wants visibility
    before tightening to BLOCK / SCALE_DOWN."""
    RISK_RULE_TEST_ONLY_ROUTED = "RISK_RULE_TEST_ONLY_ROUTED"
    """A risk rule fired with ``RiskRuleConsequence.TEST_ONLY`` — instruction
    diverted to the matching engine instead of the live venue (no live fills
    produced). Severity INFO. Used for shadow-mode rules where strategy +
    execution exercise the full path but no capital is at risk. Distinct from
    venue-side circuit-breaker route (which is post-error)."""

    # ── Kill-switch recovery (2026-05-10, risk_simulations_limits_alerting
    # Phase 1.F + DR plan Phase 1.A). Distinct events per Policy B (the
    # kill-switch supports BOTH manual-unkill AND auto-cooldown recovery
    # modes per ``BREAKER_RECOVERY_DEFAULTS`` per-action defaults). Distinct
    # codes so dashboards can show "auto-recovered vs operator-unkilled"
    # separately, and so operator-attention auditing distinguishes the two.
    # Producers: execution-service breaker / risk-and-exposure-service
    # kill-switch on transition out of armed state.
    KILL_SWITCH_AUTO_RECOVERED = "KILL_SWITCH_AUTO_RECOVERED"
    """Kill-switch transitioned from armed to inactive via the auto-cooldown
    path (metric cleared + ``cooldown_seconds`` elapsed). Severity INFO.
    Fires once per recovery transition. The ``BREAKER_RECOVERY_DEFAULTS``
    dict in ``unified_api_contracts.canonical.crosscutting.circuit_breaker``
    declares which ``BreakerAction`` values auto-recover (default:
    ``BLOCK_NEW`` + ``SCALE_DOWN``)."""
    KILL_SWITCH_MANUAL_UNKILLED = "KILL_SWITCH_MANUAL_UNKILLED"
    """Kill-switch transitioned from armed to inactive via operator manual
    unkill (DART unkill button + reason text). Severity INFO. Fires once per
    recovery transition. Default for ``BreakerAction.CANCEL_OPEN`` +
    ``BreakerAction.KILL_ALL`` per ``BREAKER_RECOVERY_DEFAULTS`` —
    operator sign-off required because cancelled / fully-unwound positions
    don't have a natural auto-restore semantic."""

    # ── Tick-staleness + connectivity-gap event taxonomy (2026-05-11 —
    # alerting_service_live_rules_2026_05_07 § "Tick-staleness +
    # connectivity-gap event taxonomy"). Complementary signals:
    # downstream-detected staleness (MDPS) vs upstream-detected gap (MTDS).
    # Recovery + backfill events round out the lifecycle so operators see
    # the full picture rather than orphan "fired-but-never-cleared" alerts.
    # The 30s coalesce window keyed on (venue, instrument) in
    # ``alerting-service/notifiers/router.py`` merges concurrent
    # TICK_STALENESS + CONNECTIVITY_GAP_DETECTED fires for the same
    # (venue, instrument, time-window) into ONE operator-visible alert.
    TICK_STALENESS = "TICK_STALENESS"
    """MDPS downstream-detected staleness — last tick for the (venue,
    instrument) is older than the configured ``tick_staleness_seconds``
    threshold (default 300s). Payload includes ``venue``, ``instrument``,
    ``baseline_seconds`` (expected inter-tick gap from baseline), ``actual_seconds``
    (observed gap), ``last_received_at`` (ISO timestamp). Severity HIGH —
    operator visibility, paged at PagerDuty P2 when ``actual_seconds`` > 5min.
    Emitter: MDPS write-gate consultation against per-venue baseline."""
    CONNECTIVITY_GAP_DETECTED = "CONNECTIVITY_GAP_DETECTED"
    """MTDS upstream-detected connectivity gap — websocket subscription
    dropped + reconnect in progress, or heartbeat-staleness threshold
    crossed per-venue (per ``venue_thresholds.py``). Payload includes
    ``venue``, ``instrument``, ``gap_window_start`` (ISO timestamp of last
    successful heartbeat), ``last_received_at``. Severity HIGH —
    operator visibility, paged at PagerDuty P2. Emitter:
    MTDS ``LiveConnectivityWatchdog``."""
    CONNECTIVITY_RECOVERED = "CONNECTIVITY_RECOVERED"
    """MTDS upstream connectivity restored — websocket reconnected +
    heartbeats resumed. Payload includes ``venue``, ``instrument``,
    ``gap_window_start`` (carry-forward from the original
    ``CONNECTIVITY_GAP_DETECTED`` event), ``recovered_at`` (ISO timestamp).
    Severity INFO — recovery event, Telegram-only (no page). Operators
    rely on this to close the loop on a previously-fired gap alert."""
    CONNECTIVITY_GAP_BACKFILLED = "CONNECTIVITY_GAP_BACKFILLED"
    """MTDS replay/backfill closed the connectivity gap with historical
    data — the gap window was retrofilled from a secondary source (REST
    poll / archive replay). Payload includes ``venue``, ``instrument``,
    ``gap_window_start``, ``recovered_at``, ``replayed_ticks_count`` (number
    of historical ticks loaded). Severity INFO — recovery event,
    Telegram-only (no page). Distinct from ``CONNECTIVITY_RECOVERED``
    because the gap is now *fully* closed (no missing data), not just
    reconnected forward."""


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


class KillSwitchScope(StrEnum):
    """Scope at which a kill-switch fires.

    Canonical layer SSOT (was at ``internal/domain/deployment_service/isolation.py``;
    moved here 2026-05-08 so canonical AlertRule can carry a per-rule
    ``kill_switch_scope`` field without a circular import). The internal-layer
    location now imports the canonical symbol so prior call sites
    (``unified_api_contracts.internal.KillSwitchScope``) keep resolving.

    - ``GLOBAL`` — halt the entire platform (human operator only).
    - ``CLIENT`` — halt all activity for one client.
    - ``VENUE`` — halt all orders to one venue.
    - ``STRATEGY`` — halt one strategy_id.
    - ``ARCHETYPE`` — halt all strategies of one archetype.
    - ``INSTRUMENT`` — halt one symbol.
    """

    GLOBAL = "global"
    CLIENT = "client"
    VENUE = "venue"
    STRATEGY = "strategy"
    ARCHETYPE = "archetype"
    INSTRUMENT = "instrument"
