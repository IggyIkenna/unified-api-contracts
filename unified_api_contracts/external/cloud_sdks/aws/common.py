from __future__ import annotations

from pydantic import BaseModel


class AwsErrorResponse(BaseModel):
    """Common AWS API error response structure."""

    Error: dict[str, str] | None = None
    ResponseMetadata: dict[str, object] | None = None


class EC2QuotaInfo(BaseModel):
    """EC2 quota info (from Service Quotas or describe)."""

    QuotaName: str | None = None
    QuotaCode: str | None = None
    Value: float | None = None
    Unit: str | None = None


class ECSQuotaInfo(BaseModel):
    """ECS quota info."""

    QuotaName: str | None = None
    QuotaCode: str | None = None
    Value: float | None = None


class LambdaQuotaInfo(BaseModel):
    """Lambda quota info."""

    QuotaName: str | None = None
    QuotaCode: str | None = None
    Value: float | None = None


class S3QuotaInfo(BaseModel):
    """S3 quota info."""

    QuotaName: str | None = None
    QuotaCode: str | None = None
    Value: float | None = None


class AwsQuotaUsage(BaseModel):
    """Consolidated quota usage across key AWS services."""

    region: str | None = None
    sqs_queues_count: int | None = None
    sns_topics_count: int | None = None
    ecr_repositories_count: int | None = None
    codebuild_concurrent_builds: int | None = None
    secrets_manager_secrets_count: int | None = None
    iam_roles_count: int | None = None
    cost_mtd_usd: float | None = None
