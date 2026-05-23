"""Per-dependency health policy — 5-class taxonomy + expected_time + buffer model.

Codifies ``disaster_recovery.md`` §10. The alerting-service Incident Gateway
evaluates dependency health against this policy and emits SEV1 / SEV0 per
the elapsed-time-vs-buffer rule.

Codex SSOT: implementation plan
``plans/active/connectivity_dependency_buffer_policy_2026_05_23.md``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class DependencyClass(StrEnum):
    """Closed set of 5 dependency criticality classes."""

    EXECUTION_CRITICAL_EXTERNAL = "EXECUTION_CRITICAL_EXTERNAL"
    """Exchange REST + WS, broker APIs, custody/wallet infrastructure, order
    gateways. Outage stops trading."""

    MARKET_DATA_CRITICAL_EXTERNAL = "MARKET_DATA_CRITICAL_EXTERNAL"
    """Primary + backup market data feeds, venue order book streams, index /
    mark price feeds."""

    INTERNAL_CONTROL_PLANE = "INTERNAL_CONTROL_PLANE"
    """Cloud Run / GKE / control plane, deployment system, config registry,
    secrets manager, feature flag service, agent orchestration."""

    INTERNAL_DATA_PLANE = "INTERNAL_DATA_PLANE"
    """PubSub / Kafka / Redis streams, databases, BigQuery / GCS sinks,
    feature stores, ledgers, reconciliation stores."""

    ALERTING_AND_OBSERVABILITY = "ALERTING_AND_OBSERVABILITY"
    """Primary incident provider (PagerDuty), Telegram, Twilio fallback,
    logging backend, metrics backend, tracing backend."""


class DependencyHealthPolicy(BaseModel):
    """Per-dependency health policy.

    The alerting-service ``evaluate_dependency_health(dependency_id,
    current_outage_seconds)`` function reads this policy and returns the
    AlertSeverity to fire (or None for "no alert").

    Escalation ladder (outage_seconds, evaluated greatest-first):

    - outage > hard_escalation_seconds OR fallback_available=False → SEV0
    - outage > warning_buffer_seconds + human_investigation_buffer_seconds → SEV1
    - outage > expected_recovery_time_seconds → WARN (Slack only)
    - outage <= expected_recovery_time_seconds → None (no alert)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    dependency_id: str
    """Stable identifier — matches the ``LIVE_ALERT_RULES`` event_pattern
    scope_key. e.g. 'binance_rest', 'helius_solana_rpc', 'gcp_pubsub'."""

    dependency_class: DependencyClass

    expected_recovery_time_seconds: int
    """Below this, no alert. Vendor-specific normal recovery time."""

    warning_buffer_seconds: int = 60
    """Slack-only warning fires when outage exceeds expected + this buffer."""

    human_investigation_buffer_seconds: int = 900
    """SEV1 (human investigation) fires when outage exceeds expected +
    warning + this buffer. Default 15 minutes per ``disaster_recovery.md`` §10."""

    hard_escalation_seconds: int
    """SEV0 fires when outage exceeds this (regardless of intervening buffers).
    Defines "this is bad enough to wake the operator no matter what."""

    fallback_available: bool
    """True if the dependency has a tested fallback (e.g. backup feed,
    secondary RPC, mocked health endpoint). If False, all outages escalate
    SEV0 immediately."""

    protected_mode_available: bool = False
    """True if the system can continue operating in a degraded read-only or
    cached mode while this dependency is down."""

    owner: str
    """Human or team responsible for this dependency."""

    runbook_doc: str
    """Path to operator runbook — e.g.
    'codex/15-runbooks/incidents/RB-CONN-002.md'."""

    test_method: str = "synthetic_probe"
    """Free-form: how the dependency's fallback is integration-tested."""
