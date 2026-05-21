"""Copper custody platform API contracts (api.copper.co/platform/).

Note: All Copper endpoints require HMAC-signed authentication.
Cassette documents the wallet balances interaction pattern with redacted auth.
"""

from unified_api_contracts.external.copper.schemas import (
    CopperBalance,
    CopperWalletBalancesResponse,
)

__all__ = ["CopperBalance", "CopperWalletBalancesResponse"]
