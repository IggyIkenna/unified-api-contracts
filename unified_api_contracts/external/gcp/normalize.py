"""GCP normalizers — infra types to canonical.

Maps GCS, Compute Engine, Artifact Registry, Cloud Build schemas to
CanonicalCloudStorage, CanonicalVirtualMachine, CanonicalContainerRegistry,
CanonicalComputeJob. Cloud-agnostic canonicals use CloudProvider.GCP.
"""

from __future__ import annotations

from ...canonical.domain.infrastructure import (
    CanonicalCloudStorage,
    CanonicalComputeJob,
    CanonicalContainerRegistry,
    CanonicalVirtualMachine,
    CloudProvider,
)
from .artifact_registry import ArtifactRepository
from .cloud_build import CloudBuildBuild
from .compute import ComputeInstance
from .gcs import BlobListResponse


def normalize_gcp_storage_bucket(
    bucket: str,
    region: str | None = None,
    venue: str = "gcp",
) -> CanonicalCloudStorage:
    """Convert bucket name to CanonicalCloudStorage."""
    return CanonicalCloudStorage(
        provider=CloudProvider.GCP,
        bucket=bucket,
        region=region,
    )


def normalize_gcp_gcs_blob_list_to_storage(
    raw: BlobListResponse,
    bucket: str,
    region: str | None = None,
    venue: str = "gcp",
) -> CanonicalCloudStorage:
    """Convert BlobListResponse + bucket name to CanonicalCloudStorage.

    BlobListResponse does not contain bucket; pass bucket explicitly.
    """
    return CanonicalCloudStorage(
        provider=CloudProvider.GCP,
        bucket=bucket,
        region=region,
    )


def normalize_gcp_compute_instance_to_vm(
    raw: ComputeInstance,
    region: str | None = None,
    venue: str = "gcp",
) -> CanonicalVirtualMachine | None:
    """Convert ComputeInstance to CanonicalVirtualMachine."""
    if not raw or not (raw.name or raw.id):
        return None
    instance_name = raw.name or raw.id or "unknown"
    machine_type = raw.machine_type or "unknown"
    zone = raw.zone
    return CanonicalVirtualMachine(
        provider=CloudProvider.GCP,
        instance_name=instance_name,
        machine_type=machine_type,
        region=region,
        zone=zone,
    )


def normalize_gcp_artifact_repository_to_registry(
    raw: ArtifactRepository,
    region: str | None = None,
    venue: str = "gcp",
) -> CanonicalContainerRegistry | None:
    """Convert ArtifactRepository to CanonicalContainerRegistry."""
    if not raw or not raw.name:
        return None
    repo = raw.name
    return CanonicalContainerRegistry(
        provider=CloudProvider.GCP,
        repository=repo,
        region=region,
    )


def normalize_gcp_cloud_build_to_job(
    raw: CloudBuildBuild,
    region: str | None = None,
    venue: str = "gcp",
) -> CanonicalComputeJob | None:
    """Convert CloudBuildBuild to CanonicalComputeJob."""
    if not raw or not raw.id:
        return None
    return CanonicalComputeJob(
        provider=CloudProvider.GCP,
        job_name=raw.id,
        region=region,
        timeout_seconds=None,
        schedule=None,
    )
