"""Rocket Pool on-chain API contracts (rETH exchange rate via EVM RPC / on-chain reads).

Rocket Pool has no public REST API for rETH rates. The IS adapter (rocket_pool.py)
is a pure static registry — instrument discovery only, no HTTP calls. rETH APY data
flows through DeFiLlama (project: "rocket-pool", already covered by
external/defillama/mocks/yields.yaml). The on-chain exchange rate for rETH is read
directly from the RocketTokenRETH contract (0xae78736Cd615f374D3085123A210448E74Fc6393)
via eth_call, documented in mocks/onchain_reth.yaml.
"""

from unified_api_contracts.external.rocket_pool.schemas import (
    RocketPoolRethConfig,
    RocketPoolRethState,
)

__all__ = ["RocketPoolRethConfig", "RocketPoolRethState"]
