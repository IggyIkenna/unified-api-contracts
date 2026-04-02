"""Client strategy override configuration — per-client customisation of strategy params."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class ClientStrategyOverride(BaseModel):
    """Per-client override of strategy execution parameters.

    Allows restricting venues, disabling rotation features, or fixing
    specific coins/weights for a given client-strategy combination.
    """

    client_id: str
    strategy_id: str
    allowed_perp_venues: list[str] | None = None
    allowed_spot_venues: list[str] | None = None
    allowed_lending_venues: list[str] | None = None
    multi_coin_rotation: bool = True
    dynamic_venue_weighting: bool = True
    strategy_rotation: bool = False
    fixed_basis_coin: str | None = None
    fixed_venue_weights: dict[str, float] | None = None
    max_leverage: Decimal | None = None
    max_position_usd: Decimal | None = None


class ClientConfigRegistry(BaseModel):
    """Registry of all client config overrides.

    Acts as the SSOT for per-client strategy restrictions and feature gating.
    Loaded from config at strategy-service startup (or from UAC fixtures for demos).
    """

    overrides: list[ClientStrategyOverride] = []

    def get_override(
        self,
        client_id: str,
        strategy_id: str,
    ) -> ClientStrategyOverride | None:
        """Get the override for a specific client+strategy combination.

        Returns None if no override exists (meaning: use strategy defaults).
        """
        for override in self.overrides:
            if override.client_id == client_id and override.strategy_id == strategy_id:
                return override
        return None

    def get_overrides_for_client(self, client_id: str) -> list[ClientStrategyOverride]:
        """Get all overrides for a client across all strategies."""
        return [o for o in self.overrides if o.client_id == client_id]


# ── Reference examples ──────────────────────────────────────────────────────

# Patrick's config: "DeFi guy" — paid for specific DeFi capabilities
# - Basis trade: OKX/Bybit/Binance only (not HyperLiquid, not Aster)
# - Single coin (ETH) — no multi-coin rotation
# - Equal venue weights — no dynamic weighting
# - Recursive staking: full access
# - Lending: full access (basic feature)
PATRICK_OVERRIDES = ClientConfigRegistry(
    overrides=[
        ClientStrategyOverride(
            client_id="patrick-elysium",
            strategy_id="BASIS_TRADE",
            allowed_perp_venues=["OKX", "BYBIT", "BINANCE"],  # No HyperLiquid, no Aster
            multi_coin_rotation=False,
            dynamic_venue_weighting=False,
            fixed_basis_coin="ETH",
        ),
        ClientStrategyOverride(
            client_id="patrick-elysium",
            strategy_id="STAKED_BASIS",
            allowed_perp_venues=["OKX", "BYBIT", "BINANCE"],
            multi_coin_rotation=False,
            # Staked basis uses equal weights by default — OK for Patrick
        ),
        ClientStrategyOverride(
            client_id="patrick-elysium",
            strategy_id="RECURSIVE_STAKED_BASIS",
            # Full access to recursive features — he paid for this
            # No venue restrictions on spot/lending side
        ),
        ClientStrategyOverride(
            client_id="patrick-elysium",
            strategy_id="AAVE_LENDING",
            # Full access to lending — basic feature included in tier
        ),
    ]
)
