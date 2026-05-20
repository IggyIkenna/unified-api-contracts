"""Per-client lifecycle event taxonomy for strategy-service supervisor.

Closed-set bus events that drive the StrategySupervisor → ClientWorker subprocess
lifecycle (hot register/deregister, preflight reporting, credential rotation,
shard capacity signalling).

§ SSOT reconciliation
---------------------

Composes with:

- :class:`unified_api_contracts.canonical.crosscutting.kill_switch.KillSwitchArmedEvent`
  — ClientLifecycleEvent.QUARANTINE is a per-client analogue of a CLIENT-scoped
  kill-switch; they travel on separate buses but carry compatible ``client_id``
  fields.
- :class:`unified_trading_library.lifecycle.KillSwitchBusSubscriberBase` — the
  ``ClientLifecycleBusSubscriberBase`` (UTL Phase 2) extends the same scaffold
  pattern, subscribing to :class:`ClientLifecycleEvent` instead of
  :class:`KillSwitchArmedEvent`.
- ``plans/active/per_client_isolation_and_venue_fanout_topology_2026_05_20.md``
  Phase 1 — canonical specification for every field in this module.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ClientLifecycleKind(StrEnum):
    """Closed-set discriminant for :class:`ClientLifecycleEvent`.

    Transition semantics (per plan Phase 1):

    - ``REGISTER``:   operator registers a new client on a running supervisor.
      Supervisor spawns a ``ClientWorker`` subprocess and waits for
      ``ClientReadyEvent`` (timeout configurable, default 30 s).
    - ``DEREGISTER``: operator removes a client. Supervisor sends SIGTERM to the
      ``ClientWorker``, waits for graceful drain (timeout 60 s), then reaps.
    - ``QUARANTINE``: supervisor quarantines a client after N restart failures.
      Triggers :class:`ClientQuarantinedEvent` on the event bus.
    - ``UNQUARANTINE``: operator clears a quarantine and allows the supervisor to
      restart the worker.
    - ``CREDENTIAL_ROTATED``: push notification from the operator (via bus) that
      the credentials for a (client_id, venue) pair have been rotated in Cloud
      KMS. The ``ClientWorker`` reloads its ``CredentialStore`` without a full
      restart. Bypasses the KMS poll interval (immediate reload).
    """

    REGISTER = "REGISTER"
    DEREGISTER = "DEREGISTER"
    QUARANTINE = "QUARANTINE"
    UNQUARANTINE = "UNQUARANTINE"
    CREDENTIAL_ROTATED = "CREDENTIAL_ROTATED"


class ClientLifecycleEvent(BaseModel):
    """Emitted by the operator (or supervisor) to drive per-client subprocess lifecycle.

    Published on the UAC event bus and consumed by
    :class:`unified_trading_library.lifecycle.ClientLifecycleBusSubscriberBase`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: ClientLifecycleKind
    client_id: str
    """Canonical client identifier (e.g. ``"odum-uk"``, ``"defi-client-1"``)."""

    archetype_id: str
    """Archetype this client runs on (e.g. ``"carry_staked_basis"``)."""

    shard_id: int
    """Shard index (0-based) within the archetype VM pool."""

    timestamp: datetime
    reason: str = ""
    """Human-readable rationale (operator note for REGISTER/DEREGISTER;
    auto-generated description for QUARANTINE/UNQUARANTINE)."""

    venue: str = ""
    """For ``CREDENTIAL_ROTATED``: the venue whose credential was rotated
    (e.g. ``"BINANCE-FUTURES"``). Empty for all other kinds."""

    metadata: dict[str, str] = Field(default_factory=dict)


class VenueAuthStatus(StrEnum):
    """Preflight auth outcome per venue for :class:`ClientReadyEvent`."""

    OK = "OK"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ClientReadyEvent(BaseModel):
    """Emitted by a ``ClientWorker`` subprocess when all preflight checks pass.

    Signals to the supervisor that the client is live and trading-ready.
    ``venue_auth_status`` gives a per-venue breakdown of the preflight outcomes
    (auth ping + balance check); ``SKIPPED`` indicates the venue is configured
    but not included in this archetype's venue set.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    client_id: str
    archetype_id: str
    shard_id: int
    timestamp: datetime
    venue_auth_status: dict[str, VenueAuthStatus] = Field(default_factory=dict)
    """Keys are canonical venue names; values are preflight outcomes."""

    metadata: dict[str, str] = Field(default_factory=dict)


class QuarantineReason(StrEnum):
    """Discriminant for why a client was quarantined.

    Carried by :class:`ClientQuarantinedEvent.quarantine_reason` so downstream
    consumers (alerting-service, deployment-UI) can route by cause.
    """

    MAX_RESTART_ATTEMPTS = "MAX_RESTART_ATTEMPTS"
    """Supervisor exhausted the restart backoff schedule (default: 5 attempts)."""

    PREFLIGHT_FAILED = "PREFLIGHT_FAILED"
    """ClientWorker preflight sequence failed (auth, balance, or timeout)."""

    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    """Balance on one or more venues is below minimum_threshold from clients.yaml."""

    VENUE_AUTH_TIMEOUT = "VENUE_AUTH_TIMEOUT"
    """Per-venue auth ping timed out during preflight."""

    OPERATOR_QUARANTINE = "OPERATOR_QUARANTINE"
    """Operator manually quarantined via :class:`ClientLifecycleEvent.QUARANTINE`."""


class ClientQuarantinedEvent(BaseModel):
    """Emitted when a client is quarantined (preflight failure or repeated crashes).

    Other clients on the same shard continue trading; this client's
    ``ClientWorker`` subprocess is reaped. The supervisor will not restart
    it until an :class:`ClientLifecycleEvent` ``UNQUARANTINE`` is received.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    client_id: str
    archetype_id: str
    shard_id: int
    timestamp: datetime
    quarantine_reason: QuarantineReason
    last_error_message: str = ""
    """Last exception message or error detail (truncated to 2 KiB)."""

    retry_after_seconds: int = 0
    """Suggested retry delay (0 = do not auto-retry; operator must UNQUARANTINE)."""

    restart_attempts: int = 0
    """How many restart attempts were made before quarantine."""

    metadata: dict[str, str] = Field(default_factory=dict)


class ShardRecommendedAction(StrEnum):
    """Action recommended by :class:`ShardCapacityEvent`."""

    SPAWN_NEW_SHARD = "SPAWN_NEW_SHARD"
    """The deployment-service should provision a new archetype VM shard."""


class ShardCapacityEvent(BaseModel):
    """Emitted by ``StrategySupervisor`` when shard resource utilisation exceeds threshold.

    Consumed by deployment-service (Phase 8) to trigger auto-shard provisioning
    (Phase E.2 — post-May-23). For May-23 launch this event is observable but
    not yet acted on automatically; it is recorded for alerting-service.

    Threshold (per plan Phase 3): any of:

    - ``memory_pct >= 70`` for 3 consecutive 10-second samples, OR
    - ``cpu_pct >= 80`` for 3 consecutive 10-second samples, OR
    - ``client_count >= shard_capacity_max``
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    archetype_id: str
    shard_id: int
    timestamp: datetime
    occupancy_pct: float
    """Clients-occupied / shard_capacity_max * 100."""

    memory_pct: float
    """VM memory utilisation percentage (psutil)."""

    cpu_pct: float
    """VM CPU utilisation percentage (psutil)."""

    client_count: int
    shard_capacity_max: int
    recommended_action: ShardRecommendedAction = ShardRecommendedAction.SPAWN_NEW_SHARD
    metadata: dict[str, str] = Field(default_factory=dict)


__all__ = [
    "ClientLifecycleEvent",
    "ClientLifecycleKind",
    "ClientQuarantinedEvent",
    "ClientReadyEvent",
    "QuarantineReason",
    "ShardCapacityEvent",
    "ShardRecommendedAction",
    "VenueAuthStatus",
]
