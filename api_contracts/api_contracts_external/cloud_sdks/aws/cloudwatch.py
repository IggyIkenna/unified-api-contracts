from __future__ import annotations

from pydantic import BaseModel


class CloudWatchLogGroup(BaseModel):
    """CloudWatch Logs log group. boto3: logs.describe_log_groups()"""

    logGroupName: str | None = None
    creationTime: int | None = None
    retentionInDays: int | None = None
    storedBytes: int | None = None
    kmsKeyId: str | None = None
    logGroupArn: str | None = None


class CloudWatchLogStream(BaseModel):
    """CloudWatch Logs log stream within a group. logs.describe_log_streams()"""

    logStreamName: str | None = None
    creationTime: int | None = None
    firstEventTimestamp: int | None = None
    lastEventTimestamp: int | None = None
    lastIngestionTime: int | None = None
    uploadSequenceToken: str | None = None
    arn: str | None = None
    storedBytes: int | None = None


class CloudWatchLogEvent(BaseModel):
    """Single log event. logs.get_log_events() or logs.filter_log_events()"""

    timestamp: int | None = None
    message: str | None = None
    ingestionTime: int | None = None
    logStreamName: str | None = None


class CloudWatchGetLogEventsRequest(BaseModel):
    """Request for logs.get_log_events()"""

    logGroupName: str | None = None
    logStreamName: str | None = None
    startTime: int | None = None
    endTime: int | None = None
    nextToken: str | None = None
    limit: int | None = None
    startFromHead: bool | None = None


class CloudWatchFilterLogEventsRequest(BaseModel):
    """Request for logs.filter_log_events() — cross-stream filter with pattern."""

    logGroupName: str | None = None
    logStreamNames: list[str] | None = None
    startTime: int | None = None
    endTime: int | None = None
    filterPattern: str | None = None
    nextToken: str | None = None
    limit: int | None = None


class CloudWatchInsightsQuery(BaseModel):
    """CloudWatch Logs Insights query. logs.start_query() / get_query_results()"""

    logGroupName: str | None = None
    logGroupNames: list[str] | None = None
    startTime: int | None = None
    endTime: int | None = None
    queryString: str | None = None
    queryId: str | None = None
    status: str | None = None
    results: list[list[dict]] | None = None


class CloudWatchLogsQuotaUsage(BaseModel):
    """CloudWatch Logs quota usage. Equivalent of GCP CloudLoggingQuotaUsage."""

    log_groups_count: int | None = None
    ingestion_gb_per_month: float | None = None
    query_data_scanned_gb: float | None = None


class CloudWatchMetricDimension(BaseModel):
    """Dimension for a CloudWatch metric (e.g. FunctionName=my-function)."""

    Name: str | None = None
    Value: str | None = None


class CloudWatchMetricDatapoint(BaseModel):
    """Single data point in a metric time series. cw.get_metric_statistics()"""

    Timestamp: str | None = None
    SampleCount: float | None = None
    Average: float | None = None
    Sum: float | None = None
    Minimum: float | None = None
    Maximum: float | None = None
    Unit: str | None = None


class CloudWatchGetMetricStatisticsRequest(BaseModel):
    """Request for cw.get_metric_statistics()"""

    Namespace: str | None = None
    MetricName: str | None = None
    Dimensions: list[CloudWatchMetricDimension] | None = None
    StartTime: str | None = None
    EndTime: str | None = None
    Period: int | None = None
    Statistics: list[str] | None = None
    ExtendedStatistics: list[str] | None = None
    Unit: str | None = None


class CloudWatchAlarm(BaseModel):
    """CloudWatch alarm. cw.describe_alarms()"""

    AlarmName: str | None = None
    AlarmArn: str | None = None
    AlarmDescription: str | None = None
    StateValue: str | None = None
    StateReason: str | None = None
    Namespace: str | None = None
    MetricName: str | None = None
    Dimensions: list[CloudWatchMetricDimension] | None = None
    Period: int | None = None
    EvaluationPeriods: int | None = None
    Threshold: float | None = None
    ComparisonOperator: str | None = None
    AlarmActions: list[str] | None = None
    OKActions: list[str] | None = None
    InsufficientDataActions: list[str] | None = None
