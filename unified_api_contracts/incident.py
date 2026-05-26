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

from unified_api_contracts.canonical.crosscutting.incident import (
    ALLOWED_TRANSITIONS as ALLOWED_TRANSITIONS,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    LIVE_AUDIT_ACK_POLICIES as LIVE_AUDIT_ACK_POLICIES,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    ActionProvenance as ActionProvenance,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    ActionStatus as ActionStatus,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    ActionType as ActionType,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    AgentActionEvent as AgentActionEvent,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    AuditAckSLAPolicy as AuditAckSLAPolicy,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    IllegalIncidentTransitionError as IllegalIncidentTransitionError,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    ImmediateSev0Override as ImmediateSev0Override,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    IncidentEnvelope as IncidentEnvelope,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    IncidentEvidence as IncidentEvidence,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    IncidentState as IncidentState,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    RecoveryAuditSignoff as RecoveryAuditSignoff,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    RecoveryVerificationResult as RecoveryVerificationResult,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    SignoffVerdict as SignoffVerdict,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    assert_allowed_transition as assert_allowed_transition,
)
from unified_api_contracts.canonical.crosscutting.incident import (
    lookup_sla as lookup_sla,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "LIVE_AUDIT_ACK_POLICIES",
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
    "RecoveryAuditSignoff",
    "RecoveryVerificationResult",
    "SignoffVerdict",
    "assert_allowed_transition",
    "lookup_sla",
]
