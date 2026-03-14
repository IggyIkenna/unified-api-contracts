"""
Google Cloud Build SDK schemas.

Maps to google.cloud.devtools.cloudbuild_v1.
"""

from pydantic import BaseModel, Field


class CloudBuildStep(BaseModel):
    """Single build step (Docker image + args)."""

    name: str | None = Field(None, description="Docker image for the step")
    args: list[str] | None = None
    env: list[str] | None = None
    id: str | None = None
    waitFor: list[str] | None = Field(None, alias="waitFor", description="Step dependencies")
    dir: str | None = None
    secretEnv: list[str] | None = Field(None, alias="secretEnv")

    model_config = {"populate_by_name": True}


class CloudBuildGitHubConfig(BaseModel):
    """GitHub repository connection config."""

    owner: str | None = None
    name: str | None = Field(None, description="Repository name")
    push: dict[str, object] | None = Field(None, description="Branch/tag filter")
    pullRequest: dict[str, object] | None = Field(None, alias="pullRequest")

    model_config = {"populate_by_name": True}


class CloudBuildConfig(BaseModel):
    """Build configuration (steps, timeout, images)."""

    steps: list[CloudBuildStep] | None = None
    timeout: str | None = None
    images: list[str] | None = None
    substitutions: dict[str, str] | None = None
    options: dict[str, object] | None = None
    serviceAccount: str | None = Field(None, alias="serviceAccount")

    model_config = {"populate_by_name": True}


class CloudBuildTrigger(BaseModel):
    """Cloud Build trigger resource."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    filename: str | None = Field(None, description="cloudbuild.yaml path")
    github: CloudBuildGitHubConfig | None = None
    build: CloudBuildConfig | None = None
    disabled: bool | None = None
    createTime: str | None = Field(None, alias="createTime")
    substitutions: dict[str, str] | None = None
    tags: list[str] | None = None

    model_config = {"populate_by_name": True}


class CloudBuildBuild(BaseModel):
    """Cloud Build build resource."""

    id: str | None = None
    projectId: str | None = Field(None, alias="projectId")
    status: str | None = Field(
        None,
        description="QUEUED/WORKING/SUCCESS/FAILURE/TIMEOUT/CANCELLED",
    )
    source: dict[str, object] | None = None
    steps: list[CloudBuildStep] | None = None
    createTime: str | None = Field(None, alias="createTime")
    startTime: str | None = Field(None, alias="startTime")
    finishTime: str | None = Field(None, alias="finishTime")
    logUrl: str | None = Field(None, alias="logUrl")
    images: list[str] | None = None
    substitutions: dict[str, str] | None = None
    logsBucket: str | None = Field(None, alias="logsBucket")
    serviceAccount: str | None = Field(None, alias="serviceAccount")
    buildTriggerId: str | None = Field(None, alias="buildTriggerId")

    model_config = {"populate_by_name": True}


class CloudBuildListBuildsResponse(BaseModel):
    """Paginated list of builds."""

    builds: list[CloudBuildBuild] | None = None
    nextPageToken: str | None = Field(None, alias="nextPageToken")

    model_config = {"populate_by_name": True}


class CloudBuildTriggerListResponse(BaseModel):
    """Paginated list of triggers."""

    triggers: list[CloudBuildTrigger] | None = None
    nextPageToken: str | None = Field(None, alias="nextPageToken")

    model_config = {"populate_by_name": True}


class CloudBuildRunTriggerRequest(BaseModel):
    """Request for running a trigger manually."""

    projectId: str = Field(..., alias="projectId")
    triggerId: str = Field(..., alias="triggerId")
    source: dict[str, object] | None = None
    substitutions: dict[str, str] | None = None

    model_config = {"populate_by_name": True}


class CloudBuildQuotaUsage(BaseModel):
    """Cloud Build quota usage for monitoring."""

    project_id: str = Field(..., description="Project ID")
    concurrent_builds_used: int | None = None
    concurrent_builds_limit: int | None = None
    build_minutes_used_today: int | None = None
