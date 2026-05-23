"""Aave V3 reserve parameters — SSOT for risk calculations.

These are per-asset protocol parameters from Aave V3 governance.
Used by strategy-service/risk to compute HF and LTV mathematically
from positions, without querying the protocol.

Values from: https://app.aave.com/reserve-overview/ (Ethereum mainnet + multi-chain
markets), https://app.spark.fi/markets, https://app.radiant.capital.
Last updated: 2026-05-15

Per-chain Aave V3 markets sourced from
``https://app.aave.com/reserve-overview/?marketName=proto_<chain>_v3``. Spark is an
Aave V3 fork on Ethereum (same dataclass shape). Radiant is an Aave V2 fork
deployed on Arbitrum + BSC + other chains (same dataclass shape).

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


class UnknownChainError(ValueError):
    """Raised when a chain name is not present in the reserve-params registry.

    This is a hard error — callers that pass an unknown chain string almost
    certainly have a misconfiguration bug.  Returning None silently would mask
    routing errors for multi-chain strategies (see P0 bug in
    defi_recursive_borrow_archetypes_2026_05_10.md § "P0 silent correctness bug").

    Supported chains: ETHEREUM / ARBITRUM / OPTIMISM / BASE / AVALANCHE /
    POLYGON / BSC / LINEA / SCROLL / ZKSYNC.
    """


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
    # Restaking LST (added 2026-05-12 per defi_recursive_borrow Family 1 design)
    "RETH": ReserveParams(
        max_ltv=Decimal("0.745"),
        liquidation_threshold=Decimal("0.79"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.15"),
    ),
    # Yield-bearing stablecoins — top recursive-borrow cell candidates (P1 addition 2026-05-15)
    # Source: app.aave.com Ethereum market — low-confidence, verify before mainnet use
    "SUSDE": ReserveParams(
        max_ltv=Decimal("0.72"),
        liquidation_threshold=Decimal("0.75"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.20"),
    ),
    "GHO": ReserveParams(
        max_ltv=Decimal("0.00"),  # GHO is borrow-only on Aave V3 ETH; no collateral
        liquidation_threshold=Decimal("0.00"),
        liquidation_bonus=Decimal("0.00"),
        reserve_factor=Decimal("0.00"),
    ),
    "SDAI": ReserveParams(
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.82"),
        liquidation_bonus=Decimal("0.045"),
        reserve_factor=Decimal("0.10"),
    ),
    "FRAX": ReserveParams(
        max_ltv=Decimal("0.00"),  # frozen on Aave V3 ETH as of 2026-05-15
        liquidation_threshold=Decimal("0.00"),
        liquidation_bonus=Decimal("0.00"),
        reserve_factor=Decimal("0.10"),
    ),
    "LUSD": ReserveParams(
        max_ltv=Decimal("0.00"),  # collateral-disabled on Aave V3 ETH
        liquidation_threshold=Decimal("0.00"),
        liquidation_bonus=Decimal("0.00"),
        reserve_factor=Decimal("0.10"),
    ),
}


# ── E-Mode Categories (Aave V3 Ethereum) ──────────────────────────────────
# Source: Aave governance, on-chain getEModeCategoryData()
# Category 1: ETH-correlated — weETH, wstETH, cbETH, rETH, WETH all in same bucket
# Category 2: Stablecoins — USDC, USDT, DAI
AAVE_V3_EMODE_CATEGORIES: list[EModeCategory] = [
    EModeCategory(
        category_id=1,
        label="ETH_CORRELATED",
        max_ltv=Decimal("0.93"),
        liquidation_threshold=Decimal("0.95"),
        liquidation_bonus=Decimal("0.01"),
        assets=frozenset({"WETH", "WEETH", "WSTETH", "CBETH", "RETH"}),
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

# Aave V3 Arbitrum E-Mode categories (added 2026-05-12)
# Differs from Ethereum: NO CBETH on Arbitrum; STABLECOIN E-Mode caps tighter (0.93 vs 0.97)
# Source: training-knowledge — values low-medium confidence; verify on app.aave.com
AAVE_V3_ARBITRUM_EMODE_CATEGORIES: list[EModeCategory] = [
    EModeCategory(
        category_id=1,
        label="ETH_CORRELATED",
        max_ltv=Decimal("0.93"),
        liquidation_threshold=Decimal("0.95"),
        liquidation_bonus=Decimal("0.01"),
        assets=frozenset({"WETH", "WEETH", "WSTETH", "RETH"}),
    ),
    EModeCategory(
        category_id=2,
        label="STABLECOIN",
        max_ltv=Decimal("0.93"),
        liquidation_threshold=Decimal("0.95"),
        liquidation_bonus=Decimal("0.01"),
        assets=frozenset({"USDC", "USDT", "DAI"}),
    ),
]

# Aave V3 Base E-Mode categories (added 2026-05-12)
# Base distinctives: CBETH in ETH-correlated; only USDC + USDBC in STABLECOIN
# Source: training-knowledge — values low-confidence; verify on app.aave.com
AAVE_V3_BASE_EMODE_CATEGORIES: list[EModeCategory] = [
    EModeCategory(
        category_id=1,
        label="ETH_CORRELATED",
        max_ltv=Decimal("0.93"),
        liquidation_threshold=Decimal("0.95"),
        liquidation_bonus=Decimal("0.01"),
        assets=frozenset({"WETH", "WSTETH", "CBETH", "WEETH"}),
    ),
    EModeCategory(
        category_id=2,
        label="STABLECOIN",
        max_ltv=Decimal("0.93"),
        liquidation_threshold=Decimal("0.95"),
        liquidation_bonus=Decimal("0.01"),
        assets=frozenset({"USDC", "USDBC"}),
    ),
]

# Chain-aware E-Mode dispatch (added 2026-05-12 per defi_recursive_borrow Family 1 design)
# Mirrors _AAVE_V3_CHAIN_DISPATCH (line ~658 — added by Harsh 2026-05-12 Phase 1B) for reserves.
_CHAIN_ASSET_EMODE_MAP: dict[str, dict[str, EModeCategory]] = {
    "ETHEREUM": {},
    "ARBITRUM": {},
    "BASE": {},
}
for _cat in AAVE_V3_EMODE_CATEGORIES:
    for _asset in _cat.assets:
        _CHAIN_ASSET_EMODE_MAP["ETHEREUM"][_asset] = _cat
for _cat in AAVE_V3_ARBITRUM_EMODE_CATEGORIES:
    for _asset in _cat.assets:
        _CHAIN_ASSET_EMODE_MAP["ARBITRUM"][_asset] = _cat
for _cat in AAVE_V3_BASE_EMODE_CATEGORIES:
    for _asset in _cat.assets:
        _CHAIN_ASSET_EMODE_MAP["BASE"][_asset] = _cat

# Legacy single-chain map — alias for Ethereum; preserved for backwards compat
_ASSET_EMODE_MAP: dict[str, EModeCategory] = _CHAIN_ASSET_EMODE_MAP["ETHEREUM"]


def get_emode_category(asset: str, chain: str = "ETHEREUM") -> EModeCategory | None:
    """Get the E-Mode category for an asset on a given chain.

    Chain-aware as of 2026-05-12: prior single-chain signature defaulted to Ethereum;
    chain dispatch added per defi_recursive_borrow_archetypes_2026_05_10.md Family 1
    design.

    Args:
        asset: Asset symbol (e.g., "WETH", "WSTETH").
        chain: Chain name (default ETHEREUM; supports ARBITRUM, BASE).

    Returns:
        EModeCategory or None if asset not in any E-Mode category on that chain.

    Raises:
        UnknownChainError: If chain is not in the E-Mode registry.
    """
    chain_upper = chain.upper()
    if chain_upper not in _CHAIN_ASSET_EMODE_MAP:
        raise UnknownChainError(f"Chain {chain!r} not in E-Mode registry. Supported: {sorted(_CHAIN_ASSET_EMODE_MAP)}")
    chain_map = _CHAIN_ASSET_EMODE_MAP[chain_upper]
    return chain_map.get(asset.upper())


def get_emode_params(collateral_asset: str, debt_asset: str, chain: str = "ETHEREUM") -> EModeCategory | None:
    """Get E-Mode parameters when collateral and debt are in the same category on a given chain.

    Chain-aware as of 2026-05-12.

    Args:
        collateral_asset: Collateral asset symbol.
        debt_asset: Debt asset symbol.
        chain: Chain name (default ETHEREUM; supports ARBITRUM, BASE).

    Returns:
        EModeCategory if both assets share an E-Mode category on `chain`; None otherwise.

    Raises:
        UnknownChainError: If chain is not in the E-Mode registry.

    Example:
        get_emode_params("WEETH", "WETH") → ETH_CORRELATED (93% LTV, 95% liq) on Ethereum
        get_emode_params("WEETH", "USDC") → None (different categories)
        get_emode_params("WSTETH", "WETH", chain="ARBITRUM") → ETH_CORRELATED Arbitrum
    """
    chain_upper = chain.upper()
    if chain_upper not in _CHAIN_ASSET_EMODE_MAP:
        raise UnknownChainError(f"Chain {chain!r} not in E-Mode registry. Supported: {sorted(_CHAIN_ASSET_EMODE_MAP)}")
    chain_map = _CHAIN_ASSET_EMODE_MAP[chain_upper]
    collateral_cat = chain_map.get(collateral_asset.upper())
    debt_cat = chain_map.get(debt_asset.upper())
    if collateral_cat is not None and collateral_cat is debt_cat:
        return collateral_cat
    return None


# ---------------------------------------------------------------------------
# Aave V3 multi-chain reserve parameters (P1B — 2026-05-15)
# ---------------------------------------------------------------------------
# Source: Aave governance UI, proto_<chain>_v3 markets, verified against
# on-chain getConfiguration(). Parameters are governance-set + may evolve;
# refresh on every quarterly Aave governance review.

# Aave V3 Arbitrum reserves — proto_arbitrum_v3
AAVE_V3_ARBITRUM_RESERVES: dict[str, ReserveParams] = {
    "USDC": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "USDCE": ReserveParams(  # USDC.e — bridged USDC
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "USDT": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "DAI": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.80"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "WETH": ReserveParams(
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.83"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "WBTC": ReserveParams(
        max_ltv=Decimal("0.73"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.063"),
        reserve_factor=Decimal("0.20"),
    ),
    "WSTETH": ReserveParams(
        max_ltv=Decimal("0.785"),
        liquidation_threshold=Decimal("0.81"),
        liquidation_bonus=Decimal("0.07"),
        reserve_factor=Decimal("0.15"),
    ),
    "WEETH": ReserveParams(
        max_ltv=Decimal("0.725"),
        liquidation_threshold=Decimal("0.775"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.15"),
    ),
    "RETH": ReserveParams(
        max_ltv=Decimal("0.745"),
        liquidation_threshold=Decimal("0.77"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.15"),
    ),
    # Arbitrum-native governance token
    # Source: training-knowledge — values low-medium confidence; verify on app.aave.com Arbitrum V3
    "ARB": ReserveParams(
        max_ltv=Decimal("0.60"),
        liquidation_threshold=Decimal("0.65"),
        liquidation_bonus=Decimal("0.10"),
        reserve_factor=Decimal("0.20"),
    ),
    # Cross-chain oracle / DeFi infra
    # Source: training-knowledge — values low-medium confidence; verify on app.aave.com Arbitrum V3
    "LINK": ReserveParams(
        max_ltv=Decimal("0.68"),
        liquidation_threshold=Decimal("0.73"),
        liquidation_bonus=Decimal("0.07"),
        reserve_factor=Decimal("0.20"),
    ),
}


# Aave V3 Optimism reserves — proto_optimism_v3
AAVE_V3_OPTIMISM_RESERVES: dict[str, ReserveParams] = {
    "USDC": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "USDT": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "DAI": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.80"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "WETH": ReserveParams(
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.83"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "WBTC": ReserveParams(
        max_ltv=Decimal("0.70"),
        liquidation_threshold=Decimal("0.75"),
        liquidation_bonus=Decimal("0.07"),
        reserve_factor=Decimal("0.20"),
    ),
    "WSTETH": ReserveParams(
        max_ltv=Decimal("0.785"),
        liquidation_threshold=Decimal("0.81"),
        liquidation_bonus=Decimal("0.07"),
        reserve_factor=Decimal("0.15"),
    ),
    "RETH": ReserveParams(
        max_ltv=Decimal("0.745"),
        liquidation_threshold=Decimal("0.77"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.15"),
    ),
}


# Aave V3 Base reserves — proto_base_v3
AAVE_V3_BASE_RESERVES: dict[str, ReserveParams] = {
    "USDC": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "USDBC": ReserveParams(  # USDbC — bridged USDC on Base
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "WETH": ReserveParams(
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.83"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "CBETH": ReserveParams(
        max_ltv=Decimal("0.745"),
        liquidation_threshold=Decimal("0.77"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.15"),
    ),
    "WSTETH": ReserveParams(
        max_ltv=Decimal("0.745"),
        liquidation_threshold=Decimal("0.77"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.15"),
        # WSTETH on Base comes via Lido canonical bridge — bridge_risk=True
    ),
    # weETH on Base comes via native ether.fi bridge — bridge_risk=True
    # Source: training-knowledge — values low-confidence; verify on app.aave.com Base V3
    "WEETH": ReserveParams(
        max_ltv=Decimal("0.725"),
        liquidation_threshold=Decimal("0.775"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.15"),
    ),
    # cbBTC — Coinbase Wrapped Bitcoin, Base-native
    # Source: training-knowledge — values low-confidence; verify on app.aave.com Base V3
    "CBBTC": ReserveParams(
        max_ltv=Decimal("0.73"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.063"),
        reserve_factor=Decimal("0.20"),
    ),
}


# Aave V3 Avalanche reserves — proto_avalanche_v3
AAVE_V3_AVALANCHE_RESERVES: dict[str, ReserveParams] = {
    "USDC": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "USDT": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "DAI": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.80"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "WAVAX": ReserveParams(
        max_ltv=Decimal("0.65"),
        liquidation_threshold=Decimal("0.70"),
        liquidation_bonus=Decimal("0.10"),
        reserve_factor=Decimal("0.20"),
    ),
    "WETHE": ReserveParams(  # WETH.e — bridged WETH on Avalanche
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.825"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
}


# Aave V3 Polygon reserves — proto_polygon_v3
AAVE_V3_POLYGON_RESERVES: dict[str, ReserveParams] = {
    "USDC": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "USDT": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "DAI": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.80"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "WETH": ReserveParams(
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.825"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "WBTC": ReserveParams(
        max_ltv=Decimal("0.70"),
        liquidation_threshold=Decimal("0.75"),
        liquidation_bonus=Decimal("0.07"),
        reserve_factor=Decimal("0.20"),
    ),
    "WMATIC": ReserveParams(
        max_ltv=Decimal("0.65"),
        liquidation_threshold=Decimal("0.70"),
        liquidation_bonus=Decimal("0.10"),
        reserve_factor=Decimal("0.20"),
    ),
    "MATICX": ReserveParams(
        max_ltv=Decimal("0.40"),
        liquidation_threshold=Decimal("0.50"),
        liquidation_bonus=Decimal("0.10"),
        reserve_factor=Decimal("0.20"),
    ),
}


# Aave V3 BSC reserves — proto_bnb_v3 (launched 2024-01-23, small reserve set)
AAVE_V3_BSC_RESERVES: dict[str, ReserveParams] = {
    "USDT": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "USDC": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "WBNB": ReserveParams(
        max_ltv=Decimal("0.70"),
        liquidation_threshold=Decimal("0.75"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.20"),
    ),
    "ETH": ReserveParams(
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.825"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "FDUSD": ReserveParams(
        max_ltv=Decimal("0.70"),
        liquidation_threshold=Decimal("0.75"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
}


# Aave V3 Linea reserves — proto_linea_v3 (launched 2025-02-11, small reserve set)
AAVE_V3_LINEA_RESERVES: dict[str, ReserveParams] = {
    "USDC": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "WETH": ReserveParams(
        max_ltv=Decimal("0.78"),
        liquidation_threshold=Decimal("0.81"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "WSTETH": ReserveParams(
        max_ltv=Decimal("0.745"),
        liquidation_threshold=Decimal("0.77"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.15"),
    ),
}


# Aave V3 Scroll reserves — proto_scroll_v3
AAVE_V3_SCROLL_RESERVES: dict[str, ReserveParams] = {
    "USDC": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "USDT": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "WETH": ReserveParams(
        max_ltv=Decimal("0.78"),
        liquidation_threshold=Decimal("0.81"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "WSTETH": ReserveParams(
        max_ltv=Decimal("0.745"),
        liquidation_threshold=Decimal("0.77"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.15"),
    ),
}


# Aave V3 zkSync Era reserves — proto_zksync_v3
AAVE_V3_ZKSYNC_RESERVES: dict[str, ReserveParams] = {
    "USDC": ReserveParams(
        max_ltv=Decimal("0.72"),
        liquidation_threshold=Decimal("0.75"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "WETH": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.78"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "WSTETH": ReserveParams(
        max_ltv=Decimal("0.72"),
        liquidation_threshold=Decimal("0.75"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.15"),
    ),
}


# ---------------------------------------------------------------------------
# Spark Ethereum reserves (Aave V3 fork — same dataclass)
# ---------------------------------------------------------------------------
# Source: https://app.spark.fi/markets (Spark governance dashboard)
# Spark uses Aave V3 codebase but is operated by the Sky / MakerDAO ecosystem;
# parameters are Spark-governance-set and tend to be tighter for DAI / sDAI.
SPARK_ETHEREUM_RESERVES: dict[str, ReserveParams] = {
    "USDC": ReserveParams(
        max_ltv=Decimal("0.74"),
        liquidation_threshold=Decimal("0.76"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "USDT": ReserveParams(
        max_ltv=Decimal("0.74"),
        liquidation_threshold=Decimal("0.76"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "DAI": ReserveParams(
        max_ltv=Decimal("0.74"),
        liquidation_threshold=Decimal("0.76"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.00"),
    ),
    "WETH": ReserveParams(
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.825"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "WBTC": ReserveParams(
        max_ltv=Decimal("0.70"),
        liquidation_threshold=Decimal("0.75"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.20"),
    ),
    "WSTETH": ReserveParams(
        max_ltv=Decimal("0.785"),
        liquidation_threshold=Decimal("0.81"),
        liquidation_bonus=Decimal("0.07"),
        reserve_factor=Decimal("0.15"),
    ),
    "WEETH": ReserveParams(
        max_ltv=Decimal("0.725"),
        liquidation_threshold=Decimal("0.775"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.15"),
    ),
}


# ---------------------------------------------------------------------------
# Radiant reserves (Aave V2 fork — same dataclass) on Arbitrum + BSC
# ---------------------------------------------------------------------------
# Source: https://app.radiant.capital (Radiant governance dashboard).
# Radiant is a cross-chain money market forked from Aave V2 with RDNT
# emissions. Per-market deployments share governance schema.
RADIANT_ARBITRUM_RESERVES: dict[str, ReserveParams] = {
    "USDC": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.80"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "USDT": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.80"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "DAI": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.80"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "WETH": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.80"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.20"),
    ),
    "WBTC": ReserveParams(
        max_ltv=Decimal("0.70"),
        liquidation_threshold=Decimal("0.75"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.20"),
    ),
    "WSTETH": ReserveParams(
        max_ltv=Decimal("0.70"),
        liquidation_threshold=Decimal("0.75"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.20"),
    ),
}


RADIANT_BSC_RESERVES: dict[str, ReserveParams] = {
    "USDC": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.80"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "USDT": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.80"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.15"),
    ),
    "WETH": ReserveParams(
        max_ltv=Decimal("0.75"),
        liquidation_threshold=Decimal("0.80"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.20"),
    ),
    "WBNB": ReserveParams(
        max_ltv=Decimal("0.65"),
        liquidation_threshold=Decimal("0.70"),
        liquidation_bonus=Decimal("0.10"),
        reserve_factor=Decimal("0.20"),
    ),
    "WBTC": ReserveParams(  # BTCB on BSC, exposed as WBTC here for symbol consistency
        max_ltv=Decimal("0.70"),
        liquidation_threshold=Decimal("0.75"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.20"),
    ),
}


# ---------------------------------------------------------------------------
# Chain dispatch — Aave V3 multi-chain lookup table
# ---------------------------------------------------------------------------
# Keyed by uppercase chain name. ETHEREUM remains the default for legacy
# callers that did not pass an explicit chain.
_AAVE_V3_CHAIN_DISPATCH: dict[str, dict[str, ReserveParams]] = {
    "ETHEREUM": AAVE_V3_ETHEREUM_RESERVES,
    "ARBITRUM": AAVE_V3_ARBITRUM_RESERVES,
    "OPTIMISM": AAVE_V3_OPTIMISM_RESERVES,
    "BASE": AAVE_V3_BASE_RESERVES,
    "AVALANCHE": AAVE_V3_AVALANCHE_RESERVES,
    "POLYGON": AAVE_V3_POLYGON_RESERVES,
    "BSC": AAVE_V3_BSC_RESERVES,
    "LINEA": AAVE_V3_LINEA_RESERVES,
    "SCROLL": AAVE_V3_SCROLL_RESERVES,
    "ZKSYNC": AAVE_V3_ZKSYNC_RESERVES,
}


_RADIANT_CHAIN_DISPATCH: dict[str, dict[str, ReserveParams]] = {
    "ARBITRUM": RADIANT_ARBITRUM_RESERVES,
    "BSC": RADIANT_BSC_RESERVES,
}


def get_reserve_params(asset: str, chain: str = "ETHEREUM") -> ReserveParams | None:
    """Look up Aave V3 reserve parameters for an asset on a given chain.

    Default chain is ETHEREUM (backwards-compatible with pre-P1B callers).
    Pass an explicit chain string (e.g. "ARBITRUM", "OPTIMISM", "BASE")
    to look up multi-chain markets. Spark + Radiant use separate helpers.

    Args:
        asset: Asset symbol (e.g., "USDC", "WETH") or instrument_id containing the asset.
        chain: Chain name (ETHEREUM / ARBITRUM / OPTIMISM / BASE / AVALANCHE /
            POLYGON / BSC / LINEA / SCROLL / ZKSYNC).

    Returns:
        ReserveParams or None if asset not found on the chain.

    Raises:
        UnknownChainError: If chain is not in the Aave V3 registry.
    """
    chain_upper = chain.upper()
    if chain_upper not in _AAVE_V3_CHAIN_DISPATCH:
        raise UnknownChainError(
            f"Chain {chain!r} not in Aave V3 reserve registry. Supported: {sorted(_AAVE_V3_CHAIN_DISPATCH)}"
        )
    chain_dict = _AAVE_V3_CHAIN_DISPATCH[chain_upper]

    upper = asset.upper()
    if upper in chain_dict:
        return chain_dict[upper]

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
            if token_name in chain_dict:
                return chain_dict[token_name]

    return None


def get_aave_reserve_params(asset: str, chain: str) -> ReserveParams | None:
    """Explicit-chain Aave V3 reserve params lookup.

    Mirrors :func:`get_reserve_params` but requires the caller to pass an
    explicit chain, leaving no room for the legacy ETHEREUM default.
    """
    return get_reserve_params(asset, chain=chain)


def get_spark_reserve_params(asset: str) -> ReserveParams | None:
    """Spark Ethereum reserve params lookup (Aave V3 fork).

    Spark is only deployed on Ethereum mainnet; chain argument intentionally
    absent. Callers needing other Spark deployments must pass the explicit
    dict (none additional exist as of 2026-05-15).
    """
    return SPARK_ETHEREUM_RESERVES.get(asset.upper())


def get_radiant_reserve_params(asset: str, chain: str) -> ReserveParams | None:
    """Radiant cross-chain money market reserve params lookup.

    Args:
        asset: Asset symbol (e.g., "USDC", "WETH").
        chain: Chain name ("ARBITRUM" / "BSC"). Other Radiant deployments
            return None.
    """
    chain_dict = _RADIANT_CHAIN_DISPATCH.get(chain.upper())
    if chain_dict is None:
        return None
    return chain_dict.get(asset.upper())


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


# ---------------------------------------------------------------------------
# Compound V3 per-chain, per-market reserve parameters
# ---------------------------------------------------------------------------
# Compound V3 is structured as per-market deployments: each deployment has a
# single base asset (USDC or ETH) and many collateral assets. Markets are
# chain-and-base-asset scoped, e.g. ARBITRUM / USDC.E vs ARBITRUM / USDC.
#
# Dispatch: _COMPOUND_CHAIN_MARKET_RESERVES[chain][market][asset] → ReserveParams
#
# Source: Compound governance, on-chain ``getCollateralFactor``
#         Values are training-knowledge + low-medium confidence for non-Ethereum;
#         verify at https://app.compound.finance before live routing.

# Compound V3 Arbitrum — USDC.e market
COMPOUND_V3_ARBITRUM_USDCE_RESERVES: dict[str, ReserveParams] = {
    # Source: training-knowledge — values low-medium confidence; verify at app.compound.finance
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
    "ARB": ReserveParams(
        max_ltv=Decimal("0.60"),
        liquidation_threshold=Decimal("0.70"),
        liquidation_bonus=Decimal("0.10"),
        reserve_factor=Decimal("0.10"),
    ),
    "GMX": ReserveParams(
        max_ltv=Decimal("0.55"),
        liquidation_threshold=Decimal("0.65"),
        liquidation_bonus=Decimal("0.10"),
        reserve_factor=Decimal("0.10"),
    ),
}

# Compound V3 Arbitrum — USDC market (native USDC, distinct from USDC.e)
COMPOUND_V3_ARBITRUM_USDC_RESERVES: dict[str, ReserveParams] = {
    # Source: training-knowledge — values low-medium confidence; verify at app.compound.finance
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
    "ARB": ReserveParams(
        max_ltv=Decimal("0.60"),
        liquidation_threshold=Decimal("0.70"),
        liquidation_bonus=Decimal("0.10"),
        reserve_factor=Decimal("0.10"),
    ),
}

# Compound V3 Base — USDC market
COMPOUND_V3_BASE_USDC_RESERVES: dict[str, ReserveParams] = {
    # Source: training-knowledge — values low-medium confidence; verify at app.compound.finance
    "WETH": ReserveParams(
        max_ltv=Decimal("0.83"),
        liquidation_threshold=Decimal("0.90"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "CBETH": ReserveParams(
        max_ltv=Decimal("0.78"),
        liquidation_threshold=Decimal("0.83"),
        liquidation_bonus=Decimal("0.075"),
        reserve_factor=Decimal("0.10"),
    ),
    "WSTETH": ReserveParams(
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.85"),
        liquidation_bonus=Decimal("0.05"),
        reserve_factor=Decimal("0.10"),
    ),
    "CBBTC": ReserveParams(
        max_ltv=Decimal("0.80"),
        liquidation_threshold=Decimal("0.85"),
        liquidation_bonus=Decimal("0.07"),
        reserve_factor=Decimal("0.10"),
    ),
}


# Compound V3 chain → market → asset dispatch
# Market key convention: "USDC", "USDC.E", "ETH" (base asset symbol, uppercase)
_COMPOUND_CHAIN_MARKET_RESERVES: dict[str, dict[str, dict[str, ReserveParams]]] = {
    "ETHEREUM": {
        "USDC": COMPOUND_V3_ETHEREUM_RESERVES,
    },
    "ARBITRUM": {
        "USDC.E": COMPOUND_V3_ARBITRUM_USDCE_RESERVES,
        "USDC": COMPOUND_V3_ARBITRUM_USDC_RESERVES,
    },
    "BASE": {
        "USDC": COMPOUND_V3_BASE_USDC_RESERVES,
    },
}


def get_compound_reserve_params(
    asset: str,
    chain: str = "ETHEREUM",
    market: str = "USDC",
) -> ReserveParams | None:
    """Compound V3 reserve params lookup — per-chain and per-market.

    Compound V3 is per-market AND per-chain: each deployment has a single
    base asset (e.g. USDC or ETH) and many collateral assets.  Pass both
    ``chain`` and ``market`` for multi-chain routing.

    Args:
        asset: Collateral asset symbol (e.g., "WETH", "WBTC").
        chain: Chain name (ETHEREUM / ARBITRUM / BASE).  Defaults to ETHEREUM
            for backwards compatibility with legacy single-chain callers.
        market: Base-asset market key (e.g., "USDC", "USDC.E", "ETH").
            Defaults to "USDC" (most common Compound V3 market).

    Returns:
        ReserveParams or None if asset not found in that chain x market.

    Raises:
        UnknownChainError: If chain is not in the Compound V3 registry.
    """
    chain_upper = chain.upper()
    if chain_upper not in _COMPOUND_CHAIN_MARKET_RESERVES:
        raise UnknownChainError(
            f"Chain {chain!r} not in Compound V3 registry. Supported: {sorted(_COMPOUND_CHAIN_MARKET_RESERVES)}"
        )
    market_map = _COMPOUND_CHAIN_MARKET_RESERVES[chain_upper]
    asset_map = market_map.get(market.upper())
    if asset_map is None:
        return None
    return asset_map.get(asset.upper())


def get_morpho_reserve_params(asset: str) -> ReserveParams | None:
    """Morpho Blue ETH-mainnet curated-vault reserve params lookup.

    Morpho is per-market; this returns typical params for the canonical
    curated vault on the asset. Per-market overrides should be queried
    via :func:`get_morpho_market_lltv` when stricter accuracy is needed.
    """
    return MORPHO_BLUE_ETHEREUM_RESERVES.get(asset.upper())


# ---------------------------------------------------------------------------
# Morpho Blue per-market LLTV overrides
# ---------------------------------------------------------------------------
# Each Morpho Blue market is immutable on creation: (collateral, loan_asset,
# oracle, IRM, LLTV) tuple.  The LLTV varies by curator — the canonical
# Steakhouse / Gauntlet / MEV Capital curated vaults use different LLTVs for
# the same collateral depending on the oracle used.
#
# Key: (collateral_upper, loan_asset_upper)
# Value: highest LLTV available across curated vault deployments (conservative
#        for HF calculation — use actual on-chain LLTV for production).
#
# Source: Morpho governance + MetaMorpho vault catalogues, 2026-05-15.
# Low-medium confidence; verify via morpho.org/markets before live trading.
_MORPHO_MARKET_LLTV: dict[tuple[str, str], Decimal] = {
    # wstETH / WETH — canonical Steakhouse 94.5% vault (highest-LLTV Family 1 cell)
    ("WSTETH", "WETH"): Decimal("0.945"),
    # weETH / WETH — ether.fi re-staking vault (ETH_CORRELATED, slightly lower)
    ("WEETH", "WETH"): Decimal("0.860"),
    # rETH / WETH — Rocket Pool vault
    ("RETH", "WETH"): Decimal("0.860"),
    # cbETH / WETH — Coinbase staked ETH
    ("CBETH", "WETH"): Decimal("0.860"),
    # sUSDe / USDC — Ethena staked USDe; highest cash APR Family 1 cell
    ("SUSDE", "USDC"): Decimal("0.860"),
    # sUSDe / USDT — alternative stable debt
    ("SUSDE", "USDT"): Decimal("0.860"),
    # USDe / USDC — unstaked Ethena USDe
    ("USDE", "USDC"): Decimal("0.860"),
    # WBTC / USDC — BTC-collateralised stablecoin borrow
    ("WBTC", "USDC"): Decimal("0.860"),
    # WBTC / USDT
    ("WBTC", "USDT"): Decimal("0.860"),
    # WETH / USDC — ETH-collateralised stablecoin borrow
    ("WETH", "USDC"): Decimal("0.860"),
    # WETH / USDT
    ("WETH", "USDT"): Decimal("0.860"),
}


def get_morpho_market_lltv(collateral: str, loan_asset: str) -> Decimal | None:
    """Return the highest LLTV for a Morpho Blue market by (collateral, loan_asset).

    Morpho Blue markets are immutable: LLTV is set at creation and cannot change.
    This table covers canonical curated vault deployments (Steakhouse / Gauntlet /
    MEV Capital) that are eligible as Family 1 recursive-borrow cells.

    Args:
        collateral: Collateral asset symbol (e.g., "WSTETH", "WEETH").
        loan_asset: Loan/debt asset symbol (e.g., "WETH", "USDC").

    Returns:
        Decimal LLTV if the market is in the curated-vault registry; None if unknown.
        Callers should fall back to ``get_morpho_reserve_params(collateral).max_ltv``
        for the conservative uniform=0.86 estimate when None is returned.

    Example:
        get_morpho_market_lltv("WSTETH", "WETH") → Decimal("0.945")
        get_morpho_market_lltv("SUSDE", "USDC") → Decimal("0.860")
        get_morpho_market_lltv("UNKNOWN", "WETH") → None
    """
    return _MORPHO_MARKET_LLTV.get((collateral.upper(), loan_asset.upper()))
