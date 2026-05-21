"""Tenderly Virtual TestNet API contracts (api.tenderly.co/api/v1/).

Used by execution-service to create mainnet fork environments for DeFi simulation.
All endpoints require X-Access-Key header (Tenderly API key).
"""

from unified_api_contracts.external.tenderly.schemas import (
    TenderlyVnetResponse,
    TenderlyVnetRpcUrls,
)

__all__ = ["TenderlyVnetResponse", "TenderlyVnetRpcUrls"]
