"""Shared types and utilities for api-contracts schemas."""

from .error_action import ErrorAction
from .quota_types import (
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
