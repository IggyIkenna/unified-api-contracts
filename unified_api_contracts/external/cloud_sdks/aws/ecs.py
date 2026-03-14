from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


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
