"""Unit tests for deployment.py — cloud-agnostic deployment schemas."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from unified_api_contracts.internal.deployment import (
    VM_INFRASTRUCTURE_EVENTS,
    CloudProvider,
    ComputeType,
    DeploymentState,
    DeploymentStatus,
    PhaseMode,
    RuntimeMode,
    ShardEvent,
    VMEventType,
)

# ---------------------------------------------------------------------------
# Enum values
# ---------------------------------------------------------------------------


def test_cloud_provider_values() -> None:
    assert CloudProvider.GCP == "gcp"
    assert CloudProvider.AWS == "aws"
    assert CloudProvider.LOCAL == "local"


def test_runtime_mode_values() -> None:
    assert RuntimeMode.BATCH == "batch"
    assert RuntimeMode.LIVE == "live"


def test_deployment_status_values() -> None:
    assert DeploymentStatus.PENDING == "pending"
    assert DeploymentStatus.RUNNING == "running"
    assert DeploymentStatus.COMPLETED == "completed"
    assert DeploymentStatus.FAILED == "failed"
    assert DeploymentStatus.CANCELLED == "cancelled"
    assert DeploymentStatus.TIMED_OUT == "timed_out"


def test_compute_type_values() -> None:
    assert ComputeType.CLOUD_RUN == "cloud_run"
    assert ComputeType.VM == "vm"
    assert ComputeType.BATCH == "batch"
    assert ComputeType.EC2 == "ec2"


def test_vm_event_type_values() -> None:
    assert VMEventType.VM_PREEMPTED == "VM_PREEMPTED"
    assert VMEventType.JOB_COMPLETED == "JOB_COMPLETED"
    assert VMEventType.LIVE_HEALTH_CHECK_PASSED == "LIVE_HEALTH_CHECK_PASSED"
    assert VMEventType.LIVE_ROLLBACK_EXECUTED == "LIVE_ROLLBACK_EXECUTED"


def test_vm_infrastructure_events_subset() -> None:
    assert VMEventType.VM_PREEMPTED in VM_INFRASTRUCTURE_EVENTS
    assert VMEventType.CONTAINER_OOM in VM_INFRASTRUCTURE_EVENTS
    assert VMEventType.CLOUD_RUN_REVISION_FAILED in VM_INFRASTRUCTURE_EVENTS
    # Job lifecycle events are NOT infrastructure events
    assert VMEventType.JOB_STARTED not in VM_INFRASTRUCTURE_EVENTS
    assert VMEventType.LIVE_HEALTH_CHECK_PASSED not in VM_INFRASTRUCTURE_EVENTS


# ---------------------------------------------------------------------------
# ShardEvent round-trip
# ---------------------------------------------------------------------------


def test_shard_event_roundtrip_jsonl() -> None:
    ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)
    event = ShardEvent(
        deployment_id="dep-123",
        shard_id="shard-0",
        event_type=VMEventType.JOB_STARTED,
        message="Shard started on zone us-central1-a",
        timestamp=ts,
        metadata={"zone": "us-central1-a"},
    )
    jsonl = event.to_jsonl()
    data = json.loads(jsonl)
    assert data["deployment_id"] == "dep-123"
    assert data["shard_id"] == "shard-0"
    assert data["event_type"] == "JOB_STARTED"
    assert data["metadata"]["zone"] == "us-central1-a"

    restored = ShardEvent.from_jsonl(jsonl)
    assert restored.deployment_id == event.deployment_id
    assert restored.event_type == VMEventType.JOB_STARTED
    assert restored.timestamp == ts


def test_shard_event_is_vm_event() -> None:
    vm_event = ShardEvent(
        deployment_id="d",
        shard_id="s",
        event_type=VMEventType.VM_PREEMPTED,
        message="preempted",
    )
    job_event = ShardEvent(
        deployment_id="d",
        shard_id="s",
        event_type=VMEventType.JOB_COMPLETED,
        message="done",
    )
    assert vm_event.is_vm_event is True
    assert job_event.is_vm_event is False


def test_shard_event_default_timestamp_is_utc() -> None:
    event = ShardEvent(
        deployment_id="d",
        shard_id="s",
        event_type=VMEventType.JOB_STARTED,
        message="started",
    )
    assert event.timestamp.tzinfo is not None


def test_shard_event_from_jsonl_missing_metadata() -> None:
    line = json.dumps(
        {
            "deployment_id": "d",
            "shard_id": "s",
            "event_type": "JOB_FAILED",
            "message": "failed",
            "timestamp": "2026-03-10T12:00:00+00:00",
        }
    )
    event = ShardEvent.from_jsonl(line)
    assert event.metadata == {}
    assert event.event_type == VMEventType.JOB_FAILED


# ---------------------------------------------------------------------------
# DeploymentState
# ---------------------------------------------------------------------------


def _make_state(**overrides: object) -> DeploymentState:
    base: dict[str, object] = {
        "deployment_id": "dep-001",
        "service": "ml-training-service",
        "status": DeploymentStatus.RUNNING,
        "tag": "v1.2.3",
        "region": "us-central1",
        "created_at": "2026-03-10T10:00:00+00:00",
        "updated_at": "2026-03-10T10:05:00+00:00",
        "total_shards": 10,
        "completed_shards": 4,
        "failed_shards": 0,
    }
    base.update(overrides)
    return DeploymentState(**base)  # type: ignore[arg-type]


def test_deployment_state_defaults() -> None:
    state = _make_state()
    assert state.deploy_mode == RuntimeMode.BATCH
    assert state.cloud_provider == CloudProvider.GCP
    assert state.compute_type == ComputeType.VM
    assert state.phase_mode == PhaseMode.PHASE_3
    assert state.parameters == {}


def test_deployment_state_explicit_fields() -> None:
    state = _make_state(
        deploy_mode=RuntimeMode.LIVE,
        cloud_provider=CloudProvider.AWS,
        compute_type=ComputeType.EC2,
        phase_mode=PhaseMode.PHASE_1,
    )
    assert state.deploy_mode == RuntimeMode.LIVE
    assert state.cloud_provider == CloudProvider.AWS
    assert state.compute_type == ComputeType.EC2
    assert state.phase_mode == PhaseMode.PHASE_1


def test_deployment_state_progress_pct() -> None:
    state = _make_state(total_shards=10, completed_shards=4)
    assert state.progress_pct == 40.0


def test_deployment_state_progress_pct_zero_shards() -> None:
    state = _make_state(total_shards=0, completed_shards=0)
    assert state.progress_pct == 0.0


def test_deployment_state_is_terminal() -> None:
    running = _make_state(status=DeploymentStatus.RUNNING)
    completed = _make_state(status=DeploymentStatus.COMPLETED)
    failed = _make_state(status=DeploymentStatus.FAILED)
    assert running.is_terminal is False
    assert completed.is_terminal is True
    assert failed.is_terminal is True


def test_deployment_state_json_roundtrip() -> None:
    state = _make_state(
        deploy_mode=RuntimeMode.LIVE,
        cloud_provider=CloudProvider.AWS,
        phase_mode=PhaseMode.PHASE_2,
        parameters={"batch_size": 32},
    )
    serialised = state.model_dump_json()
    restored = DeploymentState.model_validate_json(serialised)
    assert restored.deploy_mode == RuntimeMode.LIVE
    assert restored.cloud_provider == CloudProvider.AWS
    assert restored.phase_mode == PhaseMode.PHASE_2
    assert restored.parameters["batch_size"] == 32


def test_deployment_state_backwards_compat_missing_new_fields() -> None:
    """Old state files without deploy_mode/cloud_provider/phase_mode should load cleanly."""
    old_state_json = json.dumps(
        {
            "deployment_id": "dep-old",
            "service": "instruments-service",
            "status": "completed",
            "tag": "v0.9.0",
            "region": "europe-west1",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T01:00:00+00:00",
            "total_shards": 1,
            "completed_shards": 1,
            "failed_shards": 0,
        }
    )
    state = DeploymentState.model_validate_json(old_state_json)
    assert state.deploy_mode == RuntimeMode.BATCH
    assert state.cloud_provider == CloudProvider.GCP
    assert state.phase_mode == PhaseMode.PHASE_3


# ---------------------------------------------------------------------------
# Top-level imports
# ---------------------------------------------------------------------------


def test_top_level_imports() -> None:
    """Verify all deployment types are importable from the top-level package."""
    import unified_api_contracts.internal as uic

    assert hasattr(uic, "CloudProvider")
    assert hasattr(uic, "RuntimeMode")
    assert hasattr(uic, "DeploymentStatus")
    assert hasattr(uic, "ComputeType")
    assert hasattr(uic, "VMEventType")
    assert hasattr(uic, "ShardEvent")
    assert hasattr(uic, "DeploymentState")
    assert hasattr(uic, "VM_INFRASTRUCTURE_EVENTS")


@pytest.mark.parametrize(
    "status",
    [
        DeploymentStatus.COMPLETED,
        DeploymentStatus.FAILED,
        DeploymentStatus.CANCELLED,
        DeploymentStatus.TIMED_OUT,
    ],
)
def test_terminal_statuses(status: DeploymentStatus) -> None:
    state = _make_state(status=status)
    assert state.is_terminal is True


@pytest.mark.parametrize("status", [DeploymentStatus.PENDING, DeploymentStatus.RUNNING])
def test_non_terminal_statuses(status: DeploymentStatus) -> None:
    state = _make_state(status=status)
    assert state.is_terminal is False
