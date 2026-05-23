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
    """13-state closed-set incident lifecycle.

    Transitions are enforced by ``ALLOWED_TRANSITIONS`` (below). The state
    machine is the SSOT for "is this incident closed?" — emitters MUST NOT
    short-circuit by writing ``RESOLVED`` straight from a successful Layer-0
    action without going through recovery verification.
    """

    DETECTED = "DETECTED"
    """Incident first seen — pre-action triage."""

    AUTO_ACTION_STARTED = "AUTO_ACTION_STARTED"
    """Layer-0 deterministic script (or Layer-1.5 LLM backup actuator) has
    started executing a recovery action."""

    AUTO_ACTION_SUCCEEDED = "AUTO_ACTION_SUCCEEDED"
    """Layer-0 action returned success. **NOT** equivalent to RESOLVED."""

    AUTO_ACTION_FAILED = "AUTO_ACTION_FAILED"
    """Layer-0 action returned failure. Layer-1.5 may pick up; else escalate."""

    RECOVERY_VERIFICATION_STARTED = "RECOVERY_VERIFICATION_STARTED"
    """Per-service callbacks evaluating recovery_verification 5-tuple."""

    RECOVERY_CONFIRMED = "RECOVERY_CONFIRMED"
    """All 5 verification booleans True. Eligible for AUDIT_REPORT_GENERATED."""

    RECOVERY_UNCERTAIN = "RECOVERY_UNCERTAIN"
    """At least one verification boolean False or callback errored. Escalate."""

    SAFE_MODE_ACTIVE = "SAFE_MODE_ACTIVE"
    """System in protected mode — new trading frozen for affected scope.
    Reached from RECOVERY_UNCERTAIN, AUTO_ACTION_FAILED, or by LLM
    DISPUTE_AUTOMATED_ACTION verdict from the recovery-audit-signoff agent."""

    HUMAN_OPERATIONAL_ACKED = "HUMAN_OPERATIONAL_ACKED"
    """Operator has indicated "I'm investigating now" via DART. Distinct from
    audit ack — does NOT close the incident."""

    AUDIT_REPORT_GENERATED = "AUDIT_REPORT_GENERATED"
    """Evidence collector has populated all 14 IncidentEvidence fields;
    audit-ack queue surface is now live with countdown to ``audit_ack_due_at``."""

    HUMAN_AUDIT_ACKED = "HUMAN_AUDIT_ACKED"
    """Operator has reviewed the audit report + clicked AuditAckButton.
    Pre-cursor to RESOLVED."""

    ESCALATED = "ESCALATED"
    """Audit-ack SLA breached → secondary-human / founder / physical pager
    cascading. Returns to HUMAN_AUDIT_ACKED if any operator subsequently acks."""

    RESOLVED = "RESOLVED"
    """Recovery confirmed AND human audit ack complete. Pre-CLOSED admin state."""

    CLOSED = "CLOSED"
    """Terminal state. Incident archived to GCS audit store. No further
    transitions allowed."""


ALLOWED_TRANSITIONS: Final[dict[IncidentState, frozenset[IncidentState]]] = {
    IncidentState.DETECTED: frozenset(
        {
            IncidentState.AUTO_ACTION_STARTED,
            IncidentState.SAFE_MODE_ACTIVE,  # no auto action allowed → straight to safe-mode
            IncidentState.HUMAN_OPERATIONAL_ACKED,  # operator picks up before any auto-action
        }
    ),
    IncidentState.AUTO_ACTION_STARTED: frozenset(
        {
            IncidentState.AUTO_ACTION_SUCCEEDED,
            IncidentState.AUTO_ACTION_FAILED,
        }
    ),
    IncidentState.AUTO_ACTION_SUCCEEDED: frozenset(
        {
            IncidentState.RECOVERY_VERIFICATION_STARTED,
            # NOTE: direct → RESOLVED is FORBIDDEN. Recovery must be verified.
        }
    ),
    IncidentState.AUTO_ACTION_FAILED: frozenset(
        {
            IncidentState.AUTO_ACTION_STARTED,  # Layer-1.5 LLM backup retry
            IncidentState.SAFE_MODE_ACTIVE,
            IncidentState.ESCALATED,
        }
    ),
    IncidentState.RECOVERY_VERIFICATION_STARTED: frozenset(
        {
            IncidentState.RECOVERY_CONFIRMED,
            IncidentState.RECOVERY_UNCERTAIN,
        }
    ),
    IncidentState.RECOVERY_CONFIRMED: frozenset(
        {
            IncidentState.AUDIT_REPORT_GENERATED,
        }
    ),
    IncidentState.RECOVERY_UNCERTAIN: frozenset(
        {
            IncidentState.SAFE_MODE_ACTIVE,
            IncidentState.AUTO_ACTION_STARTED,  # Layer-1.5 retry
        }
    ),
    IncidentState.SAFE_MODE_ACTIVE: frozenset(
        {
            IncidentState.HUMAN_OPERATIONAL_ACKED,
            IncidentState.AUDIT_REPORT_GENERATED,  # operator may skip operational ack if direct audit review
            IncidentState.ESCALATED,
        }
    ),
    IncidentState.HUMAN_OPERATIONAL_ACKED: frozenset(
        {
            IncidentState.AUTO_ACTION_STARTED,  # operator authorises a Layer-0 action
            IncidentState.AUDIT_REPORT_GENERATED,
            IncidentState.SAFE_MODE_ACTIVE,
            IncidentState.ESCALATED,
        }
    ),
    IncidentState.AUDIT_REPORT_GENERATED: frozenset(
        {
            IncidentState.HUMAN_AUDIT_ACKED,
            IncidentState.ESCALATED,
        }
    ),
    IncidentState.HUMAN_AUDIT_ACKED: frozenset(
        {
            IncidentState.RESOLVED,
        }
    ),
    IncidentState.ESCALATED: frozenset(
        {
            IncidentState.HUMAN_AUDIT_ACKED,  # any operator in the escalation ladder acks
            IncidentState.HUMAN_OPERATIONAL_ACKED,  # operator takes ownership without yet audit-acking
        }
    ),
    IncidentState.RESOLVED: frozenset(
        {
            IncidentState.CLOSED,
        }
    ),
    IncidentState.CLOSED: frozenset(),  # terminal
}


class IllegalIncidentTransitionError(ValueError):
    """Raised when a state transition outside ``ALLOWED_TRANSITIONS`` is attempted."""


def assert_allowed_transition(current: IncidentState, target: IncidentState) -> None:
    """Raise ``IllegalIncidentTransitionError`` if ``current → target`` is not allowed.

    Use at every state-write site in alerting-service incident-gateway. The
    invariant `AUTO_ACTION_SUCCEEDED → RESOLVED` is forbidden by this check.
    """
    if target not in ALLOWED_TRANSITIONS[current]:
        raise IllegalIncidentTransitionError(
            f"Cannot transition {current.value} → {target.value}; "
            f"allowed targets: {sorted(s.value for s in ALLOWED_TRANSITIONS[current])}"
        )
