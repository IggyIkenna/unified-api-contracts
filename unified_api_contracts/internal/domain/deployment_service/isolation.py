"""Client isolation, SLA tiers, runtime profiles, and chaos injection schemas.

These types are the canonical source of truth for:
  - Per-service isolation policy (shared vs isolated per client)
  - SLA tiers (premium/standard/basic) with cost passthrough
  - Runtime profiles (backtest/paper/mock-live/staging/prod) — the single axis that
    collapses the 5 legacy mode env vars (CLOUD_MOCK_MODE, MOCK_STATE_MODE,
    DISABLE_AUTH, VITE_MOCK_API, VITE_SKIP_AUTH)
  - Client subscriptions — what a client is subscribed to, at what tier, with what
    per-service isolation overrides
  - Chaos injection specs — structured chaos points that ChaosController consumes

Paired SSOT: unified-trading-pm/configs/runtime-topology.yaml (v7) — the YAML
declares per-service `isolation_policies`, `sla_tiers`, `runtime_profiles`, and
`chaos_hooks` that these schemas mirror.

Decisions doc: unified-trading-pm/codex/04-architecture/client-isolation-sla-and-runtime-profiles.md

NO cloud SDKs. Pure Pydantic + StrEnum.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# KillSwitchScope moved to canonical/crosscutting/alerting/codes.py 2026-05-08
# so canonical AlertRule can carry it as a typed field without a circular
# import. Imported here from canonical so prior call sites
# (``unified_api_contracts.internal.KillSwitchScope``) still resolve.
from unified_api_contracts.canonical.crosscutting.alerting.codes import (
    KillSwitchScope,
)

__all_canonical_reexports__ = ["KillSwitchScope"]


class IsolationPolicy(StrEnum):
    """Per-service isolation choice.

    SHARED: one process instance multiplexes N clients (topic_template contains {client}).
    ISOLATED: one process instance per client (one pod/VM per client).
    """

    SHARED = "shared"
    ISOLATED = "isolated"


class SLATier(StrEnum):
    """Client SLA tier — controls allowed isolation policies, cost multiplier, and latency budget.

    BASIC: fully multi-tenant, best-effort latency, business-hours support.
    STANDARD: isolated execution required, optional isolation elsewhere, 4h support.
    PREMIUM: dedicated execution+strategy+position+risk, 30-min support, custom limits.
    """

    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"


class RuntimeProfile(StrEnum):
    """Single-axis deployment profile — collapses the 5 legacy mode env vars.

    BACKTEST: historical replay, simulated fills, isolated storage namespace.
    PAPER: live data, simulated fills, real risk + position tracking.
    MOCK_LIVE: all services live-wired but cloud-mock-mode; sample data, no cloud.
    STAGING: real cloud, real services, sandbox venues; chaos allowed.
    PROD: production; chaos FORBIDDEN; full auth; real cloud and venues.
    """

    BACKTEST = "backtest"
    PAPER = "paper"
    MOCK_LIVE = "mock-live"
    STAGING = "staging"
    PROD = "prod"


class ChaosInjectionPoint(StrEnum):
    """Structured chaos injection points exposed to UTL ChaosController.

    Each point must have a registered hook in the implementing library
    (see runtime-topology.yaml `chaos_hooks` for the declared hook_location).
    """

    VENUE_LATENCY = "venue_latency"
    RPC_TIMEOUT = "rpc_timeout"
    RECON_MISMATCH = "recon_mismatch"
    PRICE_SHOCK = "price_shock"
    INSTRUMENT_DELIST = "instrument_delist"
    CONFIG_FLIP = "config_flip"
    KILL_SWITCH_FIRE = "kill_switch_fire"
    COMPONENT_FAILURE = "component_failure"


class ServiceIsolationSpec(BaseModel):
    """Per-service isolation declaration from runtime-topology.yaml `isolation_policies`.

    Declares the default policy, the set of policies a client subscription may request,
    and a human-readable reason.
    """

    service: str
    default: IsolationPolicy
    allowed: list[IsolationPolicy]
    reason: str


class SLATierSpec(BaseModel):
    """SLA tier declaration from runtime-topology.yaml `sla_tiers`."""

    tier: SLATier
    cost_multiplier: float
    allowed_isolations: list[IsolationPolicy]
    min_isolated_services: list[str] = Field(default_factory=list)
    latency_budget_ms: int
    support_response_sla_min: int
    note: str = ""


class RuntimeProfileSpec(BaseModel):
    """Runtime profile declaration from runtime-topology.yaml `runtime_profiles`.

    Deployment-api fans these fields out to the correct env vars at VM/pod boot.
    """

    profile: RuntimeProfile
    description: str
    cloud_mock_mode: bool
    mock_state_mode: str  # "deterministic" | "interactive"
    auth_disabled: bool
    vite_mock_api: bool
    vite_skip_auth: bool
    chaos_allowed: bool
    client_isolation_required: bool
    storage_namespace: str
    allow_real_venue_calls: bool
    note: str = ""


class ChaosHookSpec(BaseModel):
    """Chaos hook declaration from runtime-topology.yaml `chaos_hooks`.

    Lists where each ChaosInjectionPoint is actually hooked in the implementing library.
    """

    point: ChaosInjectionPoint
    target_boundary: str
    hook_location: str
    parameters: list[str]
    status: str  # "planned" | "implemented"


class ClientServiceOverride(BaseModel):
    """A client's choice to override the default isolation for one service.

    Must be within `ServiceIsolationSpec.allowed` and permitted by the client's `SLATier.allowed_isolations`.
    Validation happens in UTL.resolve_deployment(), not here.
    """

    service_name: str
    isolation: IsolationPolicy


class ClientSubscription(BaseModel):
    """A client's topology subscription — drives deployment materialisation.

    Deployment-service reads this to decide: for each service in the cluster,
    does this client get a shared pool or a dedicated instance?
    """

    client_id: str
    sla_tier: SLATier
    service_overrides: list[ClientServiceOverride] = Field(default_factory=list)
    active_from: datetime
    active_until: datetime | None = None
    note: str = ""


class ChaosInjectionSpec(BaseModel):
    """A registered chaos injection — live or scheduled.

    Validated by deployment-api against runtime-topology.yaml `chaos_hooks`
    (the declared `point` must exist and `parameters` keys must match).
    ChaosController reads active specs and applies them at the declared hook locations.
    """

    injection_id: str
    point: ChaosInjectionPoint
    target_service: str
    parameters: dict[str, str] = Field(default_factory=dict)
    active_from: datetime
    active_until: datetime | None = None
    created_by: str
    runtime_profile: RuntimeProfile


__all__ = [
    "ChaosHookSpec",
    "ChaosInjectionPoint",
    "ChaosInjectionSpec",
    "ClientServiceOverride",
    "ClientSubscription",
    "IsolationPolicy",
    "KillSwitchScope",
    "RuntimeProfile",
    "RuntimeProfileSpec",
    "SLATier",
    "SLATierSpec",
    "ServiceIsolationSpec",
]
