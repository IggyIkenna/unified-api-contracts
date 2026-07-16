"""Collateral gap registry — accepted collateral, haircuts, LTV, margin, and
liquidation protocol per venue/broker.

STATUS (2026-06-12): COLLATERAL_REGISTRY BACKFILLED for the MVP venue universe
(7 perp + 2 lending venues) from in-repo SSOTs + official venue/protocol docs —
every numeric carries a ``source_of_truth`` / ``source_note`` citation; any
field that could not be sourced confidently stays ``None`` (partial-but-cited
beats complete-but-invented). Staking venues (lido/rocketpool/jito/marinade)
deliberately carry NO policy — see ``STAKING_VENUES_NO_COLLATERAL_POLICY``.
TREASURY_SPLIT_POLICIES are sourced from
``codex/04-architecture/wallet-hierarchy-and-capital-flow.md`` (DeFi 20/80,
CeFi 0/100, Sports no split). BROKER_REGISTRY remains an honest gap (no TradFi
broker in the DeFi/CeFi MVP set).

Codex SSOT:
  ``codex/04-architecture/wallet-hierarchy-and-capital-flow.md``
  ``codex/09-strategy/architecture-v2/capability-wizard.md``
Plan:
  ``plans/active/capability_wizard_and_manifest_2026_06_11.md``
  Phase 2 [SPEC] P0 (schema) + [IMPLEMENT] P2 "Registry backfills" (this fill).
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


class VenueCollateralKind(StrEnum):
    """How a venue uses the collateral the policy describes.

    Additive extension (2026-06-12 backfill) so the manifest/wizard can filter
    perp-margining venues from lending/staking venues without re-deriving the
    semantics. Mirrors ``VenueKind`` in
    ``unified_api_contracts.registry.venue_collateral`` (the live SSOT this
    backfill transcribes).
    """

    PERP_CEX = "perp_cex"
    """Collateral funds a perpetual short/long on a centralised order book."""

    PERP_DEX = "perp_dex"
    """Collateral funds a perpetual on an on-chain order book / vault DEX."""

    LENDING = "lending"
    """Collateral underwrites a borrow (Aave, Kamino, Compound, …)."""

    STAKING = "staking"
    """The asset is the principal being staked — NOT a margining venue.

    Staking venues do not take a margin/LTV ``CollateralPolicy``; the staked
    asset's downstream acceptance lives on the perp/lending venue that takes
    the LST. See ``COLLATERAL_REGISTRY`` staking notes.
    """


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
    """A single (asset, haircut) pairing accepted as collateral at a venue.

    For perp venues the relevant numeric is ``haircut_pct`` (collateral_factor
    = 1 - haircut). For LENDING venues the per-asset risk surface is the
    ``max_ltv`` / ``liquidation_threshold`` / ``liquidation_bonus`` triple
    (additive 2026-06-12 backfill — Aave-style reserves carry per-ASSET LTV,
    which the single per-policy ``CollateralPolicy.max_ltv`` could not express).
    Any unsourced field stays ``None`` — partial-but-cited beats invented.
    """

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
            "purposes. Source must be cited in the registry entry. For a "
            "lending reserve where the risk surface is LTV-expressed rather "
            "than haircut-expressed, set 0 and populate ``max_ltv`` etc."
        )
    )
    accepted: bool = Field(
        default=True,
        description=(
            "Whether this asset IS accepted as collateral at the venue. "
            "``False`` rows are DOCUMENTED negatives (e.g. an LST a perp venue "
            "does not take) — they make the staked-vs-straight-basis "
            "conditional explicit rather than silently absent. A ``False`` row "
            "carries ``haircut_pct=0``."
        ),
    )
    max_ltv: Decimal | None = Field(
        default=None,
        description=(
            "LENDING venues only: per-asset maximum loan-to-value (0-1) at "
            "which new borrows against this collateral are rejected. "
            "``None`` for perp venues / where unsourced."
        ),
    )
    liquidation_threshold: Decimal | None = Field(
        default=None,
        description=(
            "LENDING venues only: per-asset LTV (0-1) above which the position "
            "is liquidatable (Aave 'liquidation threshold'). ``None`` where unsourced."
        ),
    )
    liquidation_bonus: Decimal | None = Field(
        default=None,
        description=(
            "LENDING venues only: per-asset liquidator bonus fraction (e.g. 0.05 = 5 %). ``None`` where unsourced."
        ),
    )
    source_note: str = Field(
        default="",
        description="Where this haircut/LTV was sourced from (URL, doc, date).",
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
    venue_kind: VenueCollateralKind | None = Field(
        default=None,
        description=(
            "How the venue uses the collateral (perp / lending / staking). "
            "Drives the perp-vs-lending filter the wizard needs. "
            "``None`` only for the legacy honest-empty baseline."
        ),
    )
    accepted_collateral: list[AssetHaircut] = Field(
        default_factory=list,
        description=(
            "List of accepted collateral assets and their haircuts (and, for "
            "lending venues, per-asset LTV). Empty list = ``not_registered`` "
            "(gap, not zero assets). Documented NEGATIVES (assets the venue "
            "does NOT accept) carry ``accepted=False`` here so the "
            "staked-vs-straight-basis conditional is explicit."
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
    collateral_notes: str = Field(
        default="",
        description=(
            "Free-text caveats not expressible in the typed fields — e.g. "
            "E-Mode elevated LTVs, isolated-vs-cross differences, collateral "
            "caps, per-market collateral-set restrictions, staking semantics."
        ),
    )

    def accepted_assets(self) -> list[str]:
        """Asset symbols this venue ACCEPTS as collateral (``accepted=True``)."""
        return [h.asset for h in self.accepted_collateral if h.accepted]


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

# ---------------------------------------------------------------------------
# COLLATERAL_REGISTRY backfill — MVP venue universe (2026-06-12)
# ---------------------------------------------------------------------------
# SOURCE PRIORITY (per the backfill task):
#   1. IN-REPO SSOTs (transcribed, never re-derived):
#      - perp haircuts + accept/reject rows:
#        ``unified_api_contracts/registry/venue_collateral.py`` VENUE_COLLATERAL_MATRIX
#        (Stream A audit 2026-05-07/08).
#      - CeFi/on-chain-perp maintenance margin (tier-1 MMR at max leverage):
#        ``unified_api_contracts/registry/cefi_margin_tiers.py`` CEFI_MARGIN_TIERS
#        (last revalidated 2026-05-15). maintenance_margin = the tier-1
#        ``maintenance_margin_rate`` (smallest notional; the floor a single
#        small hedge leg sees).
#      - Aave V3 Ethereum per-asset LTV / liquidation threshold / bonus:
#        ``unified_api_contracts/registry/defi_reserve_params.py``
#        AAVE_V3_ETHEREUM_RESERVES + AAVE_V3_EMODE_CATEGORIES
#        (verified against on-chain getConfiguration(), last updated 2026-05-15).
#      - Kamino LST haircut: ``execution-service .../lst_collateral_resolver.py``
#        _LST_REGISTRY (hardcoded baseline, hot-reloadable).
#   2. OFFICIAL VENUE/PROTOCOL DOCS (verified 2026-06-12, cited per field):
#      - Hyperliquid USDC-only margin + MM = ½ IM at max leverage:
#        https://hyperliquid.gitbook.io/hyperliquid-docs/trading/margining
#      - Deribit stETH 7.5% haircut (reduced from 15%, eff. 2026-01-13, X:PM only):
#        https://insights.deribit.com/exchange-updates/portfolio-margin-improvements-for-steth-and-cross-collateral-haircuts/
#      - Aave V3 risk params dashboard: https://app.aave.com/reserve-overview/
#      - Kamino risk dashboard: https://risk.kamino.finance / https://kamino.com/docs
#   3. A number that cannot be sourced confidently is left None with a note —
#      partial-but-cited ALWAYS beats complete-but-invented. NEVER fabricated.
#
# TWO-SIDED-AUDIT FINDINGS (in-repo SSOTs disagree — see plan findings F27+):
#   - Hyperliquid LST: venue_collateral.py says USDC-ONLY (rejects wstETH);
#     execution-service lst_collateral_resolver.py says wstETH accepted @5%.
#     This backfill follows venue_collateral.py (USDC-only — matches official
#     Hyperliquid docs + the codex playbook venue-collateral-2026-05-07.md "HL is
#     USDC-only by design"). The resolver row is the conflicting in-repo claim.
#   - Bybit/Deribit/OKX stETH haircuts differ between the two in-repo files
#     (resolver 15-20% vs venue_collateral 7.5-10%). Backfill follows
#     venue_collateral.py (the Stream-A-audited SSOT with per-row citations).

# Citation shorthands (one edit site per source).
_SRC_VC = "unified_api_contracts/registry/venue_collateral.py VENUE_COLLATERAL_MATRIX (Stream A audit 2026-05-07/08)"
_SRC_CMT = "unified_api_contracts/registry/cefi_margin_tiers.py CEFI_MARGIN_TIERS (tier-1 MMR, revalidated 2026-05-15)"
_SRC_AAVE = (
    "unified_api_contracts/registry/defi_reserve_params.py AAVE_V3_ETHEREUM_RESERVES "
    "(on-chain getConfiguration(), 2026-05-15) + https://app.aave.com/reserve-overview/ (as_of 2026-06-12)"
)
_SRC_HL_DOC = (
    "https://hyperliquid.gitbook.io/hyperliquid-docs/trading/margining (USDC-only margin; "
    "MM = ½ IM at max leverage; as_of 2026-06-12)"
)
_SRC_DERIBIT_DOC = (
    "https://insights.deribit.com/exchange-updates/"
    "portfolio-margin-improvements-for-steth-and-cross-collateral-haircuts/ "
    "(stETH 7.5%, eff. 2026-01-13; as_of 2026-06-12)"
)
_SRC_KAMINO = (
    "execution-service execution_service/services/lst_collateral_resolver.py _LST_REGISTRY (KAMINO LST haircut) "
    "+ https://risk.kamino.finance (per-asset LTV on live dashboard; as_of 2026-06-12)"
)


def _ah(
    asset: str,
    haircut: str,
    *,
    accepted: bool = True,
    max_ltv: str | None = None,
    liq_threshold: str | None = None,
    liq_bonus: str | None = None,
    src: str = "",
) -> AssetHaircut:
    """Compact AssetHaircut builder (keeps the registry table readable)."""
    return AssetHaircut(
        asset=asset,
        haircut_pct=Decimal(haircut),
        accepted=accepted,
        max_ltv=Decimal(max_ltv) if max_ltv is not None else None,
        liquidation_threshold=Decimal(liq_threshold) if liq_threshold is not None else None,
        liquidation_bonus=Decimal(liq_bonus) if liq_bonus is not None else None,
        source_note=src,
    )


#: Per-venue collateral policies. Sourced from the in-repo SSOTs + official
#: venue/protocol docs cited above. Do NOT invent numbers — any unsourceable
#: field stays ``None`` with a ``collateral_notes`` line.
COLLATERAL_REGISTRY: Final[list[CollateralPolicy]] = [
    # ===================== PERP HEDGE VENUES =====================
    # ---- Hyperliquid (on-chain CLOB perp; classified cefi) ----
    CollateralPolicy(
        venue_id="hyperliquid",
        venue_kind=VenueCollateralKind.PERP_CEX,
        accepted_collateral=[
            _ah("USDC", "0", src=_SRC_VC),
            _ah("ETH", "0", accepted=False, src=_SRC_VC),
            _ah("stETH", "0", accepted=False, src=_SRC_VC),
            _ah("wstETH", "0", accepted=False, src=_SRC_VC),
            _ah("JitoSOL", "0", accepted=False, src=_SRC_VC),
            _ah("mSOL", "0", accepted=False, src=_SRC_VC),
        ],
        maintenance_margin=Decimal("0.01"),  # tier-1 MMR @ 50x BTC/ETH
        margin_modes=[MarginMode.CROSS, MarginMode.ISOLATED],
        liquidation_protocol=LiquidationProtocol.AUTO_DELEVER,
        liquidation_description="Cross/isolated margin; backstop liquidator vault then ADL. Up to 50x BTC/ETH.",
        source_of_truth=f"{_SRC_VC}; {_SRC_CMT}; {_SRC_HL_DOC}",
        collateral_notes=(
            "USDC-ONLY margin by design (linear USDC-margined, USDT-denominated oracle). "
            "No LST accepted as direct perp margin → staked-basis runs straight-basis here. "
            "F27: lst_collateral_resolver.py disagrees (claims wstETH @5%) — venue_collateral.py + "
            "official docs win."
        ),
    ),
    # ---- GMX v2 (Arbitrum perp DEX) ----
    CollateralPolicy(
        venue_id="gmx_v2",
        venue_kind=VenueCollateralKind.PERP_DEX,
        accepted_collateral=[
            _ah("USDC", "0", src=_SRC_VC),
            _ah("ETH", "5", src=_SRC_VC),
            _ah("WBTC", "5", src=_SRC_VC),
            _ah("stETH", "0", accepted=False, src=_SRC_VC),
            _ah("wstETH", "0", accepted=False, src=_SRC_VC),
        ],
        maintenance_margin=None,  # per-market on-chain config; not statically sourced
        margin_modes=[MarginMode.CROSS, MarginMode.ISOLATED],
        liquidation_protocol=LiquidationProtocol.KEEPER_AUCTION,
        liquidation_description="GMX v2 per-market collateral set; keeper-executed liquidation on-chain.",
        source_of_truth=_SRC_VC,
        collateral_notes=(
            "Per-market collateral sets exclude LSTs. Maintenance-margin is per-market on-chain "
            "(getMarketInfo) — left None (not statically sourceable; would be invented)."
        ),
    ),
    # ---- Drift (Solana perp DEX) collateral policy removed 2026-07-16 (operator ruling: all
    # Solana perp DEXes dropped except Jupiter, not integrated).
    # SSOT: unified-trading-pm/codex/04-architecture/solana-defi-coverage.md.
    # ---- Binance (USDT-M / coin-M perp) ----
    CollateralPolicy(
        venue_id="binance",
        venue_kind=VenueCollateralKind.PERP_CEX,
        accepted_collateral=[
            _ah("USDT", "0", src=_SRC_VC),
            _ah("BTC", "5", src=_SRC_VC),
            _ah("ETH", "5", src=_SRC_VC),
            _ah("stETH", "0", accepted=False, src=_SRC_VC),
            _ah("wstETH", "0", accepted=False, src=_SRC_VC),
        ],
        maintenance_margin=Decimal("0.004"),  # tier-1 MMR BTC @125x
        margin_modes=[MarginMode.CROSS, MarginMode.ISOLATED],
        liquidation_protocol=LiquidationProtocol.INSURANCE_FUND,
        liquidation_description="Tiered margin (BTC tier-1 MMR 0.4%); insurance fund then ADL.",
        source_of_truth=f"{_SRC_VC}; {_SRC_CMT}",
        collateral_notes=(
            "Multi-Assets Mode lists BTC/ETH/BNB/XRP/ADA/DOT/SOL/USDC/USDT — no LST. "
            "tier-1 MMR is the BTC schedule (0.4%); ETH tier-1 MMR is 0.5%."
        ),
    ),
    # ---- Bybit (UTA / linear perp) ----
    CollateralPolicy(
        venue_id="bybit",
        venue_kind=VenueCollateralKind.PERP_CEX,
        accepted_collateral=[
            _ah("USDT", "0", src=_SRC_VC),
            _ah("BTC", "5", src=_SRC_VC),
            _ah("stETH", "10", src=_SRC_VC),
            _ah("wstETH", "10", src=_SRC_VC),
            _ah("USDe", "5", src=_SRC_VC),
            _ah("sUSDe", "7", src=_SRC_VC),
        ],
        maintenance_margin=Decimal("0.005"),  # tier-1 MMR BTC @100x
        margin_modes=[MarginMode.CROSS, MarginMode.PORTFOLIO],
        liquidation_protocol=LiquidationProtocol.INSURANCE_FUND,
        liquidation_description="UTA portfolio margin; stETH/wstETH @10% collateral; insurance fund.",
        source_of_truth=f"{_SRC_VC}; {_SRC_CMT}",
        collateral_notes=(
            "stETH/wstETH accepted as UTA collateral since 2024-02 (10% haircut placeholder; "
            "live-API probe pending). ETH tier-1 MMR is 1.0%. F27: resolver claims stETH @15% / "
            "wstETH @10% — venue_collateral.py SSOT used."
        ),
    ),
    # ---- Deribit (portfolio-margin perp/options) ----
    CollateralPolicy(
        venue_id="deribit",
        venue_kind=VenueCollateralKind.PERP_CEX,
        accepted_collateral=[
            _ah("BTC", "0", src=_SRC_VC),
            _ah("ETH", "0", src=_SRC_VC),
            _ah("USDC", "2", src=_SRC_VC),
            _ah("stETH", "7.5", src=_SRC_DERIBIT_DOC),
            _ah("wstETH", "0", accepted=False, src=_SRC_VC),
            _ah("weETH", "0", accepted=False, src=_SRC_VC),
            _ah("rETH", "0", accepted=False, src=_SRC_VC),
        ],
        maintenance_margin=Decimal("0.01"),  # tier-1 MMR BTC/ETH @50x
        margin_modes=[MarginMode.PORTFOLIO, MarginMode.CROSS],
        liquidation_protocol=LiquidationProtocol.INSURANCE_FUND,
        liquidation_description="Portfolio margin; stETH @7.5% offsets ETH-perp (X:PM only); insurance fund.",
        source_of_truth=f"{_SRC_VC}; {_SRC_CMT}; {_SRC_DERIBIT_DOC}",
        collateral_notes=(
            "stETH cross-collateral haircut 7.5% (reduced from 15%, eff. 2026-01-13, X:PM accounts only) — "
            "verified at official Deribit insights 2026-06-12. F27: resolver claims stETH @20% (stale)."
        ),
    ),
    # ---- OKX (multi-currency-margin perp) ----
    CollateralPolicy(
        venue_id="okx",
        venue_kind=VenueCollateralKind.PERP_CEX,
        accepted_collateral=[
            _ah("USDT", "0", src=_SRC_VC),
            _ah("BTC", "5", src=_SRC_VC),
            _ah("ETH", "5", src=_SRC_VC),
            _ah("wstETH", "10", src=_SRC_VC),
            _ah("stETH", "0", accepted=False, src=_SRC_VC),
            _ah("weETH", "0", accepted=False, src=_SRC_VC),
        ],
        maintenance_margin=Decimal("0.005"),  # tier-1 MMR BTC @100x
        margin_modes=[MarginMode.CROSS, MarginMode.PORTFOLIO],
        liquidation_protocol=LiquidationProtocol.INSURANCE_FUND,
        liquidation_description="Multi-currency margin; wstETH @10% on discount-rate list; insurance fund.",
        source_of_truth=f"{_SRC_VC}; {_SRC_CMT}",
        collateral_notes=(
            "wstETH on multi-currency-margin discount-rate list (10% haircut). stETH NOT on the list "
            "(accepted=False). ETH tier-1 MMR 0.65%. F27: resolver claims stETH @15% accepted."
        ),
    ),
    # ===================== LENDING VENUES =====================
    # ---- Aave V3 (Ethereum mainnet) — per-asset LTV on each AssetHaircut ----
    CollateralPolicy(
        venue_id="aave_v3",
        venue_kind=VenueCollateralKind.LENDING,
        accepted_collateral=[
            _ah("WETH", "0", max_ltv="0.825", liq_threshold="0.86", liq_bonus="0.05", src=_SRC_AAVE),
            _ah("wstETH", "0", max_ltv="0.795", liq_threshold="0.83", liq_bonus="0.07", src=_SRC_AAVE),
            _ah("weETH", "0", max_ltv="0.725", liq_threshold="0.775", liq_bonus="0.075", src=_SRC_AAVE),
            _ah("cbETH", "0", max_ltv="0.745", liq_threshold="0.79", liq_bonus="0.075", src=_SRC_AAVE),
            _ah("rETH", "0", max_ltv="0.745", liq_threshold="0.79", liq_bonus="0.075", src=_SRC_AAVE),
            _ah("WBTC", "0", max_ltv="0.73", liq_threshold="0.78", liq_bonus="0.063", src=_SRC_AAVE),
            _ah("USDC", "0", max_ltv="0.80", liq_threshold="0.825", liq_bonus="0.045", src=_SRC_AAVE),
            _ah("USDT", "0", max_ltv="0.80", liq_threshold="0.825", liq_bonus="0.045", src=_SRC_AAVE),
            _ah("DAI", "0", max_ltv="0.77", liq_threshold="0.80", liq_bonus="0.05", src=_SRC_AAVE),
        ],
        max_ltv=Decimal("0.825"),  # WETH headline (highest non-emode major); per-asset on AssetHaircut
        liquidation_ltv=Decimal("0.86"),  # WETH headline liquidation threshold
        margin_modes=[MarginMode.CROSS],
        liquidation_protocol=LiquidationProtocol.KEEPER_AUCTION,
        liquidation_description="Health-factor liquidation; keeper repays debt for collateral + bonus.",
        source_of_truth=_SRC_AAVE,
        collateral_notes=(
            "Per-asset LTV/liquidation-threshold live on each AssetHaircut. E-Mode ETH_CORRELATED "
            "(WETH/wstETH/weETH/cbETH/rETH) elevates to max_ltv 0.93 / liq 0.95 / bonus 0.01; "
            "STABLECOIN E-Mode to 0.97/0.975. Policy-level max_ltv/liquidation_ltv are the WETH "
            "standard (non-E-Mode) headline. Ethereum mainnet only; multi-chain in defi_reserve_params.py."
        ),
    ),
    # ---- Kamino (Solana lending) — partial: LST haircut sourced, LTV None ----
    CollateralPolicy(
        venue_id="kamino",
        venue_kind=VenueCollateralKind.LENDING,
        accepted_collateral=[
            _ah("mSOL", "15", src=_SRC_KAMINO),
            _ah("JitoSOL", "15", src=_SRC_KAMINO),
            _ah("SOL", "0", src=_SRC_KAMINO),
            _ah("USDC", "0", src=_SRC_KAMINO),
            _ah("USDT", "0", src=_SRC_KAMINO),
        ],
        max_ltv=None,  # per-asset LTV lives on the live Kamino risk dashboard; not statically sourced
        liquidation_ltv=None,
        margin_modes=[MarginMode.CROSS],
        liquidation_protocol=LiquidationProtocol.KEEPER_AUCTION,
        liquidation_description="K-Lend health-factor liquidation; penalty starts 2%, capped 10%.",
        source_of_truth=_SRC_KAMINO,
        collateral_notes=(
            "PARTIAL: accepted set + LST 15% haircut sourced from lst_collateral_resolver.py; "
            "per-asset max_ltv / liquidation_threshold left None — Kamino publishes these only on the "
            "live risk dashboard (https://risk.kamino.finance), not as static docs. Liquidation penalty "
            "2-10% (official docs.kamino.finance). JitoSOL Multiply reaches ~90% LTV but that is the "
            "Multiply product, not a clean lend max_ltv → not transcribed."
        ),
    ),
]

# ---------------------------------------------------------------------------
# Staking venues (lido, rocketpool, jito, marinade) — NO CollateralPolicy.
# ---------------------------------------------------------------------------
# Per the schema's STAKING semantics + the task direction: a staking venue is
# NOT a margining/lending venue. Its "collateral" is the staking PRINCIPAL (ETH
# → stETH/wstETH/rETH; SOL → JitoSOL/mSOL), and the downstream margin/LTV
# acceptance of the resulting LST lives on the PERP / LENDING venue that takes
# it (the rows above: Aave wstETH/weETH/rETH/cbETH LTV; Kamino mSOL/JitoSOL 15%;
# Bybit/OKX/Deribit stETH/wstETH haircuts). So lido/rocketpool/jito/marinade
# deliberately carry NO CollateralPolicy entry — adding a margin/LTV row for a
# staking contract would be inventing a number the protocol does not define.
# The staking principal/output mapping is the leg-spec registry's job
# (archetype_leg_spec.py _STAKE_PROTOCOLS_ETH_SOL) + the LST-APR data feed.
STAKING_VENUES_NO_COLLATERAL_POLICY: Final[tuple[str, ...]] = (
    "lido",
    "rocketpool",
    "jito",
    "marinade",
)

#: TradFi broker list. Empty until broker capability code-scanned (not in the
#: DeFi/CeFi MVP venue set — honest gap remains).
BROKER_REGISTRY: Final[list[BrokerEntry]] = []


__all__ = [
    "BROKER_REGISTRY",
    "COLLATERAL_REGISTRY",
    "STAKING_VENUES_NO_COLLATERAL_POLICY",
    "TREASURY_SPLIT_POLICIES",
    "AssetHaircut",
    "BrokerEntry",
    "CollateralAsset",
    "CollateralPolicy",
    "LiquidationProtocol",
    "TreasurySplitPolicy",
    "VenueCollateralKind",
    "WalletTier",
]
