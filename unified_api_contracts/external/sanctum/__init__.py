"""Sanctum LST marketplace contracts (static on-chain registry, no REST API).

Sanctum has no public REST API for LST rates. The IS adapter (sanctum.py) is a
pure static registry returning hardcoded mint addresses for INF, jupSOL, laineSOL.
APY data for Sanctum-listed LSTs flows through DeFiLlama or per-protocol adapters.
The mocks/lst_static_registry.yaml cassette documents the canonical Sanctum INF
mint address and LST metadata for carry_staked_basis instrumentation.
"""

from unified_api_contracts.external.sanctum.schemas import (
    SanctumLstToken,
    SanctumStaticRegistry,
)

__all__ = ["SanctumLstToken", "SanctumStaticRegistry"]
