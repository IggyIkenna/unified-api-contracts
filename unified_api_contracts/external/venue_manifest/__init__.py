"""Single source of truth for per-venue contract coverage: REST, WebSocket, FIX, schemas, errors.

Used by tests to assert we have the right schemas and by optional live verification for secret names.
Align with docs/INDEX.md; update both if adding a venue or capability.
"""

from __future__ import annotations

from typing import TypedDict, cast

from .betting_sports import BETTING_SPORTS_VENUES
from .cefi import CEFI_VENUES
from .data_providers import DATA_PROVIDER_VENUES
from .defi import DEFI_VENUES
from .internal_services import INTERNAL_CONTRACTS, ContractEntry
from .tradfi import TRADFI_VENUES


class VenueContract(TypedDict):
    """Per-venue contract claims."""

    has_rest: bool
    has_websocket: bool
    has_fix: bool
    """Config field name for Secret Manager (UnifiedCloudConfig), or empty if no API key."""
    config_secret_field: str
    """Expected schema class names in this venue's schemas.py (REST response types)."""
    response_schema_classes: list[str]
    """Expected error/status schema class names."""
    error_schema_classes: list[str]
    """Example file name pattern -> schema class name for validation."""
    example_schema_map: dict[str, str]


VENUE_MANIFEST: dict[str, VenueContract | ContractEntry] = cast(
    dict[str, VenueContract | ContractEntry],
    {
        **DATA_PROVIDER_VENUES,
        **CEFI_VENUES,
        **DEFI_VENUES,
        **TRADFI_VENUES,
        **BETTING_SPORTS_VENUES,
        **INTERNAL_CONTRACTS,
    },
)


__all__ = [
    "BETTING_SPORTS_VENUES",
    "CEFI_VENUES",
    "DATA_PROVIDER_VENUES",
    "DEFI_VENUES",
    "INTERNAL_CONTRACTS",
    "TRADFI_VENUES",
    "VENUE_MANIFEST",
    "VenueContract",
]
