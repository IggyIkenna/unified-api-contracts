"""Closed-set sanity tests for the UAC DependencyClass + DependencyHealthPolicy.

Phase 1 of ``plans/active/connectivity_dependency_buffer_policy_2026_05_23.md``.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.dependency import DependencyClass, DependencyHealthPolicy


def test_dependency_class_has_5_members() -> None:
    assert len(list(DependencyClass)) == 5


def test_dependency_class_closed_set() -> None:
    classes = set(DependencyClass)
    assert classes == {
        DependencyClass.EXECUTION_CRITICAL_EXTERNAL,
        DependencyClass.MARKET_DATA_CRITICAL_EXTERNAL,
        DependencyClass.INTERNAL_CONTROL_PLANE,
        DependencyClass.INTERNAL_DATA_PLANE,
        DependencyClass.ALERTING_AND_OBSERVABILITY,
    }


def test_dependency_health_policy_minimal_construction() -> None:
    p = DependencyHealthPolicy(
        dependency_id="binance_rest",
        dependency_class=DependencyClass.EXECUTION_CRITICAL_EXTERNAL,
        expected_recovery_time_seconds=60,
        hard_escalation_seconds=1800,
        fallback_available=True,
        owner="ikenna@odum-research.com",
        runbook_doc="codex/15-runbooks/incidents/RB-CONN-002.md",
    )
    assert p.warning_buffer_seconds == 60  # default
    assert p.human_investigation_buffer_seconds == 900  # 15min default
    assert p.protected_mode_available is False  # default


def test_dependency_health_policy_requires_owner() -> None:
    with pytest.raises(ValidationError):
        DependencyHealthPolicy(
            dependency_id="binance_rest",
            dependency_class=DependencyClass.EXECUTION_CRITICAL_EXTERNAL,
            expected_recovery_time_seconds=60,
            hard_escalation_seconds=1800,
            fallback_available=True,
            runbook_doc="codex/15-runbooks/incidents/RB-CONN-002.md",
            # owner missing
        )  # type: ignore[call-arg]
