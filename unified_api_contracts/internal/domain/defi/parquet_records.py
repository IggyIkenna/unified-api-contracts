"""Parquet record schemas for DeFi data handlers in MTDS.

These dataclasses define the column schemas written to GCS by the
collect-lending-indices, collect-dex-pools, collect-lst-rates,
collect-perp-funding, and collect-liquidations handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class LendingIndexRecord:
    """One row in a lending-indices parquet file."""

    timestamp: datetime
    timestamp_unix: int
    protocol: str  # aave_v3, compound_v3
    chain: str  # ETHEREUM, ARBITRUM, etc.
    symbol: str  # USDC, WETH, etc. (Aave) or market name (Compound)
    liquidity_index: float  # Aave: ray-decoded (÷1e27)
    variable_borrow_index: float  # Aave: ray-decoded
    supply_rate: float  # Compound: daily snapshot rate
    borrow_rate: float  # Compound: daily snapshot rate
    utilization_rate: float
    total_supply: float  # totalATokenSupply (Aave) or totalDepositBalanceUSD (Compound)
    total_debt: float  # totalCurrentVariableDebt (Aave) or totalBorrowBalanceUSD (Compound)


@dataclass(frozen=True, slots=True)
class DexPoolDayRecord:
    """One row in a dex-pools parquet file."""

    protocol: str  # uniswap_v3, balancer, curve
    chain: str
    pool_id: str
    pool_name: str  # token pair or pool name
    date_unix: int  # start-of-day unix timestamp
    volume_usd: float
    tvl_usd: float
    fees_usd: float
    tx_count: int


@dataclass(frozen=True, slots=True)
class LstRateRecord:
    """One row in an lst-rates parquet file.

    Stores the on-chain oracle exchange rate (NOT APY).
    APY = annualised growth in the rate.
    For P&L attribution: pnl = position_size * (rate_t1 - rate_t0).
    """

    timestamp: str  # YYYY-MM-DD
    token: str  # stETH, wstETH, rETH, cbETH, sUSDe, sDAI
    exchange_rate: float  # e.g. stETH/ETH = 1.001234
    quote_asset: str  # ETH, stETH, USDe, DAI
    block_number: int
    method: str  # contract method name
    contract: str  # contract address


@dataclass(frozen=True, slots=True)
class PerpFundingRecord:
    """One row in a perp-funding parquet file."""

    protocol: str  # hyperliquid, gmx
    date: str  # YYYY-MM-DD
    time: str  # timestamp from source
    coin: str  # BTC, ETH, SOL, etc.
    funding_rate: float
    premium: float
    oracle_px: float
    mark_px: float
    open_interest: float


@dataclass(frozen=True, slots=True)
class LiquidationRecord:
    """One row in a liquidations parquet file."""

    protocol: str  # aave_v3, compound_v3
    chain: str
    event_id: str
    timestamp: int
    collateral_symbol: str  # Aave: collateral reserve symbol
    principal_symbol: str  # Aave: debt reserve symbol / Compound: asset symbol
    collateral_amount: float
    principal_amount: float
    liquidator: str
    user: str  # liquidated user address
