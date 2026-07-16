"""Solana DeFi protocol SDK types.

Types for Kamino (lending), Raydium (DEX), Jupiter (aggregator).
These mirror the response shapes from the respective Python SDKs and REST APIs.

Drift Protocol types (DriftMarketInfo/DriftMarketType/DriftOrderParams/DriftOrderResult/
DriftOrderSide/DriftOrderType/DriftPosition) were removed 2026-07-16 (operator ruling:
all Solana perp DEXes dropped except Jupiter, which is a swap aggregator not a perp DEX).
Their only consumer, execution-service's ``drift.py`` connector, was deleted the same day.
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
