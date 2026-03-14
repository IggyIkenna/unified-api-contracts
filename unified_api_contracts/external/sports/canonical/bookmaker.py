"""Thin re-export — canonical bookmaker types live in canonical.domain.sports."""

from unified_api_contracts.canonical.domain.bookmaker_registry import (
    BOOKMAKER_REGISTRY,
    BookmakerRegistry,
)
from unified_api_contracts.canonical.domain.sports import (
    BookmakerCategory,
    BookmakerInfo,
)

__all__ = ["BOOKMAKER_REGISTRY", "BookmakerCategory", "BookmakerInfo", "BookmakerRegistry"]
