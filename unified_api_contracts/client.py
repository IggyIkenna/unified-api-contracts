"""Client + capital allocation public facade.

See :mod:`unified_api_contracts.canonical.domain.client.model` for the SSOT
implementation. Consumers must import from this facade only — deep paths under
``canonical.*`` are UAC-internal per the workspace import-rules.
"""

from .canonical.domain.client.model import (
    CAPITAL_ALLOCATION_SEED,
    CLIENTS_SEED,
    AccountId,
    AllocationKey,
    AllocationViolationError,
    ArchetypeRef,
    CapitalAllocation,
    Client,
    ClientId,
    VenueAccount,
    get_capital_allocation,
    get_client,
    is_allocation_declared,
    is_within_allocation,
    validate_allocation_respect,
)

__all__ = [
    "CAPITAL_ALLOCATION_SEED",
    "CLIENTS_SEED",
    "AccountId",
    "AllocationKey",
    "AllocationViolationError",
    "ArchetypeRef",
    "CapitalAllocation",
    "Client",
    "ClientId",
    "VenueAccount",
    "get_capital_allocation",
    "get_client",
    "is_allocation_declared",
    "is_within_allocation",
    "validate_allocation_respect",
]
