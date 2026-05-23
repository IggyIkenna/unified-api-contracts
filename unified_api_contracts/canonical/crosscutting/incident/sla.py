"""AuditAckSLAPolicy — per-severity ack window + escalation ladder.

Default policy table covers CRITICAL / HIGH / WARN / INFO. Operator-tunable
overrides per-strategy via ``audit_ack_policy:`` key in strategy config.

Codex SSOT: ``codex/15-runbooks/alerting/audit-acknowledgement-flow.md``.
Implementation plan: ``plans/active/audit_acknowledgement_sla_and_state_2026_05_23.md``.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, model_validator

from unified_api_contracts.canonical.crosscutting.alerting import AlertSeverity


class AuditAckSLAPolicy(BaseModel):
    """Per-severity SLA policy.

    Time-axis values are seconds since incident transitions to
    AUDIT_REPORT_GENERATED. Escalation steps fire in order:

    1. T + default_seconds: primary on-call PagerDuty page (handled outside
       this policy; AuditAckSLAPolicy starts the clock on the secondary).
    2. T + secondary_human_after_seconds: secondary PagerDuty page.
    3. T + founder_after_seconds: founder Twilio voice call.
    4. T + physical_pager_after_seconds (if defined): physical pager fires.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    severity: AlertSeverity

    default_seconds: int | None = None
    """Initial audit-ack window. None for INFO (no enforcement)."""

    secondary_human_after_seconds: int | None = None
    """Seconds after AUDIT_REPORT_GENERATED at which secondary on-call is paged."""

    founder_after_seconds: int | None = None
    """Seconds after which founder is paged + Twilio voice fires."""

    physical_pager_after_seconds: int | None = None
    """Seconds after which physical pager device fires. None = not used at this
    severity (e.g. WARN should not trigger the pager)."""

    @model_validator(mode="after")
    def _enforce_monotonic(self) -> "AuditAckSLAPolicy":
        """The 3 core escalation timers MUST be monotonically increasing:
        default < secondary_human_after < founder_after.

        ``physical_pager_after_seconds`` is allowed to equal ``founder_after_seconds``
        ("fire alongside founder") OR be > founder. None values are skipped.
        """
        # Step 1: monotonic ladder for default / secondary / founder (strict <)
        core_ladder = [
            ("default_seconds", self.default_seconds),
            (
                "secondary_human_after_seconds",
                self.secondary_human_after_seconds,
            ),
            ("founder_after_seconds", self.founder_after_seconds),
        ]
        prev_name, prev_val = None, None
        for name, val in core_ladder:
            if val is None:
                continue
            if prev_val is not None and val <= prev_val:
                raise ValueError(
                    f"{name}={val} must be > {prev_name}={prev_val} (monotonic ladder)"
                )
            prev_name, prev_val = name, val

        # Step 2: physical_pager_after >= founder_after (may fire alongside).
        if (
            self.physical_pager_after_seconds is not None
            and self.founder_after_seconds is not None
            and self.physical_pager_after_seconds < self.founder_after_seconds
        ):
            raise ValueError(
                f"physical_pager_after_seconds={self.physical_pager_after_seconds} "
                f"must be >= founder_after_seconds={self.founder_after_seconds}"
            )
        return self


LIVE_AUDIT_ACK_POLICIES: Final[tuple[AuditAckSLAPolicy, ...]] = (
    AuditAckSLAPolicy(
        severity=AlertSeverity.CRITICAL,
        default_seconds=300,  # 5 min
        secondary_human_after_seconds=600,  # 10 min
        founder_after_seconds=1800,  # 30 min
        physical_pager_after_seconds=1800,  # alongside founder
    ),
    AuditAckSLAPolicy(
        severity=AlertSeverity.HIGH,
        default_seconds=7200,  # 2h
        secondary_human_after_seconds=10800,  # 3h
        founder_after_seconds=21600,  # 6h
        physical_pager_after_seconds=21600,  # alongside founder
    ),
    AuditAckSLAPolicy(
        severity=AlertSeverity.WARN,
        default_seconds=21600,  # 6h
        secondary_human_after_seconds=43200,  # 12h
        founder_after_seconds=86400,  # 24h
        physical_pager_after_seconds=None,  # no physical pager for WARN
    ),
    AuditAckSLAPolicy(
        severity=AlertSeverity.INFO,
        default_seconds=None,  # no enforcement
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
