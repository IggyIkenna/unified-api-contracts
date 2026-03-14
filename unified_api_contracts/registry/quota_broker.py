"""
Quota broker API schemas.

Request/response types for the centralized quota-broker (Cloud Run IAM).
Reference: deployment-service/deployment/quota_broker_client.py
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from unified_api_contracts.shared import ComputeType


class QuotaBrokerAcquireRequest(BaseModel):
    """Request body for POST /v1/admissions/acquire."""

    deployment_id: str = Field(..., description="Deployment identifier")
    shard_id: str = Field(..., description="Shard identifier")
    compute_type: ComputeType = Field(..., description="Compute backend: vm or cloud_run")
    region: str = Field(..., description="Target region")
    resources: dict[str, float] = Field(..., description="Resource metrics and requested amounts")
    ttl_seconds: int | None = Field(None, description="Lease TTL in seconds")


class QuotaBrokerAcquireResult(BaseModel):
    """Response from POST /v1/admissions/acquire."""

    granted: bool = Field(..., description="Whether quota was granted")
    lease_id: str = Field(..., description="Lease ID for release; empty if not granted")
    reason: str | None = Field(None, description="Human-readable reason when denied")
    retry_after_seconds: int | None = Field(None, description="Suggested retry delay when denied")


class QuotaBrokerReleaseRequest(BaseModel):
    """Request body for POST /v1/admissions/release."""

    lease_id: str = Field(..., description="Lease ID to release")


class QuotaBrokerReleaseResponse(BaseModel):
    """Response from POST /v1/admissions/release."""

    released: bool = Field(..., description="Whether the lease was released")


class QuotaBrokerLiveQuotasRequest(BaseModel):
    """Query params for GET /v1/quotas/live."""

    regions: list[str] = Field(..., description="Regions to fetch live quota for")


class QuotaBrokerLiveQuotasResponse(BaseModel):
    """Response from GET /v1/quotas/live.

    Structure: regions[region_name][metric_name] = {usage, limit} or similar.
    """

    regions: dict[str, dict[str, dict[str, float]]] = Field(
        default_factory=dict,
        description="Per-region metrics: region -> metric -> {usage, limit, ...}",
    )


class QuotaExceededMessage(BaseModel):
    """Message emitted when quota acquisition is denied."""

    reason: str = Field(..., description="Human-readable reason for denial")
    retry_after_seconds: int | None = Field(None, description="Suggested retry delay")
    lease_id: str = Field("", description="Lease ID if partial; empty when not granted")
    deployment_id: str = Field("", description="Deployment that was denied")
    shard_id: str = Field("", description="Shard that was denied")
