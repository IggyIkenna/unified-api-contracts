from __future__ import annotations

from pydantic import BaseModel


class SnsPublishRequest(BaseModel):
    """Publish to SNS topic. sns.publish()"""

    TopicArn: str | None = None
    TargetArn: str | None = None
    PhoneNumber: str | None = None
    Message: str | None = None
    Subject: str | None = None
    MessageStructure: str | None = None
    MessageAttributes: dict[str, object] | None = None
    MessageGroupId: str | None = None
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
    FifoTopic: str | None = None
    ContentBasedDeduplication: str | None = None


class SnsSubscription(BaseModel):
    """SNS subscription. sns.list_subscriptions_by_topic()"""

    SubscriptionArn: str | None = None
    Owner: str | None = None
    Protocol: str | None = None
    Endpoint: str | None = None
    TopicArn: str | None = None
