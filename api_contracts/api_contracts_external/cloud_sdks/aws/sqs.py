from __future__ import annotations

from pydantic import BaseModel


class SqsMessage(BaseModel):
    """SQS message. sqs.receive_message() returns Messages list."""

    MessageId: str | None = None
    ReceiptHandle: str | None = None
    MD5OfBody: str | None = None
    Body: str | None = None
    Attributes: dict[str, str] | None = None
    MessageAttributes: dict[str, object] | None = None


class SqsSendMessageRequest(BaseModel):
    """Send a message to SQS. sqs.send_message()"""

    QueueUrl: str | None = None
    MessageBody: str | None = None
    DelaySeconds: int | None = None
    MessageAttributes: dict[str, object] | None = None
    MessageGroupId: str | None = None
    MessageDeduplicationId: str | None = None


class SqsSendMessageResponse(BaseModel):
    """Response from sqs.send_message()."""

    MD5OfMessageBody: str | None = None
    MD5OfMessageAttributes: str | None = None
    MessageId: str | None = None
    SequenceNumber: str | None = None


class SqsReceiveMessageRequest(BaseModel):
    """Request to receive messages. sqs.receive_message()"""

    QueueUrl: str | None = None
    MaxNumberOfMessages: int | None = None
    WaitTimeSeconds: int | None = None
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
    RedrivePolicy: str | None = None
