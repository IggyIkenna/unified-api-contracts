"""Shared types and utilities — re-exports from config/."""

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction
from unified_api_contracts.config.quota_types import (
    AwsQuotaExceeded,
    AwsServiceQuota,
    ComputeType,
    GcpQuotaExceeded,
    GcpQuotaUsage,
    VmQuotaShape,
)

__all__ = [
    "AwsQuotaExceeded",
    "AwsServiceQuota",
    "ComputeType",
    "ErrorAction",
    "GcpQuotaExceeded",
    "GcpQuotaUsage",
    "VmQuotaShape",
]
