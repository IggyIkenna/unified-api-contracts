"""
Google Cloud Scheduler schemas.

Maps to google.cloud.scheduler_v1. Used for triggering batch jobs on a cron schedule
(daily market data runs, feature calculation jobs).
"""

from pydantic import BaseModel, Field


class CloudSchedulerJob(BaseModel):
    """Cloud Scheduler job resource."""

    name: str | None = Field(
        None,
        description="projects/{p}/locations/{l}/jobs/{j}",
    )
    description: str | None = None
    schedule: str | None = Field(None, description="Cron expression e.g. '0 6 * * *'")
    time_zone: str | None = Field(None, alias="timeZone", description="e.g. 'Asia/Tokyo'")
    state: str | None = Field(
        None,
        description="ENABLED/PAUSED/DISABLED",
    )
    last_attempt_time: str | None = Field(None, alias="lastAttemptTime")
    next_schedule_time: str | None = Field(None, alias="nextScheduleTime")
    http_target: dict[str, object] | None = Field(
        None,
        alias="httpTarget",
        description="{uri, httpMethod, headers, body, oidcToken}",
    )
    pubsub_target: dict[str, object] | None = Field(
        None,
        alias="pubsubTarget",
        description="{topicName, data, attributes}",
    )
    app_engine_http_target: dict[str, object] | None = Field(
        None,
        alias="appEngineHttpTarget",
    )
    schedule_time: str | None = Field(None, alias="scheduleTime")
    attempt_deadline: str | None = Field(None, alias="attemptDeadline")

    model_config = {"populate_by_name": True}


class CloudSchedulerCreateJobRequest(BaseModel):
    """Request for CloudSchedulerClient.create_job()."""

    parent: str = Field(..., description="projects/{p}/locations/{l}")
    job: CloudSchedulerJob = Field(..., description="Job to create")


class CloudSchedulerPauseJobRequest(BaseModel):
    """Request for CloudSchedulerClient.pause_job()."""

    name: str = Field(..., description="Job resource name")


class CloudSchedulerResumeJobRequest(BaseModel):
    """Request for CloudSchedulerClient.resume_job()."""

    name: str = Field(..., description="Job resource name")


class CloudSchedulerRunJobRequest(BaseModel):
    """Request for CloudSchedulerClient.run_job()."""

    name: str = Field(..., description="Job resource name")


class CloudSchedulerListJobsResponse(BaseModel):
    """Response from CloudSchedulerClient.list_jobs()."""

    jobs: list[CloudSchedulerJob] | None = None
    next_page_token: str | None = Field(None, alias="nextPageToken")

    model_config = {"populate_by_name": True}


class CloudSchedulerAttempt(BaseModel):
    """Single scheduler attempt metadata."""

    schedule_time: str | None = Field(None, alias="scheduleTime")
    dispatch_time: str | None = Field(None, alias="dispatchTime")
    response_time: str | None = Field(None, alias="responseTime")
    dispatch_count: int | None = Field(None, alias="dispatchCount")
    failure_count: int | None = Field(None, alias="failureCount")
    retry_count: int | None = Field(None, alias="retryCount")

    model_config = {"populate_by_name": True}
