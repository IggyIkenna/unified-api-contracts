from __future__ import annotations

from pydantic import BaseModel


class CodeBuildProject(BaseModel):
    """CodeBuild project. cb.batch_get_projects()"""

    name: str | None = None
    arn: str | None = None
    description: str | None = None
    source: dict[str, object] | None = None
    sourceVersion: str | None = None
    artifacts: dict[str, object] | None = None
    environment: dict[str, object] | None = None
    serviceRole: str | None = None
    timeoutInMinutes: int | None = None
    queuedTimeoutInMinutes: int | None = None
    encryptionKey: str | None = None
    created: str | None = None
    lastModified: str | None = None
    badge: dict[str, object] | None = None


class CodeBuildBuild(BaseModel):
    """CodeBuild build run. cb.batch_get_builds() / cb.start_build()"""

    id: str | None = None
    arn: str | None = None
    buildNumber: int | None = None
    startTime: str | None = None
    endTime: str | None = None
    currentPhase: str | None = None
    buildStatus: str | None = None
    projectName: str | None = None
    phases: list[dict[str, object]] | None = None
    source: dict[str, object] | None = None
    sourceVersion: str | None = None
    artifacts: dict[str, object] | None = None
    environment: dict[str, object] | None = None
    logs: dict[str, object] | None = None
    timeoutInMinutes: int | None = None
    buildComplete: bool | None = None
    initiator: str | None = None
    encryptionKey: str | None = None


class CodeBuildStartBuildRequest(BaseModel):
    """Start a CodeBuild build. cb.start_build()"""

    projectName: str | None = None
    sourceVersion: str | None = None
    artifactsOverride: dict[str, object] | None = None
    environmentVariablesOverride: list[dict[str, object]] | None = None
    imageOverride: str | None = None
    buildspecOverride: str | None = None
