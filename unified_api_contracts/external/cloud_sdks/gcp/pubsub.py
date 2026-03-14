"""
Google Pub/Sub SDK schemas.

google.cloud.pubsub_v1. Pub/Sub is used for live service-to-service messaging.
"""

from pydantic import BaseModel, Field


class PubSubTopic(BaseModel):
    """Pub/Sub topic resource."""

    name: str | None = Field(None, description="projects/{project}/topics/{topic}")
    labels: dict[str, str] | None = Field(None, description="Topic labels")
    message_retention_duration: str | None = Field(None, description="Retention duration")
    kms_key_name: str | None = Field(None, description="KMS key for encryption")


class PubSubSubscription(BaseModel):
    """Pub/Sub subscription resource."""

    name: str | None = None
    topic: str | None = None
    push_config: dict[str, object] | None = Field(None, description="Push endpoint config")
    ack_deadline_seconds: int | None = None
    retain_acked_messages: bool | None = None
    message_retention_duration: str | None = None
    filter: str | None = Field(None, description="Subscription filter")
    enable_exactly_once_delivery: bool | None = None


class PubSubMessage(BaseModel):
    """Single Pub/Sub message."""

    data: str = Field(..., description="Base64 encoded payload")
    attributes: dict[str, str] | None = None
    ordering_key: str | None = None


class PubSubPublishRequest(BaseModel):
    """Request for Publisher.publish()."""

    topic: str = Field(..., description="Topic name (projects/{project}/topics/{topic})")
    messages: list[PubSubMessage] = Field(default_factory=list)


class PubSubPublishResponse(BaseModel):
    """Response from Publisher.publish()."""

    message_ids: list[str] = Field(default_factory=list)


class PubSubPullRequest(BaseModel):
    """Request for Subscriber.pull()."""

    subscription: str = Field(..., description="Subscription name")
    max_messages: int = Field(1000, description="Max messages to pull")


class PubSubReceivedMessage(BaseModel):
    """Received message from pull."""

    ack_id: str = Field(..., description="Ack ID for acknowledge")
    message: PubSubMessage = Field(..., description="Message payload")
    delivery_attempt: int | None = None


class PubSubPullResponse(BaseModel):
    """Response from Subscriber.pull()."""

    received_messages: list[PubSubReceivedMessage] = Field(default_factory=list)


class PubSubAcknowledgeRequest(BaseModel):
    """Request for Subscriber.acknowledge()."""

    subscription: str = Field(..., description="Subscription name")
    ack_ids: list[str] = Field(default_factory=list)


class PubSubSeekRequest(BaseModel):
    """Request for Subscriber.seek()."""

    subscription: str = Field(..., description="Subscription name")
    time: str | None = Field(None, description="Seek to timestamp")
    snapshot: str | None = Field(None, description="Seek to snapshot")


class PubSubQuotaUsage(BaseModel):
    """Pub/Sub quota usage for monitoring."""

    project_id: str = Field(..., description="Project ID")
    topic_name: str | None = None
    publish_bytes_per_second: int | None = None
    publish_requests_per_second: int | None = None
    daily_message_quota_used: int | None = None
