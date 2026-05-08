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

from __future__ import annotations

from enum import StrEnum
from typing import Final


class ServiceEmissionPolicy(StrEnum):
    """Closed-set policy for what a service publishes when upstream input is incomplete.

    Every (service, output_data_type) pair MUST resolve to exactly one of these. The default
    for unknown pairs is :attr:`STRICT_FAIL` — fail-loud — to force explicit declaration as
    services migrate. See :data:`SERVICE_OUTPUT_POLICIES` for the seeded pairs.
    """

    STRICT_FAIL = "strict_fail"
    """Current-window upstream gap → DON'T publish the output row. Emit ``STALE_DATA``
    lifecycle event (heartbeat-only, no metric). Downstream sees: service is UP but data
    is stale.

    Use for: real-time current-bar metrics (``ohlcv_1m`` current, derivative_ticker
    snapshots), per-archetype signals, per-strategy orders, fills — anywhere partial
    truth is wrong (would mislead a trading decision)."""

    PARTIAL_OK = "partial_ok"
    """Inner-window upstream gaps → publish output row WITH ``completeness_fraction``
    column. Downstream branches its own policy on that fraction.

    Use for: rolling-window aggregates whose denominator is the WINDOW not the inner-bar
    count (``ohlcv_24h`` high/low, daily volume, weekly correlation matrices).
    Catalog-snapshot-style outputs where partial-best-effort is normal."""

    NAN_FILL = "nan_fill"
    """Inner-window upstream gaps → publish output row with NaN where affected.
    Downstream (typically ML) NaN-fills per its own training-time rule.

    Use for: features tree-based models can NaN-fill natively (per CLAUDE.md
    "Honest absence vs fake placeholders" — 1-10% missing tolerance is fine for
    rank-based allocators and tree learners). Rolling vols, autocorrelation matrices,
    feature_groups whose downstream consumer is ML."""

    BLOCK_CRITICAL = "block_critical"
    """Any upstream gap → don't publish + fire P0 alert. No heartbeat-only fallback.

    Use for: position-balance-monitor portfolio_state, execution fill confirmation,
    risk-and-exposure risk_state, ml-training model_version — anywhere "partial truth"
    is worse than "no truth + alert"."""


# ---------------------------------------------------------------------------
# Lifecycle event types — re-export-friendly string constants.
#
# UTL ``emission_publisher.publish_with_policy`` emits one of these at every
# emission cycle. Schema lives in UTL events module; the names + semantics
# are pinned here so producers + consumers share a single SSOT.
# ---------------------------------------------------------------------------


class EmissionLifecycleEvent(StrEnum):
    """Lifecycle event names emitted by the publish boundary on every emission cycle.

    Downstream branching:

    * **Service-down** (no heartbeat at all over N intervals) → service alarm.
    * **Data-stale** (heartbeat + ``STALE_DATA``) → upstream-data alarm, service is fine.
    * **Degraded-but-running** (``PUBLISHED_DEGRADED``) → operator watch-list, service
      decisions tolerated.
    * **Broken** (``BLOCKED``) → P0, manual intervention required.
    """

    PUBLISHED_OK = "PUBLISHED_OK"
    """``completeness_fraction == 1.0`` — full upstream window represented. Default-happy path."""

    PUBLISHED_DEGRADED = "PUBLISHED_DEGRADED"
    """Gaps present but published per ``PARTIAL_OK`` / ``NAN_FILL`` policy. Event metadata
    carries ``completeness_fraction`` + ``incomplete_window`` (list of upstream
    ``(venue, data_type, instrument_id, iso_window_start, iso_window_end)`` tuples)."""

    STALE_DATA = "STALE_DATA"
    """``STRICT_FAIL`` policy fired — heartbeat-only, no metric row written. Distinguishes
    upstream-data outage from service-process outage (no heartbeat at all)."""

    BLOCKED = "BLOCKED"
    """``BLOCK_CRITICAL`` policy fired — no metric row, P0 alert dispatched.
    Manual operator intervention required."""


EMISSION_LIFECYCLE_EVENTS: Final[frozenset[str]] = frozenset(member.value for member in EmissionLifecycleEvent)
"""String-membership view of :class:`EmissionLifecycleEvent`. UTL event-emission
hot path validates names against this set — unknown event names raise the same
fail-loud pattern as :data:`unified_api_contracts.canonical.crosscutting.honest_coverage.EMPTY_CONFIRMED_REASONS`."""


# ---------------------------------------------------------------------------
# Per-(service, output_data_type) policy SSOT — initial seed.
#
# Service-team owners extend per their domain. The default for any unseeded pair
# is STRICT_FAIL (via :func:`get_emission_policy`) — fail-loud — so an unowned
# pair surfaces as a deliberate operator decision rather than a silent
# permissive policy.
#
# Conventions:
# * ``service`` is the canonical service name as it appears in ``setup_events(service_name=...)``
#   (e.g. ``"market-tick-data-service"``, ``"features-volatility-service"``,
#   ``"strategy-service"``, ``"execution-service"``).
# * ``output_data_type`` is the data_type the SERVICE PUBLISHES — distinct from
#   any input data_type the service reads. ``ohlcv_1m`` is consumed by MDPS as
#   input AND emitted by MDPS as output (different policies for current vs
#   historical re-emission).
# * Real-time ``current`` slices and historical re-emissions for the same
#   data_type can carry different policies — encode that with a
#   ``"<data_type>:<slice>"`` key shape (e.g. ``"ohlcv_1m:current"`` vs
#   ``"ohlcv_1m:historical"``).
# ---------------------------------------------------------------------------


SERVICE_OUTPUT_POLICIES: Final[dict[tuple[str, str], ServiceEmissionPolicy]] = {
    # MDPS — candle outputs at multiple cadences. Current bars are real-time;
    # partial = wrong. Historical re-emission tolerates inner gaps via
    # completeness_fraction.
    ("market-data-pipeline-service", "ohlcv_1m:current"): ServiceEmissionPolicy.STRICT_FAIL,
    ("market-data-pipeline-service", "ohlcv_1m:historical"): ServiceEmissionPolicy.PARTIAL_OK,
    ("market-data-pipeline-service", "ohlcv_1h:current"): ServiceEmissionPolicy.STRICT_FAIL,
    ("market-data-pipeline-service", "ohlcv_1h:historical"): ServiceEmissionPolicy.PARTIAL_OK,
    ("market-data-pipeline-service", "ohlcv_24h"): ServiceEmissionPolicy.PARTIAL_OK,
    ("market-data-pipeline-service", "book_snapshot_5"): ServiceEmissionPolicy.STRICT_FAIL,
    # features-volatility — operator-flagged 24h-high-low example as PARTIAL_OK; rolling
    # vols are NaN_FILL because the ML consumer NaN-fills natively.
    ("features-volatility-service", "high_low_24h"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-volatility-service", "vol_30d"): ServiceEmissionPolicy.NAN_FILL,
    ("features-volatility-service", "realised_vol_intraday"): ServiceEmissionPolicy.PARTIAL_OK,
    # features-cross-instrument — paired-spec compute is leak-risk-sensitive: both legs
    # MUST be current. Partial = lookahead-bias trap.
    ("features-cross-instrument-service", "paired_spec"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-cross-instrument-service", "pairwise_correlation"): ServiceEmissionPolicy.NAN_FILL,
    # ml-training — training a model on incomplete data is the worst-case silent corruption.
    # block_critical forces operator review.
    ("ml-training-service", "model_version"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    # ml-inference — signals off stale features pollute strategy decisions.
    ("ml-inference-service", "per_strategy_signal"): ServiceEmissionPolicy.STRICT_FAIL,
    # strategy — same as ml-inference; partial-truth signals fire wrong orders.
    ("strategy-service", "per_archetype_signal"): ServiceEmissionPolicy.STRICT_FAIL,
    # execution — orders + fill confirmations are no-partial-truth zones.
    ("execution-service", "order_intent"): ServiceEmissionPolicy.STRICT_FAIL,
    ("execution-service", "fill_confirmation"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    # position-balance-monitor — portfolio_state must be authoritative; partial = wrong.
    ("position-balance-monitor-service", "portfolio_state"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    # risk-and-exposure — same.
    ("risk-and-exposure-service", "risk_state"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    # instruments-service — catalog snapshot is best-effort union of multiple source
    # feeds; partial publish is normal. Per-source partial coverage handled at
    # the manifest layer (per-row capture_status), not at the catalog-publish layer.
    ("instruments-service", "catalog_snapshot"): ServiceEmissionPolicy.PARTIAL_OK,
}
"""Per-(service, output_data_type) emission policy seed.

This is **not the final shape** — it is the initial seed per writegate plan
Phase 3.D.5 Wave 4. Per-service rollout (slice c) extends this dict per the
service team's audit. Adding a row that disagrees with the operator-msg-10
framing requires plan annotation explaining why.

**Why STRICT_FAIL is the default for unseeded pairs**: a missing entry means
"the service team has not declared a policy for this output yet." Policy
declaration is a deliberate architectural choice; silently defaulting to
permissive ``PARTIAL_OK`` would let services ship partial-truth outputs
without operator review. Fail-loud forces the decision.
"""


def get_emission_policy(service: str, output_data_type: str) -> ServiceEmissionPolicy:
    """Resolve the emission policy for ``(service, output_data_type)``.

    Args:
        service: Canonical service name (e.g. ``"market-data-pipeline-service"``).
            Must match the ``service_name`` passed to
            :func:`unified_trading_library.events.setup_events`.
        output_data_type: The data_type the service publishes. Use the
            ``"<data_type>:<slice>"`` shape (e.g. ``"ohlcv_1m:current"``) when
            real-time vs historical re-emission warrant different policies.

    Returns:
        The declared :class:`ServiceEmissionPolicy`, or
        :attr:`ServiceEmissionPolicy.STRICT_FAIL` for unseeded pairs (see module
        docstring rationale).
    """
    return SERVICE_OUTPUT_POLICIES.get((service, output_data_type), ServiceEmissionPolicy.STRICT_FAIL)


def is_emission_policy_declared(service: str, output_data_type: str) -> bool:
    """Return ``True`` if ``(service, output_data_type)`` has an explicit policy entry.

    The companion to :func:`get_emission_policy` — the writer-side guard in UTL
    ``emission_publisher.publish_with_policy`` warns when a service publishes
    to an undeclared output_data_type so service-team owners notice missing
    seed entries during rollout.
    """
    return (service, output_data_type) in SERVICE_OUTPUT_POLICIES


def policy_is_publish_row(policy: ServiceEmissionPolicy) -> bool:
    """Return ``True`` if ``policy`` writes a parquet row, ``False`` if heartbeat-only.

    * :attr:`ServiceEmissionPolicy.PARTIAL_OK` + :attr:`ServiceEmissionPolicy.NAN_FILL` write rows.
    * :attr:`ServiceEmissionPolicy.STRICT_FAIL` + :attr:`ServiceEmissionPolicy.BLOCK_CRITICAL`
      do NOT write rows (heartbeat-only / blocked).

    Used by UTL ``emission_publisher.publish_with_policy`` to drive the
    write-row-or-emit-event-only branch without re-implementing the policy
    table per call site.
    """
    return policy in {ServiceEmissionPolicy.PARTIAL_OK, ServiceEmissionPolicy.NAN_FILL}


def policy_is_alert(policy: ServiceEmissionPolicy) -> bool:
    """Return ``True`` if ``policy`` should fire a P0 alert (no heartbeat fallback).

    Only :attr:`ServiceEmissionPolicy.BLOCK_CRITICAL` triggers an alert; the other
    three policies emit lifecycle events (``PUBLISHED_OK`` / ``PUBLISHED_DEGRADED`` /
    ``STALE_DATA``) without escalating to alerting-service.
    """
    return policy is ServiceEmissionPolicy.BLOCK_CRITICAL


__all__ = [
    "EMISSION_LIFECYCLE_EVENTS",
    "SERVICE_OUTPUT_POLICIES",
    "EmissionLifecycleEvent",
    "ServiceEmissionPolicy",
    "get_emission_policy",
    "is_emission_policy_declared",
    "policy_is_alert",
    "policy_is_publish_row",
]
