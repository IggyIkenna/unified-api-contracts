"""AuditAckSLAPolicy — per-severity escalation ladder for recovery audit acknowledgement."""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, model_validator

from unified_api_contracts.canonical.crosscutting.alerting import AlertSeverity


class AuditAckSLAPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: AlertSeverity
    default_seconds: int | None = None
    secondary_human_after_seconds: int | None = None
    founder_after_seconds: int | None = None
    physical_pager_after_seconds: int | None = None

    @model_validator(mode="after")
    def _enforce_monotonic(self) -> AuditAckSLAPolicy:
        d = self.default_seconds
        s = self.secondary_human_after_seconds
        f = self.founder_after_seconds
        p = self.physical_pager_after_seconds
        pairs = [("default_seconds", d), ("secondary_human_after_seconds", s), ("founder_after_seconds", f)]
        prev_name, prev_val = pairs[0]
        for name, val in pairs[1:]:
            if prev_val is not None and val is not None and val <= prev_val:
                raise ValueError(f"{name}={val} must be > {prev_name}={prev_val} (monotonic ladder)")
            if val is not None:
                prev_name, prev_val = name, val
        if p is not None and f is not None and p < f:
            raise ValueError(f"physical_pager_after_seconds={p} must be >= founder_after_seconds={f}")
        return self


LIVE_AUDIT_ACK_POLICIES: Final[tuple[AuditAckSLAPolicy, ...]] = (
    AuditAckSLAPolicy(
        severity=AlertSeverity.CRITICAL,
        default_seconds=300,
        secondary_human_after_seconds=600,
        founder_after_seconds=1200,
        physical_pager_after_seconds=1800,
    ),
    AuditAckSLAPolicy(
        severity=AlertSeverity.HIGH,
        default_seconds=1800,
        secondary_human_after_seconds=3600,
        founder_after_seconds=7200,
        physical_pager_after_seconds=None,
    ),
    AuditAckSLAPolicy(
        severity=AlertSeverity.WARN,
        default_seconds=14400,
        secondary_human_after_seconds=None,
        founder_after_seconds=None,
        physical_pager_after_seconds=None,
    ),
    AuditAckSLAPolicy(
        severity=AlertSeverity.INFO,
        default_seconds=None,
        secondary_human_after_seconds=None,
        founder_after_seconds=None,
        physical_pager_after_seconds=None,
    ),
)


def lookup_sla(severity: AlertSeverity) -> AuditAckSLAPolicy:
    """Return the SLA policy for a given severity. Closed-set lookup; raises
    KeyError on unknown severity (defensive — closed StrEnum)."""
    for policy in LIVE_AUDIT_ACK_POLICIES:
        if policy.severity == severity:
            return policy
    raise KeyError(f"No SLA policy for severity={severity!r}")
