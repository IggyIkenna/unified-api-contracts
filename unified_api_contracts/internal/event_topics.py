"""Event topic registry — Pub/Sub topic to producer/consumer mapping.

Per audit P1.0b (workspace audit 2026-05-01): the gap was that event-routing
metadata lived implicitly in service code. The audit found ``MARGIN_WARNINGS``
declared as a Pub/Sub topic with **zero publishers** — exactly the kind of
soft-coupling bug a topic registry catches structurally.

Each entry maps an inter-service domain event (see
:mod:`unified_api_contracts.internal.inter_service_events`) to:
- Pub/Sub topic
- canonical producer (single service)
- consumer set
- replayability + retention policy

Tests can assert:
1. Every declared event_type has exactly one producer in the registry.
2. Every topic in the workspace ``pubsub.py`` is declared here OR explicitly
   marked ``reserved=True``.
3. Every topic has at least one producer (catches the MARGIN_WARNINGS bug).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class TopicSpec:
    """Routing metadata for a single inter-service domain event."""

    event_type: str
    topic: str
    producer: str
    consumers: frozenset[str]
    replayable: bool = True
    retention_days: int = 7
    reserved: bool = False
    """``True`` for topics declared but intentionally not yet wired (rare)."""


EVENT_TOPIC_REGISTRY: Final[dict[str, TopicSpec]] = {
    # ── Margin / liquidation ────────────────────────────────────────────────
    "MarginEvent": TopicSpec(
        event_type="MarginEvent",
        topic="margin-events",
        producer="position-balance-monitor-service",
        consumers=frozenset(
            {
                "alerting-service",
                "risk-and-exposure-service",
                "strategy-service",
                "execution-service",
                "pnl-attribution-service",
            }
        ),
        replayable=True,
        retention_days=14,
    ),
    "LiquidationAlert": TopicSpec(
        event_type="LiquidationAlert",
        topic="liquidation-alerts",
        producer="position-balance-monitor-service",
        consumers=frozenset(
            {
                "alerting-service",
                "pnl-attribution-service",
                "risk-and-exposure-service",
            }
        ),
        retention_days=30,
    ),
    # ── Position / balance / fill ───────────────────────────────────────────
    "PositionSnapshotEvent": TopicSpec(
        event_type="PositionSnapshotEvent",
        topic="position-snapshots",
        producer="position-balance-monitor-service",
        consumers=frozenset(
            {
                "strategy-service",
                "risk-and-exposure-service",
                "pnl-attribution-service",
                "batch-live-reconciliation-service",
            }
        ),
    ),
    "BalanceSnapshot": TopicSpec(
        event_type="BalanceSnapshot",
        topic="balance-snapshots",
        producer="position-balance-monitor-service",
        consumers=frozenset(
            {
                "strategy-service",
                "risk-and-exposure-service",
            }
        ),
    ),
    "FillEvent": TopicSpec(
        event_type="FillEvent",
        topic="fill-events",
        producer="execution-service",
        consumers=frozenset(
            {
                "position-balance-monitor-service",
                "pnl-attribution-service",
                "strategy-service",
                "alerting-service",
                "batch-live-reconciliation-service",
            }
        ),
        retention_days=14,
    ),
    "OrderSubmitted": TopicSpec(
        event_type="OrderSubmitted",
        topic="order-events",
        producer="execution-service",
        consumers=frozenset(
            {
                "strategy-service",
                "batch-live-reconciliation-service",
            }
        ),
    ),
    "DeleverageActionSubmitted": TopicSpec(
        event_type="DeleverageActionSubmitted",
        topic="deleverage-actions",
        producer="execution-service",
        consumers=frozenset(
            {
                "alerting-service",
                "risk-and-exposure-service",
                "pnl-attribution-service",
            }
        ),
        retention_days=30,
    ),
    # ── Pricing ─────────────────────────────────────────────────────────────
    "PriceSnapshot": TopicSpec(
        event_type="PriceSnapshot",
        topic="price-snapshots",
        producer="market-tick-data-service",
        consumers=frozenset(
            {
                "strategy-service",
                "position-balance-monitor-service",
                "risk-and-exposure-service",
            }
        ),
        retention_days=2,
    ),
    # ── Risk / kill-switch ──────────────────────────────────────────────────
    "RiskEvent": TopicSpec(
        event_type="RiskEvent",
        topic="risk-events",
        producer="risk-and-exposure-service",
        consumers=frozenset(
            {
                "alerting-service",
                "strategy-service",
                "batch-live-reconciliation-service",
            }
        ),
        retention_days=14,
    ),
    "KillSwitchTrigger": TopicSpec(
        event_type="KillSwitchTrigger",
        topic="kill-switch-triggers",
        producer="risk-and-exposure-service",
        consumers=frozenset(
            {
                "execution-service",
                "strategy-service",
                "alerting-service",
                "position-balance-monitor-service",
            }
        ),
        retention_days=30,
    ),
    # ── Strategy / signals ──────────────────────────────────────────────────
    "StrategyInstruction": TopicSpec(
        event_type="StrategyInstruction",
        topic="strategy-instructions",
        producer="strategy-service",
        consumers=frozenset(
            {
                "execution-service",
                "risk-and-exposure-service",
                "batch-live-reconciliation-service",
            }
        ),
        retention_days=14,
    ),
    "SignalEvent": TopicSpec(
        event_type="SignalEvent",
        topic="strategy-signals",
        producer="strategy-service",
        consumers=frozenset(
            {
                "batch-live-reconciliation-service",
            }
        ),
        retention_days=7,
    ),
    "ShadowComparisonMetrics": TopicSpec(
        event_type="ShadowComparisonMetrics",
        topic="shadow-comparison",
        producer="strategy-service",
        consumers=frozenset(
            {
                "alerting-service",
            }
        ),
    ),
    # ── P&L ─────────────────────────────────────────────────────────────────
    "PnLPoint": TopicSpec(
        event_type="PnLPoint",
        topic="pnl-points",
        producer="position-balance-monitor-service",
        consumers=frozenset(
            {
                "pnl-attribution-service",
                "alerting-service",
                "strategy-service",
            }
        ),
    ),
    "PnLAttributionPublished": TopicSpec(
        event_type="PnLAttributionPublished",
        topic="pnl-attribution",
        producer="pnl-attribution-service",
        consumers=frozenset(
            {
                "alerting-service",
                "batch-live-reconciliation-service",
            }
        ),
        retention_days=30,
    ),
    # ── Alerting (sink, no consumers in this bus) ───────────────────────────
    "AlertDispatched": TopicSpec(
        event_type="AlertDispatched",
        topic="alert-dispatched",
        producer="alerting-service",
        consumers=frozenset(),
        retention_days=30,
    ),
    # ── Reconciliation ──────────────────────────────────────────────────────
    "ReconciliationCompleted": TopicSpec(
        event_type="ReconciliationCompleted",
        topic="reconciliation-completed",
        producer="batch-live-reconciliation-service",
        consumers=frozenset({"alerting-service"}),
        retention_days=30,
    ),
    "ReconciliationDeviation": TopicSpec(
        event_type="ReconciliationDeviation",
        topic="reconciliation-deviation",
        producer="batch-live-reconciliation-service",
        consumers=frozenset({"alerting-service"}),
        retention_days=30,
    ),
}


def get_topic_spec(event_type: str) -> TopicSpec | None:
    """Lookup helper. Returns ``None`` for unknown events."""
    return EVENT_TOPIC_REGISTRY.get(event_type)


def topic_for(event_type: str) -> str | None:
    """Return the Pub/Sub topic name for a given event type, or ``None``."""
    spec = EVENT_TOPIC_REGISTRY.get(event_type)
    return spec.topic if spec is not None else None


def consumers_for_topic(topic: str) -> frozenset[str]:
    """Return all services that subscribe to a given topic."""
    for spec in EVENT_TOPIC_REGISTRY.values():
        if spec.topic == topic:
            return spec.consumers
    return frozenset()


def producer_for_topic(topic: str) -> str | None:
    """Return the canonical producer service for a given topic."""
    for spec in EVENT_TOPIC_REGISTRY.values():
        if spec.topic == topic:
            return spec.producer
    return None
