"""Euler V2 EVK vault on-chain response schemas.

Data source: EVM RPC (eth_call) against Euler V2 EVK vault contracts.
Reference: https://app.euler.finance/
Note: Euler V2 has no public REST API — all reads are on-chain via Alchemy/RPC.
"""

__api_version__ = "v2"

from pydantic import BaseModel


class EulerV2VaultState(BaseModel):
    """Live state from an Euler V2 EVK vault (totalAssets / totalBorrows / APY)."""

    vault_address: str | None = None
    collateral_asset: str | None = None
    borrow_asset: str | None = None
    total_assets_wei: str | None = None
    total_borrows_wei: str | None = None
    supply_apy_bps: int | None = None
    borrow_apy_bps: int | None = None
    utilization_rate_bps: int | None = None
    block_number: int | None = None
    timestamp: str | None = None


class EulerV2VaultConfig(BaseModel):
    """Static configuration from an Euler V2 EVK vault (LTV / liquidation params)."""

    vault_address: str | None = None
    max_ltv_bps: int | None = None
    liquidation_threshold_bps: int | None = None
    liquidation_penalty_bps: int | None = None
    interest_rate_model: str | None = None
