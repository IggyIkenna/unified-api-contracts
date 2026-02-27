"""Internal health check, dependency, and error-handling schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class HealthStatusEnum(StrEnum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class ComponentHealth(BaseModel):
    name: str
    status: HealthStatusEnum
    message: str | None = None
    last_checked: datetime | None = None


class ServiceHealthStatus(BaseModel):
    """HTTP health-check response — returned by /health endpoint."""

    status: HealthStatusEnum
    timestamp: datetime
    components: dict[str, str] = Field(default_factory=dict)
    uptime_seconds: float = 0.0
    version: str = "1.0.0"
    service_name: str | None = None
    mode: str | None = None


class DependencyStatus(BaseModel):
    name: str
    service: str
    available: bool
    message: str
    required: bool
    checked_path: str
    date: str
    category: str


class DependencyReport(BaseModel):
    """Full preflight dependency check result."""

    service: str
    all_available: bool
    required_available: bool
    checks: list[DependencyStatus]


class DependencyFailure(BaseModel):
    upstream_service: str
    missing_path: str
    date: str
    category: str
    required: bool
    message: str


# ---------------------------------------------------------------------------
# Error handling schemas (from handle_api_errors / EnhancedError)
# ---------------------------------------------------------------------------

class ErrorCategory(StrEnum):
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    NETWORK = "network"
    SERVER_ERROR = "server_error"
    DATA_QUALITY = "data_quality"
    DEPENDENCY = "dependency"
    UNKNOWN = "unknown"


class ErrorSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorRecoveryStrategy(StrEnum):
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    FALLBACK = "fallback"
    FAIL_FAST = "fail_fast"
    SKIP = "skip"
    ALERT = "alert"


class ErrorContext(BaseModel):
    service: str | None = None
    operation: str | None = None
    venue: str | None = None
    instrument_key: str | None = None
    shard: str | None = None
    retry_count: int = 0
    timestamp: datetime | None = None
    request_id: str | None = None
    extra: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class EnhancedError(BaseModel):
    """Serialised form of a handled API error (from handle_api_errors decorator)."""

    error_type: str = "EnhancedError"
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    recovery_strategy: ErrorRecoveryStrategy
    context: ErrorContext
    retry_count: int = 0
    max_retries: int = 3
    original_error: dict[str, str] = Field(default_factory=dict)
    additional_info: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Circuit breaker (standardised schema for future adoption)
# ---------------------------------------------------------------------------

class CircuitBreakerStateEnum(StrEnum):
    CLOSED = "closed"        # Normal — requests flow through
    OPEN = "open"            # Tripped — requests rejected immediately
    HALF_OPEN = "half_open"  # Probing — one request allowed through


class CircuitBreakerState(BaseModel):
    """Snapshot of a circuit breaker for a downstream dependency."""

    name: str
    state: CircuitBreakerStateEnum = CircuitBreakerStateEnum.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: datetime | None = None
    last_state_change: datetime | None = None
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    half_open_max_calls: int = 1


class CircuitBreakerEvent(BaseModel):
    name: str
    previous_state: CircuitBreakerStateEnum
    new_state: CircuitBreakerStateEnum
    timestamp: datetime
    reason: str | None = None
    failure_count: int = 0
