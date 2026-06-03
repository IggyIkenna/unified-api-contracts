"""Service emission policy functions — helper functions and state resolution."""

from __future__ import annotations

from unified_api_contracts.canonical.crosscutting.service_emission_state import (
    ServiceEmissionStateEnum,
)

from ._enums import EmissionLifecycleEvent, ServiceEmissionPolicy
from ._policies import EVENT_TO_STATE, SERVICE_OUTPUT_POLICIES


def get_emission_policy(service: str, output_data_type: str) -> ServiceEmissionPolicy:
    """Resolve the emission policy for ``(service, output_data_type)``.

    Args:
        service: Canonical service name (e.g. ``"market-data-processing-service"``).
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


def next_state(
    *,
    policy: ServiceEmissionPolicy,
    event: EmissionLifecycleEvent,
) -> ServiceEmissionStateEnum:
    """Resolve a publish-boundary ``(policy, event)`` to the manifest-row state.

    Pure function. UTL ``emission_publisher.publish_with_policy`` calls this
    after emitting the lifecycle event so the v8 manifest write carries the
    structured state column. Downstream consumers reading the manifest can
    then reason about absence semantics from the column alone — no
    event-stream replay needed.

    The :class:`EmissionLifecycleEvent` taxonomy maps 1:1 to
    :class:`ServiceEmissionStateEnum` except for ``STALE_DATA`` →
    ``STALE_DATA_HEARTBEAT_ONLY`` (the manifest column name elaborates
    "heartbeat only" so downstream readers know the service is up). All four
    combinations are covered.

    Args:
        policy: The resolved policy from :func:`get_emission_policy`. Echoed
            into the signature for caller-side documentation + forward-compat
            with future policy-specific state nuances. Currently advisory —
            state derives from ``event`` alone.
        event: The lifecycle event the publish boundary just emitted (one of
            the 4 :class:`EmissionLifecycleEvent` members).

    Returns:
        The resolved :class:`ServiceEmissionStateEnum` value to write into
        the v8 ``service_emission_state`` manifest column.

    Reference: ``manifest_schema_final_gate_2026_05_09.md`` Phase 1.B.
    """
    # Mark as referenced — caller-side documentation contract.
    _ = policy
    return EVENT_TO_STATE[event]


__all__ = [
    "get_emission_policy",
    "is_emission_policy_declared",
    "next_state",
    "policy_is_alert",
    "policy_is_publish_row",
]
