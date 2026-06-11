"""Collateral gap registry — accepted collateral, haircuts, LTV, margin, and
liquidation protocol per venue/broker.

STATUS: schema shipped; numeric entries (haircuts/LTVs) are NOT seeded because
no authoritative per-venue source has been code-scanned yet. The sole exception
is the treasury/hot-wallet split policy which IS sourced from:
  ``codex/04-architecture/wallet-hierarchy-and-capital-flow.md``
(DeFi 20 % treasury / 80 % hot, CeFi 0 % / 100 %, Sports no split).

The honest ``not_registered`` baseline is the point — it forces the manifest
to surface these as gaps rather than silently omitting the dimension.

Codex SSOT:
  ``codex/04-architecture/wallet-hierarchy-and-capital-flow.md``
  ``codex/09-strategy/architecture-v2/capability-wizard.md``
Plan:
  ``plans/active/capability_wizard_and_manifest_2026_06_11.md``
  Phase 2 [SPEC] P0.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.internal.architecture_v2.enums import MarginMode

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CollateralAsset(StrEnum):
    """Well-known collateral asset identifiers.

    Intentionally open-ended — venues may accept long-tail assets not listed
    here. Use free-text ``str`` for unlisted assets.
    """

    USDC = "USDC"
    USDT = "USDT"
    BTC = "BTC"
    ETH = "ETH"
    SOL = "SOL"
    STETH = "stETH"
    RETH = "rETH"
    CBETH = "cbETH"
    WBTC = "wBTC"
    DAI = "DAI"
    FDUSD = "FDUSD"


class LiquidationProtocol(StrEnum):
    """High-level liquidation mechanism categories.

    For detailed per-venue descriptions use the ``liquidation_description``
    free-text field on ``CollateralPolicy``.
    """

    AUTO_DELEVER = "auto_delever"
    """Exchange auto-deleverage (ADL) — matched against profitable positions."""

    SOCIALIZED_LOSS = "socialized_loss"
    """Loss socialised across the insurance fund or all position holders."""

    INSURANCE_FUND = "insurance_fund"
    """Exchange insurance fund absorbs shortfall before any socialisation."""

    KEEPER_AUCTION = "keeper_auction"
    """DeFi-style keeper auction (e.g. Aave, Compound, MakerDAO)."""

    DUTCH_AUCTION = "dutch_auction"
    """Declining-price auction for collateral (e.g. some MakerDAO Vaults)."""

    BROKER_MANAGED = "broker_managed"
    """TradFi broker initiates margin call and liquidation at discretion."""


# ---------------------------------------------------------------------------
# Treasury split policy (sourced, not a gap)
# ---------------------------------------------------------------------------


class WalletTier(StrEnum):
    """Wallet tier in the two-tier capital hierarchy."""

    TREASURY = "treasury"
    """Client-facing deposit/withdrawal wallet. Share-class keyed."""

    HOT = "hot"
    """Strategy execution wallet per (strategy, chain)."""


class TreasurySplitPolicy(BaseModel):
    """Treasury-vs-hot capital allocation policy for a given asset group.

    Source:
      ``codex/04-architecture/wallet-hierarchy-and-capital-flow.md``
      §§ "Capital Allocation Model — DeFi", "CeFi", "Sports".
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_group: str = Field(
        description=(
            "Asset group this policy applies to "
            "(``'defi'`` / ``'cefi'`` / ``'sports'`` / ``'tradfi'`` / ``'prediction'``)."
        )
    )
    treasury_pct: Decimal = Field(
        description=(
            "Percentage of AUM held in the treasury wallet (0-100). "
            "DeFi default: 20. CeFi: 0 (pass-through). Sports: N/A (0)."
        )
    )
    hot_pct: Decimal = Field(
        description=(
            "Percentage of AUM deployed to hot / trading wallets (0-100). "
            "DeFi default: 80. CeFi: 100. Sports: N/A (100)."
        )
    )
    rebalance_min_threshold_pct: Decimal | None = Field(
        default=None,
        description=(
            "When treasury falls below this percentage, strategies reduce "
            "positions and flow capital back. DeFi default: 10 %. "
            "``None`` = no lower bound (CeFi / Sports)."
        ),
    )
    rebalance_max_threshold_pct: Decimal | None = Field(
        default=None,
        description=(
            "When treasury exceeds this percentage, excess flows to hot wallets. "
            "DeFi default: 30 %. ``None`` = no upper bound (CeFi / Sports)."
        ),
    )
    notes: str = Field(
        default="",
        description="Free-text notes on the policy and its source.",
    )


# ---------------------------------------------------------------------------
# CollateralPolicy — per-venue schema (gaps remain un-seeded)
# ---------------------------------------------------------------------------


class AssetHaircut(BaseModel):
    """A single (asset, haircut) pairing accepted as collateral at a venue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset: str = Field(
        description=(
            "Collateral asset identifier. Prefer ``CollateralAsset`` values; use free-text for unlisted assets."
        )
    )
    haircut_pct: Decimal = Field(
        description=(
            "Haircut as a percentage (0-100). A haircut of 10 means the "
            "collateral is valued at 90 % of its market price for margin "
            "purposes. Source must be cited in the registry entry."
        )
    )
    source_note: str = Field(
        default="",
        description="Where this haircut was sourced from (URL, doc, date).",
    )


class CollateralPolicy(BaseModel):
    """Collateral, LTV, margin, and liquidation policy for a single venue.

    Fields that cannot be sourced from existing UAC constants or docs are
    left as ``None`` — honest absence, not invented numbers.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    venue_id: str = Field(
        description=(
            "Stable venue identifier matching the instruments-service / "
            "ENDPOINT_REGISTRY convention (e.g. ``'hyperliquid'``, "
            "``'binance'``, ``'aave_v3'``)."
        )
    )
    accepted_collateral: list[AssetHaircut] = Field(
        default_factory=list,
        description=(
            "List of accepted collateral assets and their haircuts. "
            "Empty list = ``not_registered`` (gap, not zero assets)."
        ),
    )
    max_ltv: Decimal | None = Field(
        default=None,
        description=(
            "Maximum loan-to-value ratio (0-1). At this LTV new borrows are rejected. ``None`` = not registered."
        ),
    )
    liquidation_ltv: Decimal | None = Field(
        default=None,
        description=("LTV at which the position is eligible for liquidation (0-1). ``None`` = not registered."),
    )
    maintenance_margin: Decimal | None = Field(
        default=None,
        description=(
            "Minimum maintenance margin fraction required to keep a position open (0-1). ``None`` = not registered."
        ),
    )
    margin_modes: list[MarginMode] = Field(
        default_factory=list,
        description=(
            "Margin modes supported by this venue for the configured position "
            "(reuses ``MarginMode`` from ``architecture_v2.enums``)."
        ),
    )
    liquidation_protocol: LiquidationProtocol | None = Field(
        default=None,
        description=("High-level liquidation mechanism. ``None`` = not registered."),
    )
    liquidation_description: str = Field(
        default="",
        description=(
            "Free-text description of the liquidation protocol, including "
            "insurance-fund mechanics, ADL rules, or keeper thresholds."
        ),
    )
    source_of_truth: str = Field(
        default="",
        description=(
            "Where the numbers in this entry came from. "
            "Required if any numeric field is populated. "
            "E.g. ``'Hyperliquid docs 2026-05 / codex reference'``."
        ),
    )


class BrokerEntry(BaseModel):
    """A TradFi broker entry in the collateral registry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    broker_id: str = Field(
        description=("Stable broker identifier (e.g. ``'interactive_brokers'``, ``'tradestation'``).")
    )
    supported_margin_modes: list[MarginMode] = Field(
        default_factory=list,
        description="Margin modes available on this broker's accounts.",
    )
    notes: str = Field(
        default="",
        description="Free-text notes on the broker's collateral / margin rules.",
    )


# ---------------------------------------------------------------------------
# Seeded registries
# ---------------------------------------------------------------------------

#: Treasury/hot split policies — sourced from
#: ``codex/04-architecture/wallet-hierarchy-and-capital-flow.md``.
#: These three entries ARE definitive; numeric LTV/haircut entries are empty
#: (``not_registered``) until per-venue sources are code-scanned.
TREASURY_SPLIT_POLICIES: Final[list[TreasurySplitPolicy]] = [
    TreasurySplitPolicy(
        asset_group="defi",
        treasury_pct=Decimal("20"),
        hot_pct=Decimal("80"),
        rebalance_min_threshold_pct=Decimal("10"),
        rebalance_max_threshold_pct=Decimal("30"),
        notes=(
            "Source: codex/04-architecture/wallet-hierarchy-and-capital-flow.md "
            "§ 'Capital Allocation Model — DeFi'. "
            "Configurable; 20/80 is the operational default."
        ),
    ),
    TreasurySplitPolicy(
        asset_group="cefi",
        treasury_pct=Decimal("0"),
        hot_pct=Decimal("100"),
        rebalance_min_threshold_pct=None,
        rebalance_max_threshold_pct=None,
        notes=(
            "Source: codex/04-architecture/wallet-hierarchy-and-capital-flow.md "
            "§ 'Capital Allocation Model — CeFi'. "
            "Exchange-managed; client deposits land in funding account, "
            "system transfers to trading sub-account immediately."
        ),
    ),
    TreasurySplitPolicy(
        asset_group="sports",
        treasury_pct=Decimal("0"),
        hot_pct=Decimal("100"),
        rebalance_min_threshold_pct=None,
        rebalance_max_threshold_pct=None,
        notes=(
            "Source: codex/04-architecture/wallet-hierarchy-and-capital-flow.md "
            "§ 'Sports'. Single wallet per venue. No treasury/hot split."
        ),
    ),
]

#: Per-venue collateral policies. Empty until per-venue haircut/LTV sources
#: are code-scanned. Do NOT invent numbers — ``not_registered`` is honest.
COLLATERAL_REGISTRY: Final[list[CollateralPolicy]] = []

#: TradFi broker list. Empty until broker capability code-scanned.
BROKER_REGISTRY: Final[list[BrokerEntry]] = []


__all__ = [
    "BROKER_REGISTRY",
    "COLLATERAL_REGISTRY",
    "TREASURY_SPLIT_POLICIES",
    "AssetHaircut",
    "BrokerEntry",
    "CollateralAsset",
    "CollateralPolicy",
    "LiquidationProtocol",
    "TreasurySplitPolicy",
    "WalletTier",
]
