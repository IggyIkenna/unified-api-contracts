"""Service-output emission-policy SSOT — the orthogonal axis to manifest 4-state.

Manifest ``capture_status`` describes raw-shard capture state per
``(venue, data_type, instrument_id, day)``. This module describes **what each
service publishes for its own derived/aggregated output when upstream is
incomplete** — a separate concern that's invisible to the manifest but critical
for downstream service reasoning.

Operator framing 2026-05-07 evening (msg 10): _"missing data unexpected feels
more like something which should fail to deliver data for the downstream
client if it needs constant data ... whereas for lets say 24h high low you
still want that to probably record if you missing some data which is expected
because its tradfi and market isnt continuously open ... batch = live symmetry
and this happens like you would wanna alert/warn downstream that data is stale
by not publishing which is same as publishing nothing in batch ... heartbeat
you are alive just stale data so services know its not a disconnect but it is
a bad data event."_

Three stacked layers — net architecture:

* **Manifest 4-state** (``EmptyConfirmedReason``) — "What's the raw shard's
  capture state?" Per ``(venue, data_type, instrument_id, day)``. Lives in
  :mod:`~unified_api_contracts.canonical.crosscutting.honest_coverage`.
* **Service emission policy** (this module) — "What does service X publish
  for output Y when upstream is incomplete?"
* **Service output completeness** (UTL ``emission_publisher`` writes
  ``completeness_fraction`` + ``incomplete_window`` columns on derived
  parquets) — "What % of the upstream window made it into THIS published
  row + which inner shards are gaps?"

Plan: ``writegate_honest_coverage_endtoend_2026_05_06.md`` § Phase 3.D.5
Wave 4. UTL companion: :mod:`unified_trading_library.emission_publisher`.

Wave-4 scope — slice (a) only (the schema floor): enum + seed dict + helper.
No consumer wiring. Per-service rollout (slice c) is multi-week. Each
service-team owns its row of the policy table + the per-(service, output_data_type)
declaration.
"""

from ._enums import EMISSION_LIFECYCLE_EVENTS, EmissionLifecycleEvent, ServiceEmissionPolicy
from ._functions import (
    get_emission_policy,
    is_emission_policy_declared,
    next_state,
    policy_is_alert,
    policy_is_publish_row,
)
from ._policies import SERVICE_OUTPUT_POLICIES

__all__ = [
    "EMISSION_LIFECYCLE_EVENTS",
    "SERVICE_OUTPUT_POLICIES",
    "EmissionLifecycleEvent",
    "ServiceEmissionPolicy",
    "get_emission_policy",
    "is_emission_policy_declared",
    "next_state",
    "policy_is_alert",
    "policy_is_publish_row",
]
