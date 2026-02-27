"""
GCP Cloud Storage: Pydantic request/response schemas.

Client: google.cloud.storage.Client (sync), no built-in async client.
Sync: Client, Bucket, Blob are sync. Use asyncio.to_thread() or run_in_executor for async.
Async: Use google-cloud-storage async transport (experimental) or wrap sync calls.
"""

from pydantic import BaseModel, Field

# --- Bucket request schemas ---


class BucketCreateRequest(BaseModel):
    """Request for Client.create_bucket()."""

    bucket_or_name: str = Field(..., description="Bucket name to create")
    project: str | None = Field(None, description="Project (defaults to client project)")
    location: str | None = Field(None, description="Location (e.g. US, asia-northeast1)")
    requester_pays: bool | None = Field(None, description="Requester pays")


# --- Blob request schemas ---


class BlobUploadRequest(BaseModel):
    """Request for Blob.upload_from_file / upload_from_string."""

    bucket_name: str = Field(..., description="Bucket name")
    blob_name: str = Field(..., description="Blob path/name")
    content_type: str | None = Field(None, description="Content-Type")
    metadata: dict[str, str] | None = Field(None, description="Custom metadata")


class BlobDownloadRequest(BaseModel):
    """Request for Blob.download_to_file / download_as_bytes."""

    bucket_name: str = Field(..., description="Bucket name")
    blob_name: str = Field(..., description="Blob path/name")
    start: int | None = Field(None, description="Byte range start")
    end: int | None = Field(None, description="Byte range end")


class BlobListRequest(BaseModel):
    """Request for Bucket.list_blobs()."""

    bucket_name: str = Field(..., description="Bucket name")
    prefix: str | None = Field(None, description="Prefix filter")
    delimiter: str | None = Field(None, description="Delimiter for pseudo-hierarchy")
    max_results: int | None = Field(None, description="Max results per page")
    page_token: str | None = Field(None, description="Page token")


# --- Response schemas ---


class GcsBlobInfo(BaseModel):
    """Blob metadata (simplified)."""

    name: str | None = None
    size: int | None = None
    content_type: str | None = None
    etag: str | None = None
    updated: str | None = None


class BlobListResponse(BaseModel):
    """List of blobs (and optionally prefixes)."""

    blobs: list[GcsBlobInfo] = Field(default_factory=list)
    prefixes: list[str] = Field(default_factory=list)
    next_page_token: str | None = None


# --- Quota ---


class GcsQuotaUsage(BaseModel):
    """GCS quota usage for monitoring."""

    project_id: str = Field(..., description="Project ID")
    buckets_count: int = Field(0, description="Number of buckets")
    objects_count: int = Field(0, description="Total objects")
    storage_bytes: int = Field(0, description="Total storage bytes")
