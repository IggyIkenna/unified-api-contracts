"""Pydantic schemas for Rocket Pool rETH on-chain state (EVM RPC reads).

Rocket Pool has no public REST API. rETH exchange rate and APY are read
on-chain via eth_call against the RocketTokenRETH contract on Ethereum mainnet.
APY tracking uses DeFiLlama (project: "rocket-pool") as the aggregator.
"""

from pydantic import BaseModel, Field


class RocketPoolRethConfig(BaseModel):
    """Static configuration for the rETH contract on Ethereum mainnet."""

    contract_address: str = Field(
        default="0xae78736Cd615f374D3085123A210448E74Fc6393",
        description="RocketTokenRETH ERC-20 contract address on Ethereum mainnet",
    )
    decimals: int = Field(default=18, description="rETH token decimal precision")
    deploy_date: str = Field(default="2021-11-08", description="Rocket Pool mainnet GA date")


class RocketPoolRethState(BaseModel):
    """On-chain state snapshot from eth_call to RocketTokenRETH.getExchangeRate()."""

    exchange_rate_wei: int = Field(description="rETH/ETH exchange rate (wei per rETH, 1e18 = 1:1 parity)")
    total_supply_wei: int = Field(description="Total rETH supply (wei)")
    eth_balance_wei: int = Field(description="ETH backing the rETH pool (wei)")
