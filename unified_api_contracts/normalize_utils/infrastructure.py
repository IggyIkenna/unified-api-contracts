"""Infrastructure normalizers — AWS, GCP to canonical infra types."""

from __future__ import annotations

from ..external.aws.normalize import (
    normalize_aws_codebuild_to_job,
    normalize_aws_ec2_instance_to_vm,
    normalize_aws_ecr_repository_to_registry,
    normalize_aws_s3_bucket_to_storage,
    normalize_aws_s3_list_to_storage,
)
from ..external.gcp.normalize import (
    normalize_gcp_artifact_repository_to_registry,
    normalize_gcp_cloud_build_to_job,
    normalize_gcp_compute_instance_to_vm,
    normalize_gcp_gcs_blob_list_to_storage,
    normalize_gcp_storage_bucket,
)

__all__ = [
    "normalize_aws_codebuild_to_job",
    "normalize_aws_ec2_instance_to_vm",
    "normalize_aws_ecr_repository_to_registry",
    "normalize_aws_s3_bucket_to_storage",
    "normalize_aws_s3_list_to_storage",
    "normalize_gcp_artifact_repository_to_registry",
    "normalize_gcp_cloud_build_to_job",
    "normalize_gcp_compute_instance_to_vm",
    "normalize_gcp_gcs_blob_list_to_storage",
    "normalize_gcp_storage_bucket",
]
