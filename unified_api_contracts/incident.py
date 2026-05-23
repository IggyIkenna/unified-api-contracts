"""Incident facade — workspace-public surface for Incident Gateway schemas.

Consumers MUST import from this facade, not from the deep
``unified_api_contracts.canonical.crosscutting.incident.*`` paths
(per UAC import-surface rules).

Example::

    from unified_api_contracts.incident import (
        IncidentEnvelope,
        IncidentState,
        AgentActionEvent,
        ActionType,
        ActionStatus,
        ActionProvenance,
        RecoveryVerificationResult,
        ImmediateSev0Override,
        IncidentEvidence,
        RecoveryAuditSignoff,
        SignoffVerdict,
        AuditAckSLAPolicy,
        LIVE_AUDIT_ACK_POLICIES,
        lookup_sla,
        ALLOWED_TRANSITIONS,
        assert_allowed_transition,
        IllegalIncidentTransitionError,
    )

Codex SSOT: ``codex/04-architecture/incident-gateway-state-machine.md`` +
``codex/04-architecture/recovery-defence-in-depth-layers.md`` +
``codex/15-runbooks/alerting/audit-acknowledgement-flow.md``.
"""

from __future__ import annotations

from .canonical.crosscutting.incident import (
    ALLOWED_TRANSITIONS,
    LIVE_AUDIT_ACK_POLICIES,
    ActionProvenance,
    ActionStatus,
    ActionType,
    AgentActionEvent,
    AuditAckSLAPolicy,
    IllegalIncidentTransitionError,
    ImmediateSev0Override,
    IncidentEnvelope,
    IncidentEvidence,
    IncidentState,
    RecoveryAuditSignoff,
    RecoveryVerificationResult,
    SignoffVerdict,
    assert_allowed_transition,
    lookup_sla,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "ActionProvenance",
    "ActionStatus",
    "ActionType",
    "AgentActionEvent",
    "AuditAckSLAPolicy",
    "IllegalIncidentTransitionError",
    "ImmediateSev0Override",
    "IncidentEnvelope",
    "IncidentEvidence",
    "IncidentState",
    "LIVE_AUDIT_ACK_POLICIES",
    "RecoveryAuditSignoff",
    "RecoveryVerificationResult",
    "SignoffVerdict",
    "assert_allowed_transition",
    "lookup_sla",
]
