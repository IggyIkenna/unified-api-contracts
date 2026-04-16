"""
Client Registry — SSOT for client identity and name resolution.

Used by RecordEnricher to stamp client_name on orders, fills, and positions
at write time. Also consumed by API gateway for filtering.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClientDefinition:
    """Client identity definition."""

    client_id: str
    name: str
    entity: str  # Legal entity name
    share_classes: tuple[str, ...] = ()  # Share classes this client invests in
    is_active: bool = True


class ClientRegistry:
    """Registry of all clients for name resolution and lookups."""

    def __init__(self, clients: list[ClientDefinition] | None = None) -> None:
        entries = clients or _DEFAULT_CLIENTS
        self._by_id: dict[str, ClientDefinition] = {c.client_id: c for c in entries}

    def get(self, client_id: str) -> ClientDefinition | None:
        """Get a client definition by ID."""
        return self._by_id.get(client_id)

    def resolve_name(self, client_id: str) -> str:
        """Resolve client_id → display name. Returns ID if not found."""
        defn = self._by_id.get(client_id)
        return defn.name if defn else client_id

    def get_all_active(self) -> list[ClientDefinition]:
        """Get all active clients."""
        return [c for c in self._by_id.values() if c.is_active]

    def __len__(self) -> int:
        return len(self._by_id)

    def to_dict(self) -> dict[str, object]:
        """Serialise for JSON export (used by generate_ui_reference_data.py)."""
        return {
            "clients": [
                {
                    "client_id": c.client_id,
                    "name": c.name,
                    "entity": c.entity,
                    "share_classes": list(c.share_classes),
                    "is_active": c.is_active,
                }
                for c in self._by_id.values()
            ],
        }


# ---------------------------------------------------------------------------
# Default clients
# ---------------------------------------------------------------------------

_DEFAULT_CLIENTS: list[ClientDefinition] = [
    ClientDefinition("patrick-elysium", "Patrick", "Elysium Capital", ("USDC", "ETH")),
    ClientDefinition("acme-fund", "Acme Fund", "Acme Capital Management", ("USDC",)),
    ClientDefinition("internal-prop", "Internal Prop", "Internal Proprietary Trading", ("USDT", "ETH", "BTC")),
]

CLIENT_REGISTRY = ClientRegistry()
"""Module-level singleton — import this for lookups."""
