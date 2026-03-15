"""AWS normalizers — infra types to canonical.

Maps S3, EC2, ECR, CodeBuild schemas to CanonicalCloudStorage,
CanonicalVirtualMachine, CanonicalContainerRegistry, CanonicalComputeJob.
"""

from __future__ import annotations

from ...canonical.domain.infrastructure import (
    CanonicalCloudStorage,
    CanonicalComputeJob,
    CanonicalContainerRegistry,
    CanonicalVirtualMachine,
    CloudProvider,
)
from .codebuild import CodeBuildBuild
from .ec2 import EC2Instance
from .ecr import EcrRepository
from .s3 import S3ListObjectsV2Response


def normalize_aws_s3_list_to_storage(
    raw: S3ListObjectsV2Response,
    region: str | None = None,
    venue: str = "aws",
) -> CanonicalCloudStorage | None:
    """Convert S3 list_objects_v2 response to CanonicalCloudStorage.

    Uses Name (bucket) from response. Region not in response — pass explicitly.
    """
    bucket = raw.Name if raw else None
    if not bucket:
        return None
    return CanonicalCloudStorage(
        provider=CloudProvider.AWS,
        bucket=bucket,
        region=region,
    )


def normalize_aws_s3_bucket_to_storage(
    bucket: str,
    region: str | None = None,
    venue: str = "aws",
) -> CanonicalCloudStorage:
    """Convert bucket name to CanonicalCloudStorage."""
    return CanonicalCloudStorage(
        provider=CloudProvider.AWS,
        bucket=bucket,
        region=region,
    )


def normalize_aws_ec2_instance_to_vm(
    raw: EC2Instance,
    region: str | None = None,
    venue: str = "aws",
) -> CanonicalVirtualMachine | None:
    """Convert EC2Instance to CanonicalVirtualMachine."""
    if not raw or not raw.InstanceId:
        return None
    instance_id = raw.InstanceId
    machine_type = raw.InstanceType or "unknown"
    zone = None
    if raw.Placement and isinstance(raw.Placement, dict):
        zone = raw.Placement.get("AvailabilityZone")
    return CanonicalVirtualMachine(
        provider=CloudProvider.AWS,
        instance_name=instance_id,
        machine_type=machine_type,
        region=region,
        zone=zone,
    )


def normalize_aws_ecr_repository_to_registry(
    raw: EcrRepository,
    region: str | None = None,
    venue: str = "aws",
) -> CanonicalContainerRegistry | None:
    """Convert EcrRepository to CanonicalContainerRegistry."""
    if not raw or not raw.repositoryName:
        return None
    repo = raw.repositoryUri or raw.repositoryName
    return CanonicalContainerRegistry(
        provider=CloudProvider.AWS,
        repository=repo,
        region=region,
    )


def normalize_aws_codebuild_to_job(
    raw: CodeBuildBuild,
    region: str | None = None,
    venue: str = "aws",
) -> CanonicalComputeJob | None:
    """Convert CodeBuildBuild to CanonicalComputeJob."""
    if not raw or not raw.id:
        return None
    timeout_sec = None
    if raw.timeoutInMinutes is not None:
        timeout_sec = raw.timeoutInMinutes * 60
    return CanonicalComputeJob(
        provider=CloudProvider.AWS,
        job_name=raw.id,
        region=region,
        timeout_seconds=timeout_sec,
        schedule=None,
    )
