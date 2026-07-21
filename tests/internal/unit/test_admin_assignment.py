"""Tests for architecture_v2 admin strategy-assignment model (Phase 9)."""

from __future__ import annotations

import pytest

from unified_api_contracts.internal import (
    AdminStrategyAssignment,
    AdminStrategyAssignmentWriter,
    AssignmentRoute,
    AssignmentScope,
    OrgConflictOnStrategyError,
)


def _assignment(
    *,
    assignment_id: str = "asg-1",
    scope: AssignmentScope = AssignmentScope.ARCHETYPE,
    scope_id: str = "ML_DIRECTIONAL",
    route: AssignmentRoute = AssignmentRoute.DART,
    org_id: str = "org-alpha",
) -> AdminStrategyAssignment:
    return AdminStrategyAssignment(
        assignment_id=assignment_id,
        scope=scope,
        scope_id=scope_id,
        route=route,
        org_id=org_id,
        created_by="admin@example.com",
    )


def test_assignment_defaults() -> None:
    assignment = _assignment()
    assert assignment.config_version == "v1"
    assert assignment.notes == ""
    assert assignment.created_at.tzinfo is not None


def test_assignment_is_frozen() -> None:
    assignment = _assignment()
    with pytest.raises(Exception):
        assignment.org_id = "org-beta"  # type: ignore[misc]


def test_writer_allows_same_org_update() -> None:
    existing = _assignment(org_id="org-alpha", route=AssignmentRoute.DART)
    writer = AdminStrategyAssignmentWriter([existing])
    candidate = _assignment(assignment_id="asg-2", org_id="org-alpha", route=AssignmentRoute.LOCKED)
    writer.validate(candidate)  # should not raise


def test_writer_allows_different_org_non_locked() -> None:
    existing = _assignment(org_id="org-alpha", route=AssignmentRoute.DART)
    writer = AdminStrategyAssignmentWriter([existing])
    candidate = _assignment(assignment_id="asg-2", org_id="org-beta", route=AssignmentRoute.REPORTING_ONLY)
    writer.validate(candidate)  # should not raise


def test_writer_rejects_locked_conflict_from_existing() -> None:
    existing = _assignment(org_id="org-alpha", route=AssignmentRoute.LOCKED)
    writer = AdminStrategyAssignmentWriter([existing])
    candidate = _assignment(assignment_id="asg-2", org_id="org-beta", route=AssignmentRoute.DART)
    with pytest.raises(OrgConflictOnStrategyError, match="ORG_CONFLICT_ON_STRATEGY"):
        writer.validate(candidate)


def test_writer_rejects_locked_conflict_from_candidate() -> None:
    existing = _assignment(org_id="org-alpha", route=AssignmentRoute.DART)
    writer = AdminStrategyAssignmentWriter([existing])
    candidate = _assignment(assignment_id="asg-2", org_id="org-beta", route=AssignmentRoute.LOCKED)
    with pytest.raises(OrgConflictOnStrategyError, match="ORG_CONFLICT_ON_STRATEGY"):
        writer.validate(candidate)


def test_writer_ignores_different_scope_id() -> None:
    existing = _assignment(scope_id="ML_DIRECTIONAL", org_id="org-alpha", route=AssignmentRoute.LOCKED)
    writer = AdminStrategyAssignmentWriter([existing])
    candidate = _assignment(
        assignment_id="asg-2",
        scope_id="VOL_TRADING_OPTIONS",
        org_id="org-beta",
        route=AssignmentRoute.LOCKED,
    )
    writer.validate(candidate)  # different scope_id — no conflict
