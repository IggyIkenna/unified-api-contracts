"""
Shared quota types for cloud resource management.

Reference: deployment-api/utils/quota_requirements.py
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ComputeType(StrEnum):
    """Compute backend type for quota requests."""

    VM = "vm"
    CLOUD_RUN = "cloud_run"


class VmQuotaShape(BaseModel):
    """VM resource shape for quota calculation.

    Maps machine config to GCP regional quota metrics.
    """

    cpu_metric: str = Field(..., description="GCP quota metric name (e.g. C2_CPUS, N2_CPUS)")
    vcpus: int = Field(..., description="vCPU count")
    external_ipv4: int = Field(..., description="External IPv4 addresses (typically 1 per VM)")
    ssd_gb: int = Field(..., description="SSD disk size in GB")

    def per_shard(self) -> dict[str, float]:
        """Return resource dict for one shard (per quota_requirements.VmQuotaShape.per_shard)."""
        return {
            self.cpu_metric: float(self.vcpus),
            "IN_USE_ADDRESSES": float(self.external_ipv4),
            "SSD_TOTAL_GB": float(self.ssd_gb),
        }


class GcpQuotaUsage(BaseModel):
    """GCP regional quota usage for a single metric."""

    region: str = Field(..., description="GCP region")
    metric: str = Field(..., description="Quota metric name (e.g. C2_CPUS)")
    usage: float = Field(..., description="Current usage")
    limit: float = Field(..., description="Quota limit")


class GcpQuotaExceeded(BaseModel):
    """GCP quota exceeded event."""

    region: str = Field(..., description="GCP region")
    metric: str = Field(..., description="Quota metric that was exceeded")
    usage: float = Field(..., description="Current usage")
    limit: float = Field(..., description="Quota limit")
    reason: str = Field(..., description="Human-readable reason")


class AwsServiceQuota(BaseModel):
    """AWS Service Quotas usage for a single quota."""

    service_code: str = Field(..., description="AWS service code (e.g. ec2)")
    quota_code: str = Field(..., description="Quota identifier")
    usage: float = Field(..., description="Current usage")
    limit: float = Field(..., description="Quota limit")


class AwsQuotaExceeded(BaseModel):
    """AWS quota exceeded event."""

    service_code: str = Field(..., description="AWS service code")
    quota_code: str = Field(..., description="Quota that was exceeded")
    usage: float = Field(..., description="Current usage")
    limit: float = Field(..., description="Quota limit")
    reason: str = Field(..., description="Human-readable reason")
