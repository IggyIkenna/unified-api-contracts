"""
Client Registry — SSOT for client identity and name resolution.

Used by RecordEnricher to stamp client_name on orders, fills, and positions
at write time. Also consumed by API gateway for filtering.

``account_type`` distinguishes live client accounts from Odum's representative
paper / live accounts (``odum-paper`` / ``odum-live``) — client zero in the
Plan A maturity model. These are regular rows, not special-cased in code:
downstream services (position-balance-monitor, execution-service,
strategy-service) treat them like any other client, and every strategy
instance runs through both odum accounts by default so tearsheets always
have a continuous backtest → paper → live series to show.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AccountType(StrEnum):
    """Client account flavour.

    ``LIVE`` is the default for fee-paying customers. ``PAPER`` is reserved
    for the ``odum-paper`` seed (single instance per environment) that runs
    every catalogue strategy through the execution-service matching engine
    in always-fill mode. No real venue orders fire for PAPER accounts.
    """

    LIVE = "live"
    PAPER = "paper"


@dataclass(frozen=True)
class ClientDefinition:
    """Client identity definition."""

    client_id: str
    name: str
    entity: str  # Legal entity name
    account_type: AccountType = AccountType.LIVE
    share_classes: tuple[str, ...] = ()  # Share classes this client invests in
    is_active: bool = True
    seed: bool = False
    """True for UAC-seeded rows (odum-paper / odum-live) — surfaces in admin UI
    as non-deletable system clients."""


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

    def get_by_account_type(self, account_type: AccountType) -> list[ClientDefinition]:
        """Get all clients of a given account type (paper vs live)."""
        return [c for c in self._by_id.values() if c.account_type is account_type]

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
                    "account_type": c.account_type.value,
                    "share_classes": list(c.share_classes),
                    "is_active": c.is_active,
                    "seed": c.seed,
                }
                for c in self._by_id.values()
            ],
        }


# ---------------------------------------------------------------------------
# Default clients
# ---------------------------------------------------------------------------

_DEFAULT_CLIENTS: list[ClientDefinition] = [
    # Client zero — runs every catalogue instance through the matching engine
    # in paper mode. Source of the "paper" line on IM / DART / FOMO tearsheets.
    ClientDefinition(
        client_id="odum-paper",
        name="Odum (Paper)",
        entity="Odum Research",
        account_type=AccountType.PAPER,
        share_classes=("USD", "USDT", "ETH", "BTC"),
        seed=True,
    ),
    # Live twin — a strategy graduates to ``odum-live`` when it reaches
    # ``LIVE_EARLY`` maturity, giving the overlay its "live" line with Odum's
    # own small capital (never another client's private flow).
    ClientDefinition(
        client_id="odum-live",
        name="Odum (Live)",
        entity="Odum Research",
        account_type=AccountType.LIVE,
        share_classes=("USD", "USDT", "ETH", "BTC"),
        seed=True,
    ),
    ClientDefinition("patrick-elysium", "Patrick", "Elysium Capital", share_classes=("USDC", "ETH")),
    ClientDefinition("acme-fund", "Acme Fund", "Acme Capital Management", share_classes=("USDC",)),
    ClientDefinition(
        "internal-prop",
        "Internal Prop",
        "Internal Proprietary Trading",
        share_classes=("USDT", "ETH", "BTC"),
    ),
]

CLIENT_REGISTRY = ClientRegistry()
"""Module-level singleton — import this for lookups."""
