"""Service contract map — owns / emits / consumes / persists / forbidden per service.

UAC schemas tell you what messages look like; this map tells you **which service
is allowed to produce or mutate them**. Together with import-boundary tests
(per-repo ``tests/architecture/test_import_boundaries.py``) this prevents the
"soft duplication" pattern where two services drift to computing the same thing.

Per audit P1.0a (workspace audit 2026-05-01).

Producer-consumer pairs feed:
- :mod:`unified_api_contracts.internal.event_topics` (per-event canonical
  producer + consumer set)
- Per-repo import-boundary tests (consume ``forbidden`` directly)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final


@dataclass(frozen=True)
class ServiceContract:
    """Contract for a single service: what it owns / emits / consumes / forbids."""

    service_name: str
    owns: frozenset[str] = field(default_factory=frozenset)
    """State entities for which this service is the System of Record."""

    emits: frozenset[str] = field(default_factory=frozenset)
    """Domain event types this service publishes (Pub/Sub or GCS)."""

    consumes: frozenset[str] = field(default_factory=frozenset)
    """Domain event types this service subscribes to."""

    persists: frozenset[str] = field(default_factory=frozenset)
    """Persistence destinations this service owns (Postgres / Firestore / GCS prefix)."""

    forbidden_imports: frozenset[str] = field(default_factory=frozenset)
    """Module path prefixes this service must never import (enforced by static
    test ``test_import_boundaries.py``)."""

    forbidden_exceptions: frozenset[str] = field(default_factory=frozenset)
    """Specific module paths that match a ``forbidden_imports`` prefix but are
    architecturally permitted. Each entry should carry a comment explaining why
    (typically: "target/this should move to UAC eventually"). Use sparingly —
    every entry is technical debt."""


# Domain event type names — see
# :mod:`unified_api_contracts.internal.inter_service_events` for the schemas
# and :mod:`unified_api_contracts.internal.event_topics` for the topic mapping.
SERVICE_CONTRACT_MAP: Final[dict[str, ServiceContract]] = {
    # NOTE: position-balance-monitor-service, risk-and-exposure-service, and
    # pnl-attribution-service have been consolidated into strategy-service
    # sub-packages (strategy_service.position, strategy_service.risk,
    # strategy_service.pnl respectively). These services are archived.
    # Their contracts are now expressed via the strategy-service entry below.
    "alerting-service": ServiceContract(
        service_name="alerting-service",
        owns=frozenset(
            {
                "alert_rules",
                "channel_routing",
                "alert_dispatch_history",
            }
        ),
        emits=frozenset(
            {
                "AlertDispatched",
            }
        ),
        consumes=frozenset(
            {
                "RiskEvent",
                "MarginEvent",
                "KillSwitchTrigger",
                "FillEvent",
            }
        ),
        persists=frozenset(
            {
                "firestore:alert_history/",
            }
        ),
        forbidden_imports=frozenset(
            {
                "strategy_service.engine",
                "strategy_service.risk",
                "strategy_service.position",
                "strategy_service.pnl",
                "execution_service.connectors",
            }
        ),
    ),
    "strategy-service": ServiceContract(
        service_name="strategy-service",
        owns=frozenset(
            {
                "archetype_definitions",
                "strategy_instances",
                "signal_generation",
                "instruction_lifecycle",
            }
        ),
        emits=frozenset(
            {
                "StrategyInstruction",
                "SignalEvent",
                "ShadowComparisonMetrics",
            }
        ),
        consumes=frozenset(
            {
                "PositionSnapshotEvent",
                "BalanceSnapshot",
                "MarginEvent",
                "FillEvent",
                "PriceSnapshot",
                "KillSwitchTrigger",
            }
        ),
        persists=frozenset(
            {
                "firestore:strategy_state/",
                "gcs:signals/",
            }
        ),
        forbidden_imports=frozenset(
            {
                "strategy_service.position",
                "strategy_service.risk",
                "strategy_service.pnl",
                "execution_service.connectors",
                "execution_service.matching_engine",
            }
        ),
    ),
    "execution-service": ServiceContract(
        service_name="execution-service",
        owns=frozenset(
            {
                "matching_engine_simulated_fills",
                "venue_connectors",
                "execution_algos",
                "order_lifecycle",
                "kill_switch_drain_mode",
                "deleverage_actions",
            }
        ),
        emits=frozenset(
            {
                "FillEvent",
                "OrderSubmitted",
                "DeleverageActionSubmitted",
            }
        ),
        consumes=frozenset(
            {
                "StrategyInstruction",
                "MarginEvent",
                "KillSwitchTrigger",
            }
        ),
        persists=frozenset(
            {
                "gcs:execution-events/",
                "firestore:order_state/",
            }
        ),
        forbidden_imports=frozenset(
            {
                "strategy_service.engine.strategies",
                "strategy_service.position",
                "strategy_service.risk",
                "strategy_service.pnl",
            }
        ),
        forbidden_exceptions=frozenset(
            {
                # Target universe catalog is shared reference data that
                # execution-service legitimately consults to build the rebalance
                # recommender's universe. Should move to UAC `registry/` long-
                # term — tracked in deprecation_ledger.yaml.
                "strategy_service.engine.strategies.v2.target_universe.catalog",
            }
        ),
    ),
    "batch-live-reconciliation-service": ServiceContract(
        service_name="batch-live-reconciliation-service",
        owns=frozenset(
            {
                "reconciliation_reports",
                "deviation_thresholds",
            }
        ),
        emits=frozenset(
            {
                "ReconciliationCompleted",
                "ReconciliationDeviation",
            }
        ),
        consumes=frozenset(
            {
                "PositionSnapshotEvent",
                "FillEvent",
                "PnLPoint",
                "RiskEvent",
                "StrategyInstruction",
                "SignalEvent",
            }
        ),
        persists=frozenset(
            {
                "gcs:t1-recon/",
            }
        ),
        forbidden_imports=frozenset(
            {
                "strategy_service.engine",
                "strategy_service.risk",
                "strategy_service.position",
                "strategy_service.pnl",
                "execution_service.connectors",
            }
        ),
    ),
}


def get_service_contract(service_name: str) -> ServiceContract | None:
    """Lookup helper. Returns ``None`` for unknown services."""
    return SERVICE_CONTRACT_MAP.get(service_name)


def canonical_producer(event_type: str) -> str | None:
    """Find the single service that owns producing an event type.

    Used by topic-registry tests to enforce one-canonical-producer-per-event.
    """
    for contract in SERVICE_CONTRACT_MAP.values():
        if event_type in contract.emits:
            return contract.service_name
    return None


def consumers_of(event_type: str) -> frozenset[str]:
    """All services that consume a given event type."""
    return frozenset(
        contract.service_name for contract in SERVICE_CONTRACT_MAP.values() if event_type in contract.consumes
    )
