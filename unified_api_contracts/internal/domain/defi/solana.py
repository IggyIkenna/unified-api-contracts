"""Solana DeFi protocol SDK types.

Types for Drift (perps/spot), Kamino (lending), Raydium (DEX), Jupiter (aggregator).
These mirror the response shapes from the respective Python SDKs and REST APIs.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel


class SolanaChainId(StrEnum):
    """Solana cluster identifiers."""

    MAINNET = "mainnet-beta"
    DEVNET = "devnet"
    TESTNET = "testnet"


# ---------------------------------------------------------------------------
# Drift Protocol types (driftpy SDK)
# ---------------------------------------------------------------------------


class DriftMarketType(StrEnum):
    """Drift market types."""

    PERP = "perp"
    SPOT = "spot"


class DriftOrderType(StrEnum):
    """Drift order types."""

    MARKET = "market"
    LIMIT = "limit"
    TRIGGER_MARKET = "trigger_market"
    TRIGGER_LIMIT = "trigger_limit"


class DriftOrderSide(StrEnum):
    """Drift order side."""

    LONG = "long"
    SHORT = "short"


class DriftMarketInfo(BaseModel):
    """Drift perp or spot market metadata."""

    market_index: int
    market_type: DriftMarketType
    symbol: str
    base_asset: str
    quote_asset: str
    oracle_price_usd: Decimal
    total_deposits: Decimal | None = None
    total_borrows: Decimal | None = None
    open_interest: Decimal | None = None
    funding_rate_1h: Decimal | None = None
    is_active: bool = True


class DriftOrderParams(BaseModel):
    """Parameters for placing a Drift order."""

    market_index: int
    market_type: DriftMarketType
    order_type: DriftOrderType
    side: DriftOrderSide
    base_amount: Decimal
    price: Decimal | None = None  # None for market orders
    reduce_only: bool = False


class DriftPosition(BaseModel):
    """Drift position snapshot."""

    market_index: int
    market_type: DriftMarketType
    base_amount: Decimal
    quote_amount: Decimal
    entry_price: Decimal
    unrealized_pnl: Decimal
    oracle_price: Decimal


class DriftOrderResult(BaseModel):
    """Result of a Drift order execution."""

    tx_signature: str
    market_index: int
    side: DriftOrderSide
    base_filled: Decimal
    quote_filled: Decimal
    fee: Decimal
    timestamp: datetime


# ---------------------------------------------------------------------------
# Kamino Finance types (REST API / on-chain)
# ---------------------------------------------------------------------------


class KaminoReserve(BaseModel):
    """Kamino lending reserve (market)."""

    reserve_address: str
    token_mint: str
    symbol: str
    supply_apy: Decimal
    borrow_apy: Decimal
    total_supply: Decimal
    total_borrows: Decimal
    ltv: Decimal
    liquidation_threshold: Decimal
    is_active: bool = True


class KaminoDepositParams(BaseModel):
    """Parameters for a Kamino lending deposit."""

    reserve_address: str
    token_mint: str
    amount: Decimal


class KaminoBorrowParams(BaseModel):
    """Parameters for a Kamino borrow."""

    reserve_address: str
    token_mint: str
    amount: Decimal


# ---------------------------------------------------------------------------
# Jupiter types (REST API: quote-api.jup.ag/v6)
# ---------------------------------------------------------------------------


class JupiterSwapQuote(BaseModel):
    """Jupiter aggregator swap quote."""

    input_mint: str
    output_mint: str
    in_amount: int  # lamports / smallest unit
    out_amount: int
    price_impact_pct: Decimal
    route_plan: list[JupiterRoutePlanStep]
    slippage_bps: int


class JupiterRoutePlanStep(BaseModel):
    """Single hop in a Jupiter swap route."""

    amm_key: str
    label: str
    input_mint: str
    output_mint: str
    in_amount: int
    out_amount: int
    fee_amount: int
    fee_mint: str


class JupiterSwapResult(BaseModel):
    """Result of executing a Jupiter swap."""

    tx_signature: str
    input_amount: Decimal
    output_amount: Decimal
    price_impact_pct: Decimal
    fee_sol: Decimal


# ---------------------------------------------------------------------------
# Raydium types (REST API: api-v3.raydium.io)
# ---------------------------------------------------------------------------


class RaydiumPoolInfo(BaseModel):
    """Raydium liquidity pool info."""

    pool_id: str
    pool_type: str  # "concentrated" or "standard"
    token_a_mint: str
    token_b_mint: str
    token_a_symbol: str
    token_b_symbol: str
    tvl_usd: Decimal
    volume_24h_usd: Decimal
    fee_rate: Decimal
    apr_24h: Decimal | None = None


# ---------------------------------------------------------------------------
# Solana transaction result (shared across protocols)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Marinade / Jito liquid staking types
# ---------------------------------------------------------------------------


class SolanaStakePoolInfo(BaseModel):
    """Liquid staking pool info (Marinade mSOL, Jito jitoSOL)."""

    protocol: str  # "marinade" or "jito"
    pool_token_mint: str
    pool_token_symbol: str  # "mSOL" or "jitoSOL"
    exchange_rate: Decimal  # SOL per pool token
    apy: Decimal
    total_staked_sol: Decimal
    validators: int


# ---------------------------------------------------------------------------
# Orca Whirlpool types
# ---------------------------------------------------------------------------


class OrcaWhirlpoolInfo(BaseModel):
    """Orca concentrated liquidity pool."""

    pool_address: str
    token_a_mint: str
    token_b_mint: str
    token_a_symbol: str
    token_b_symbol: str
    tick_spacing: int
    fee_rate: Decimal
    tvl_usd: Decimal
    volume_24h_usd: Decimal | None = None
    current_price: Decimal | None = None


# ---------------------------------------------------------------------------
# Solana transaction result (shared across protocols)
# ---------------------------------------------------------------------------


class SolanaTransactionResult(BaseModel):
    """Result of any Solana transaction."""

    tx_signature: str
    slot: int
    block_time: datetime | None = None
    fee_lamports: int
    compute_units_consumed: int
    success: bool
    error_message: str | None = None
