"""Tests for event taxonomy expansions (strategy_system_citadel_master plan).

Covers:
- Task 1: CI/CD event types and detail models (p5-cicd-events)
- Task 2: Agent event types and AgentEventDetails model (p5-agent-events)
- Task 3: Error event hierarchy — ErrorCategory, FailedDetails extension (p5-error-event-hierarchy)
"""

from __future__ import annotations

from unified_api_contracts.internal.events import (
    AgentEventDetails,
    CascadeDispatchDetails,
    CategorizedErrorDetails,
    DeploymentDetails,
    FailedDetails,
    LifecycleEventType,
    QualityGateDetails,
    VersionBumpDetails,
)
from unified_api_contracts.internal.schemas.errors import ErrorCategory

# ═══════════════════════════════════════════════════════════════════════════
# Task 1: CI/CD event taxonomy
# ═══════════════════════════════════════════════════════════════════════════


class TestCICDEventTypes:
    """All CI/CD event types exist as valid LifecycleEventType enum members."""

    def test_qg_passed_exists(self) -> None:
        assert LifecycleEventType.QG_PASSED == "QG_PASSED"

    def test_qg_failed_exists(self) -> None:
        assert LifecycleEventType.QG_FAILED == "QG_FAILED"

    def test_deployment_started_exists(self) -> None:
        assert LifecycleEventType.DEPLOYMENT_STARTED == "DEPLOYMENT_STARTED"

    def test_deployment_completed_exists(self) -> None:
        assert LifecycleEventType.DEPLOYMENT_COMPLETED == "DEPLOYMENT_COMPLETED"

    def test_deployment_failed_exists(self) -> None:
        assert LifecycleEventType.DEPLOYMENT_FAILED == "DEPLOYMENT_FAILED"

    def test_deployment_rolled_back_exists(self) -> None:
        assert LifecycleEventType.DEPLOYMENT_ROLLED_BACK == "DEPLOYMENT_ROLLED_BACK"

    def test_version_bumped_exists(self) -> None:
        assert LifecycleEventType.VERSION_BUMPED == "VERSION_BUMPED"

    def test_cascade_dispatched_exists(self) -> None:
        assert LifecycleEventType.CASCADE_DISPATCHED == "CASCADE_DISPATCHED"

    def test_cicd_events_are_valid_enum_members(self) -> None:
        """All CI/CD events are proper LifecycleEventType members."""
        cicd_events = {
            LifecycleEventType.QG_PASSED,
            LifecycleEventType.QG_FAILED,
            LifecycleEventType.DEPLOYMENT_STARTED,
            LifecycleEventType.DEPLOYMENT_COMPLETED,
            LifecycleEventType.DEPLOYMENT_FAILED,
            LifecycleEventType.DEPLOYMENT_ROLLED_BACK,
            LifecycleEventType.VERSION_BUMPED,
            LifecycleEventType.CASCADE_DISPATCHED,
        }
        all_members = set(LifecycleEventType)
        assert cicd_events.issubset(all_members)


class TestQualityGateDetails:
    """QualityGateDetails model with basedpyright_clean field."""

    def test_instantiation_with_all_fields(self) -> None:
        details = QualityGateDetails(
            repo="unified-events-interface",
            duration_seconds=45.2,
            tests_passed=120,
            tests_failed=0,
            coverage_pct=92.5,
            basedpyright_clean=True,
        )
        assert details.repo == "unified-events-interface"
        assert details.duration_seconds == 45.2
        assert details.tests_passed == 120
        assert details.tests_failed == 0
        assert details.coverage_pct == 92.5
        assert details.basedpyright_clean is True

    def test_basedpyright_clean_defaults_true(self) -> None:
        details = QualityGateDetails(
            repo="test-repo",
            duration_seconds=10.0,
            tests_passed=50,
            tests_failed=2,
            coverage_pct=85.0,
        )
        assert details.basedpyright_clean is True

    def test_basedpyright_clean_false(self) -> None:
        details = QualityGateDetails(
            repo="test-repo",
            duration_seconds=10.0,
            tests_passed=50,
            tests_failed=2,
            coverage_pct=85.0,
            basedpyright_clean=False,
        )
        assert details.basedpyright_clean is False

    def test_serialization_round_trip(self) -> None:
        details = QualityGateDetails(
            repo="unified-internal-contracts",
            duration_seconds=30.0,
            tests_passed=200,
            tests_failed=1,
            coverage_pct=91.0,
            basedpyright_clean=False,
        )
        d = details.model_dump()
        restored = QualityGateDetails(**d)
        assert restored == details


class TestDeploymentDetails:
    """DeploymentDetails model with rollback_reason field."""

    def test_instantiation_for_started(self) -> None:
        details = DeploymentDetails(
            repo="execution-service",
            environment="staging",
            version="0.5.12",
            trigger="cascade",
        )
        assert details.repo == "execution-service"
        assert details.environment == "staging"
        assert details.version == "0.5.12"
        assert details.trigger == "cascade"
        assert details.rollback_reason is None

    def test_instantiation_for_rollback(self) -> None:
        details = DeploymentDetails(
            repo="strategy-service",
            environment="production",
            version="0.3.8",
            trigger="manual",
            rollback_reason="SIT failure: test_risk_limits_enforced",
        )
        assert details.rollback_reason == "SIT failure: test_risk_limits_enforced"

    def test_rollback_reason_defaults_none(self) -> None:
        details = DeploymentDetails(
            repo="r",
            environment="staging",
            version="0.1.0",
            trigger="cascade",
        )
        assert details.rollback_reason is None


class TestVersionBumpDetails:
    """VersionBumpDetails model instantiation."""

    def test_instantiation(self) -> None:
        details = VersionBumpDetails(
            repo="unified-trading-library",
            old_version="0.1.55",
            new_version="0.1.56",
            bump_type="patch",
            is_breaking=False,
        )
        assert details.repo == "unified-trading-library"
        assert details.old_version == "0.1.55"
        assert details.new_version == "0.1.56"
        assert details.bump_type == "patch"
        assert details.is_breaking is False

    def test_breaking_change(self) -> None:
        details = VersionBumpDetails(
            repo="unified-api-contracts",
            old_version="0.4.0",
            new_version="0.5.0",
            bump_type="minor",
            is_breaking=True,
        )
        assert details.is_breaking is True
        assert details.bump_type == "minor"


class TestCascadeDispatchDetails:
    """CascadeDispatchDetails model for CASCADE_DISPATCHED events."""

    def test_instantiation(self) -> None:
        details = CascadeDispatchDetails(
            source_repo="unified-api-contracts",
            source_version="0.4.1",
            target_repos=["execution-service", "strategy-service", "risk-service"],
            bump_type="patch",
        )
        assert details.source_repo == "unified-api-contracts"
        assert details.source_version == "0.4.1"
        assert len(details.target_repos) == 3
        assert "execution-service" in details.target_repos
        assert details.bump_type == "patch"

    def test_empty_target_repos(self) -> None:
        details = CascadeDispatchDetails(
            source_repo="unified-trading-library",
            source_version="0.1.56",
            target_repos=[],
            bump_type="patch",
        )
        assert details.target_repos == []

    def test_serialization_round_trip(self) -> None:
        details = CascadeDispatchDetails(
            source_repo="unified-events-interface",
            source_version="2.0.1",
            target_repos=["alerting-service"],
            bump_type="minor",
        )
        d = details.model_dump()
        restored = CascadeDispatchDetails(**d)
        assert restored == details


# ═══════════════════════════════════════════════════════════════════════════
# Task 2: Agent event types
# ═══════════════════════════════════════════════════════════════════════════


class TestAgentEventTypes:
    """All agent event types exist as valid LifecycleEventType enum members."""

    def test_agent_investigation_triggered_exists(self) -> None:
        assert LifecycleEventType.AGENT_INVESTIGATION_TRIGGERED == "AGENT_INVESTIGATION_TRIGGERED"

    def test_agent_investigation_completed_exists(self) -> None:
        assert LifecycleEventType.AGENT_INVESTIGATION_COMPLETED == "AGENT_INVESTIGATION_COMPLETED"

    def test_agent_fix_applied_exists(self) -> None:
        assert LifecycleEventType.AGENT_FIX_APPLIED == "AGENT_FIX_APPLIED"

    def test_agent_fix_failed_exists(self) -> None:
        assert LifecycleEventType.AGENT_FIX_FAILED == "AGENT_FIX_FAILED"

    def test_agent_events_are_valid_enum_members(self) -> None:
        agent_events = {
            LifecycleEventType.AGENT_INVESTIGATION_TRIGGERED,
            LifecycleEventType.AGENT_INVESTIGATION_COMPLETED,
            LifecycleEventType.AGENT_FIX_APPLIED,
            LifecycleEventType.AGENT_FIX_FAILED,
        }
        all_members = set(LifecycleEventType)
        assert agent_events.issubset(all_members)


class TestAgentEventDetails:
    """AgentEventDetails model with extended fields."""

    def test_minimal_instantiation(self) -> None:
        details = AgentEventDetails(
            agent_type="semver",
            repo="unified-events-interface",
            trigger_reason="feat: commit detected on staging",
        )
        assert details.agent_type == "semver"
        assert details.repo == "unified-events-interface"
        assert details.trigger_reason == "feat: commit detected on staging"
        assert details.resolution is None
        assert details.investigation_id is None
        assert details.decision is None
        assert details.reasoning_summary is None
        assert details.files_changed is None
        assert details.commit_sha is None
        assert details.error_message is None

    def test_full_instantiation(self) -> None:
        details = AgentEventDetails(
            agent_type="conflict-resolution",
            repo="unified-internal-contracts",
            trigger_reason="merge conflict on staging",
            resolution="auto-resolved",
            investigation_id="inv-2026-03-16-001",
            decision="rebase_and_merge",
            reasoning_summary="No semantic conflicts, only formatting changes",
            files_changed=["events.py", "schemas/errors.py"],
            commit_sha="abc123def456",
            error_message=None,
        )
        assert details.investigation_id == "inv-2026-03-16-001"
        assert details.decision == "rebase_and_merge"
        assert details.reasoning_summary == "No semantic conflicts, only formatting changes"
        assert details.files_changed == ["events.py", "schemas/errors.py"]
        assert details.commit_sha == "abc123def456"

    def test_fix_failed_with_error_message(self) -> None:
        details = AgentEventDetails(
            agent_type="overnight",
            repo="execution-service",
            trigger_reason="QG failure detected",
            resolution=None,
            investigation_id="inv-overnight-42",
            decision="apply_fix",
            error_message="basedpyright found 3 type errors in engine/router.py",
        )
        assert details.error_message == "basedpyright found 3 type errors in engine/router.py"
        assert details.resolution is None

    def test_serialization_round_trip(self) -> None:
        details = AgentEventDetails(
            agent_type="semver",
            repo="test-repo",
            trigger_reason="version bump needed",
            files_changed=["pyproject.toml"],
            commit_sha="deadbeef",
        )
        d = details.model_dump()
        restored = AgentEventDetails(**d)
        assert restored == details


# ═══════════════════════════════════════════════════════════════════════════
# Task 3: Error event hierarchy
# ═══════════════════════════════════════════════════════════════════════════


class TestErrorCategory:
    """ErrorCategory StrEnum has all required values."""

    def test_infrastructure_exists(self) -> None:
        assert ErrorCategory.INFRASTRUCTURE == "infrastructure"

    def test_authentication_exists(self) -> None:
        assert ErrorCategory.AUTHENTICATION == "authentication"

    def test_data_quality_exists(self) -> None:
        assert ErrorCategory.DATA_QUALITY == "data_quality"

    def test_execution_exists(self) -> None:
        assert ErrorCategory.EXECUTION == "execution"

    def test_configuration_exists(self) -> None:
        assert ErrorCategory.CONFIGURATION == "configuration"

    def test_dependency_exists(self) -> None:
        assert ErrorCategory.DEPENDENCY == "dependency"

    def test_rate_limit_exists(self) -> None:
        assert ErrorCategory.RATE_LIMIT == "rate_limit"

    def test_timeout_exists(self) -> None:
        assert ErrorCategory.TIMEOUT == "timeout"

    def test_unknown_exists(self) -> None:
        assert ErrorCategory.UNKNOWN == "unknown"

    def test_all_values_are_strings(self) -> None:
        for member in ErrorCategory:
            assert isinstance(member.value, str), f"{member.name} value must be str"
            assert member.value, f"{member.name} must be non-empty"

    def test_is_str_enum(self) -> None:
        """ErrorCategory members are strings (StrEnum)."""
        assert isinstance(ErrorCategory.INFRASTRUCTURE, str)
        assert ErrorCategory.INFRASTRUCTURE == "infrastructure"


class TestFailedDetailsExtension:
    """FailedDetails extended with error classification fields."""

    def test_original_fields_preserved(self) -> None:
        details = FailedDetails(
            error_type="ValueError",
            error_message="Invalid instrument key",
            traceback="Traceback ...",
            stage="validation",
            shard="2026-03-16",
        )
        assert details.error_type == "ValueError"
        assert details.error_message == "Invalid instrument key"
        assert details.traceback == "Traceback ..."
        assert details.stage == "validation"
        assert details.shard == "2026-03-16"

    def test_new_fields_defaults(self) -> None:
        details = FailedDetails()
        assert details.error_category is None
        assert details.is_retryable is False
        assert details.escalation_level == 0
        assert details.retry_count == 0
        assert details.first_occurrence_ts is None

    def test_full_instantiation_with_error_hierarchy(self) -> None:
        details = FailedDetails(
            error_type="TimeoutError",
            error_message="Venue API timed out after 30s",
            traceback="Traceback ...",
            stage="execution",
            error_category="timeout",
            is_retryable=True,
            escalation_level=1,
            retry_count=2,
            first_occurrence_ts="2026-03-16T10:30:00Z",
        )
        assert details.error_category == "timeout"
        assert details.is_retryable is True
        assert details.escalation_level == 1
        assert details.retry_count == 2
        assert details.first_occurrence_ts == "2026-03-16T10:30:00Z"

    def test_non_retryable_auth_failure(self) -> None:
        details = FailedDetails(
            error_type="AuthenticationError",
            error_message="API key expired",
            error_category="authentication",
            is_retryable=False,
            escalation_level=2,
        )
        assert details.is_retryable is False
        assert details.escalation_level == 2
        assert details.error_category == "authentication"

    def test_serialization_round_trip(self) -> None:
        details = FailedDetails(
            error_type="RateLimitError",
            error_message="429 Too Many Requests",
            error_category="rate_limit",
            is_retryable=True,
            escalation_level=0,
            retry_count=5,
            first_occurrence_ts="2026-03-16T09:00:00Z",
        )
        d = details.model_dump()
        restored = FailedDetails(**d)
        assert restored == details


class TestCategorizedErrorDetails:
    """CategorizedErrorDetails model instantiation."""

    def test_instantiation(self) -> None:
        details = CategorizedErrorDetails(
            error_category="infrastructure",
            error_type="ConnectionError",
            error_message="Cannot reach database",
            is_retryable=True,
            escalation_level="WARN",
        )
        assert details.error_category == "infrastructure"
        assert details.is_retryable is True
        assert details.escalation_level == "WARN"


# ═══════════════════════════════════════════════════════════════════════════
# Cross-cutting: event type count and import verification
# ═══════════════════════════════════════════════════════════════════════════


class TestLifecycleEventTypeCount:
    """LifecycleEventType enum has the expected number of members."""

    def test_enum_has_at_least_30_members(self) -> None:
        """After expansion, enum should have at least 30 members."""
        count = len(list(LifecycleEventType))
        assert count >= 30, f"Expected >= 30 LifecycleEventType members, got {count}"

    def test_all_members_are_uppercase_strings(self) -> None:
        """Every enum member value is an uppercase string matching its name."""
        for member in LifecycleEventType:
            assert isinstance(member.value, str)
            assert member.value.isupper(), f"{member.name} value must be uppercase"
            assert member.value == member.name, f"{member.name} value should match name"


class TestTopLevelImports:
    """Verify new symbols are importable from unified_api_contracts.internal root."""

    def test_cascade_dispatch_details_importable(self) -> None:
        from unified_api_contracts.internal import CascadeDispatchDetails

        assert CascadeDispatchDetails is not None

    def test_error_category_importable(self) -> None:
        from unified_api_contracts.internal import ErrorCategory

        assert ErrorCategory is not None

    def test_agent_event_details_importable(self) -> None:
        from unified_api_contracts.internal import AgentEventDetails

        assert AgentEventDetails is not None

    def test_quality_gate_details_importable(self) -> None:
        from unified_api_contracts.internal import QualityGateDetails

        assert QualityGateDetails is not None

    def test_failed_details_importable(self) -> None:
        from unified_api_contracts.internal import FailedDetails

        assert FailedDetails is not None
