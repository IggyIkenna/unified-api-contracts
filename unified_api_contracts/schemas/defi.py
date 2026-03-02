"""DeFi protocol data schemas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class Swap:
    protocol: str
    chain: str
    tx_hash: str
    token_in: str
    token_out: str
    amount_in: Decimal
    amount_out: Decimal
    fee: Decimal
    timestamp: datetime
    sender: str | None = None
    pool_address: str | None = None


@dataclass
class LiquidityPool:
    protocol: str
    chain: str
    pool_address: str
    token0: str
    token1: str
    reserve0: Decimal
    reserve1: Decimal
    total_liquidity_usd: Decimal
    volume_24h_usd: Decimal
    fee_tier: Decimal = Decimal("0.003")
    timestamp: datetime | None = None


@dataclass
class OraclePrice:
    oracle: str
    pair: str
    price: Decimal
    timestamp: datetime
    confidence: Decimal | None = None
    chain: str | None = None


@dataclass
class StakingRate:
    protocol: str
    asset: str
    apy: Decimal
    tvl_usd: Decimal
    timestamp: datetime
    chain: str | None = None


@dataclass
class LendingRate:
    protocol: str
    asset: str
    supply_apy: Decimal
    borrow_apy: Decimal
    utilization_rate: Decimal
    tvl_usd: Decimal
    timestamp: datetime
    chain: str | None = None
