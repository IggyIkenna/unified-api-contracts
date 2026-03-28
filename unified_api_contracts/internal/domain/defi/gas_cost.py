"""DeFi gas cost estimation schemas."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel


class GasCostAction(StrEnum):
    SWAP = "SWAP"
    SUPPLY = "SUPPLY"
    BORROW = "BORROW"
    STAKE = "STAKE"
    UNSTAKE = "UNSTAKE"
    WITHDRAW = "WITHDRAW"
    REPAY = "REPAY"
    LIQUIDATE = "LIQUIDATE"
    TRANSFER = "TRANSFER"
    BRIDGE = "BRIDGE"
    APPROVE = "APPROVE"
    ADD_LIQUIDITY = "ADD_LIQUIDITY"
    REMOVE_LIQUIDITY = "REMOVE_LIQUIDITY"
    FLASH_BORROW = "FLASH_BORROW"
    FLASH_REPAY = "FLASH_REPAY"
    ATOMIC_BUNDLE = "ATOMIC_BUNDLE"
    WRAP = "WRAP"
    UNWRAP = "UNWRAP"


class GasCostEstimate(BaseModel):
    protocol: str
    chain: str
    action: GasCostAction
    gas_estimate_gwei: Decimal
    gas_estimate_usd: Decimal | None = None


class BlockGasFee(BaseModel):
    """Historical gas fee data for a single block from eth_feeHistory."""

    chain_id: int
    block_number: int
    timestamp: datetime
    base_fee_gwei: Decimal
    priority_fee_p25_gwei: Decimal
    priority_fee_p50_gwei: Decimal
    priority_fee_p75_gwei: Decimal
    gas_used_ratio: float
    blob_base_fee_gwei: Decimal | None = None


class GasFeeSnapshot(BaseModel):
    """Point-in-time gas fee snapshot for cost estimation."""

    chain_id: int
    timestamp: datetime
    block_number: int
    base_fee_gwei: Decimal
    priority_fee_gwei: Decimal
    eth_price_usd: Decimal | None = None
    gas_estimates: dict[str, int] | None = None


class InstructionGasCost(BaseModel):
    """Actual gas cost for a single execution instruction."""

    instruction_id: str
    operation: str
    chain_id: int
    gas_units: int
    gas_price_gwei: Decimal
    priority_fee_gwei: Decimal
    gas_cost_eth: Decimal
    gas_cost_usd: Decimal
    eth_price_usd: Decimal
    block_number: int
    timestamp: datetime
    # Chain-aware fields (populated for non-ETH gas token chains)
    native_token: str | None = None
    gas_cost_native: Decimal | None = None


class EthBalanceImpact(BaseModel):
    """Impact of gas deduction on wallet ETH balance (ETH-native chains)."""

    wallet_address: str
    chain_id: int
    instruction_id: str
    gas_cost_eth: Decimal
    eth_balance_before: Decimal
    eth_balance_after: Decimal
    creates_eth_debt: bool
    debt_amount_eth: Decimal | None = None


class GasTokenBalanceImpact(BaseModel):
    """Impact of gas deduction on wallet native token balance (any chain)."""

    wallet_address: str
    chain_id: int
    instruction_id: str
    native_token: str
    gas_cost_native: Decimal
    gas_cost_usd: Decimal | None = None
    native_balance_before: Decimal
    native_balance_after: Decimal
    creates_debt: bool
    debt_amount_native: Decimal | None = None
