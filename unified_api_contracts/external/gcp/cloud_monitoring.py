"""
Google Cloud Monitoring (formerly Stackdriver) schemas.

Maps to google.cloud.monitoring_v3. Used for health checks, uptime monitoring,
alerting, and custom metrics.
"""

from pydantic import BaseModel, Field


class MonitoringPoint(BaseModel):
    """Single data point in a time series."""

    interval: dict[str, object] | None = Field(
        None,
        description="{startTime, endTime}",
    )
    value: dict[str, object] | None = Field(
        None,
        description="{int64Value, doubleValue, boolValue, stringValue}",
    )


class MonitoringTimeSeries(BaseModel):
    """Monitoring time series (metric + resource + points)."""

    metric: dict[str, object] | None = Field(
        None,
        description="{type, labels}",
    )
    resource: dict[str, object] | None = Field(
        None,
        description="{type, labels}",
    )
    points: list[MonitoringPoint] | None = None
    metric_kind: str | None = Field(
        None,
        alias="metricKind",
        description="GAUGE/DELTA/CUMULATIVE",
    )
    value_type: str | None = Field(
        None,
        alias="valueType",
        description="INT64/DOUBLE/BOOL/STRING/DISTRIBUTION",
    )

    model_config = {"populate_by_name": True}


class ListTimeSeriesRequest(BaseModel):
    """Request for MetricServiceClient.list_time_series()."""

    name: str | None = Field(None, description="projects/{p}")
    filter: str | None = Field(
        None,
        description='e.g. metric.type="run.googleapis.com/request_count"',
    )
    interval_start_time: str | None = None
    interval_end_time: str | None = None
    aggregation: dict[str, object] | None = Field(
        None,
        description="{alignmentPeriod, perSeriesAligner}",
    )
    page_token: str | None = Field(None, alias="pageToken")

    model_config = {"populate_by_name": True}


class ListTimeSeriesResponse(BaseModel):
    """Response from list_time_series()."""

    time_series: list[MonitoringTimeSeries] | None = Field(
        None,
        alias="timeSeries",
    )
    next_page_token: str | None = Field(None, alias="nextPageToken")
    execution_errors: list[dict[str, object]] | None = Field(
        None,
        alias="executionErrors",
    )

    model_config = {"populate_by_name": True}


class UptimeCheckConfig(BaseModel):
    """Uptime check configuration."""

    name: str | None = Field(
        None,
        description="projects/{p}/uptimeCheckConfigs/{c}",
    )
    display_name: str | None = Field(None, alias="displayName")
    monitored_resource: dict[str, object] | None = Field(
        None,
        alias="monitoredResource",
        description="{type: 'uptime_url', labels: {host, project_id}}",
    )
    http_check: dict[str, object] | None = Field(
        None,
        alias="httpCheck",
        description="{path, port, requestMethod, headers, useSsl, validateSsl}",
    )
    period: str | None = Field(None, description="e.g. '60s'")
    timeout: str | None = Field(None, description="e.g. '10s'")
    selected_regions: list[str] | None = Field(None, alias="selectedRegions")

    model_config = {"populate_by_name": True}


class AlertPolicy(BaseModel):
    """Alert policy resource."""

    name: str | None = Field(
        None,
        description="projects/{p}/alertPolicies/{a}",
    )
    display_name: str | None = Field(None, alias="displayName")
    conditions: list[dict[str, object]] | None = None
    notification_channels: list[str] | None = Field(None, alias="notificationChannels")
    enabled: bool | None = None
    combiner: str | None = Field(None, description="AND/OR")
    creation_record: dict[str, object] | None = Field(None, alias="creationRecord")
    mutation_record: dict[str, object] | None = Field(None, alias="mutationRecord")

    model_config = {"populate_by_name": True}


class MonitoringCreateTimeSeriesRequest(BaseModel):
    """Request for MetricServiceClient.create_time_series()."""

    name: str | None = Field(None, description="projects/{p}")
    time_series: list[MonitoringTimeSeries] | None = Field(
        None,
        alias="timeSeries",
    )

    model_config = {"populate_by_name": True}
