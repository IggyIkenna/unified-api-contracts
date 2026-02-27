"""
GCP Compute Engine: Pydantic request/response schemas.

Client: google.cloud.compute_v1.InstancesClient
Sync: All methods (insert, delete, get, list, start, stop) are sync by default.
Async: Use InstancesAsyncClient from google.cloud.compute_v1.services.instances for async.
"""

from pydantic import BaseModel, Field

# --- Request schemas ---


class InsertInstanceRequest(BaseModel):
    """Request for InstancesClient.insert() / insert_unary()."""

    project: str = Field(..., description="Project ID")
    zone: str = Field(..., description="Zone (e.g. us-central1-a)")
    instance_resource: dict[str, object] = Field(
        ...,
        description="Instance resource body (name, machineType, disks, networkInterfaces, etc.)",
    )


class DeleteInstanceRequest(BaseModel):
    """Request for InstancesClient.delete() / delete_unary()."""

    project: str = Field(..., description="Project ID")
    zone: str = Field(..., description="Zone")
    instance: str = Field(..., description="Instance name to delete")


class GetInstanceRequest(BaseModel):
    """Request for InstancesClient.get()."""

    project: str = Field(..., description="Project ID")
    zone: str = Field(..., description="Zone")
    instance: str = Field(..., description="Instance name")


class ListInstancesRequest(BaseModel):
    """Request for InstancesClient.list()."""

    project: str = Field(..., description="Project ID")
    zone: str = Field(..., description="Zone")
    filter: str | None = Field(None, description="Filter expression")
    max_results: int | None = Field(None, description="Max results per page")
    order_by: str | None = Field(None, description="Sort order")
    page_token: str | None = Field(None, description="Page token for pagination")


class StartInstanceRequest(BaseModel):
    """Request for InstancesClient.start() / start_unary()."""

    project: str = Field(..., description="Project ID")
    zone: str = Field(..., description="Zone")
    instance: str = Field(..., description="Instance name to start")


class StopInstanceRequest(BaseModel):
    """Request for InstancesClient.stop() / stop_unary()."""

    project: str = Field(..., description="Project ID")
    zone: str = Field(..., description="Zone")
    instance: str = Field(..., description="Instance name to stop")


# --- Response schemas ---


class ComputeInstance(BaseModel):
    """Instance resource (simplified). Full schema: google.cloud.compute_v1.types.Instance."""

    id: str | None = None
    name: str | None = None
    zone: str | None = None
    machine_type: str | None = None
    status: str | None = None  # RUNNING, STOPPED, TERMINATED, etc.
    creation_timestamp: str | None = None


class ComputeOperation(BaseModel):
    """Long-running operation (insert, delete, start, stop)."""

    id: str | None = None
    name: str | None = None
    status: str | None = None  # PENDING, RUNNING, DONE
    error: dict[str, object] | None = None


class InstanceListResponse(BaseModel):
    """Paginated list of instances."""

    items: list[ComputeInstance] = Field(default_factory=list)
    next_page_token: str | None = None


# --- Quota ---


class GcpComputeQuotaUsage(BaseModel):
    """Compute Engine quota usage for monitoring."""

    project_id: str = Field(..., description="Project ID")
    zone: str | None = Field(None, description="Zone (or None for aggregated)")
    instances_count: int = Field(0, description="Number of instances")
    cpus_used: int = Field(0, description="CPUs in use")
    memory_mb_used: int = Field(0, description="Memory MB in use")
    disks_count: int = Field(0, description="Number of disks")
