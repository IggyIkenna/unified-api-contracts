"""Venus Protocol vToken API contracts (on-chain reads via EVM RPC on BSC/Ethereum)."""

from unified_api_contracts.external.venus.schemas import (
    VenusVTokenConfig,
    VenusVTokenState,
)

__all__ = ["VenusVTokenConfig", "VenusVTokenState"]
