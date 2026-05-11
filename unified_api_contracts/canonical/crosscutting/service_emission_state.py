"""Service-emission manifest-row state — v8 manifest column SSOT (slice b).

Closed-set enum carried as the ``service_emission_state`` column on every
v8+ manifest row. Companion to
:class:`~unified_api_contracts.canonical.crosscutting.service_emission_policy.ServiceEmissionPolicy`
(the per-(service, output_data_type) declaration) and
:class:`~unified_api_contracts.canonical.crosscutting.service_emission_policy.EmissionLifecycleEvent`
(the publish-boundary lifecycle event emitted by UTL ``emission_publisher``).
The three pieces compose:

1. Operator declares the per-output **policy** (slice a — already shipped at
   :mod:`~unified_api_contracts.canonical.crosscutting.service_emission_policy`).
2. UTL ``publish_with_policy`` emits a **lifecycle event** per publish cycle.
3. The manifest row carries the resolved **state** as a v8 column so
   downstream consumers can reason about absence semantics from the manifest
   alone — no event-stream replay needed.

The resolution from ``(policy, event)`` → state is
:func:`~unified_api_contracts.canonical.crosscutting.service_emission_policy.next_state`
(Phase 1.B of the manifest schema final gate plan).

Manifest-read protocol per row's ``service_emission_state``:

* :attr:`PUBLISHED_OK` — consume normally.
* :attr:`PUBLISHED_DEGRADED` — consume with the ``completeness_fraction`` column
  applied per-consumer policy (ML NaN-fills, rolling-window features adjust
  denominator while keeping window size, execution skips, cross-instrument
  calcs propagate per-leg).
* :attr:`STALE_DATA_HEARTBEAT_ONLY` — **consumer-skip + log**. No metric row
  was written; service is up + emitting heartbeat events. Downstream MUST NOT
  proxy-fill the row from prior windows; the absence is the signal.
* :attr:`BLOCKED` — **consumer-skip + raise** :class:`ManifestRowBlockedError`.
  A P0 alert was fired at publish time; any downstream read of a ``BLOCKED``
  row is a correctness-critical attempt to use data that was deliberately
  withheld for being too incomplete.

Plan: ``manifest_schema_final_gate_2026_05_09.md`` Phase 1.A (slice b of
writegate ``writegate_honest_coverage_endtoend_2026_05_06.md`` Phase 3.D.5
Wave 4).

Schema-bump version: v8 (rows pre-v8 default ``service_emission_state=None``;
:func:`~unified_api_contracts.canonical.crosscutting.service_emission_policy.next_state`
never produces ``None`` so the column distinguishes "this row was written by
a v8-aware service" from "this row predates v8").
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class ServiceEmissionStateEnum(StrEnum):
    """Closed-set manifest-row state for the v8 ``service_emission_state`` column.

    Four values — frozen 2026-05-09 → 2026-05-23 per the manifest schema final
    gate plan ``UAC enums frozen for the window`` section. Any proposal to add a
    value during the freeze window is rejected; defer to post-cutover.

    String-valued members so manifest writes serialise straight to parquet
    without enum-to-str gymnastics. Bare-string callers
    (``service_emission_state="PUBLISHED_OK"``) are validated via
    :data:`SERVICE_EMISSION_STATES` membership lookup at the writer boundary.
    """

    PUBLISHED_OK = "PUBLISHED_OK"
    """Full upstream window represented; ``completeness_fraction == 1.0``.

    Downstream consumes the row without any absence handling. Emitted at
    publish time as the default-happy path."""

    PUBLISHED_DEGRADED = "PUBLISHED_DEGRADED"
    """Inner-window gaps present but the per-output policy permitted publish
    (``PARTIAL_OK`` or ``NAN_FILL``).

    Row carries ``completeness_fraction`` < 1.0 and
    ``expected_window_completeness_fraction`` columns. Downstream branches its
    own NaN-fill / denominator-adjustment / propagate-per-leg policy per the
    per-service consumer-class audit at ``codex/02-data/honest-absence-downstream-handling.md``
    § "Per-service consumer-class audit"."""

    STALE_DATA_HEARTBEAT_ONLY = "STALE_DATA_HEARTBEAT_ONLY"
    """Policy was ``STRICT_FAIL`` + gap detected → no metric row written.

    The manifest row exists (so the data-status reader can see the shard was
    attempted) but downstream MUST NOT consume any data from it. Service is
    up + emitting heartbeat events; the absence is the signal. Distinguishes
    upstream-data outage (heartbeat-only) from service-process outage (no
    heartbeat at all over N intervals)."""

    BLOCKED = "BLOCKED"
    """Policy was ``BLOCK_CRITICAL`` + gap detected → no metric row + P0 alert.

    Manual operator intervention required. Downstream reads of a ``BLOCKED``
    row raise :class:`ManifestRowBlockedError` — proceeding would consume
    data deliberately withheld for being too incomplete (typical use:
    ``position-balance-monitor`` ``portfolio_state``, ``execution-service``
    ``fill_confirmation``, ``ml-training`` ``model_version``)."""


SERVICE_EMISSION_STATES: Final[frozenset[str]] = frozenset(member.value for member in ServiceEmissionStateEnum)
"""String-membership view of :class:`ServiceEmissionStateEnum` for the writer hot path.

UTL ``ManifestWriter`` validates the ``service_emission_state`` kwarg against
this set; unknown values raise the same fail-loud pattern as
:data:`~unified_api_contracts.canonical.crosscutting.honest_coverage.EMPTY_CONFIRMED_REASONS`.
"""


class ManifestRowBlockedError(RuntimeError):
    """Raised when a downstream consumer reads a manifest row with ``service_emission_state == "BLOCKED"``.

    The publish-boundary policy decided the upstream window was too incomplete
    to publish a metric row AND too critical to silently downgrade. A P0 alert
    fired at publish time. Any code that reads a ``BLOCKED`` row is attempting
    to use data that was deliberately withheld — fail loud rather than proceed
    with wrong-by-construction inputs.

    The right consumer response: skip the read, surface the
    ``correlation_id`` to operators (the publish-time event carries the
    ``BLOCKED`` lifecycle event + the failing shard's row_key + completeness
    fraction), and wait for the operator to clear the cause.

    Args:
        row_key: The shard-dimension dict the consumer attempted to read.
            Echoed in the exception so triage knows which (venue, instrument,
            data_type, day) tuple was blocked.
        publish_correlation_id: Optional correlation id of the publish-time
            lifecycle event so operators can grep the event stream
            (``gs://{pid}-events/events/<service>/<YYYY-MM-DD>/<correlation_id>/...``)
            for the original ``BLOCKED`` event metadata.

    Reference: writegate plan ``writegate_honest_coverage_endtoend_2026_05_06.md``
    Phase 3.D.5 Wave 4 + manifest schema final gate
    ``manifest_schema_final_gate_2026_05_09.md`` Phase 1.A slice b.
    """

    def __init__(
        self,
        row_key: object,
        publish_correlation_id: str | None = None,
    ) -> None:
        self.row_key = row_key
        self.publish_correlation_id = publish_correlation_id
        suffix = f" publish_correlation_id={publish_correlation_id!r}" if publish_correlation_id else ""
        super().__init__(
            f"ManifestRowBlockedError: cannot consume row with "
            f"service_emission_state=BLOCKED — publish-time policy withheld "
            f"the metric row and fired a P0 alert. row_key={row_key!r}.{suffix}"
        )


__all__ = [
    "SERVICE_EMISSION_STATES",
    "ManifestRowBlockedError",
    "ServiceEmissionStateEnum",
]
