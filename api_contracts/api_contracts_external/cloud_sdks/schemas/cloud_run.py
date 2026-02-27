"""
GCP Cloud Run: Pydantic request/response schemas.

Client: google.cloud.run_v2.ServicesClient (services), RevisionsClient (revisions)
Sync: All methods are sync by default.
Async: Use ServicesAsyncClient / RevisionsAsyncClient for async.
"""

from pydantic import BaseModel, Field

# --- Service request schemas ---


class CreateServiceRequest(BaseModel):
    """Request for ServicesClient.create_service()."""

    parent: str = Field(..., description="Parent: projects/{project}/locations/{location}")
    service_id: str = Field(..., description="Unique service ID")
    service: dict[str, object] = Field(
        default_factory=dict,
        description="Service resource (template, scaling, etc.)",
    )


class UpdateServiceRequest(BaseModel):
    """Request for ServicesClient.update_service()."""

    service: dict[str, object] = Field(..., description="Service resource with updates")
    update_mask: list[str] | None = Field(
        None,
        description="Field mask paths for partial updates",
    )


# --- Revision request schemas ---


class ListRevisionsRequest(BaseModel):
    """Request for RevisionsClient.list_revisions()."""

    parent: str = Field(
        ...,
        description="Parent: projects/{project}/locations/{location}/services/{service}",
    )
    page_size: int | None = Field(None, description="Page size")
    page_token: str | None = Field(None, description="Page token")


# --- Traffic split ---


class TrafficTarget(BaseModel):
    """Single revision traffic target."""

    revision: str = Field(..., description="Revision name or LATEST")
    percent: int = Field(..., ge=0, le=100, description="Traffic percentage")


class UpdateTrafficSplitRequest(BaseModel):
    """Request for ServicesClient.update_service() with traffic split."""

    service_name: str = Field(..., description="Full service resource name")
    traffic_targets: list[TrafficTarget] = Field(
        ...,
        description="Traffic split (must sum to 100)",
    )


# --- Response schemas ---


class CloudRunService(BaseModel):
    """Cloud Run Service (simplified)."""

    name: str | None = None
    uid: str | None = None
    generation: int | None = None
    create_time: str | None = None
    update_time: str | None = None


class CloudRunRevision(BaseModel):
    """Cloud Run Revision (simplified)."""

    name: str | None = None
    uid: str | None = None
    generation: int | None = None
    create_time: str | None = None
    active: bool | None = None


class RevisionListResponse(BaseModel):
    """Paginated list of revisions."""

    revisions: list[CloudRunRevision] = Field(default_factory=list)
    next_page_token: str | None = None


# --- Quota ---


class GcpCloudRunQuotaUsage(BaseModel):
    """Cloud Run quota usage for monitoring."""

    project_id: str = Field(..., description="Project ID")
    region: str | None = Field(None, description="Region")
    services_count: int = Field(0, description="Number of services")
    revisions_count: int = Field(0, description="Number of revisions")
    concurrent_requests: int = Field(0, description="Concurrent request capacity")
