"""Matching engine domain contracts.

Internal schemas for order matching, AMM swap results, and fee calculations.
Used by matching-engine-library. External exchange/venue schemas live in UAC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TypedDict

__all__ = [
    "BookType",
    "FeeResult",
    "FillResult",
    "MatchResult",
    "MatchingFeeType",
    "OrderRecord",
    "OrderSide",
    "OrderType",
    "PoolShape",
    "SwapQuote",
    "SwapResult",
]


class OrderType(StrEnum):
    """Order types supported by the matching engine."""

    LIMIT = "LIMIT"
    IOC = "IOC"
    FOK = "FOK"
    MAX_SLIPPAGE = "MAX_SLIPPAGE"
    MARKET = "MARKET"


class BookType(StrEnum):
    """Book types that determine matching logic.

    Ordering by fidelity (descending L2_MBP > CANDLE_BOOK_COLS > L1_MBP > L0_TOB)
    for the price-discovery tiers; AMM + ALPHA_ZERO are orthogonal protocol-fill
    paths. ``CANDLE_BOOK_COLS`` is the mid-fidelity tier sourced from the Plan-1
    intra-bar book-summary columns precomputed on the processed candle (spread
    TW-mean, mid_close, per-level depth) — sits between L1 OHLC and L2 tick walk
    in :class:`~unified_api_contracts.ExecutionFidelityTier`.
    """

    L0_TOB = "L0_TOB"
    L1_MBP = "L1_MBP"
    CANDLE_BOOK_COLS = "CANDLE_BOOK_COLS"
    L2_MBP = "L2_MBP"
    AMM = "AMM"
    ALPHA_ZERO = "ALPHA_ZERO"


class MatchingFeeType(StrEnum):
    """Fee structure type based on venue domain."""

    ASYMMETRIC = "asymmetric"
    SYMMETRIC = "symmetric"
    POOL = "pool"
    LENDING = "lending"
    NONE = "none"


class OrderRecord(TypedDict):
    """Record of a limit order placed via narrow-range liquidity."""

    pool_key: dict[str, str | int]
    params: dict[str, str | int | Decimal]


@dataclass
class FeeResult:
    """Fee calculation result."""

    fee_amount: Decimal
    fee_rate_bps: Decimal
    fee_type: MatchingFeeType
    is_maker: bool


@dataclass
class SwapResult:
    """Result of an AMM swap calculation."""

    amount_in: Decimal
    amount_out: Decimal
    fee_amount: Decimal
    price_impact_bps: Decimal
    execution_price: Decimal
    spot_price_before: Decimal
    spot_price_after: Decimal

    @property
    def slippage_bps(self) -> Decimal:
        """Calculate slippage in basis points."""
        if self.spot_price_before == 0:
            return Decimal("0")
        return abs((self.execution_price - self.spot_price_before) / self.spot_price_before * Decimal("10000"))


@dataclass
class MatchResult:
    """Result of order matching."""

    success: bool
    filled_quantity: Decimal
    remaining_quantity: Decimal
    fill_price: Decimal
    timestamp: datetime
    order_type: OrderType
    book_type: BookType
    price_impact_bps: Decimal | None = None
    fee_amount: Decimal | None = None
    error_message: str | None = None

    @property
    def is_partial_fill(self) -> bool:
        """Check if this was a partial fill."""
        return self.filled_quantity > 0 and self.remaining_quantity > 0

    @property
    def is_full_fill(self) -> bool:
        """Check if this was a full fill."""
        return self.remaining_quantity == 0 and self.success


class OrderSide(StrEnum):
    """Swap / order side as seen by the matching engine.

    BUY = acquire token0 by spending token1; SELL = spend token0 to acquire token1.
    Pool matchers map this onto their internal token-x / token-y axis.
    """

    BUY = "BUY"
    SELL = "SELL"


class PoolShape(StrEnum):
    """AMM pool-shape discriminator for matching-engine ``PoolMatcher`` dispatch.

    Each DeFi pool instrument carries a ``pool_shape: PoolShape`` field; the matching
    engine resolves it to the per-shape ``PoolMatcher`` implementation. Solidly forks
    (Velodrome / Aerodrome / Equalizer / Thena / Ramses ...) share one matcher
    discriminated internally by ``(chain_id, factory_address)``; aggregator shapes are
    multi-leg route composers, not single-pool matchers.

    SSOT: ``codex/04-architecture/amm-slippage-simulation.md`` § "Pool shape taxonomy".
    Declared by ``defi_simulation_realism_2026_05_10.md`` Phase 1A.
    """

    UNISWAP_V2 = "UNISWAP_V2"
    UNISWAP_V3 = "UNISWAP_V3"
    UNISWAP_V4_HOOK = "UNISWAP_V4_HOOK"
    CURVE_STABLE = "CURVE_STABLE"
    CURVE_CRYPTO = "CURVE_CRYPTO"
    BALANCER_WEIGHTED = "BALANCER_WEIGHTED"
    BALANCER_BOOSTED = "BALANCER_BOOSTED"
    BALANCER_COMPOSABLE = "BALANCER_COMPOSABLE"
    SOLANA_CLMM = "SOLANA_CLMM"
    SOLANA_AMM = "SOLANA_AMM"
    JUPITER_ROUTE_AGGREGATOR = "JUPITER_ROUTE_AGGREGATOR"
    ONEINCH_AGGREGATOR = "1INCH_AGGREGATOR"
    ZEROX_AGGREGATOR = "0X_AGGREGATOR"
    SOLIDLY_FORK = "SOLIDLY_FORK"
    SOLIDLY_CL_FORK = "SOLIDLY_CL_FORK"


@dataclass
class SwapQuote:
    """Read-only pre-trade quote returned by ``PoolMatcher.quote()``.

    Referentially transparent for a fixed pool snapshot — does NOT mutate pool state.
    ``amount_out`` / ``fee_amount`` are in the output / input token's native decimals.
    For aggregator routes, ``legs`` holds the per-leg sub-quotes.
    """

    pool_shape: PoolShape
    amount_in: Decimal
    amount_out: Decimal
    fee_amount: Decimal
    price_impact_bps: Decimal
    spot_price_pre: Decimal
    spot_price_post: Decimal
    execution_price: Decimal
    gas_estimate_units: int = 0
    hooks_invoked: tuple[str, ...] = ()
    ticks_crossed: int = 0
    used_curves: tuple[str, ...] = ()
    legs: tuple[SwapQuote, ...] = field(default_factory=tuple)

    @property
    def slippage_bps(self) -> Decimal:
        """Realised execution price slippage vs spot, in basis points."""
        if self.spot_price_pre == 0:
            return Decimal("0")
        return abs((self.execution_price - self.spot_price_pre) / self.spot_price_pre * Decimal("10000"))


@dataclass
class FillResult:
    """Realised fill from ``PoolMatcher.apply()`` — superset of :class:`SwapQuote`.

    Adds the post-fill bookkeeping that the matching engine + execution-alpha
    attribution need: the block the fill confirmed at (``None`` for batch / Tenderly-
    fork simulation), the realised slippage of the executed fill vs the pre-trade
    quote, the mempool path (for separating MEV loss from genuine slippage), and the
    ordered hook-invocation log. ``mempool_path`` is one of ``BATCH_SIM`` / ``PUBLIC``
    / ``PRIVATE``.
    """

    pool_shape: PoolShape
    amount_in: Decimal
    amount_out: Decimal
    fee_amount: Decimal
    price_impact_bps: Decimal
    spot_price_pre: Decimal
    spot_price_post: Decimal
    execution_price: Decimal
    realized_slippage_vs_quote_bps: Decimal = Decimal("0")
    filled_at_block: int | None = None
    gas_estimate_units: int = 0
    hooks_invoked: tuple[str, ...] = ()
    ticks_crossed: int = 0
    used_curves: tuple[str, ...] = ()
    mempool_path: str = "BATCH_SIM"
    hooks_log: tuple[str, ...] = ()
    legs: tuple[SwapQuote, ...] = field(default_factory=tuple)

    @property
    def slippage_bps(self) -> Decimal:
        """Realised execution price slippage vs spot, in basis points."""
        if self.spot_price_pre == 0:
            return Decimal("0")
        return abs((self.execution_price - self.spot_price_pre) / self.spot_price_pre * Decimal("10000"))
