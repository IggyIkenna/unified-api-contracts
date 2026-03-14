from __future__ import annotations

from pydantic import BaseModel


class DynamoDbTableDescription(BaseModel):
    """DynamoDB table metadata. ddb.describe_table()"""

    TableName: str | None = None
    TableArn: str | None = None
    TableId: str | None = None
    TableStatus: str | None = None
    CreationDateTime: str | None = None
    TableSizeBytes: int | None = None
    ItemCount: int | None = None
    KeySchema: list[dict[str, object]] | None = None
    AttributeDefinitions: list[dict[str, object]] | None = None
    ProvisionedThroughput: dict[str, object] | None = None
    BillingModeSummary: dict[str, object] | None = None
    GlobalSecondaryIndexes: list[dict[str, object]] | None = None
    LocalSecondaryIndexes: list[dict[str, object]] | None = None
    StreamSpecification: dict[str, object] | None = None
    SSEDescription: dict[str, object] | None = None
    Replicas: list[dict[str, object]] | None = None


class DynamoDbGetItemRequest(BaseModel):
    """Get a single item by primary key. ddb.get_item()"""

    TableName: str | None = None
    Key: dict[str, object] | None = None
    ProjectionExpression: str | None = None
    ExpressionAttributeNames: dict[str, object] | None = None
    ConsistentRead: bool | None = None


class DynamoDbPutItemRequest(BaseModel):
    """Put (create or replace) a single item. ddb.put_item()"""

    TableName: str | None = None
    Item: dict[str, object] | None = None
    ConditionExpression: str | None = None
    ExpressionAttributeNames: dict[str, object] | None = None
    ExpressionAttributeValues: dict[str, object] | None = None
    ReturnValues: str | None = None


class DynamoDbQueryRequest(BaseModel):
    """Query items by partition key (+ optional sort key range). ddb.query()"""

    TableName: str | None = None
    IndexName: str | None = None
    KeyConditionExpression: str | None = None
    FilterExpression: str | None = None
    ExpressionAttributeNames: dict[str, object] | None = None
    ExpressionAttributeValues: dict[str, object] | None = None
    ProjectionExpression: str | None = None
    Limit: int | None = None
    ScanIndexForward: bool | None = None
    ExclusiveStartKey: dict[str, object] | None = None
    ConsistentRead: bool | None = None
    Select: str | None = None


class DynamoDbQueryResponse(BaseModel):
    """Query result. Equivalent of Firestore QuerySnapshot."""

    Items: list[dict[str, object]] | None = None
    Count: int | None = None
    ScannedCount: int | None = None
    LastEvaluatedKey: dict[str, object] | None = None
    ConsumedCapacity: dict[str, object] | None = None


class DynamoDbTransactWriteRequest(BaseModel):
    """Atomic multi-item write transaction. ddb.transact_write_items()"""

    TransactItems: list[dict[str, object]] | None = None
    ReturnConsumedCapacity: str | None = None
    ReturnItemCollectionMetrics: str | None = None
    ClientRequestToken: str | None = None


class DynamoDbStreamRecord(BaseModel):
    """DynamoDB Stream record — change data capture for Kinesis/Lambda triggers."""

    eventID: str | None = None
    eventVersion: str | None = None
    eventSource: str | None = None
    awsRegion: str | None = None
    eventName: str | None = None
    dynamodb: dict[str, object] | None = None
    eventSourceARN: str | None = None


class DynamoDbQuotaUsage(BaseModel):
    """DynamoDB quota/capacity usage. Equivalent of GCP Firestore quota info."""

    region: str | None = None
    tables_count: int | None = None
    account_max_read_capacity_units: int | None = None
    account_max_write_capacity_units: int | None = None
    table_max_read_capacity_units: int | None = None
    table_max_write_capacity_units: int | None = None
