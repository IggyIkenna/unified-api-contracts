"""
Google Artifact Registry schemas.

Maps to google.cloud.artifactregistry_v1. Used for unified Python library publishing
and Cloud Run image storage.
"""

from pydantic import BaseModel, Field


class ArtifactRepository(BaseModel):
    """Artifact Registry repository."""

    name: str | None = Field(
        None,
        description="projects/{p}/locations/{l}/repositories/{r}",
    )
    format: str | None = Field(
        None,
        description="DOCKER/PYTHON/NPM/GO",
    )
    description: str | None = None
    createTime: str | None = Field(None, alias="createTime")
    updateTime: str | None = Field(None, alias="updateTime")
    kmsKeyName: str | None = Field(None, alias="kmsKeyName")
    labels: dict[str, str] | None = None

    model_config = {"populate_by_name": True}


class ArtifactPackage(BaseModel):
    """Package within a repository."""

    name: str | None = Field(None, description=".../packages/{p}")
    displayName: str | None = Field(None, alias="displayName")
    createTime: str | None = Field(None, alias="createTime")
    updateTime: str | None = Field(None, alias="updateTime")

    model_config = {"populate_by_name": True}


class ArtifactVersion(BaseModel):
    """Package version."""

    name: str | None = Field(None, description=".../versions/{v}")
    description: str | None = None
    createTime: str | None = Field(None, alias="createTime")
    updateTime: str | None = Field(None, alias="updateTime")
    relatedTags: list[dict[str, object]] | None = Field(None, alias="relatedTags")

    model_config = {"populate_by_name": True}


class ArtifactTag(BaseModel):
    """Package tag."""

    name: str | None = Field(None, description=".../tags/{t}")
    version: str | None = None


class PythonPackage(BaseModel):
    """Python package metadata."""

    name: str | None = None
    uri: str | None = None
    packageName: str | None = Field(None, alias="packageName")
    version: str | None = None
    uploadTime: str | None = Field(None, alias="uploadTime")

    model_config = {"populate_by_name": True}


class ListRepositoriesResponse(BaseModel):
    """Paginated list of repositories."""

    repositories: list[ArtifactRepository] | None = None
    nextPageToken: str | None = Field(None, alias="nextPageToken")

    model_config = {"populate_by_name": True}


class ListPackagesResponse(BaseModel):
    """Paginated list of packages."""

    packages: list[ArtifactPackage] | None = None
    nextPageToken: str | None = Field(None, alias="nextPageToken")

    model_config = {"populate_by_name": True}


class ArtifactRegistryQuotaUsage(BaseModel):
    """Artifact Registry quota usage for monitoring."""

    project_id: str = Field(..., description="Project ID")
    requests_per_minute: int | None = None
    storage_bytes_used: int | None = None


# ---------------------------------------------------------------------------
# Docker image / container registry schemas
# ---------------------------------------------------------------------------


class DockerImage(BaseModel):
    """Docker container image in Artifact Registry."""

    name: str | None = None
    uri: str | None = None
    tags: list[str] | None = None
    image_size_bytes: int | None = None
    media_type: str | None = None
    build_time: str | None = None
    upload_time: str | None = None
    update_time: str | None = None


class ListDockerImagesResponse(BaseModel):
    """Paginated Docker image list."""

    docker_images: list[DockerImage] | None = None
    next_page_token: str | None = None


class NpmPackage(BaseModel):
    """NPM package in Artifact Registry."""

    name: str | None = None
    package_name: str | None = None
    version: str | None = None
    tags: list[str] | None = None
    create_time: str | None = None
    update_time: str | None = None


class ArtifactRegistryCleanupPolicy(BaseModel):
    """Cleanup policy for automatic deletion of old images/packages."""

    id: str | None = None
    action: str | None = None
    most_recent_versions: dict[str, object] | None = None
    condition: dict[str, object] | None = None
