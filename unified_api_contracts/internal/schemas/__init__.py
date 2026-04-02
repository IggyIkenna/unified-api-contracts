"""Internal request/response/error schemas."""

from unified_api_contracts.internal.schemas.errors import (
    DeadLetterRecord,
    EnhancedError,
    ErrorCategory,
    ErrorContext,
    ErrorRecoveryStrategy,
    ErrorSeverity,
    StartupValidationError,
)
from unified_api_contracts.internal.schemas.rbac import (
    ROLE_PERMISSIONS,
    TIER_ENTITLEMENTS,
    Entitlement,
    OrgType,
    Permission,
    ProvisioningRole,
    SubscriptionTier,
    UserProfile,
    UserRole,
    has_role_permission,
)
from unified_api_contracts.internal.schemas.strategy import (
    StrategySpec,
    StrategyType,
)

__all__ = [
    "ROLE_PERMISSIONS",
    "TIER_ENTITLEMENTS",
    "DeadLetterRecord",
    "EnhancedError",
    "Entitlement",
    "ErrorCategory",
    "ErrorContext",
    "ErrorRecoveryStrategy",
    "ErrorSeverity",
    "OrgType",
    "Permission",
    "ProvisioningRole",
    "StartupValidationError",
    "StrategySpec",
    "StrategyType",
    "SubscriptionTier",
    "UserProfile",
    "UserRole",
    "has_role_permission",
]
