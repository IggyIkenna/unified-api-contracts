"""Max underlying move assumptions — SSOT for dynamic leverage caps.

Two move types per base currency:
- outright: max expected move vs USD in a given timeframe (e.g., ETH/USD -50%)
  → used for CeFi perp leverage and DeFi outright positions
- spread: max expected spread move between correlated pairs (e.g., eETH/ETH depeg 3%)
  → used for DeFi lending with same-category collateral/debt (E-Mode)

Leverage is reverse-engineered from these moves:
  max_leverage_outright = 1 / max_outright_move  (survive full drawdown)
  max_leverage_spread = liq_threshold / (1 - liq_threshold + max_spread_move)

These are conservative assumptions. Override per-strategy via config.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MaxMoveAssumption:
    """Max expected move for a base currency."""

    base_currency: str
    max_outright_move: Decimal  # vs USD, e.g. 0.50 = 50% crash
    max_spread_move: Decimal  # vs correlated pair, e.g. 0.03 = 3% depeg
    timeframe_hours: int  # assumption window (e.g. 1h, 24h)
    notes: str


# Default move assumptions — conservative for production use.
# Outright = worst-case crash scenario for margin sizing on perps/outright positions.
# Spread = worst-case depeg/basis divergence for same-category DeFi positions.
MAX_UNDERLYING_MOVES: dict[str, MaxMoveAssumption] = {
    "ETH": MaxMoveAssumption(
        base_currency="ETH",
        max_outright_move=Decimal("0.30"),  # 30% crash in 1h (Black Thursday was ~43% in 24h)
        max_spread_move=Decimal("0.03"),  # 3% weETH/ETH or stETH/ETH depeg
        timeframe_hours=1,
        notes="ETH outright: covers flash crash. Spread: covers stETH depeg (Jun 2022 was ~5%).",
    ),
    "BTC": MaxMoveAssumption(
        base_currency="BTC",
        max_outright_move=Decimal("0.25"),  # 25% crash in 1h
        max_spread_move=Decimal("0.02"),  # 2% WBTC/BTC depeg
        timeframe_hours=1,
        notes="BTC less volatile than ETH at extreme. WBTC depeg: Nov 2022 was ~1.5%.",
    ),
    "SOL": MaxMoveAssumption(
        base_currency="SOL",
        max_outright_move=Decimal("0.40"),  # 40% crash in 1h (SOL more volatile)
        max_spread_move=Decimal("0.05"),  # 5% mSOL/SOL depeg
        timeframe_hours=1,
        notes="SOL higher vol. mSOL depeg: FTX collapse saw >3%.",
    ),
    "USDC": MaxMoveAssumption(
        base_currency="USDC",
        max_outright_move=Decimal("0.05"),  # 5% depeg vs USD (SVB was ~12%)
        max_spread_move=Decimal("0.02"),  # 2% USDC/USDT spread
        timeframe_hours=1,
        notes="Stablecoins: SVB-era USDC depeg was worst case.",
    ),
    "USDT": MaxMoveAssumption(
        base_currency="USDT",
        max_outright_move=Decimal("0.03"),  # 3% depeg vs USD
        max_spread_move=Decimal("0.02"),  # 2% USDT/USDC spread
        timeframe_hours=1,
        notes="USDT: smaller depegs historically than USDC.",
    ),
}


def get_max_move(base_currency: str) -> MaxMoveAssumption | None:
    """Get max move assumption for a base currency."""
    return MAX_UNDERLYING_MOVES.get(base_currency.upper())


def compute_max_leverage_from_outright_move(
    base_currency: str,
    maintenance_margin_rate: Decimal = Decimal("0.05"),
) -> Decimal:
    """Compute max leverage for outright/perp positions from max move assumption.

    Formula: max_leverage = (1 - maintenance_margin_rate) / max_outright_move
    This ensures you survive the worst-case move without liquidation.

    For CeFi perps: maintenance_margin_rate is the exchange's maintenance margin.
    For DeFi outright: use (1 - LTV) as the margin equivalent.

    Args:
        base_currency: "ETH", "BTC", "SOL", etc.
        maintenance_margin_rate: Exchange maintenance margin (default 5% for most perps).

    Returns:
        Max safe leverage. Falls back to Decimal("1") if no move data.
    """
    move = MAX_UNDERLYING_MOVES.get(base_currency.upper())
    if move is None or move.max_outright_move <= 0:
        return Decimal("1")
    return (Decimal("1") - maintenance_margin_rate) / move.max_outright_move


def compute_max_leverage_from_spread_move(
    base_currency: str,
    liquidation_threshold: Decimal = Decimal("0.95"),
) -> Decimal:
    """Compute max leverage for same-category DeFi positions from spread move.

    Formula: max_leverage = liq_threshold / (1 - liq_threshold + max_spread_move)
    This is the generalized depeg-safe leverage formula.

    Used when collateral and debt are correlated (E-Mode): weETH/WETH, wstETH/WETH,
    mSOL/SOL, etc. The spread move is much smaller than the outright move.

    Args:
        base_currency: "ETH", "BTC", "SOL" — determines spread assumption.
        liquidation_threshold: Protocol liq threshold (E-Mode: 0.95, standard: 0.775).

    Returns:
        Max safe leverage for spread positions.
    """
    move = MAX_UNDERLYING_MOVES.get(base_currency.upper())
    if move is None or move.max_spread_move <= 0:
        return Decimal("1")
    denom = Decimal("1") - liquidation_threshold + move.max_spread_move
    if denom <= 0:
        return Decimal("1")
    return liquidation_threshold / denom
