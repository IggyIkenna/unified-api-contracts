"""Integration tests for event taxonomy expansion in UIC.

Exercises the full Pydantic model lifecycle: construction -> serialization -> deserialization.
Verifies cross-model consistency between event types, detail models, and envelopes.
"""

from __future__ import annotations

from datetime import UTC, datetime

from unified_api_contracts.internal.events import (
    AgentEventDetails,
    CascadeDispatchDetails,
    DeploymentDetails,
    EventMetadata,
    FailedDetails,
    LifecycleEventEnvelope,
    LifecycleEventType,
    QualityGateDetails,
    VersionBumpDetails,
)
from unified_api_contracts.internal.schemas.errors import ErrorCategory


class TestEventEnvelopeWithNewEventTypes:
    """LifecycleEventEnvelope works with all new CI/CD and agent event types."""

    def test_envelope_with_deployment_rolled_back(self) -> None:
        """DEPLOYMENT_ROLLED_BACK can be used in an event envelope."""
        ts = datetime(2026, 3, 16, 14, 0, 0, tzinfo=UTC)
        envelope = LifecycleEventEnvelope(
            event=LifecycleEventType.DEPLOYMENT_ROLLED_BACK,
            service="deployment-service",
            timestamp=ts,
            metadata=EventMetadata(
                timestamp=ts,
                service_name="deployment-service",
                details={
                    "repo": "strategy-service",
                    "version": "0.3.8",
                    "rollback_reason": "SIT failure",
                },
            ),
        )
        assert envelope.event == LifecycleEventType.DEPLOYMENT_ROLLED_BACK
        d = envelope.model_dump()
        assert d["event"] == "DEPLOYMENT_ROLLED_BACK"

    def test_envelope_with_agent_fix_applied(self) -> None:
        """AGENT_FIX_APPLIED can be used in an event envelope."""
        ts = datetime(2026, 3, 16, 10, 30, 0, tzinfo=UTC)
        envelope = LifecycleEventEnvelope(
            event=LifecycleEventType.AGENT_FIX_APPLIED,
            service="agent-orchestrator",
            timestamp=ts,
            metadata=EventMetadata(
                timestamp=ts,
                service_name="agent-orchestrator",
                details={
                    "agent_type": "semver",
                    "repo": "unified-events-interface",
                    "commit_sha": "abc123",
                },
            ),
        )
        d = envelope.model_dump()
        assert d["event"] == "AGENT_FIX_APPLIED"

    def test_envelope_serialization_round_trip(self) -> None:
        """Envelope -> dict -> Envelope for each new event type."""
        ts = datetime(2026, 3, 16, 12, 0, 0, tzinfo=UTC)
        new_event_types = [
            LifecycleEventType.QG_PASSED,
            LifecycleEventType.QG_FAILED,
            LifecycleEventType.DEPLOYMENT_STARTED,
            LifecycleEventType.DEPLOYMENT_COMPLETED,
            LifecycleEventType.DEPLOYMENT_FAILED,
            LifecycleEventType.DEPLOYMENT_ROLLED_BACK,
            LifecycleEventType.VERSION_BUMPED,
            LifecycleEventType.CASCADE_DISPATCHED,
            LifecycleEventType.AGENT_INVESTIGATION_TRIGGERED,
            LifecycleEventType.AGENT_INVESTIGATION_COMPLETED,
            LifecycleEventType.AGENT_FIX_APPLIED,
            LifecycleEventType.AGENT_FIX_FAILED,
        ]
        for event_type in new_event_types:
            envelope = LifecycleEventEnvelope(
                event=event_type,
                service="test-service",
                timestamp=ts,
                metadata=EventMetadata(timestamp=ts, service_name="test-service"),
            )
            d = envelope.model_dump()
            restored = LifecycleEventEnvelope(**d)
            assert restored.event == event_type


class TestDetailModelCrossConsistency:
    """Detail models serialize correctly and can be used as event metadata."""

    def test_quality_gate_details_as_envelope_details(self) -> None:
        """QualityGateDetails can populate envelope metadata details."""
        qg = QualityGateDetails(
            repo="unified-internal-contracts",
            duration_seconds=30.0,
            tests_passed=200,
            tests_failed=0,
            coverage_pct=92.5,
            basedpyright_clean=True,
        )
        d = qg.model_dump()
        # All fields present and correct types
        assert isinstance(d["repo"], str)
        assert isinstance(d["duration_seconds"], float)
        assert isinstance(d["basedpyright_clean"], bool)

    def test_deployment_details_rollback_serialization(self) -> None:
        """DeploymentDetails with rollback_reason serializes correctly."""
        details = DeploymentDetails(
            repo="strategy-service",
            environment="production",
            version="0.3.8",
            trigger="manual",
            rollback_reason="SIT test_risk_limits failed",
        )
        d = details.model_dump()
        assert d["rollback_reason"] == "SIT test_risk_limits failed"

        restored = DeploymentDetails(**d)
        assert restored.rollback_reason == "SIT test_risk_limits failed"

    def test_cascade_dispatch_details_list_field(self) -> None:
        """CascadeDispatchDetails target_repos list survives round-trip."""
        details = CascadeDispatchDetails(
            source_repo="unified-api-contracts",
            source_version="0.4.1",
            target_repos=["execution-service", "strategy-service", "risk-service"],
            bump_type="patch",
        )
        d = details.model_dump()
        restored = CascadeDispatchDetails(**d)
        assert restored.target_repos == ["execution-service", "strategy-service", "risk-service"]

    def test_agent_event_details_files_changed_list(self) -> None:
        """AgentEventDetails files_changed list survives round-trip."""
        details = AgentEventDetails(
            agent_type="conflict-resolution",
            repo="unified-internal-contracts",
            trigger_reason="merge conflict",
            files_changed=["events.py", "schemas/errors.py", "__init__.py"],
            commit_sha="deadbeef12345678",
            investigation_id="inv-001",
        )
        d = details.model_dump()
        restored = AgentEventDetails(**d)
        assert restored.files_changed == ["events.py", "schemas/errors.py", "__init__.py"]
        assert restored.commit_sha == "deadbeef12345678"

    def test_version_bump_details_with_breaking(self) -> None:
        """VersionBumpDetails with is_breaking=True round-trips."""
        details = VersionBumpDetails(
            repo="unified-api-contracts",
            old_version="0.4.0",
            new_version="0.5.0",
            bump_type="minor",
            is_breaking=True,
        )
        d = details.model_dump()
        restored = VersionBumpDetails(**d)
        assert restored.is_breaking is True
        assert restored.bump_type == "minor"


class TestFailedDetailsErrorHierarchyIntegration:
    """FailedDetails extended error fields work with ErrorCategory values."""

    def test_failed_details_with_error_category_values(self) -> None:
        """FailedDetails accepts valid ErrorCategory string values."""
        for category in ErrorCategory:
            details = FailedDetails(
                error_type="TestError",
                error_message=f"Test error for {category.value}",
                error_category=category.value,
                is_retryable=category in {ErrorCategory.RATE_LIMIT, ErrorCategory.TIMEOUT},
            )
            assert details.error_category == category.value

    def test_failed_details_escalation_levels(self) -> None:
        """FailedDetails escalation_level works for all defined levels."""
        for level in [0, 1, 2, 3]:
            details = FailedDetails(
                error_type="TestError",
                error_message="test",
                escalation_level=level,
            )
            assert details.escalation_level == level

    def test_failed_details_retry_tracking(self) -> None:
        """FailedDetails tracks retry count and first occurrence timestamp."""
        details = FailedDetails(
            error_type="TimeoutError",
            error_message="Connection timed out",
            error_category="timeout",
            is_retryable=True,
            retry_count=3,
            first_occurrence_ts="2026-03-16T10:00:00Z",
        )
        d = details.model_dump()
        restored = FailedDetails(**d)
        assert restored.retry_count == 3
        assert restored.first_occurrence_ts == "2026-03-16T10:00:00Z"
        assert restored.is_retryable is True

    def test_error_category_configuration_value(self) -> None:
        """ErrorCategory.CONFIGURATION exists and can be used in FailedDetails."""
        details = FailedDetails(
            error_type="ConfigurationError",
            error_message="Missing required config key",
            error_category=ErrorCategory.CONFIGURATION.value,
            is_retryable=False,
            escalation_level=2,
        )
        assert details.error_category == "configuration"
