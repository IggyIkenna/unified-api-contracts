"""Canonical schema for deployment-service/configs/strategy/{archetype}/clients.yaml.

Each archetype's clients.yaml lists the per-client + per-shard entries that
StrategySupervisor reads at boot and on REGISTER/DEREGISTER lifecycle events.

For May-23 the supervisor ships with shard_id=0 for all clients; multi-shard
operation comes in Phase E.2 (auto-shard supervisor signal, 2026-05-28).

KMS path convention
-------------------
``venue_creds_kms_path`` is a fully-qualified GCP Secret Manager resource name:
    projects/{project}/secrets/{secret-name}/versions/latest
The ClientCredentialKmsPoller in UTL resolves this at boot and on hot-reload.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MinBalancePerVenue(_Base):
    """Minimum USD-equivalent balance required per venue before CLIENT_READY.

    Keys are lowercase venue slugs matching UAC VenueSlug (e.g. "binance",
    "hyperliquid", "aave-v3"). Values are USD-equivalent amounts.
    """

    root: dict[str, float] = Field(default_factory=dict)

    def __getitem__(self, venue: str) -> float:
        return self.root[venue]

    def items(self) -> list[tuple[str, float]]:
        return list(self.root.items())

    model_config = ConfigDict(extra="allow")


class ClientRiskLimits(_Base):
    """Per-client risk envelope enforced by StrategySupervisor before order emission."""

    max_position_usd: float = Field(
        ...,
        description="Maximum aggregate open position in USD-equivalent across all venues.",
        gt=0,
    )
    max_drawdown_pct: float = Field(
        ...,
        description="Maximum intraday drawdown as a fraction of NAV (e.g. 0.05 = 5%).",
        gt=0,
        le=1.0,
    )
    max_order_size_usd: float | None = Field(
        default=None,
        description="Per-order size cap in USD. None = no per-order cap (position cap still applies).",
        gt=0,
    )


class ClientsYamlEntry(_Base):
    """Single client entry in clients.yaml for a given archetype + shard."""

    client_id: str = Field(
        ...,
        description="Stable identifier for this managed account (e.g. 'us', 'defi-client-1').",
        min_length=1,
    )
    shard_id: int = Field(
        default=0,
        description="Shard index this client is pinned to. 0 for all May-23 clients.",
        ge=0,
    )
    venue_creds_kms_path: str = Field(
        ...,
        description=(
            "GCP Secret Manager resource name for venue credentials bundle. "
            "Format: projects/{project}/secrets/{secret}/versions/latest"
        ),
        pattern=r"^projects/[^/]+/secrets/[^/]+/versions/[^/]+$",
    )
    min_balance_per_venue: dict[str, float] = Field(
        default_factory=dict,
        description="Minimum USD-equivalent balance required per venue slug before CLIENT_READY.",
    )
    risk_limits: ClientRiskLimits


class ClientsYaml(_Base):
    """Root schema for deployment-service/configs/strategy/{archetype}/clients.yaml."""

    clients: list[ClientsYamlEntry] = Field(
        ...,
        description="Ordered list of per-client entries. At least one entry required.",
        min_length=1,
    )

    def client_ids(self) -> list[str]:
        return [c.client_id for c in self.clients]

    def for_shard(self, shard_id: int) -> list[ClientsYamlEntry]:
        """Return entries pinned to the given shard_id."""
        return [c for c in self.clients if c.shard_id == shard_id]
