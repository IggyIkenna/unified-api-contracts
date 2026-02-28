"""Internal lifecycle event schemas — envelope structure, all event types, per-type metadata."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class LifecycleEventType(StrEnum):
    # Universal
    STARTED = "STARTED"
    VALIDATION_STARTED = "VALIDATION_STARTED"
    VALIDATION_COMPLETED = "VALIDATION_COMPLETED"
    DATA_INGESTION_STARTED = "DATA_INGESTION_STARTED"
    DATA_INGESTION_COMPLETED = "DATA_INGESTION_COMPLETED"
    PROCESSING_STARTED = "PROCESSING_STARTED"
    PROCESSING_COMPLETED = "PROCESSING_COMPLETED"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    # Batch-specific
    UPLOAD_STARTED = "UPLOAD_STARTED"
    UPLOAD_COMPLETED = "UPLOAD_COMPLETED"
    # Live-specific (replace UPLOAD_*)
    DATA_BROADCAST = "DATA_BROADCAST"
    PERSISTENCE_STARTED = "PERSISTENCE_STARTED"
    PERSISTENCE_COMPLETED = "PERSISTENCE_COMPLETED"
    # Security / audit
    AUTH_FAILURE = "AUTH_FAILURE"
    CONFIG_CHANGED = "CONFIG_CHANGED"
    SECRET_ACCESSED = "SECRET_ACCESSED"


class EventSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ServiceMode(StrEnum):
    BATCH = "batch"
    LIVE = "live"


# ---------------------------------------------------------------------------
# Per-event metadata payloads (the ``details`` dict typed as a model)
# ---------------------------------------------------------------------------


class StartedDetails(BaseModel):
    """Metadata for STARTED events."""

    mode: ServiceMode | None = None
    config_snapshot: dict[str, str | int | float | bool] | None = None


class ValidationStartedDetails(BaseModel):
    validation_type: str = "preflight"
    dependencies: list[str] | None = None


class ValidationCompletedDetails(BaseModel):
    duration_ms: float | None = None
    dependencies_checked: int | None = None
    all_available: bool | None = None


class DataIngestionDetails(BaseModel):
    source: str | None = None
    shard: str | None = None
    date: str | None = None
    venue: str | None = None


class DataIngestionCompletedDetails(DataIngestionDetails):
    rows_loaded: int | None = None
    bytes_read: int | None = None
    duration_ms: float | None = None


class ProcessingStartedDetails(BaseModel):
    shard: str | None = None
    instrument_count: int | None = None


class ProcessingCompletedDetails(BaseModel):
    shard: str | None = None
    rows: int | None = None
    duration_ms: float | None = None
    success: bool | None = None


class UploadStartedDetails(BaseModel):
    bucket: str | None = None
    path: str | None = None
    row_count: int | None = None


class UploadCompletedDetails(BaseModel):
    bucket: str | None = None
    path: str | None = None
    files_written: int | None = None
    total_bytes: int | None = None
    duration_ms: float | None = None


class DataBroadcastDetails(BaseModel):
    topic: str | None = None
    messages_published: int | None = None
    instrument_key: str | None = None


class PersistenceStartedDetails(BaseModel):
    bucket: str | None = None
    path: str | None = None


class PersistenceCompletedDetails(BaseModel):
    bucket: str | None = None
    path: str | None = None
    files_written: int | None = None
    total_bytes: int | None = None


class StoppedDetails(BaseModel):
    reason: str | None = None
    total_duration_ms: float | None = None


class FailedDetails(BaseModel):
    error_type: str | None = None
    error_message: str | None = None
    traceback: str | None = None
    stage: str | None = None
    shard: str | None = None


class AuthFailureDetails(BaseModel):
    auth_type: Annotated[str, Field(description="api_key | oauth | jwt | mtls")] | None = None
    username: str | None = None
    failure_reason: str | None = None
    ip_address: str | None = None
    endpoint: str | None = None
    attempt_count: int | None = None


class ConfigChangedDetails(BaseModel):
    config_file: str | None = None
    changed_by: str | None = None
    change_type: Annotated[str, Field(description="update | create | delete")] | None = None
    authorized: bool | None = None
    git_commit_sha: str | None = None
    fields_changed: list[str] | None = None


class SecretAccessedDetails(BaseModel):
    secret_name: str
    caller_identity: str
    operation: Annotated[str, Field(description="access | create | delete | rotate")] = "access"
    success: bool = True
    version: str | None = None


# ---------------------------------------------------------------------------
# Event envelope — what GCSEventSink writes (one JSON line in JSONL)
# ---------------------------------------------------------------------------


class EventMetadata(BaseModel):
    """Inner metadata dict embedded in every event."""

    timestamp: datetime
    service_name: str
    severity: EventSeverity = EventSeverity.INFO
    details: dict[str, str | int | float | bool | list[str] | None] = Field(default_factory=dict)
    client_id: str | None = None
    correlation_id: str | None = None


class LifecycleEventEnvelope(BaseModel):
    """Top-level shape of every event written to GCS JSONL or published to Pub/Sub.

    GCS path: ```events/{service_name}/{YYYY-MM-DD}/events.jsonl```
    """

    event: LifecycleEventType
    service: str
    timestamp: datetime
    metadata: EventMetadata


class PubSubLifecycleEventMessage(BaseModel):
    """Pub/Sub variant — no top-level timestamp (only in metadata)."""

    event: LifecycleEventType
    service: str
    metadata: EventMetadata


# ---------------------------------------------------------------------------
# Typed convenience wrappers for well-known event types
# ---------------------------------------------------------------------------


class StartedEvent(BaseModel):
    event: Literal[LifecycleEventType.STARTED] = LifecycleEventType.STARTED
    service: str
    timestamp: datetime
    details: StartedDetails = Field(default_factory=StartedDetails)


class FailedEvent(BaseModel):
    event: Literal[LifecycleEventType.FAILED] = LifecycleEventType.FAILED
    service: str
    timestamp: datetime
    details: FailedDetails = Field(default_factory=FailedDetails)


class AuthFailureEvent(BaseModel):
    event: Literal[LifecycleEventType.AUTH_FAILURE] = LifecycleEventType.AUTH_FAILURE
    service: str
    timestamp: datetime
    details: AuthFailureDetails


class ConfigChangedEvent(BaseModel):
    event: Literal[LifecycleEventType.CONFIG_CHANGED] = LifecycleEventType.CONFIG_CHANGED
    service: str
    timestamp: datetime
    details: ConfigChangedDetails


class SecretAccessedEvent(BaseModel):
    event: Literal[LifecycleEventType.SECRET_ACCESSED] = LifecycleEventType.SECRET_ACCESSED
    service: str
    timestamp: datetime
    details: SecretAccessedDetails
