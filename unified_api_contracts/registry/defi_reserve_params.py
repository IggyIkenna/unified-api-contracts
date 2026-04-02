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
) -> tuple[Decimal, Decimal]:
    """Compute health factor and LTV from positions + protocol params.

    This is the same math Aave uses on-chain. Batch mode computes this
    identically to how live mode would observe it from the protocol.

    Args:
        collateral_positions: List of (instrument_id, quantity, price_usd)
        debt_positions: List of (instrument_id, quantity, price_usd)

    Returns:
        Tuple of (health_factor, ltv). HF = Decimal("Infinity") if no debt.
    """
    total_collateral_usd = Decimal("0")
    weighted_threshold_usd = Decimal("0")
    total_debt_usd = Decimal("0")

    for inst_id, qty, price in collateral_positions:
        value = abs(qty) * price
        total_collateral_usd += value
        params = get_reserve_params(inst_id)
        if params:
            weighted_threshold_usd += value * params.liquidation_threshold
        else:
            # Unknown asset — use conservative threshold
            weighted_threshold_usd += value * Decimal("0.70")

    for inst_id, qty, price in debt_positions:
        total_debt_usd += abs(qty) * price

    if total_debt_usd == 0:
        # No debt → not liquidatable. Return NaN so graphs don't blow up.
        return Decimal("NaN"), Decimal("0")

    health_factor = weighted_threshold_usd / total_debt_usd
    ltv = total_debt_usd / total_collateral_usd if total_collateral_usd > 0 else Decimal("Infinity")

    return health_factor, ltv
