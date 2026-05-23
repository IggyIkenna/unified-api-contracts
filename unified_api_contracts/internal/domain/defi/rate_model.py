"""Aave V3 + Compound V3 Interest Rate Models — pure math for rate impact simulation.

Implements the Aave V3 variable interest rate model exactly as specified in the
Aave V3 protocol docs. Given pool parameters (slopes, optimal utilization,
reserve factor) and a proposed trade (supply or borrow), computes the resulting
utilization shift and new supply/borrow APYs.

Phase 1B (``defi_simulation_realism_2026_05_10``) adds a generalised
``LendingMarketState`` model with a ``protocol_irm_shape`` discriminator so
the matching engine's rate-impact calculator dispatches by protocol family.
Compound V3 uses a different (single-kink) IRM shape than Aave's
piecewise-linear kinked-slope; Spark + Radiant inherit Aave's shape.

All computations use Decimal for precision — no floats.

Reference: https://docs.aave.com/risk/liquidity-risk/borrow-interest-rate
"""

from decimal import Decimal
from enum import StrEnum
from typing import TypedDict

from pydantic import BaseModel


class ProtocolIRMShape(StrEnum):
    """Discriminator for per-protocol interest-rate-model shape dispatch.

    Distinct shapes drive distinct ``compute_borrow_rate`` formulas:

    - ``AAVE_KINKED`` — Aave V3, Spark, Radiant. Piecewise linear with a kink
      at ``optimal_utilization``: below kink uses ``slope1`` only; above kink
      adds ``slope2`` scaled by ``(U - U_opt) / (1 - U_opt)``.
    - ``COMPOUND_V3`` — Comet single-asset borrow model. Different shape: base
      rate + linear ``below_kink_slope`` to the kink; then jumps to a different
      linear ``above_kink_slope * (U - kink)`` beyond it. Critical: the matcher
      MUST dispatch by ``protocol_irm_shape`` — applying Aave math to Compound
      pools silently corrupts post-trade rate predictions.
    - ``MORPHO_ADAPTIVE`` — Morpho-Blue adaptive curve (FUTURE; not yet wired).

    SSOT: ``codex/04-architecture/amm-slippage-simulation.md`` § "Per-protocol
    IRM parameter capture". Declared by ``defi_simulation_realism_2026_05_10``
    Phase 1B.
    """

    AAVE_KINKED = "AAVE_KINKED"
    COMPOUND_V3 = "COMPOUND_V3"
    MORPHO_ADAPTIVE = "MORPHO_ADAPTIVE"


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
    # USDC — verified from DefaultReserveInterestRateStrategyV2.getInterestRateData(USDC)
    # at Ethereum mainnet block 23364831 via _fetch_irm_params_live in Phase 3C harness.
    # V2 ABI returns (optimalUsageRatio, baseVariableBorrowRate, variableRateSlope1, variableRateSlope2)
    # all as uint256 in RAY (1e27 = 100%). reserve_factor from configuration.data bits 64-79 in bps.
    "USDC": {
        "optimal_utilization": Decimal("0.92"),
        "slope1": Decimal("0.065"),
        "slope2": Decimal("0.20"),
        "base_rate": Decimal("0.00"),
        "reserve_factor": Decimal("0.10"),
    },
    # USDT — V2 strategy per-asset params (same singleton contract as USDC).
    # slope2=0.14 per Phase 3C v4 investigation (per-asset cache confirmed distinct from USDC).
    "USDT": {
        "optimal_utilization": Decimal("0.92"),
        "slope1": Decimal("0.065"),
        "slope2": Decimal("0.14"),
        "base_rate": Decimal("0.00"),
        "reserve_factor": Decimal("0.10"),
    },
    # DAI — V2 or V1 strategy; slope2=0.35 per Phase 3C v4 investigation (cache pollution fixed).
    "DAI": {
        "optimal_utilization": Decimal("0.92"),
        "slope1": Decimal("0.055"),
        "slope2": Decimal("0.35"),
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
    "WBTC": {
        "optimal_utilization": Decimal("0.45"),
        "slope1": Decimal("0.04"),
        "slope2": Decimal("3.00"),
        "base_rate": Decimal("0.00"),
        "reserve_factor": Decimal("0.20"),
    },
    "wstETH": {
        "optimal_utilization": Decimal("0.45"),
        "slope1": Decimal("0.07"),
        "slope2": Decimal("3.00"),
        "base_rate": Decimal("0.00"),
        "reserve_factor": Decimal("0.15"),
    },
    "weETH": {
        "optimal_utilization": Decimal("0.35"),
        "slope1": Decimal("0.07"),
        "slope2": Decimal("3.00"),
        "base_rate": Decimal("0.00"),
        "reserve_factor": Decimal("0.15"),
    },
    "rETH": {
        "optimal_utilization": Decimal("0.45"),
        "slope1": Decimal("0.07"),
        "slope2": Decimal("3.00"),
        "base_rate": Decimal("0.00"),
        "reserve_factor": Decimal("0.15"),
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


class LendingMarketState(BaseModel):
    """Generalised per-protocol lending market state with IRM-shape discriminator.

    Phase 1B (``defi_simulation_realism_2026_05_10``). Superset of ``AavePoolParams``
    with a ``protocol_irm_shape`` field so the matching engine's rate-impact
    calculator dispatches to the right IRM math (Aave V3 / Spark / Radiant share
    ``AAVE_KINKED``; Compound V3 has its own shape).

    Consumed by:

    - matching-engine ``LendingRateImpactCalculator`` (execution-service Phase 3A)
      for backtest + live pre-trade post-trade-rate estimation.
    - features-onchain rate-impact analytics (``aave_rate_impact_calculator``
      is the historical Aave-only consumer; that consumer reads
      ``LendingMarketState`` and adapts via ``protocol_irm_shape == AAVE_KINKED``).
    - strategy-service/risk forward-impact projection for archetype
      capital-allocation gates.

    Compound V3 specific fields (``compound_kink``, ``compound_below_kink_slope``,
    ``compound_above_kink_slope``) carry the Comet IRM parameters that the
    Aave-shape fields don't represent. Both sets are populated by the MTDS
    ``lending_indices`` adapter at capture time; the matcher reads the
    discriminator-relevant subset only.
    """

    pool_symbol: str
    chain: str  # "ethereum" / "arbitrum" / "optimism" / "polygon" / "base" / "avalanche" / "gnosis" / "bsc"
    protocol: str  # "AAVE_V3" / "COMPOUND_V3" / "SPARK" / "RADIANT" / "MORPHO"
    protocol_irm_shape: ProtocolIRMShape

    # Pool liquidity state (always populated, native units):
    total_supply: Decimal
    total_borrow: Decimal
    reserve_factor: Decimal

    # Aave-shape IRM parameters (populated when protocol_irm_shape == AAVE_KINKED):
    optimal_utilization_rate: Decimal = Decimal("0")
    irm_base: Decimal = Decimal("0")
    irm_slope1: Decimal = Decimal("0")
    irm_slope2: Decimal = Decimal("0")

    # Compound V3-shape IRM parameters (populated when protocol_irm_shape == COMPOUND_V3):
    compound_kink: Decimal = Decimal("0")
    compound_base_rate: Decimal = Decimal("0")
    compound_below_kink_slope: Decimal = Decimal("0")
    compound_above_kink_slope: Decimal = Decimal("0")

    # Aave-only on-chain index snapshots (used for live state reconciliation):
    liquidity_index: Decimal = Decimal("1")
    variable_borrow_index: Decimal = Decimal("1")

    @classmethod
    def from_aave_pool_params(cls, params: AavePoolParams, chain: str = "ethereum") -> "LendingMarketState":
        """Backwards-compat builder — promote a legacy ``AavePoolParams`` into the
        generalised ``LendingMarketState`` shape with ``protocol_irm_shape``
        set to ``AAVE_KINKED``. Consumers can incrementally migrate to the new
        model without breaking existing call sites.
        """
        return cls(
            pool_symbol=params.pool_symbol,
            chain=chain,
            protocol="AAVE_V3",
            protocol_irm_shape=ProtocolIRMShape.AAVE_KINKED,
            total_supply=params.total_supply_usd,
            total_borrow=params.total_borrow_usd,
            reserve_factor=params.reserve_factor,
            optimal_utilization_rate=params.optimal_utilization,
            irm_base=params.base_rate,
            irm_slope1=params.slope1,
            irm_slope2=params.slope2,
        )


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


def compute_borrow_rate_compound_v3(
    utilization: Decimal,
    kink: Decimal,
    base_rate: Decimal,
    below_kink_slope: Decimal,
    above_kink_slope: Decimal,
) -> Decimal:
    """Compute the variable borrow rate using Compound V3 (Comet) interest rate model.

    DIFFERENT shape from Aave V3's piecewise-linear kinked-slope. Compound V3
    uses a base rate + separate below-kink and above-kink slopes:

        if U <= kink:
            R_borrow = base_rate + below_kink_slope * U
        else:
            R_borrow = base_rate + below_kink_slope * kink + above_kink_slope * (U - kink)

    Used by ``LendingMarketState`` when ``protocol_irm_shape == COMPOUND_V3``.
    Reference: Compound V3 (Comet) Solidity implementation —
    `Comet.getBorrowRate(utilization)`.
    """
    if utilization <= kink:
        return base_rate + below_kink_slope * utilization
    return base_rate + below_kink_slope * kink + above_kink_slope * (utilization - kink)


def compute_borrow_rate_for_state(state: "LendingMarketState", utilization: Decimal) -> Decimal:
    """Protocol-dispatched borrow rate — selects the right IRM formula by ``protocol_irm_shape``.

    Phase 1B helper used by the matching engine's ``post_trade_rate`` calculator
    (execution-service Phase 3A) + the features-onchain Aave-rate-impact-calculator
    consumer. Dispatching here keeps callers ignorant of per-protocol IRM math.
    """
    if state.protocol_irm_shape == ProtocolIRMShape.AAVE_KINKED:
        return compute_borrow_rate(
            utilization=utilization,
            slope1=state.irm_slope1,
            slope2=state.irm_slope2,
            optimal_utilization=state.optimal_utilization_rate,
            base_rate=state.irm_base,
        )
    if state.protocol_irm_shape == ProtocolIRMShape.COMPOUND_V3:
        return compute_borrow_rate_compound_v3(
            utilization=utilization,
            kink=state.compound_kink,
            base_rate=state.compound_base_rate,
            below_kink_slope=state.compound_below_kink_slope,
            above_kink_slope=state.compound_above_kink_slope,
        )
    # MORPHO_ADAPTIVE not yet implemented — return base_rate as a conservative
    # placeholder until the Morpho-Blue adaptive-curve helper lands.
    return state.irm_base


def post_trade_rate(
    state: "LendingMarketState",
    supply_delta: Decimal,
    borrow_delta: Decimal,
) -> tuple[Decimal, Decimal]:
    """Compute post-trade (supply_apy, borrow_apy) for the given state mutation.

    Phase 1B + 3A canonical entry point. Dispatches by ``state.protocol_irm_shape``
    via ``compute_borrow_rate_for_state``. Mirrors the codex section
    ``amm-slippage-simulation.md`` § "Per-protocol IRM parameter capture".

    Args:
        state: current lending market state (pre-trade).
        supply_delta: change to ``total_supply`` (positive for supply, negative for withdraw).
        borrow_delta: change to ``total_borrow`` (positive for borrow, negative for repay).

    Returns:
        ``(supply_apy, borrow_apy)`` — post-trade rates implied by the new utilization.
    """
    new_total_supply = state.total_supply + supply_delta
    new_total_borrow = state.total_borrow + borrow_delta
    new_utilization = compute_utilization(new_total_supply, new_total_borrow)
    borrow_apy = compute_borrow_rate_for_state(state, new_utilization)
    supply_apy = compute_supply_rate(new_utilization, borrow_apy, state.reserve_factor)
    return supply_apy, borrow_apy


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
