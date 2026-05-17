"""DeFi crosscutting protocol enums — shared across MTDS, strategy, execution, risk.

These enums identify DeFi lending protocols used in recursive-borrow archetypes
(``CARRY_RECURSIVE_BORROW_LENDING_ONLY`` and ``CARRY_RECURSIVE_BORROW_PERP_HEDGED``).

They live here (not in a service-specific module) because the same enum values
flow through UAC archetype config, strategy-service factory, execution-service
orchestrator, risk-and-exposure-service HF calculation, and MTDS lending-rate
adapter keys — four services, one source of truth.

Plan: ``plans/active/defi_recursive_borrow_archetypes_2026_05_10.md`` Phase 2
(UAC config schema extension).
"""

from __future__ import annotations

from enum import StrEnum


class LendingProtocol(StrEnum):
    """Canonical DeFi lending protocol identifier.

    Used by:

    * :mod:`unified_api_contracts.internal.architecture_v2.archetype_config` —
      ``lending_protocol`` field on :class:`~archetype_config.ArchetypeConfig`
      to declare which protocol the recursive-borrow strategy targets.
    * MTDS lending-rate adapters — ``aave_v3_lending_rates.py`` /
      ``compound_v3_lending_rates.py`` / etc. as their canonical protocol key.
    * Strategy-service factory — to route lending-leg execution to the
      correct on-chain integration.
    * Risk-and-exposure-service — to look up
      ``defi_reserve_params.get_reserve_params(asset, protocol=...)`` for HF
      calculation.

    Members ``SPARK``, ``MORPHO_BLUE``, and ``MAKER_DSR`` are included for
    completeness; they are P1/P2 for May-23 (AAVE_V3 + COMPOUND_V3 are P0).
    """

    AAVE_V3 = "aave_v3"
    """Aave V3 (multi-chain: Ethereum, Arbitrum, Base, Optimism, Polygon, …)."""

    COMPOUND_V3 = "compound_v3"
    """Compound V3 / Comet (multi-chain: Ethereum, Arbitrum, Base, Polygon)."""

    SPARK = "spark"
    """Spark Protocol (Aave V3 fork on Ethereum, operated by MakerDAO/Sky)."""

    MORPHO_BLUE = "morpho_blue"
    """Morpho Blue — isolated per-market lending with configurable LLTV."""

    MAKER_DSR = "maker_dsr"
    """MakerDAO DAI Savings Rate — single yield stream, no borrow leg."""
