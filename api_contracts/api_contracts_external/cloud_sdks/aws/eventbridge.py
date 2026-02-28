from __future__ import annotations

from pydantic import BaseModel


class EventBridgeRule(BaseModel):
    """EventBridge rule. eb.list_rules() / eb.describe_rule()"""

    Name: str | None = None
    Arn: str | None = None
    EventPattern: str | None = None
    ScheduleExpression: str | None = None
    State: str | None = None
    Description: str | None = None
    EventBusName: str | None = None
    CreatedBy: str | None = None


class EventBridgeTarget(BaseModel):
    """Target for an EventBridge rule. eb.list_targets_by_rule()"""

    Id: str | None = None
    Arn: str | None = None
    RoleArn: str | None = None
    Input: str | None = None
    InputPath: str | None = None
    InputTransformer: dict[str, object] | None = None
    EcsParameters: dict[str, object] | None = None
    HttpParameters: dict[str, object] | None = None


class EventBridgePutEventsRequest(BaseModel):
    """Publish custom events to EventBridge. eb.put_events()"""

    Entries: list[dict[str, object]] | None = None


class EventBridgePutEventsResponse(BaseModel):
    """Response from put_events()."""

    FailedEntryCount: int | None = None
    Entries: list[dict[str, object]] | None = None
