"""Aave V3 Interest Rate Model — pure math for rate impact simulation.

Implements the Aave V3 variable interest rate model exactly as specified in the
Aave V3 protocol docs. Given pool parameters (slopes, optimal utilization,
reserve factor) and a proposed trade (supply or borrow), computes the resulting
utilization shift and new supply/borrow APYs.

All computations use Decimal for precision — no floats.

Reference: https://docs.aave.com/risk/liquidity-risk/borrow-interest-rate
"""

from decimal import Decimal
from typing import TypedDict

from pydantic import BaseModel


class AaveV3RateModelDefaults(TypedDict):
    """Per-asset Aave V3 interest rate model parameters.

    Sourced from Aave V3 governance config on Ethereum mainnet (snapshot —
    governance can change these via vote, captured at the canonical
    ``ReserveInterestRateStrategy`` contract per reserve). For
    historically-correct values use the per-tick fields captured by the
    MTDS lending_indices_handler from The Graph subgraph (which writes
    ``optimal_utilization``, ``slope1``, ``slope2``, ``base_rate``,
    ``reserve_factor`` columns alongside the rate indices).
    """

    optimal_utilization: Decimal
    slope1: Decimal
    slope2: Decimal
    base_rate: Decimal
    reserve_factor: Decimal


# Per-asset Aave V3 rate model defaults (Ethereum mainnet, governance current
# as of 2026-05-05). Single source of truth — features-onchain rate-impact
# simulator and MTDS instruments-discovery fallbacks both import from here.
#
# To historically refine: use captured per-tick values from the MTDS
# lending_indices_handler (post the schema-drift fix that adds
# ``optimal_utilization`` / ``slope1`` / ``slope2`` / ``base_rate`` /
# ``reserve_factor`` to the parquet). When a captured value exists for a
# (timestamp, reserve) pair, prefer it over this default snapshot.
AAVE_V3_RATE_MODEL_DEFAULTS_BY_ASSET: dict[str, AaveV3RateModelDefaults] = {
    "USDC": {
        "optimal_utilization": Decimal("0.90"),
        "slope1": Decimal("0.04"),
        "slope2": Decimal("0.60"),
        "base_rate": Decimal("0.00"),
        "reserve_factor": Decimal("0.10"),
    },
    "USDT": {
        "optimal_utilization": Decimal("0.90"),
        "slope1": Decimal("0.04"),
        "slope2": Decimal("0.60"),
        "base_rate": Decimal("0.00"),
        "reserve_factor": Decimal("0.10"),
    },
    "DAI": {
        "optimal_utilization": Decimal("0.90"),
        "slope1": Decimal("0.04"),
        "slope2": Decimal("0.75"),
        "base_rate": Decimal("0.00"),
        "reserve_factor": Decimal("0.10"),
    },
    "ETH": {
        "optimal_utilization": Decimal("0.80"),
        "slope1": Decimal("0.038"),
        "slope2": Decimal("0.80"),
        "base_rate": Decimal("0.00"),
        "reserve_factor": Decimal("0.15"),
    },
    "WETH": {
        "optimal_utilization": Decimal("0.80"),
        "slope1": Decimal("0.038"),
        "slope2": Decimal("0.80"),
        "base_rate": Decimal("0.00"),
        "reserve_factor": Decimal("0.15"),
    },
    "wstETH": {
        "optimal_utilization": Decimal("0.80"),
        "slope1": Decimal("0.038"),
        "slope2": Decimal("0.80"),
        "base_rate": Decimal("0.00"),
        "reserve_factor": Decimal("0.10"),
    },
    "weETH": {
        "optimal_utilization": Decimal("0.80"),
        "slope1": Decimal("0.038"),
        "slope2": Decimal("0.80"),
        "base_rate": Decimal("0.00"),
        "reserve_factor": Decimal("0.10"),
    },
}

# Default fallback for any asset not in the table above.
AAVE_V3_RATE_MODEL_DEFAULT_FALLBACK: AaveV3RateModelDefaults = {
    "optimal_utilization": Decimal("0.80"),
    "slope1": Decimal("0.04"),
    "slope2": Decimal("0.75"),
    "base_rate": Decimal("0.00"),
    "reserve_factor": Decimal("0.10"),
}


def get_aave_v3_rate_model_defaults(symbol: str) -> AaveV3RateModelDefaults:
    """Return per-asset Aave V3 rate model defaults, falling back to a
    conservative shape when the symbol isn't in the curated table.

    Symbol normalisation: upper-cased, chain suffix stripped (``USDC-USDT``
    splits at the dash and uses the first token). Matches the legacy
    behaviour of features-onchain ``aave_rate_impact_calculator`` so this
    function is a drop-in replacement.
    """
    normalised = symbol.upper().split("-")[0].strip()
    return AAVE_V3_RATE_MODEL_DEFAULTS_BY_ASSET.get(normalised, AAVE_V3_RATE_MODEL_DEFAULT_FALLBACK)


class AavePoolParams(BaseModel):
    """Aave V3 reserve parameters for interest rate computation.

    These values come from The Graph query on Aave V3 reserves:
    ``optimalUtilisationRate``, ``variableRateSlope1``, ``variableRateSlope2``,
    ``baseVariableBorrowRate``, ``reserveFactor``.

    Pool liquidity (total_supply_usd, total_borrow_usd) comes from DefiLlama
    or The Graph ``totalLiquidity`` / ``totalCurrentVariableDebt``.
    """

    pool_symbol: str
    optimal_utilization: Decimal  # e.g. 0.90 for 90%
    slope1: Decimal  # variable rate slope below optimal (e.g. 0.04 = 4%)
    slope2: Decimal  # variable rate slope above optimal (e.g. 0.60 = 60%)
    base_rate: Decimal  # base variable borrow rate (e.g. 0.00 = 0%)
    reserve_factor: Decimal  # protocol fee on interest (e.g. 0.10 = 10%)
    total_supply_usd: Decimal  # total supplied liquidity in USD
    total_borrow_usd: Decimal  # total borrowed in USD


class RateImpactResult(BaseModel):
    """Result of simulating a lending/borrowing trade's impact on pool rates."""

    pool_symbol: str
    trade_amount_usd: Decimal
    trade_type: str  # "supply" or "borrow"

    utilization_before: Decimal
    utilization_after: Decimal
    utilization_delta_bps: int  # basis points change in utilization

    pre_borrow_apy: Decimal
    post_borrow_apy: Decimal
    borrow_rate_change_bps: int

    pre_supply_apy: Decimal
    post_supply_apy: Decimal
    supply_rate_change_bps: int


def compute_utilization(total_supply: Decimal, total_borrow: Decimal) -> Decimal:
    """Compute pool utilization ratio U = total_borrow / total_supply.

    Returns 0 if total_supply is zero (empty pool).
    """
    if total_supply <= 0:
        return Decimal("0")
    return total_borrow / total_supply


def compute_borrow_rate(
    utilization: Decimal,
    slope1: Decimal,
    slope2: Decimal,
    optimal_utilization: Decimal,
    base_rate: Decimal,
) -> Decimal:
    """Compute the variable borrow rate using Aave V3 interest rate model.

    Formula:
        if U <= U_optimal:
            R_borrow = base_rate + (U / U_optimal) * slope1
        else:
            R_borrow = base_rate + slope1 + ((U - U_optimal) / (1 - U_optimal)) * slope2
    """
    if optimal_utilization <= 0:
        return base_rate

    if utilization <= optimal_utilization:
        return base_rate + (utilization / optimal_utilization) * slope1

    excess = utilization - optimal_utilization
    denominator = Decimal("1") - optimal_utilization
    if denominator <= 0:
        return base_rate + slope1 + slope2
    return base_rate + slope1 + (excess / denominator) * slope2


def compute_supply_rate(
    utilization: Decimal,
    borrow_rate: Decimal,
    reserve_factor: Decimal,
) -> Decimal:
    """Compute the supply rate from the borrow rate.

    Formula: R_supply = R_borrow * U * (1 - reserve_factor)

    Suppliers earn the borrow rate weighted by utilization, minus the protocol cut.
    """
    return borrow_rate * utilization * (Decimal("1") - reserve_factor)


def simulate_rate_impact(
    pool_params: AavePoolParams,
    our_amount_usd: Decimal,
    trade_type: str,
) -> RateImpactResult:
    """Simulate how a supply or borrow trade changes pool rates.

    Args:
        pool_params: Current pool state and rate model parameters.
        our_amount_usd: Size of our trade in USD.
        trade_type: "supply" or "borrow".

    For supply: total_supply increases, utilization decreases, rates decrease.
    For borrow: total_borrow increases, utilization increases, rates increase.
    """
    total_supply_before = pool_params.total_supply_usd
    total_borrow_before = pool_params.total_borrow_usd

    # Pre-trade rates
    u_before = compute_utilization(total_supply_before, total_borrow_before)
    r_borrow_before = compute_borrow_rate(
        u_before,
        pool_params.slope1,
        pool_params.slope2,
        pool_params.optimal_utilization,
        pool_params.base_rate,
    )
    r_supply_before = compute_supply_rate(u_before, r_borrow_before, pool_params.reserve_factor)

    # Post-trade pool state
    if trade_type == "supply":
        total_supply_after = total_supply_before + our_amount_usd
        total_borrow_after = total_borrow_before
    elif trade_type == "borrow":
        total_supply_after = total_supply_before
        total_borrow_after = total_borrow_before + our_amount_usd
    elif trade_type == "withdraw":
        total_supply_after = max(total_supply_before - our_amount_usd, Decimal("0"))
        total_borrow_after = total_borrow_before
    elif trade_type == "repay":
        total_supply_after = total_supply_before
        total_borrow_after = max(total_borrow_before - our_amount_usd, Decimal("0"))
    else:
        total_supply_after = total_supply_before
        total_borrow_after = total_borrow_before

    # Post-trade rates
    u_after = compute_utilization(total_supply_after, total_borrow_after)
    r_borrow_after = compute_borrow_rate(
        u_after,
        pool_params.slope1,
        pool_params.slope2,
        pool_params.optimal_utilization,
        pool_params.base_rate,
    )
    r_supply_after = compute_supply_rate(u_after, r_borrow_after, pool_params.reserve_factor)

    # Deltas in basis points
    _bps = Decimal("10000")
    u_delta_bps = int((u_after - u_before) * _bps)
    borrow_delta_bps = int((r_borrow_after - r_borrow_before) * _bps)
    supply_delta_bps = int((r_supply_after - r_supply_before) * _bps)

    return RateImpactResult(
        pool_symbol=pool_params.pool_symbol,
        trade_amount_usd=our_amount_usd,
        trade_type=trade_type,
        utilization_before=u_before,
        utilization_after=u_after,
        utilization_delta_bps=u_delta_bps,
        pre_borrow_apy=r_borrow_before,
        post_borrow_apy=r_borrow_after,
        borrow_rate_change_bps=borrow_delta_bps,
        pre_supply_apy=r_supply_before,
        post_supply_apy=r_supply_after,
        supply_rate_change_bps=supply_delta_bps,
    )
