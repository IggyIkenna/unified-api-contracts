"""Single source of truth for per-venue contract coverage: REST, WebSocket, FIX, schemas, errors.

Used by tests to assert we have the right schemas and by optional live verification for secret names.
Align with docs/INDEX.md; update both if adding a venue or capability.
"""

from .unified_api_contracts_external.venue_manifest import VENUE_MANIFEST, VenueContract

__all__ = ["VENUE_MANIFEST", "VenueContract"]
