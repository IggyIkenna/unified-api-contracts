"""Admin strategy-assignment model — Phase 9 of the archived DART UI plan.

The UAC-side source of truth for which strategy scope (family / archetype /
instance) is routed to which org, and at what access level. The UI's
``lib/entitlements/strategy-route.ts`` resolvers are a UI-side PROJECTION —
they read ``AuthUser.assigned_strategies``, which in production is sourced
from ``AdminStrategyAssignment`` records (see that file's module docstring).
This module owns the canonical assignment shape plus the exclusivity-write
validation a real backing store enforces on create/update.

SSOT flow: this model defines the assignment contract + the
``ORG_CONFLICT_ON_STRATEGY`` exclusivity rule (a ``scope_id`` LOCKED to one
org excludes every other org on that same ``scope_id``, regardless of
route); the UI (``app/(ops)/admin/strategy-assignments/``) owns the actual
persistence + CRUD surface and mirrors this shape.

See ``codex/09-strategy/architecture-v2/instruments-resolver-architecture.md``
and the archived ``dart_ui_strategy_filtering_and_onboarding_2026_04_24.plan.md``
Phase 9 for the original spec this model implements.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AssignmentScope(StrEnum):
    """Granularity of the strategy scope an assignment covers."""

    FAMILY = "family"
    ARCHETYPE = "archetype"
    INSTANCE = "instance"


class AssignmentRoute(StrEnum):
    """Access level routed to the assigned org for this scope."""

    DART = "DART"
    REPORTING_ONLY = "REPORTING_ONLY"
    LOCKED = "LOCKED"


class OrgConflictOnStrategyError(ValueError):
    """Raised when a candidate write violates the LOCKED-exclusivity rule."""


class AdminStrategyAssignment(BaseModel):
    """One admin-authored strategy -> org routing record.

    ``scope_id`` is a ``StrategyFamily`` / ``StrategyArchetype`` value or an
    instance slot label, keyed by ``scope``. A ``LOCKED`` route is
    exclusive: no other org may hold ANY assignment (regardless of that
    assignment's own route) against the same ``scope_id`` — enforced by
    :class:`AdminStrategyAssignmentWriter`, not by this model alone (a bare
    ``model_validate`` does not see the rest of the assignment set).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    assignment_id: str
    scope: AssignmentScope
    scope_id: str
    route: AssignmentRoute
    org_id: str
    config_version: str = "v1"
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str


class AdminStrategyAssignmentWriter:
    """Validates a candidate assignment against an existing assignment set.

    Construct with the full existing assignment set for the ``scope_id``
    namespace being written to, then call :meth:`validate` per candidate
    write. Raises :class:`OrgConflictOnStrategyError` rather than returning
    a bool — write-path callers should let it propagate (fail-loud) rather
    than silently dropping a conflicting assignment.
    """

    def __init__(self, existing: Iterable[AdminStrategyAssignment]) -> None:
        self._existing: tuple[AdminStrategyAssignment, ...] = tuple(existing)

    def validate(self, candidate: AdminStrategyAssignment) -> None:
        """Raise ``OrgConflictOnStrategyError`` if ``candidate`` conflicts.

        Conflict = another org already holds an assignment on the same
        ``scope_id`` AND either side's route is ``LOCKED``. Same-org
        updates (re-assigning your own org's route) are never a conflict.
        """
        for other in self._existing:
            if other.scope_id != candidate.scope_id or other.org_id == candidate.org_id:
                continue
            if other.route == AssignmentRoute.LOCKED or candidate.route == AssignmentRoute.LOCKED:
                raise OrgConflictOnStrategyError(
                    f"ORG_CONFLICT_ON_STRATEGY: scope_id={candidate.scope_id!r} is already "
                    f"assigned to org_id={other.org_id!r} (route={other.route}); cannot assign "
                    f"to org_id={candidate.org_id!r} with route={candidate.route}"
                )


__all__ = [
    "AdminStrategyAssignment",
    "AdminStrategyAssignmentWriter",
    "AssignmentRoute",
    "AssignmentScope",
    "OrgConflictOnStrategyError",
]
