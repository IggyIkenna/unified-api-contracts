"""Plan D — Strategy version records + version-governance state machine.

A ``StrategyVersion`` represents one configuration revision of a
``StrategyInstance``. The genesis version is the catalogue's shipped config
(status=ROLLED_OUT, parent_version_id=None). Every fork creates a new
``DRAFT``; promotion follows DRAFT → PENDING_APPROVAL → APPROVED → ROLLED_OUT
(retiring the prior active version on the same instance).

Approval requires the backtest series associated with the version to reach
the BACKTEST_1YR maturity floor (per Plan A's maturity ladder). The exposed
helper ``minimum_approval_maturity()`` is the SSOT — never re-hardcode this
constant in consumer code.

SSOT:
    plans/active/dart_exclusive_subscription_research_fork_2026_04_21.md
    codex/14-playbooks/shared-core/strategy-version-governance.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from unified_api_contracts.internal.domain.strategy_service.lifecycle import (
    StrategyMaturityPhase,
    maturity_phase_rank,
)

__all__ = [
    "ApprovalRecord",
    "ConfigDiff",
    "StrategyVersion",
    "VersionStatus",
    "minimum_approval_maturity",
]


def minimum_approval_maturity() -> StrategyMaturityPhase:
    """SSOT for the approval-eligibility maturity floor.

    Plan D rule: a version cannot be APPROVED unless its backtest reached
    BACKTEST_1YR coverage at minimum. This helper is imported by:
      - the UTA approve endpoint (returns 412 below floor)
      - the strategy-service ``backtest_gate.is_approval_eligible``
      - the UI admin queue (greys out Approve button below floor).
    """
    return StrategyMaturityPhase.BACKTEST_1YR


class VersionStatus(StrEnum):
    """Forward-only state machine for a ``StrategyVersion``."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ROLLED_OUT = "rolled_out"
    RETIRED = "retired"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ConfigDiff:
    """Forked-version diff against the parent version's config.

    ``changed_fields`` is a sequence of ``(field_name, old_value_str,
    new_value_str)`` tuples — string-serialised for transport. Consumers
    re-parse against the parent archetype schema for type-safety.
    ``unchanged_fingerprint`` is the sha256 hex of the unchanged subset, used
    by reviewers to confirm the draft only touches the declared fields.
    """

    base_version_id: str
    changed_fields: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)
    unchanged_fingerprint: str = ""


@dataclass(frozen=True)
class ApprovalRecord:
    """Audit record attached to an APPROVED version."""

    approved_by: str
    approved_at: datetime
    backtest_maturity: StrategyMaturityPhase
    backtest_series_ref: str
    review_notes: str | None = None


@dataclass(frozen=True)
class StrategyVersion:
    """Frozen version record. Status changes are modelled by writing a new
    record (the in-memory + Firestore stores never mutate in place).
    """

    version_id: str
    parent_instance_id: str
    maturity_phase: StrategyMaturityPhase
    status: VersionStatus
    authored_by: str
    created_at: datetime
    parent_version_id: str | None = None
    config_diff: ConfigDiff | None = None
    backtest_series_ref: str | None = None
    approval: ApprovalRecord | None = None
    rolled_out_at: datetime | None = None
    supersedes_version_id: str | None = None
    review_history: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        # Genesis invariant: no parent_version_id => no config_diff.
        if self.parent_version_id is None and self.config_diff is not None:
            raise ValueError("Genesis version (parent_version_id=None) must have config_diff=None.")
        # APPROVED invariant: approval must exist + maturity >= BACKTEST_1YR.
        if self.status is VersionStatus.APPROVED:
            if self.approval is None:
                raise ValueError(f"version_id={self.version_id} has status=APPROVED but approval=None.")
            min_phase = minimum_approval_maturity()
            if maturity_phase_rank(self.approval.backtest_maturity) < maturity_phase_rank(min_phase):
                raise ValueError(
                    f"version_id={self.version_id} approval.backtest_maturity="
                    f"{self.approval.backtest_maturity.value} is below the "
                    f"BACKTEST_1YR floor required for APPROVED status."
                )
        # ROLLED_OUT invariant: rolled_out_at must be set.
        if self.status is VersionStatus.ROLLED_OUT and self.rolled_out_at is None:
            raise ValueError(f"version_id={self.version_id} has status=ROLLED_OUT but rolled_out_at=None.")
