"""Per-archetype circuit-breaker registry seeds.

Each ``<archetype>.py`` module exposes ``BREAKERS`` and ``RECOVERY_RULES``
sequences. Adding a new archetype:

1. Create ``<archetype_lowercase>.py`` with ``BREAKERS`` +
   ``RECOVERY_RULES`` at module scope.
2. Append the module to :data:`PER_ARCHETYPE_BREAKERS` /
   :data:`PER_ARCHETYPE_RECOVERY_RULES` here.
3. Cover the new archetype in
   ``tests/internal/unit/test_circuit_breaker_taxonomy.py``.
"""

from __future__ import annotations

from typing import Final

from ...canonical.crosscutting.circuit_breaker import BreakerConfig, BreakerRecoveryRule
from . import (
    arbitrage_price_dispersion,
    carry_staked_basis,
    leveraged_funding_arb,
    ml_directional_continuous,
)

PER_ARCHETYPE_BREAKERS: Final[dict[str, tuple[BreakerConfig, ...]]] = {
    "CARRY_STAKED_BASIS": carry_staked_basis.BREAKERS,
    "ARBITRAGE_PRICE_DISPERSION": arbitrage_price_dispersion.BREAKERS,
    "LEVERAGED_FUNDING_ARB": leveraged_funding_arb.BREAKERS,
    "ML_DIRECTIONAL_CONTINUOUS": ml_directional_continuous.BREAKERS,
}

PER_ARCHETYPE_RECOVERY_RULES: Final[dict[str, tuple[BreakerRecoveryRule, ...]]] = {
    "CARRY_STAKED_BASIS": carry_staked_basis.RECOVERY_RULES,
    "ARBITRAGE_PRICE_DISPERSION": arbitrage_price_dispersion.RECOVERY_RULES,
    "LEVERAGED_FUNDING_ARB": leveraged_funding_arb.RECOVERY_RULES,
    "ML_DIRECTIONAL_CONTINUOUS": ml_directional_continuous.RECOVERY_RULES,
}

__all__ = (
    "PER_ARCHETYPE_BREAKERS",
    "PER_ARCHETYPE_RECOVERY_RULES",
)
