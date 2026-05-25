"""Incident state machine — 13-state lifecycle owned by alerting-service Incident Gateway.

SSOT for the state names + allowed transitions. Mirrors the
`EmptyConfirmedReason` / `AlertCode` closed-set discipline. The central
invariant: ``AUTO_ACTION_SUCCEEDED`` is NEVER a direct predecessor of
``RESOLVED`` — recovery verification (positions reconcile, orders reconcile,
market data fresh, strategy state restored) is a separate gate. A restart can
succeed while reconciliation remains unresolved.

Codex SSOT: ``codex/04-architecture/incident-gateway-state-machine.md``.
Implementation plan: ``plans/active/incident_gateway_and_state_machine_2026_05_23.md``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class IncidentState(StrEnum):
    DETECTED = "DETECTED"
    AUTO_ACTION_STARTED = "AUTO_ACTION_STARTED"
    SAFE_MODE_ACTIVE = "SAFE_MODE_ACTIVE"
    HUMAN_OPERATIONAL_ACKED = "HUMAN_OPERATIONAL_ACKED"
    AUTO_ACTION_SUCCEEDED = "AUTO_ACTION_SUCCEEDED"
    AUTO_ACTION_FAILED = "AUTO_ACTION_FAILED"
    RECOVERY_VERIFICATION_STARTED = "RECOVERY_VERIFICATION_STARTED"
    ESCALATED = "ESCALATED"
    RECOVERY_CONFIRMED = "RECOVERY_CONFIRMED"
    RECOVERY_UNCERTAIN = "RECOVERY_UNCERTAIN"
    AUDIT_REPORT_GENERATED = "AUDIT_REPORT_GENERATED"
    HUMAN_AUDIT_ACKED = "HUMAN_AUDIT_ACKED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


ALLOWED_TRANSITIONS: Final[dict[IncidentState, frozenset[IncidentState]]] = {
    IncidentState.DETECTED: frozenset({
        IncidentState.AUTO_ACTION_STARTED,
        IncidentState.SAFE_MODE_ACTIVE,
        IncidentState.ESCALATED,
    }),
    IncidentState.AUTO_ACTION_STARTED: frozenset({
        IncidentState.AUTO_ACTION_SUCCEEDED,
        IncidentState.AUTO_ACTION_FAILED,
        IncidentState.SAFE_MODE_ACTIVE,
    }),
    IncidentState.AUTO_ACTION_SUCCEEDED: frozenset({
        IncidentState.RECOVERY_VERIFICATION_STARTED,
    }),
    IncidentState.AUTO_ACTION_FAILED: frozenset({
        IncidentState.ESCALATED,
        IncidentState.SAFE_MODE_ACTIVE,
    }),
    IncidentState.RECOVERY_VERIFICATION_STARTED: frozenset({
        IncidentState.RECOVERY_CONFIRMED,
        IncidentState.RECOVERY_UNCERTAIN,
    }),
    IncidentState.RECOVERY_CONFIRMED: frozenset({
        IncidentState.AUDIT_REPORT_GENERATED,
    }),
    IncidentState.RECOVERY_UNCERTAIN: frozenset({
        IncidentState.SAFE_MODE_ACTIVE,
        IncidentState.ESCALATED,
    }),
    IncidentState.SAFE_MODE_ACTIVE: frozenset({
        IncidentState.HUMAN_OPERATIONAL_ACKED,
        IncidentState.ESCALATED,
    }),
    IncidentState.HUMAN_OPERATIONAL_ACKED: frozenset({
        IncidentState.RECOVERY_VERIFICATION_STARTED,
        IncidentState.RESOLVED,
    }),
    IncidentState.ESCALATED: frozenset({
        IncidentState.HUMAN_OPERATIONAL_ACKED,
        IncidentState.SAFE_MODE_ACTIVE,
    }),
    IncidentState.AUDIT_REPORT_GENERATED: frozenset({
        IncidentState.HUMAN_AUDIT_ACKED,
    }),
    IncidentState.HUMAN_AUDIT_ACKED: frozenset({
        IncidentState.RESOLVED,
    }),
    IncidentState.RESOLVED: frozenset({
        IncidentState.CLOSED,
    }),
    IncidentState.CLOSED: frozenset(),
}


class IllegalIncidentTransitionError(ValueError):
    """Raised when a state transition is not in ALLOWED_TRANSITIONS."""


def assert_allowed_transition(from_state: IncidentState, to_state: IncidentState) -> None:
    """Raise IllegalIncidentTransitionError if the transition is not allowed."""
    allowed = ALLOWED_TRANSITIONS.get(from_state, frozenset())
    if to_state not in allowed:
        raise IllegalIncidentTransitionError(
            f"Transition {from_state!r} → {to_state!r} is not allowed; "
            f"valid next states: {sorted(s.value for s in allowed)}"
        )
