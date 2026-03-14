"""
Google Secret Manager schemas.

google.cloud.secretmanager_v1. Used for all API key and credential storage.
"""

from pydantic import BaseModel, Field


class SecretVersion(BaseModel):
    """Secret version resource."""

    name: str | None = Field(
        None,
        description="projects/{p}/secrets/{s}/versions/{v}",
    )
    createTime: str | None = Field(None, alias="createTime")
    destroyTime: str | None = Field(None, alias="destroyTime")
    state: str | None = Field(
        None,
        description="ENABLED/DISABLED/DESTROYED",
    )
    replicationStatus: dict[str, object] | None = Field(None, alias="replicationStatus")

    model_config = {"populate_by_name": True}


class SecretAccessRequest(BaseModel):
    """Request for access_secret_version()."""

    name: str = Field(
        ...,
        description="projects/{p}/secrets/{s}/versions/{v or 'latest'}",
    )


class SecretAccessResponse(BaseModel):
    """Response from access_secret_version()."""

    name: str | None = None
    payload_data: str | None = Field(None, description="Base64 encoded secret value")


class SecretCreateRequest(BaseModel):
    """Request for create_secret()."""

    parent: str = Field(..., description="projects/{p}")
    secret_id: str = Field(..., description="Secret ID")
    replication: dict[str, object] | None = Field(
        None,
        description="automatic or user-managed",
    )
    labels: dict[str, str] | None = None
    topics: list[str] | None = None


class SecretAddVersionRequest(BaseModel):
    """Request for add_secret_version()."""

    parent: str = Field(..., description="projects/{p}/secrets/{s}")
    payload_data: str = Field(..., description="Base64 encoded payload")


class SecretAddVersionResponse(BaseModel):
    """Response from add_secret_version()."""

    name: str | None = None
    createTime: str | None = None
    state: str | None = None


class ListSecretsResponse(BaseModel):
    """Paginated list of secrets."""

    secrets: list[dict[str, object]] | None = None
    nextPageToken: str | None = None


class SecretManagerQuotaUsage(BaseModel):
    """Secret Manager quota usage for monitoring."""

    project_id: str = Field(..., description="Project ID")
    access_requests_per_minute: int | None = None
    secret_versions_per_secret: int | None = None
