"""
AWS Cloud SDK (boto3) Pydantic request/response schemas.

Covers EC2, ECS, Lambda, S3, Glue, and Service Quotas APIs.
Field names mirror boto3 response keys (camelCase) for direct validation.
See README.md in this package for boto3 vs aioboto3 (sync vs async).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Common / Shared
# ---------------------------------------------------------------------------


class AwsErrorResponse(BaseModel):
    """Common AWS API error response structure."""

    Error: dict[str, str] | None = None
    ResponseMetadata: dict[str, object] | None = None


# ---------------------------------------------------------------------------
# EC2
# ---------------------------------------------------------------------------


class EC2RunInstancesRequest(BaseModel):
    """Request schema for ec2.run_instances()."""

    ImageId: str
    MinCount: int = 1
    MaxCount: int = 1
    InstanceType: str | None = None
    KeyName: str | None = None
    SecurityGroupIds: list[str] | None = None
    SecurityGroups: list[str] | None = None
    SubnetId: str | None = None
    UserData: str | None = None
    IamInstanceProfile: dict[str, str] | None = None
    BlockDeviceMappings: list[dict[str, object]] | None = None
    TagSpecifications: list[dict[str, object]] | None = None
    DryRun: bool | None = None
    ClientToken: str | None = None


class EC2InstanceState(BaseModel):
    """EC2 instance state."""

    Code: int | None = None
    Name: str | None = None  # pending|running|shutting-down|terminated|stopping|stopped


class EC2Instance(BaseModel):
    """EC2 instance from run_instances/describe_instances response."""

    InstanceId: str | None = None
    InstanceType: str | None = None
    State: EC2InstanceState | None = None
    Architecture: str | None = None
    LaunchTime: datetime | None = None
    Placement: dict[str, str] | None = None
    PrivateIpAddress: str | None = None
    PublicIpAddress: str | None = None
    SubnetId: str | None = None
    VpcId: str | None = None
    ImageId: str | None = None
    KeyName: str | None = None
    SecurityGroups: list[dict[str, str]] | None = None
    Tags: list[dict[str, str]] | None = None


class EC2RunInstancesResponse(BaseModel):
    """Response from ec2.run_instances()."""

    ReservationId: str | None = None
    OwnerId: str | None = None
    Instances: list[EC2Instance] | None = None
    Groups: list[dict[str, str]] | None = None


class EC2DescribeInstancesRequest(BaseModel):
    """Request schema for ec2.describe_instances()."""

    InstanceIds: list[str] | None = None
    Filters: list[dict[str, list[str]]] | None = None
    MaxResults: int | None = None
    NextToken: str | None = None
    DryRun: bool | None = None


class EC2Reservation(BaseModel):
    """Reservation from describe_instances."""

    ReservationId: str | None = None
    OwnerId: str | None = None
    Instances: list[EC2Instance] | None = None
    Groups: list[dict[str, str]] | None = None


class EC2DescribeInstancesResponse(BaseModel):
    """Response from ec2.describe_instances()."""

    Reservations: list[EC2Reservation] | None = None
    NextToken: str | None = None


class EC2StartInstancesRequest(BaseModel):
    """Request for ec2.start_instances()."""

    InstanceIds: list[str]
    DryRun: bool | None = None


class EC2StopInstancesRequest(BaseModel):
    """Request for ec2.stop_instances()."""

    InstanceIds: list[str]
    Force: bool | None = None
    DryRun: bool | None = None


class EC2TerminateInstancesRequest(BaseModel):
    """Request for ec2.terminate_instances()."""

    InstanceIds: list[str]
    DryRun: bool | None = None


class EC2InstanceStateChange(BaseModel):
    """Instance state change from start/stop/terminate."""

    InstanceId: str | None = None
    CurrentState: EC2InstanceState | None = None
    PreviousState: EC2InstanceState | None = None


class EC2StartStopTerminateResponse(BaseModel):
    """Response from start_instances, stop_instances, terminate_instances."""

    StartingInstances: list[EC2InstanceStateChange] | None = None
    StoppingInstances: list[EC2InstanceStateChange] | None = None
    TerminatingInstances: list[EC2InstanceStateChange] | None = None


# ---------------------------------------------------------------------------
# ECS
# ---------------------------------------------------------------------------


class ECSRunTaskRequest(BaseModel):
    """Request schema for ecs.run_task()."""

    cluster: str
    taskDefinition: str
    count: int | None = 1
    launchType: Literal["EC2", "FARGATE"] | None = None
    networkConfiguration: dict[str, object] | None = None
    overrides: dict[str, object] | None = None
    startedBy: str | None = None


class ECSTask(BaseModel):
    """ECS task from run_task/describe_tasks response."""

    taskArn: str | None = None
    clusterArn: str | None = None
    taskDefinitionArn: str | None = None
    lastStatus: str | None = None
    desiredStatus: str | None = None
    cpu: str | None = None
    memory: str | None = None
    startedAt: datetime | None = None
    stoppedAt: datetime | None = None


class ECSRunTaskResponse(BaseModel):
    """Response from ecs.run_task()."""

    tasks: list[ECSTask] | None = None
    failures: list[dict[str, str]] | None = None


class ECSDescribeTasksRequest(BaseModel):
    """Request for ecs.describe_tasks()."""

    cluster: str
    tasks: list[str]
    include: list[str] | None = None


class ECSDescribeTasksResponse(BaseModel):
    """Response from ecs.describe_tasks()."""

    tasks: list[ECSTask] | None = None
    failures: list[dict[str, str]] | None = None


# ---------------------------------------------------------------------------
# Lambda
# ---------------------------------------------------------------------------


class LambdaInvokeRequest(BaseModel):
    """Request schema for lambda.invoke()."""

    FunctionName: str
    InvocationType: Literal["Event", "RequestResponse", "DryRun"] | None = "RequestResponse"
    Payload: bytes | str | None = None
    Qualifier: str | None = None


class LambdaInvokeResponse(BaseModel):
    """Response from lambda.invoke()."""

    StatusCode: int | None = None
    ExecutedVersion: str | None = None
    Payload: bytes | None = None
    FunctionError: str | None = None  # Unhandled|Handled
    LogResult: str | None = None


# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------


class S3CreateBucketRequest(BaseModel):
    """Request schema for s3.create_bucket()."""

    Bucket: str
    ACL: str | None = None
    CreateBucketConfiguration: dict[str, str] | None = None  # LocationConstraint


class S3CreateBucketResponse(BaseModel):
    """Response from s3.create_bucket()."""

    Location: str | None = None


class S3ListObjectsV2Request(BaseModel):
    """Request schema for s3.list_objects_v2()."""

    Bucket: str
    Prefix: str | None = None
    Delimiter: str | None = None
    MaxKeys: int | None = 1000
    ContinuationToken: str | None = None
    StartAfter: str | None = None
    FetchOwner: bool | None = None


class S3ObjectOwner(BaseModel):
    """S3 object owner."""

    DisplayName: str | None = None
    ID: str | None = None


class S3ObjectSummary(BaseModel):
    """S3 object summary from list_objects_v2 Contents."""

    Key: str | None = None
    LastModified: datetime | None = None
    ETag: str | None = None
    Size: int | None = None
    StorageClass: str | None = None
    Owner: S3ObjectOwner | None = None


class S3ListObjectsV2Response(BaseModel):
    """Response from s3.list_objects_v2()."""

    IsTruncated: bool | None = None
    Contents: list[S3ObjectSummary] | None = None
    Name: str | None = None
    Prefix: str | None = None
    MaxKeys: int | None = None
    KeyCount: int | None = None
    NextContinuationToken: str | None = None
    ContinuationToken: str | None = None
    CommonPrefixes: list[dict[str, str]] | None = None


class S3PutObjectRequest(BaseModel):
    """Request schema for s3.put_object()."""

    Bucket: str
    Key: str
    Body: bytes | None = None
    ContentType: str | None = None
    ContentLength: int | None = None
    Metadata: dict[str, str] | None = None
    StorageClass: str | None = None


class S3PutObjectResponse(BaseModel):
    """Response from s3.put_object()."""

    ETag: str | None = None
    VersionId: str | None = None


class S3GetObjectRequest(BaseModel):
    """Request schema for s3.get_object()."""

    Bucket: str
    Key: str
    Range: str | None = None
    VersionId: str | None = None


class S3GetObjectResponse(BaseModel):
    """Response from s3.get_object(). Body is stream; metadata only here."""

    Body: object | None = None  # StreamingBody - not modeled
    ContentLength: int | None = None
    ContentType: str | None = None
    ETag: str | None = None
    LastModified: datetime | None = None
    Metadata: dict[str, str] | None = None


# ---------------------------------------------------------------------------
# Glue
# ---------------------------------------------------------------------------


class GlueCreateTableRequest(BaseModel):
    """Request schema for glue.create_table()."""

    DatabaseName: str
    TableInput: dict[str, object]  # Name, StorageDescriptor, PartitionKeys, etc.


class GlueCreateTableResponse(BaseModel):
    """Response from glue.create_table(). No response body."""

    model_config = {"extra": "allow"}


class GlueGetTableRequest(BaseModel):
    """Request for glue.get_table()."""

    DatabaseName: str
    Name: str
    CatalogId: str | None = None


class GlueTable(BaseModel):
    """Glue table from get_table/get_tables."""

    Name: str | None = None
    DatabaseName: str | None = None
    Description: str | None = None
    StorageDescriptor: dict[str, object] | None = None
    PartitionKeys: list[dict[str, object]] | None = None
    CreateTime: datetime | None = None
    UpdateTime: datetime | None = None


class GlueGetTableResponse(BaseModel):
    """Response from glue.get_table()."""

    Table: GlueTable | None = None


class GlueGetTablesRequest(BaseModel):
    """Request for glue.get_tables()."""

    DatabaseName: str
    CatalogId: str | None = None
    Expression: str | None = None
    NextToken: str | None = None
    MaxResults: int | None = None


class GlueGetTablesResponse(BaseModel):
    """Response from glue.get_tables()."""

    TableList: list[GlueTable] | None = None
    NextToken: str | None = None


class GlueGetDatabaseRequest(BaseModel):
    """Request for glue.get_database()."""

    Name: str
    CatalogId: str | None = None


class GlueDatabase(BaseModel):
    """Glue database from get_database."""

    Name: str | None = None
    Description: str | None = None
    LocationUri: str | None = None
    CreateTime: datetime | None = None


class GlueGetDatabaseResponse(BaseModel):
    """Response from glue.get_database()."""

    Database: GlueDatabase | None = None


# ---------------------------------------------------------------------------
# Service Quotas
# ---------------------------------------------------------------------------


class ServiceQuotasGetServiceQuotaRequest(BaseModel):
    """Request for service-quotas.get_service_quota()."""

    ServiceCode: str
    QuotaCode: str


class ServiceQuota(BaseModel):
    """Service quota from get_service_quota/list_service_quotas."""

    ServiceCode: str | None = None
    ServiceName: str | None = None
    QuotaArn: str | None = None
    QuotaCode: str | None = None
    QuotaName: str | None = None
    Value: float | None = None
    Unit: str | None = None
    Adjustable: bool | None = None
    UsageMetric: dict[str, object] | None = None


class ServiceQuotasGetServiceQuotaResponse(BaseModel):
    """Response from service-quotas.get_service_quota()."""

    Quota: ServiceQuota | None = None


class ServiceQuotasListServiceQuotasRequest(BaseModel):
    """Request for service-quotas.list_service_quotas()."""

    ServiceCode: str
    NextToken: str | None = None
    MaxResults: int | None = None


class ServiceQuotasListServiceQuotasResponse(BaseModel):
    """Response from service-quotas.list_service_quotas()."""

    Quotas: list[ServiceQuota] | None = None
    NextToken: str | None = None


# ---------------------------------------------------------------------------
# Service Quotas Error Schemas
# ---------------------------------------------------------------------------


class ServiceQuotasErrorDetail(BaseModel):
    """Error detail from Service Quotas API."""

    ErrorCode: str | None = None
    ErrorMessage: str | None = None


class ServiceQuotasErrorResponse(BaseModel):
    """Error response from Service Quotas API."""

    Error: ServiceQuotasErrorDetail | None = None
    ResponseMetadata: dict[str, object] | None = None


# ---------------------------------------------------------------------------
# Quota Schemas (EC2, ECS, Lambda, S3 - via Service Quotas or describe)
# ---------------------------------------------------------------------------


class EC2QuotaInfo(BaseModel):
    """EC2 quota info (from Service Quotas or describe)."""

    QuotaName: str | None = None
    QuotaCode: str | None = None
    Value: float | None = None
    Unit: str | None = None


class ECSQuotaInfo(BaseModel):
    """ECS quota info."""

    QuotaName: str | None = None
    QuotaCode: str | None = None
    Value: float | None = None


class LambdaQuotaInfo(BaseModel):
    """Lambda quota info."""

    QuotaName: str | None = None
    QuotaCode: str | None = None
    Value: float | None = None


class S3QuotaInfo(BaseModel):
    """S3 quota info."""

    QuotaName: str | None = None
    QuotaCode: str | None = None
    Value: float | None = None


# ===========================================================================
# AWS CloudWatch Logs (equivalent of GCP Cloud Logging)
# boto3 client: cloudwatch_logs = boto3.client('logs')
# ===========================================================================


class CloudWatchLogGroup(BaseModel):
    """CloudWatch Logs log group. boto3: logs.describe_log_groups()"""

    logGroupName: str | None = None
    creationTime: int | None = None  # Unix ms
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

    timestamp: int | None = None  # Unix ms
    message: str | None = None
    ingestionTime: int | None = None
    logStreamName: str | None = None  # included in filter_log_events results


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
    filterPattern: str | None = None  # e.g. "{$.level = ERROR}"
    nextToken: str | None = None
    limit: int | None = None


class CloudWatchInsightsQuery(BaseModel):
    """CloudWatch Logs Insights query. logs.start_query() / get_query_results()

    SQL-like syntax for log analysis:
    fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20
    """

    logGroupName: str | None = None
    logGroupNames: list[str] | None = None
    startTime: int | None = None
    endTime: int | None = None
    queryString: str | None = None  # CloudWatch Logs Insights query language
    queryId: str | None = None  # returned by start_query
    status: str | None = None  # Running, Complete, Failed, Cancelled, Timeout, Unknown
    results: list[list[dict]] | None = None  # [[{field, value},...],...]


class CloudWatchLogsQuotaUsage(BaseModel):
    """CloudWatch Logs quota usage. Equivalent of GCP CloudLoggingQuotaUsage."""

    log_groups_count: int | None = None
    ingestion_gb_per_month: float | None = None
    query_data_scanned_gb: float | None = None


# ===========================================================================
# AWS CloudWatch Metrics (equivalent of GCP Cloud Monitoring)
# boto3 client: cw = boto3.client('cloudwatch')
# ===========================================================================


class CloudWatchMetricDimension(BaseModel):
    """Dimension for a CloudWatch metric (e.g. FunctionName=my-function)."""

    Name: str | None = None
    Value: str | None = None


class CloudWatchMetricDatapoint(BaseModel):
    """Single data point in a metric time series. cw.get_metric_statistics()"""

    Timestamp: str | None = None  # ISO 8601
    SampleCount: float | None = None
    Average: float | None = None
    Sum: float | None = None
    Minimum: float | None = None
    Maximum: float | None = None
    Unit: str | None = None  # Seconds, Bytes, Count, Percent, etc.


class CloudWatchGetMetricStatisticsRequest(BaseModel):
    """Request for cw.get_metric_statistics()"""

    Namespace: str | None = None  # e.g. "AWS/Lambda", "AWS/ECS", "AWS/S3"
    MetricName: str | None = None
    Dimensions: list[CloudWatchMetricDimension] | None = None
    StartTime: str | None = None
    EndTime: str | None = None
    Period: int | None = None  # Seconds (60, 300, 3600, etc.)
    Statistics: list[str] | None = None  # Sum, Average, Minimum, Maximum, SampleCount
    ExtendedStatistics: list[str] | None = None  # p99, p50, etc.
    Unit: str | None = None


class CloudWatchAlarm(BaseModel):
    """CloudWatch alarm. cw.describe_alarms()

    Equivalent of GCP Monitoring AlertPolicy.
    """

    AlarmName: str | None = None
    AlarmArn: str | None = None
    AlarmDescription: str | None = None
    StateValue: str | None = None  # OK, ALARM, INSUFFICIENT_DATA
    StateReason: str | None = None
    Namespace: str | None = None
    MetricName: str | None = None
    Dimensions: list[CloudWatchMetricDimension] | None = None
    Period: int | None = None
    EvaluationPeriods: int | None = None
    Threshold: float | None = None
    ComparisonOperator: str | None = None
    AlarmActions: list[str] | None = None  # ARNs (SNS topics, Auto Scaling, etc.)
    OKActions: list[str] | None = None
    InsufficientDataActions: list[str] | None = None


# ===========================================================================
# AWS EventBridge (equivalent of GCP Cloud Scheduler + Pub/Sub routing)
# boto3 client: eb = boto3.client('events')
# ===========================================================================


class EventBridgeRule(BaseModel):
    """EventBridge rule. eb.list_rules() / eb.describe_rule()

    Rules trigger on schedule (cron/rate) or event pattern matching.
    Equivalent of GCP Cloud Scheduler + Cloud Pub/Sub subscription routing.
    """

    Name: str | None = None
    Arn: str | None = None
    EventPattern: str | None = None  # JSON pattern for event matching
    ScheduleExpression: str | None = None  # cron(0 12 * * ? *) or rate(5 minutes)
    State: str | None = None  # ENABLED, DISABLED
    Description: str | None = None
    EventBusName: str | None = None
    CreatedBy: str | None = None


class EventBridgeTarget(BaseModel):
    """Target for an EventBridge rule. eb.list_targets_by_rule()"""

    Id: str | None = None
    Arn: str | None = None  # Lambda ARN, SQS ARN, ECS task def, etc.
    RoleArn: str | None = None
    Input: str | None = None  # Static JSON to pass to target
    InputPath: str | None = None  # JSONPath into event
    InputTransformer: dict[str, object] | None = None
    EcsParameters: dict[str, object] | None = None  # For ECS task targets
    HttpParameters: dict[str, object] | None = None  # For API Gateway / HTTP targets


class EventBridgePutEventsRequest(BaseModel):
    """Publish custom events to EventBridge. eb.put_events()"""

    Entries: list[dict[str, object]] | None = None  # [{Source, DetailType, Detail, EventBusName, Time, Resources}]


class EventBridgePutEventsResponse(BaseModel):
    """Response from put_events()."""

    FailedEntryCount: int | None = None
    Entries: list[dict[str, object]] | None = None  # [{EventId, ErrorCode, ErrorMessage}]


# ===========================================================================
# AWS CodeBuild (equivalent of GCP Cloud Build)
# boto3 client: cb = boto3.client('codebuild')
# ===========================================================================


class CodeBuildProject(BaseModel):
    """CodeBuild project. cb.batch_get_projects()

    Equivalent of GCP Cloud Build trigger configuration.
    """

    name: str | None = None
    arn: str | None = None
    description: str | None = None
    source: dict[str, object] | None = None  # {type: GITHUB/S3/CODECOMMIT, location, buildspec}
    sourceVersion: str | None = None  # branch/tag
    artifacts: dict[str, object] | None = None  # {type: S3/NO_ARTIFACTS, location, name}
    environment: dict[str, object] | None = None  # {type: LINUX_CONTAINER, image, computeType, privilegedMode}
    serviceRole: str | None = None  # IAM role ARN
    timeoutInMinutes: int | None = None
    queuedTimeoutInMinutes: int | None = None
    encryptionKey: str | None = None
    created: str | None = None
    lastModified: str | None = None
    badge: dict[str, object] | None = None


class CodeBuildBuild(BaseModel):
    """CodeBuild build run. cb.batch_get_builds() / cb.start_build()

    Equivalent of GCP CloudBuildBuild.
    """

    id: str | None = None
    arn: str | None = None
    buildNumber: int | None = None
    startTime: str | None = None
    endTime: str | None = None
    currentPhase: str | None = None
    buildStatus: str | None = None  # SUCCEEDED, FAILED, FAULT, TIMED_OUT, IN_PROGRESS, STOPPED
    projectName: str | None = None
    phases: list[dict[str, object]] | None = None  # [{phaseType, phaseStatus, startTime, endTime, durationInSeconds}]
    source: dict[str, object] | None = None
    sourceVersion: str | None = None
    artifacts: dict[str, object] | None = None
    environment: dict[str, object] | None = None
    logs: dict[str, object] | None = None  # {groupName, streamName, deepLink, cloudWatchLogsArn}
    timeoutInMinutes: int | None = None
    buildComplete: bool | None = None
    initiator: str | None = None
    encryptionKey: str | None = None


class CodeBuildStartBuildRequest(BaseModel):
    """Start a CodeBuild build. cb.start_build()"""

    projectName: str | None = None
    sourceVersion: str | None = None  # Override branch/commit
    artifactsOverride: dict[str, object] | None = None
    environmentVariablesOverride: list[dict[str, object]] | None = None  # [{name, value, type}]
    imageOverride: str | None = None
    buildspecOverride: str | None = None


# ===========================================================================
# AWS Secrets Manager (equivalent of GCP Secret Manager)
# boto3 client: sm = boto3.client('secretsmanager')
# ===========================================================================


class SecretsManagerSecret(BaseModel):
    """Secrets Manager secret metadata. sm.list_secrets() / sm.describe_secret()

    Equivalent of GCP SecretVersion.
    """

    ARN: str | None = None
    Name: str | None = None
    Description: str | None = None
    KmsKeyId: str | None = None
    RotationEnabled: bool | None = None
    RotationLambdaARN: str | None = None
    LastRotatedDate: str | None = None
    LastChangedDate: str | None = None
    LastAccessedDate: str | None = None
    DeletedDate: str | None = None
    Tags: list[dict[str, object]] | None = None  # [{Key, Value}]
    SecretVersionsToStages: dict[str, list[str]] | None = None  # {versionId: [AWSCURRENT, AWSPREVIOUS]}


class SecretsManagerGetSecretValueRequest(BaseModel):
    """Request to get secret value. sm.get_secret_value()

    Equivalent of GCP SecretAccessRequest.
    """

    SecretId: str | None = None  # Name or ARN
    VersionId: str | None = None
    VersionStage: str | None = None  # "AWSCURRENT" (default) or "AWSPREVIOUS"


class SecretsManagerGetSecretValueResponse(BaseModel):
    """Secret value response. Equivalent of GCP SecretAccessResponse."""

    ARN: str | None = None
    Name: str | None = None
    VersionId: str | None = None
    SecretBinary: bytes | None = None
    SecretString: str | None = None  # JSON string or raw secret
    VersionStages: list[str] | None = None
    CreatedDate: str | None = None


class SecretsManagerCreateSecretRequest(BaseModel):
    """Create a new secret. sm.create_secret()"""

    Name: str | None = None
    Description: str | None = None
    KmsKeyId: str | None = None
    SecretString: str | None = None
    SecretBinary: bytes | None = None
    Tags: list[dict[str, object]] | None = None
    AddReplicaRegions: list[dict[str, object]] | None = None


# ===========================================================================
# AWS SQS (equivalent of GCP Pub/Sub — message queuing)
# boto3 client: sqs = boto3.client('sqs')
# ===========================================================================


class SqsMessage(BaseModel):
    """SQS message. sqs.receive_message() returns Messages list.

    Equivalent of GCP PubSubReceivedMessage.
    """

    MessageId: str | None = None
    ReceiptHandle: str | None = None  # Used for deletion after processing
    MD5OfBody: str | None = None
    Body: str | None = None  # Message payload
    Attributes: dict[str, str] | None = None  # {ApproximateReceiveCount, SentTimestamp, ...}
    MessageAttributes: dict[str, object] | None = None  # {name: {DataType, StringValue}}


class SqsSendMessageRequest(BaseModel):
    """Send a message to SQS. sqs.send_message()

    Equivalent of GCP PubSubPublishRequest.
    """

    QueueUrl: str | None = None
    MessageBody: str | None = None
    DelaySeconds: int | None = None
    MessageAttributes: dict[str, object] | None = None
    MessageGroupId: str | None = None  # FIFO queues only
    MessageDeduplicationId: str | None = None  # FIFO queues only


class SqsSendMessageResponse(BaseModel):
    """Response from sqs.send_message()."""

    MD5OfMessageBody: str | None = None
    MD5OfMessageAttributes: str | None = None
    MessageId: str | None = None
    SequenceNumber: str | None = None  # FIFO queues only


class SqsReceiveMessageRequest(BaseModel):
    """Request to receive messages. sqs.receive_message()

    Equivalent of GCP PubSubPullRequest.
    """

    QueueUrl: str | None = None
    MaxNumberOfMessages: int | None = None  # 1-10
    WaitTimeSeconds: int | None = None  # Long polling: 0-20
    VisibilityTimeout: int | None = None
    MessageAttributeNames: list[str] | None = None
    AttributeNames: list[str] | None = None


class SqsQueueAttributes(BaseModel):
    """SQS queue attributes. sqs.get_queue_attributes()"""

    QueueArn: str | None = None
    ApproximateNumberOfMessages: str | None = None
    ApproximateNumberOfMessagesNotVisible: str | None = None
    ApproximateNumberOfMessagesDelayed: str | None = None
    CreatedTimestamp: str | None = None
    LastModifiedTimestamp: str | None = None
    VisibilityTimeout: str | None = None
    MaximumMessageSize: str | None = None
    MessageRetentionPeriod: str | None = None
    ReceiveMessageWaitTimeSeconds: str | None = None
    RedrivePolicy: str | None = None  # JSON string with deadLetterTargetArn and maxReceiveCount


# ===========================================================================
# AWS SNS (equivalent of GCP Pub/Sub — fan-out publish)
# boto3 client: sns = boto3.client('sns')
# ===========================================================================


class SnsPublishRequest(BaseModel):
    """Publish to SNS topic. sns.publish()

    Equivalent of GCP PubSubPublishRequest (fan-out to multiple subscribers).
    """

    TopicArn: str | None = None
    TargetArn: str | None = None  # For direct device/endpoint publish
    PhoneNumber: str | None = None  # For SMS
    Message: str | None = None
    Subject: str | None = None
    MessageStructure: str | None = None  # "json" for per-protocol messages
    MessageAttributes: dict[str, object] | None = None
    MessageGroupId: str | None = None  # FIFO topics only
    MessageDeduplicationId: str | None = None


class SnsTopic(BaseModel):
    """SNS topic. sns.list_topics() / sns.get_topic_attributes()"""

    TopicArn: str | None = None
    DisplayName: str | None = None
    SubscriptionsConfirmed: str | None = None
    SubscriptionsPending: str | None = None
    SubscriptionsDeleted: str | None = None
    Policy: str | None = None
    Owner: str | None = None
    FifoTopic: str | None = None  # "true" or "false"
    ContentBasedDeduplication: str | None = None


class SnsSubscription(BaseModel):
    """SNS subscription. sns.list_subscriptions_by_topic()"""

    SubscriptionArn: str | None = None
    Owner: str | None = None
    Protocol: str | None = None  # http/https/email/sms/sqs/lambda/firehose
    Endpoint: str | None = None  # URL, email, phone, SQS ARN, Lambda ARN
    TopicArn: str | None = None


# ===========================================================================
# AWS IAM (equivalent of GCP IAM)
# boto3 client: iam = boto3.client('iam')
# ===========================================================================


class AwsIamUser(BaseModel):
    """IAM user. iam.get_user() / iam.list_users()

    Equivalent of GCP ServiceAccount (human or programmatic users).
    """

    UserName: str | None = None
    UserId: str | None = None
    Arn: str | None = None  # arn:aws:iam::{account}:user/{name}
    Path: str | None = None
    CreateDate: str | None = None
    PasswordLastUsed: str | None = None
    PermissionsBoundary: dict[str, object] | None = None
    Tags: list[dict[str, object]] | None = None


class AwsIamRole(BaseModel):
    """IAM role. iam.get_role() / iam.list_roles()

    Equivalent of GCP IAM Role. Roles are assumed by services/users.
    """

    RoleName: str | None = None
    RoleId: str | None = None
    Arn: str | None = None  # arn:aws:iam::{account}:role/{name}
    Path: str | None = None
    AssumeRolePolicyDocument: dict[str, object] | None = None  # Trust policy (who can assume)
    CreateDate: str | None = None
    Description: str | None = None
    MaxSessionDuration: int | None = None
    PermissionsBoundary: dict[str, object] | None = None
    Tags: list[dict[str, object]] | None = None


class AwsIamPolicy(BaseModel):
    """IAM managed policy. iam.get_policy()

    Equivalent of GCP IamPolicy (role-to-members binding).
    """

    PolicyName: str | None = None
    PolicyId: str | None = None
    Arn: str | None = None
    Path: str | None = None
    DefaultVersionId: str | None = None
    AttachmentCount: int | None = None
    CreateDate: str | None = None
    UpdateDate: str | None = None
    Description: str | None = None
    IsAttachable: bool | None = None


class AwsIamPolicyDocument(BaseModel):
    """IAM policy document (JSON policy). iam.get_policy_version()

    Contains Statement list — each grants/denies actions on resources.
    """

    Version: str | None = None  # "2012-10-17"
    Statement: list[dict[str, object]] | None = None  # [{Effect, Action, Resource, Principal, Condition}]


class AwsAssumeRoleRequest(BaseModel):
    """Assume an IAM role. sts.assume_role()

    Equivalent of GCP ServiceAccountImpersonationRequest.
    """

    RoleArn: str | None = None  # arn:aws:iam::{account}:role/{role}
    RoleSessionName: str | None = None  # Identifier for the session
    DurationSeconds: int | None = None  # 900-43200 (default 3600)
    ExternalId: str | None = None  # For cross-account role assumption
    Policy: str | None = None  # JSON inline session policy (restrict permissions)
    Tags: list[dict[str, object]] | None = None
    TransitiveTagKeys: list[str] | None = None


class AwsAssumeRoleResponse(BaseModel):
    """Credentials from sts.assume_role(). Equivalent of GCP ServiceAccountImpersonationResponse."""

    Credentials: dict[str, object] | None = None  # {AccessKeyId, SecretAccessKey, SessionToken, Expiration}
    AssumedRoleUser: dict[str, object] | None = None  # {AssumedRoleId, Arn}


class AwsIamAccessKey(BaseModel):
    """IAM access key. iam.list_access_keys() / iam.create_access_key()

    Equivalent of GCP ServiceAccountKey.
    """

    UserName: str | None = None
    AccessKeyId: str | None = None
    Status: str | None = None  # Active, Inactive
    SecretAccessKey: str | None = None  # Only on create_access_key
    CreateDate: str | None = None


# ===========================================================================
# AWS ECR (Elastic Container Registry — equivalent of GCP Artifact Registry Docker)
# boto3 client: ecr = boto3.client('ecr')
# ===========================================================================


class EcrRepository(BaseModel):
    """ECR repository. ecr.describe_repositories()

    Equivalent of GCP ArtifactRepository (format=DOCKER).
    """

    repositoryName: str | None = None
    repositoryArn: str | None = None
    registryId: str | None = None
    repositoryUri: str | None = None  # {account}.dkr.ecr.{region}.amazonaws.com/{name}
    createdAt: str | None = None
    imageTagMutability: str | None = None  # MUTABLE, IMMUTABLE
    imageScanningConfiguration: dict[str, object] | None = None
    encryptionConfiguration: dict[str, object] | None = None


class EcrImage(BaseModel):
    """ECR image. ecr.describe_images()

    Equivalent of GCP DockerImage.
    """

    registryId: str | None = None
    repositoryName: str | None = None
    imageDigest: str | None = None  # sha256:...
    imageTags: list[str] | None = None
    imageSizeInBytes: int | None = None
    imagePushedAt: str | None = None
    imageScanStatus: dict[str, object] | None = None
    imageManifestMediaType: str | None = None


class EcrGetAuthorizationTokenResponse(BaseModel):
    """ECR auth token for docker login. ecr.get_authorization_token()

    Token is base64(user:password) valid 12 hours.
    Usage: docker login -u AWS -p {decoded_password} {proxyEndpoint}
    """

    authorizationData: list[dict[str, object]] | None = None  # [{authorizationToken, expiresAt, proxyEndpoint}]


class EcrLifecyclePolicy(BaseModel):
    """ECR lifecycle policy — auto-delete old images. ecr.put_lifecycle_policy()

    Equivalent of GCP ArtifactRegistryCleanupPolicy.
    """

    registryId: str | None = None
    repositoryName: str | None = None
    lifecyclePolicyText: str | None = None  # JSON policy string
    lastEvaluatedAt: str | None = None


# ===========================================================================
# AWS Cost Explorer (equivalent of GCP Cloud Billing)
# boto3 client: ce = boto3.client('ce')
# ===========================================================================


class CostExplorerDateInterval(BaseModel):
    """Date range for Cost Explorer queries."""

    Start: str | None = None  # YYYY-MM-DD
    End: str | None = None


class CostExplorerGetCostRequest(BaseModel):
    """Request for ce.get_cost_and_usage()

    Equivalent of GCP BillingCostEntry (querying BigQuery billing export).
    """

    TimePeriod: CostExplorerDateInterval | None = None
    Granularity: str | None = None  # DAILY, MONTHLY, HOURLY
    Filter: dict[str, object] | None = None  # {Dimensions: {Key: SERVICE, Values: [...]}, Tags: ...}
    Metrics: list[str] | None = None  # ["BlendedCost", "UnblendedCost", "UsageQuantity", "NormalizedUsageAmount"]
    GroupBy: list[dict[str, object]] | None = None  # [{Type: DIMENSION, Key: SERVICE}] — group by service/tag/account


class CostExplorerResultByTime(BaseModel):
    """Cost result for a single time period. One entry per granularity period."""

    TimePeriod: dict[str, str] | None = None  # {Start, End}
    Total: dict[str, object] | None = None  # {BlendedCost: {Amount, Unit}}
    Groups: list[dict[str, object]] | None = None  # [{Keys: [service_name], Metrics: {...}}]
    Estimated: bool | None = None


class CostExplorerGetCostResponse(BaseModel):
    """Response from ce.get_cost_and_usage()"""

    ResultsByTime: list[CostExplorerResultByTime] | None = None
    NextPageToken: str | None = None
    DimensionValueAttributes: list[dict[str, object]] | None = None


class CostExplorerBudget(BaseModel):
    """AWS Budget. budgets.describe_budget()

    Equivalent of GCP BudgetAlert.
    """

    BudgetName: str | None = None
    BudgetLimit: dict[str, object] | None = None  # {Amount, Unit: "USD"}
    PlannedBudgetLimits: dict[str, object] | None = None
    CostFilters: dict[str, object] | None = None
    CostTypes: dict[str, object] | None = None
    TimeUnit: str | None = None  # DAILY, MONTHLY, QUARTERLY, ANNUALLY
    TimePeriod: dict[str, str] | None = None
    CalculatedSpend: dict[str, object] | None = None  # {ActualSpend, ForecastedSpend}
    BudgetType: str | None = None  # COST, USAGE, RI_UTILIZATION, RI_COVERAGE, SAVINGS_PLANS_*
    LastUpdatedTime: str | None = None
    AutoAdjustData: dict[str, object] | None = None


class AwsQuotaUsage(BaseModel):
    """Consolidated quota usage across key AWS services."""

    region: str | None = None
    sqs_queues_count: int | None = None
    sns_topics_count: int | None = None
    ecr_repositories_count: int | None = None
    codebuild_concurrent_builds: int | None = None
    secrets_manager_secrets_count: int | None = None
    iam_roles_count: int | None = None
    cost_mtd_usd: float | None = None  # Month-to-date spend from Cost Explorer


# ===========================================================================
# AWS Cognito (equivalent of Firebase Auth + Google OAuth2 user management)
# boto3 client: cognito = boto3.client('cognito-idp')
# Also: cognito-identity for federated identity pools
# ===========================================================================


class CognitoUserPool(BaseModel):
    """Cognito User Pool. cognito.describe_user_pool()

    Equivalent of Firebase Auth project / Google Identity Platform tenant.
    """

    Id: str | None = None
    Name: str | None = None
    Policies: dict | None = None  # {PasswordPolicy: {MinimumLength, ...}}
    LambdaConfig: dict | None = None  # Pre/post auth triggers
    Status: str | None = None  # Enabled, Disabled
    LastModifiedDate: str | None = None
    CreationDate: str | None = None
    SchemaAttributes: list[dict] | None = None  # Custom user attributes
    AutoVerifiedAttributes: list[str] | None = None  # email, phone_number
    AliasAttributes: list[str] | None = None  # email, phone_number, preferred_username
    UsernameAttributes: list[str] | None = None
    SmsVerificationMessage: str | None = None
    EmailVerificationMessage: str | None = None
    MfaConfiguration: str | None = None  # OFF, ON, OPTIONAL
    UserPoolTags: dict | None = None
    Arn: str | None = None
    AccountRecoverySetting: dict | None = None


class CognitoUser(BaseModel):
    """Cognito user record. cognito.admin_get_user() / list_users()

    Equivalent of Firebase AuthUser / GCP FirebaseAuthUser.
    """

    Username: str | None = None
    UserAttributes: list[dict] | None = None  # [{Name, Value}] — email, sub, custom:*
    UserCreateDate: str | None = None
    UserLastModifiedDate: str | None = None
    Enabled: bool | None = None
    UserStatus: str | None = None  # CONFIRMED, UNCONFIRMED, ARCHIVED, COMPROMISED, RESET_REQUIRED
    MFAOptions: list[dict] | None = None


class CognitoAuthRequest(BaseModel):
    """Initiate auth flow. cognito.initiate_auth()

    Equivalent of OAuth2TokenRequest / Firebase signInWithPassword.
    """

    AuthFlow: str | None = None  # USER_PASSWORD_AUTH, USER_SRP_AUTH, REFRESH_TOKEN_AUTH, CUSTOM_AUTH
    ClientId: str | None = None
    AuthParameters: dict | None = None  # {USERNAME, PASSWORD, REFRESH_TOKEN, etc.}
    UserPoolId: str | None = None


class CognitoAuthResponse(BaseModel):
    """Auth response with tokens. cognito.initiate_auth() result.

    Equivalent of OAuth2TokenResponse.
    """

    ChallengeName: str | None = None  # NEW_PASSWORD_REQUIRED, SMS_MFA, etc.
    AuthenticationResult: dict | None = None  # {AccessToken, IdToken, RefreshToken, ExpiresIn, TokenType}
    ChallengeParameters: dict | None = None
    Session: str | None = None


class CognitoIdentityPool(BaseModel):
    """Cognito Identity Pool (federated identities). cognito-identity.describe_identity_pool()

    Allows external identities (Google, Facebook, SAML, Cognito User Pool) to get
    temporary AWS credentials via STS. Equivalent of GCP Workload Identity Federation.
    """

    IdentityPoolId: str | None = None
    IdentityPoolName: str | None = None
    AllowUnauthenticatedIdentities: bool | None = None
    AllowClassicFlow: bool | None = None
    SupportedLoginProviders: dict | None = None  # {accounts.google.com: client_id, ...}
    DeveloperProviderName: str | None = None
    OpenIdConnectProviderARNs: list[str] | None = None
    CognitoIdentityProviders: list[dict] | None = None
    SamlProviderARNs: list[str] | None = None
    IdentityPoolTags: dict | None = None


class CognitoGetCredentialsResponse(BaseModel):
    """Temporary AWS credentials from Cognito Identity Pool.
    cognito-identity.get_credentials_for_identity()

    Equivalent of GCP ServiceAccountImpersonationResponse.
    """

    IdentityId: str | None = None
    Credentials: dict | None = None  # {AccessKeyId, SecretKey, SessionToken, Expiration}


# ===========================================================================
# AWS DynamoDB (equivalent of Google Firestore — NoSQL document/key-value store)
# boto3 client: ddb = boto3.client('dynamodb') or boto3.resource('dynamodb')
# ===========================================================================


class DynamoDbTableDescription(BaseModel):
    """DynamoDB table metadata. ddb.describe_table()

    Equivalent of Firestore collection configuration.
    """

    TableName: str | None = None
    TableArn: str | None = None
    TableId: str | None = None
    TableStatus: str | None = None  # CREATING, UPDATING, DELETING, ACTIVE
    CreationDateTime: str | None = None
    TableSizeBytes: int | None = None
    ItemCount: int | None = None
    KeySchema: list[dict] | None = None  # [{AttributeName, KeyType: HASH/RANGE}]
    AttributeDefinitions: list[dict] | None = None  # [{AttributeName, AttributeType: S/N/B}]
    ProvisionedThroughput: dict | None = None  # {ReadCapacityUnits, WriteCapacityUnits}
    BillingModeSummary: dict | None = None  # {BillingMode: PAY_PER_REQUEST/PROVISIONED}
    GlobalSecondaryIndexes: list[dict] | None = None
    LocalSecondaryIndexes: list[dict] | None = None
    StreamSpecification: dict | None = None
    SSEDescription: dict | None = None
    Replicas: list[dict] | None = None  # Global table replicas


class DynamoDbGetItemRequest(BaseModel):
    """Get a single item by primary key. ddb.get_item()

    Equivalent of Firestore document.get().
    """

    TableName: str | None = None
    Key: dict | None = None  # {pk: {S: "value"}, sk: {N: "123"}}
    ProjectionExpression: str | None = None
    ExpressionAttributeNames: dict | None = None
    ConsistentRead: bool | None = None


class DynamoDbPutItemRequest(BaseModel):
    """Put (create or replace) a single item. ddb.put_item()

    Equivalent of Firestore document.set().
    """

    TableName: str | None = None
    Item: dict | None = None  # {field: {type: value}}
    ConditionExpression: str | None = None  # e.g. "attribute_not_exists(pk)"
    ExpressionAttributeNames: dict | None = None
    ExpressionAttributeValues: dict | None = None
    ReturnValues: str | None = None  # NONE, ALL_OLD, UPDATED_OLD, ALL_NEW, UPDATED_NEW


class DynamoDbQueryRequest(BaseModel):
    """Query items by partition key (+ optional sort key range). ddb.query()

    Equivalent of Firestore collection.where() on indexed field.
    """

    TableName: str | None = None
    IndexName: str | None = None  # GSI/LSI name
    KeyConditionExpression: str | None = None  # "pk = :pk AND sk BETWEEN :start AND :end"
    FilterExpression: str | None = None
    ExpressionAttributeNames: dict | None = None
    ExpressionAttributeValues: dict | None = None
    ProjectionExpression: str | None = None
    Limit: int | None = None
    ScanIndexForward: bool | None = None  # False = descending sort
    ExclusiveStartKey: dict | None = None  # Pagination cursor
    ConsistentRead: bool | None = None
    Select: str | None = None  # ALL_ATTRIBUTES, ALL_PROJECTED_ATTRIBUTES, COUNT, SPECIFIC_ATTRIBUTES


class DynamoDbQueryResponse(BaseModel):
    """Query result. Equivalent of Firestore QuerySnapshot."""

    Items: list[dict] | None = None  # List of DynamoDB attribute maps
    Count: int | None = None
    ScannedCount: int | None = None
    LastEvaluatedKey: dict | None = None  # Pagination cursor; None if last page
    ConsumedCapacity: dict | None = None


class DynamoDbTransactWriteRequest(BaseModel):
    """Atomic multi-item write transaction. ddb.transact_write_items()

    Equivalent of Firestore batch write / transaction.
    Up to 100 items across multiple tables, all-or-nothing.
    """

    TransactItems: list[dict] | None = None  # [{Put, Update, Delete, ConditionCheck}]
    ReturnConsumedCapacity: str | None = None
    ReturnItemCollectionMetrics: str | None = None
    ClientRequestToken: str | None = None  # Idempotency key


class DynamoDbStreamRecord(BaseModel):
    """DynamoDB Stream record — change data capture for Kinesis/Lambda triggers.

    Equivalent of Firestore real-time listener updates / GCP Pub/Sub messages.
    """

    eventID: str | None = None
    eventVersion: str | None = None
    eventSource: str | None = None  # "aws:dynamodb"
    awsRegion: str | None = None
    eventName: str | None = None  # INSERT, MODIFY, REMOVE
    dynamodb: dict | None = None  # Keys, NewImage, OldImage, SequenceNumber, StreamViewType
    eventSourceARN: str | None = None


class DynamoDbQuotaUsage(BaseModel):
    """DynamoDB quota/capacity usage. Equivalent of GCP Firestore quota info."""

    region: str | None = None
    tables_count: int | None = None
    account_max_read_capacity_units: int | None = None
    account_max_write_capacity_units: int | None = None
    table_max_read_capacity_units: int | None = None
    table_max_write_capacity_units: int | None = None
