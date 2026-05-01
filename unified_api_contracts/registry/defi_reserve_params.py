"""Aave V3 reserve parameters — SSOT for risk calculations.

These are per-asset protocol parameters from Aave V3 governance.
Used by risk-and-exposure-service to compute HF and LTV mathematically
from positions, without querying the protocol.

Values from: https://app.aave.com/reserve-overview/ (Ethereum mainnet)
Last updated: 2026-03-29

Format: asset → {max_ltv, liquidation_threshold, liquidation_bonus, reserve_factor}
- max_ltv: Maximum loan-to-value ratio for borrowing (e.g., 0.80 = can borrow 80% of collateral value)
- liquidation_threshold: LTV at which position becomes liquidatable (e.g., 0.825)
- liquidation_bonus: Bonus liquidators receive (e.g., 0.05 = 5%)
- reserve_factor: Protocol fee on interest (e.g., 0.10 = 10%)

Health Factor = Σ(collateral_i * liquidation_threshold_i) / total_debt
LTV = total_debt / total_collateral

E-Mode (Efficiency Mode): When collateral and debt are in the same asset category
(e.g., ETH-correlated: weETH collateral + WETH debt), Aave V3 allows significantly
higher LTV (~93% vs 72.5% standard). This dramatically changes leverage calculations.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ReserveParams:
    """Aave V3 reserve configuration for a single asset."""

    max_ltv: Decimal
    liquidation_threshold: Decimal
    liquidation_bonus: Decimal
    reserve_factor: Decimal


@dataclass(frozen=True)
class EModeCategory:
    """Aave V3 E-Mode category with elevated risk parameters."""

    category_id: int
    label: str
    max_ltv: Decimal
    liquidation_threshold: Decimal
    liquidation_bonus: Decimal
    assets: frozenset[str]


# Aave V3 Ethereum Mainnet reserve parameters
# Source: Aave governance, verified against on-chain getConfiguration()
AAVE_V3_ETHEREUM_RESERVES: dict[str, ReserveParams] = {
    # Stablecoins
    "USDC": ReserveParams(
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.825"),
        liquidation_bonus=Decimal("0.045"),
        reserve_factor=Decimal("0.10"),
    ),
    "USDT": ReserveParams(
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.825"),
        liquidation_bonus=Decimal("0.045"),
        reserve_factor=Decimal("0.10"),
    ),
    "DAI": ReserveParams(
        max_ltv=Decimal("0.77"),
        liquidation_threshold=Decimal("0.80"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    # Major assets
    "WETH": ReserveParams(
        max_ltv=Decimal("0.825"),
        liquidation_threshold=Decimal("0.86"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "WBTC": ReserveParams(
        max_ltv=Decimal("0.73"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.063"),
        reserve_factor=Decimal("0.20"),
    ),
    # LSTs
    "WSTETH": ReserveParams(
        max_ltv=Decimal("0.795"),
        liquidation_threshold=Decimal("0.83"),
        liquidation_bonus=Decimal("0.07"),
        reserve_factor=Decimal("0.05"),
    ),
    "WEETH": ReserveParams(
        max_ltv=Decimal("0.725"),
        liquidation_threshold=Decimal("0.775"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.15"),
    ),
    "CBETH": ReserveParams(
        max_ltv=Decimal("0.745"),
        liquidation_threshold=Decimal("0.79"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.15"),
    ),
    # DeFi tokens
    "LINK": ReserveParams(
        max_ltv=Decimal("0.68"),
        liquidation_threshold=Decimal("0.76"),
        liquidation_bonus=Decimal("0.07"),
        reserve_factor=Decimal("0.20"),
    ),
    "AAVE": ReserveParams(
        max_ltv=Decimal("0.66"),
        liquidation_threshold=Decimal("0.73"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.20"),
    ),
}


# ── E-Mode Categories (Aave V3 Ethereum) ──────────────────────────────────
# Source: Aave governance, on-chain getEModeCategoryData()
# Category 1: ETH-correlated — weETH, wstETH, cbETH, WETH all in same bucket
# Category 2: Stablecoins — USDC, USDT, DAI
AAVE_V3_EMODE_CATEGORIES: list[EModeCategory] = [
    EModeCategory(
        category_id=1,
        label="ETH_CORRELATED",
        max_ltv=Decimal("0.93"),
        liquidation_threshold=Decimal("0.95"),
        liquidation_bonus=Decimal("0.01"),
        assets=frozenset({"WETH", "WEETH", "WSTETH", "CBETH"}),
    ),
    EModeCategory(
        category_id=2,
        label="STABLECOIN",
        max_ltv=Decimal("0.97"),
        liquidation_threshold=Decimal("0.975"),
        liquidation_bonus=Decimal("0.01"),
        assets=frozenset({"USDC", "USDT", "DAI"}),
    ),
]

# Lookup: asset → E-Mode category
_ASSET_EMODE_MAP: dict[str, EModeCategory] = {}
for _cat in AAVE_V3_EMODE_CATEGORIES:
    for _asset in _cat.assets:
        _ASSET_EMODE_MAP[_asset] = _cat


def get_emode_category(asset: str) -> EModeCategory | None:
    """Get the E-Mode category for an asset, or None if not in any E-Mode category."""
    return _ASSET_EMODE_MAP.get(asset.upper())


def get_emode_params(collateral_asset: str, debt_asset: str) -> EModeCategory | None:
    """Get E-Mode parameters when collateral and debt are in the same category.

    Returns the EModeCategory if both assets share an E-Mode category (enabling
    higher LTV/liquidation thresholds), or None if they're in different categories
    or neither is in an E-Mode category.

    Example:
        get_emode_params("WEETH", "WETH") → ETH_CORRELATED (93% LTV, 95% liq)
        get_emode_params("WEETH", "USDC") → None (different categories)
    """
    collateral_cat = _ASSET_EMODE_MAP.get(collateral_asset.upper())
    debt_cat = _ASSET_EMODE_MAP.get(debt_asset.upper())
    if collateral_cat is not None and collateral_cat is debt_cat:
        return collateral_cat
    return None


def get_reserve_params(asset: str, chain: str = "ETHEREUM") -> ReserveParams | None:
    """Look up reserve parameters for an asset.

    Args:
        asset: Asset symbol (e.g., "USDC", "WETH") or instrument_id containing the asset.
        chain: Chain name (currently only ETHEREUM supported).

    Returns:
        ReserveParams or None if asset not found.
    """
    # Direct match
    upper = asset.upper()
    if upper in AAVE_V3_ETHEREUM_RESERVES:
        return AAVE_V3_ETHEREUM_RESERVES[upper]

    # Extract asset from A_TOKEN/DEBT_TOKEN instrument_id
    # Format: AAVEV3-ETHEREUM:A_TOKEN:AUSDC → USDC
    if ":" in upper:
        parts = upper.split(":")
        if len(parts) >= 3:
            token_name = parts[2].split("@")[0]  # Strip @CHAIN
            # A_TOKEN: AUSDC → USDC, AWETH → WETH
            if token_name.startswith("A"):
                token_name = token_name[1:]
            # DEBT_TOKEN: DEBTUSDC → USDC
            if token_name.startswith("DEBT"):
                token_name = token_name[4:]
            if token_name in AAVE_V3_ETHEREUM_RESERVES:
                return AAVE_V3_ETHEREUM_RESERVES[token_name]

    return None


def compute_health_factor(
    collateral_positions: list[tuple[str, Decimal, Decimal]],
    debt_positions: list[tuple[str, Decimal, Decimal]],
    emode_category: EModeCategory | None = None,
) -> tuple[Decimal, Decimal]:
    """Compute health factor and LTV from positions + protocol params.

    This is the same math Aave uses on-chain. Batch mode computes this
    identically to how live mode would observe it from the protocol.

    Args:
        collateral_positions: List of (instrument_id, quantity, price_usd)
        debt_positions: List of (instrument_id, quantity, price_usd)
        emode_category: If provided, uses E-Mode liquidation thresholds for
            assets in this category (significantly higher than standard).
            Pass the result of get_emode_params(collateral, debt).

    Returns:
        Tuple of (health_factor, ltv). HF = Decimal("NaN") if no debt.
    """
    total_collateral_usd = Decimal("0")
    weighted_threshold_usd = Decimal("0")
    total_debt_usd = Decimal("0")

    for inst_id, qty, price in collateral_positions:
        value = abs(qty) * price
        total_collateral_usd += value

        # E-Mode: use elevated threshold if asset is in the E-Mode category
        asset_upper = _extract_asset_symbol(inst_id)
        if emode_category is not None and asset_upper in emode_category.assets:
            weighted_threshold_usd += value * emode_category.liquidation_threshold
        else:
            params = get_reserve_params(inst_id)
            if params:
                weighted_threshold_usd += value * params.liquidation_threshold
            else:
                weighted_threshold_usd += value * Decimal("0.70")

    for _inst_id, qty, price in debt_positions:
        total_debt_usd += abs(qty) * price

    if total_debt_usd == 0:
        # No debt — lending only. HF is Infinity (no liquidation risk), LTV is 0.
        return Decimal("Infinity"), Decimal("0")

    health_factor = weighted_threshold_usd / total_debt_usd
    ltv = total_debt_usd / total_collateral_usd if total_collateral_usd > 0 else Decimal("Infinity")

    return health_factor, ltv


def _extract_asset_symbol(inst_id: str) -> str:
    """Extract the base asset symbol from an instrument ID.

    Handles formats like:
    - "WETH" → "WETH"
    - "AAVEV3-ETHEREUM:A_TOKEN:AWEETH@ETHEREUM" → "WEETH"
    - "AAVEV3-ETHEREUM:DEBT_TOKEN:DEBTWETH@ETHEREUM" → "WETH"
    - "AAVE_V3_WEETH_A_TOKEN" → "WEETH"
    - "AAVE_V3_WETH_DEBT_TOKEN" → "WETH"
    """
    upper = inst_id.upper()

    # Colon-delimited format: AAVEV3-ETHEREUM:A_TOKEN:AWEETH@ETHEREUM
    if ":" in upper:
        parts = upper.split(":")
        if len(parts) >= 3:
            token_name = parts[2].split("@")[0]
            if token_name.startswith("A") and not token_name.startswith("AAVE"):
                token_name = token_name[1:]
            if token_name.startswith("DEBT"):
                token_name = token_name[4:]
            return token_name
        return upper

    # Underscore suffix format: AAVE_V3_WEETH_A_TOKEN / AAVE_V3_WETH_DEBT_TOKEN
    for suffix in ("_A_TOKEN", "_DEBT_TOKEN", "_VARIABLE_DEBT"):
        if upper.endswith(suffix):
            core = upper[: -len(suffix)]
            parts = core.rsplit("_", 1)
            return parts[-1] if parts else upper

    return upper


# ---------------------------------------------------------------------------
# Compound V3 reserve parameters (P2.1a — workspace audit 2026-05-01)
# ---------------------------------------------------------------------------
# Source: Compound governance, on-chain ``getCollateralFactor`` /
# ``getLiquidationFactor``. Compound V3 uses per-asset collateral factors
# (max LTV) and liquidation factors (liquidation threshold) similar to Aave.
# Per-market: each Compound deployment has one base asset (USDC or ETH) and
# many collateral assets. Below is the USDC market on Ethereum.
COMPOUND_V3_ETHEREUM_RESERVES: dict[str, ReserveParams] = {
    # Compound V3 USDC market — base asset is USDC; collaterals listed below
    "WETH": ReserveParams(
        max_ltv=Decimal("0.83"),
        liquidation_threshold=Decimal("0.90"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "WBTC": ReserveParams(
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.85"),
        liquidation_bonus=Decimal("0.07"),
        reserve_factor=Decimal("0.10"),
    ),
    "WSTETH": ReserveParams(
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.85"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "CBETH": ReserveParams(
        max_ltv=Decimal("0.78"),
        liquidation_threshold=Decimal("0.83"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.10"),
    ),
    "LINK": ReserveParams(
        max_ltv=Decimal("0.74"),
        liquidation_threshold=Decimal("0.80"),
        liquidation_bonus=Decimal("0.07"),
        reserve_factor=Decimal("0.10"),
    ),
    "UNI": ReserveParams(
        max_ltv=Decimal("0.65"),
        liquidation_threshold=Decimal("0.71"),
        liquidation_bonus=Decimal("0.10"),
        reserve_factor=Decimal("0.10"),
    ),
}


# ---------------------------------------------------------------------------
# Morpho Blue reserve parameters (P2.1a — workspace audit 2026-05-01)
# ---------------------------------------------------------------------------
# Source: Morpho governance + per-market ``MarketParams`` (immutable on creation).
# Morpho Blue is permissionless: each market is isolated (one collateral, one
# loan asset, one oracle, one IRM, one LLTV). The values below cover the
# canonical curated MetaMorpho vaults' underlying markets — most-traded
# collateral assets vs USDC/USDT/DAI base. ``max_ltv`` here is the LLTV
# (liquidation loan-to-value) since Morpho Blue uses a single threshold.
MORPHO_BLUE_ETHEREUM_RESERVES: dict[str, ReserveParams] = {
    # Format: (collateral asset symbol) -> typical curated-vault params
    "WETH": ReserveParams(
        max_ltv=Decimal("0.86"),
        liquidation_threshold=Decimal("0.86"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.00"),
    ),
    "WBTC": ReserveParams(
        max_ltv=Decimal("0.86"),
        liquidation_threshold=Decimal("0.86"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.00"),
    ),
    "WSTETH": ReserveParams(
        max_ltv=Decimal("0.86"),
        liquidation_threshold=Decimal("0.86"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.00"),
    ),
    "WEETH": ReserveParams(
        max_ltv=Decimal("0.86"),
        liquidation_threshold=Decimal("0.86"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.00"),
    ),
    "USDE": ReserveParams(
        max_ltv=Decimal("0.86"),
        liquidation_threshold=Decimal("0.86"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.00"),
    ),
    "RETH": ReserveParams(
        max_ltv=Decimal("0.86"),
        liquidation_threshold=Decimal("0.86"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.00"),
    ),
}


def get_compound_reserve_params(asset: str) -> ReserveParams | None:
    """Compound V3 ETH-mainnet reserve params lookup."""
    return COMPOUND_V3_ETHEREUM_RESERVES.get(asset.upper())


def get_morpho_reserve_params(asset: str) -> ReserveParams | None:
    """Morpho Blue ETH-mainnet curated-vault reserve params lookup.

    Morpho is per-market; this returns typical params for the canonical
    curated vault on the asset. Per-market overrides should be queried
    directly via ``MarketParams`` on chain when stricter accuracy is needed.
    """
    return MORPHO_BLUE_ETHEREUM_RESERVES.get(asset.upper())
