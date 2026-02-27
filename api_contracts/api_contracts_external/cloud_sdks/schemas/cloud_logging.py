"""
Google Cloud Logging schemas.

Maps to google.cloud.logging_v2. Used for reading service logs from Cloud Logging
(Log Explorer queries) and for writing structured logs.
"""

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """Single log entry."""

    logName: str | None = Field(None, alias="logName")
    resource: dict[str, object] | None = Field(None, description="Monitored resource")
    timestamp: str | None = None
    severity: str | None = Field(
        None,
        description="DEFAULT/DEBUG/INFO/NOTICE/WARNING/ERROR/CRITICAL/ALERT/EMERGENCY",
    )
    insertId: str | None = Field(None, alias="insertId")
    jsonPayload: dict[str, object] | None = Field(None, alias="jsonPayload")
    textPayload: str | None = Field(None, alias="textPayload")
    labels: dict[str, str] | None = None
    trace: str | None = None
    spanId: str | None = Field(None, alias="spanId")

    model_config = {"populate_by_name": True}


class ListLogEntriesRequest(BaseModel):
    """Request for LoggingClient.list_entries()."""

    resourceNames: list[str] = Field(..., alias="resourceNames")
    filter: str | None = None
    orderBy: str | None = Field(None, alias="orderBy", description='e.g. "timestamp desc"')
    pageSize: int | None = Field(None, alias="pageSize")
    pageToken: str | None = Field(None, alias="pageToken")

    model_config = {"populate_by_name": True}


class ListLogEntriesResponse(BaseModel):
    """Response from list_entries()."""

    entries: list[LogEntry] | None = None
    nextPageToken: str | None = Field(None, alias="nextPageToken")

    model_config = {"populate_by_name": True}


class LogSink(BaseModel):
    """Log sink configuration."""

    name: str | None = None
    destination: str | None = Field(
        None,
        description="e.g. bigquery.googleapis.com/...",
    )
    filter: str | None = None
    description: str | None = None
    disabled: bool | None = None
    createTime: str | None = Field(None, alias="createTime")
    updateTime: str | None = Field(None, alias="updateTime")
    writerIdentity: str | None = Field(None, alias="writerIdentity")

    model_config = {"populate_by_name": True}


class LogMetric(BaseModel):
    """Log-based metric."""

    name: str | None = None
    description: str | None = None
    filter: str | None = None
    metricDescriptor: dict[str, object] | None = Field(None, alias="metricDescriptor")
    labelExtractors: dict[str, str] | None = Field(None, alias="labelExtractors")
    createTime: str | None = Field(None, alias="createTime")
    updateTime: str | None = Field(None, alias="updateTime")

    model_config = {"populate_by_name": True}


class WriteLogEntriesRequest(BaseModel):
    """Request for LoggingClient.write_log_entries()."""

    logName: str | None = Field(None, alias="logName")
    resource: dict[str, object] | None = None
    labels: dict[str, str] | None = None
    entries: list[LogEntry] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class CloudLoggingQuotaUsage(BaseModel):
    """Cloud Logging quota usage for monitoring."""

    project_id: str = Field(..., description="Project ID")
    log_entries_per_minute: int | None = None
    ingestion_bytes_per_day: int | None = None
