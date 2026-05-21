"""Venus Protocol vToken on-chain response schemas.

Data source: EVM RPC (eth_call) against Venus vToken contracts on BSC/Ethereum.
Reference: https://app.venus.io/
Note: Venus has no public REST API for market rates — reads via BNB Chain / ETH RPC.
"""

__api_version__ = "v3"

from pydantic import BaseModel


class VenusVTokenState(BaseModel):
    """Live state from a Venus vToken (supply rate / borrow rate / cash / borrows)."""

    vtoken_address: str | None = None
    collateral_asset: str | None = None
    chain: str | None = None
    supply_rate_per_block: str | None = None
    borrow_rate_per_block: str | None = None
    total_cash_wei: str | None = None
    total_borrows_wei: str | None = None
    total_supply_wei: str | None = None
    exchange_rate_stored: str | None = None
    block_number: int | None = None
    timestamp: str | None = None


class VenusVTokenConfig(BaseModel):
    """Static configuration from a Venus vToken (collateral factor / reserve factor)."""

    vtoken_address: str | None = None
    collateral_factor_mantissa: str | None = None
    reserve_factor_mantissa: str | None = None
    interest_rate_model: str | None = None
    decimals: int | None = None
