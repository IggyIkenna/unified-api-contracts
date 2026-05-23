"""Incident state machine + envelope + action + audit-ack + signoff schemas.

Top-level facade: import from ``unified_api_contracts.incident`` (see
``unified_api_contracts/__init__.py``). Internal modules:

- ``state.py`` — IncidentState (13 enum) + ALLOWED_TRANSITIONS + assert helper
- ``envelope.py`` — IncidentEnvelope (central schema)
- ``action.py`` — AgentActionEvent + ActionType (10 enum) + ActionStatus +
  ActionProvenance + RecoveryVerificationResult
- ``overrides.py`` — ImmediateSev0Override (7 enum)
- ``evidence.py`` — IncidentEvidence (14 fields)
- ``recovery_audit.py`` — RecoveryAuditSignoff + SignoffVerdict (4 enum)
- ``sla.py`` — AuditAckSLAPolicy + LIVE_AUDIT_ACK_POLICIES + lookup_sla

Codex SSOT: ``codex/04-architecture/incident-gateway-state-machine.md``.
"""

from __future__ import annotations

from unified_api_contracts.canonical.crosscutting.incident.action import (
    ActionProvenance,
    ActionStatus,
    ActionType,
    AgentActionEvent,
    RecoveryVerificationResult,
)
from unified_api_contracts.canonical.crosscutting.incident.envelope import (
    IncidentEnvelope,
)
from unified_api_contracts.canonical.crosscutting.incident.evidence import (
    IncidentEvidence,
)
from unified_api_contracts.canonical.crosscutting.incident.overrides import (
    ImmediateSev0Override,
)
from unified_api_contracts.canonical.crosscutting.incident.recovery_audit import (
    RecoveryAuditSignoff,
    SignoffVerdict,
)
from unified_api_contracts.canonical.crosscutting.incident.sla import (
    LIVE_AUDIT_ACK_POLICIES,
    AuditAckSLAPolicy,
    lookup_sla,
)
from unified_api_contracts.canonical.crosscutting.incident.state import (
    ALLOWED_TRANSITIONS,
    IllegalIncidentTransitionError,
    IncidentState,
    assert_allowed_transition,
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
