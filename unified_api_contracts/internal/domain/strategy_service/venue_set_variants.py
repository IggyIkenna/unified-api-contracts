"""Venue-set variants — the 3rd cascade dimension of the strategy-instance catalogue.

A single strategy ``archetype`` is offered at multiple pricing tiers by varying
the set of venues it can trade on. Each variant is a separate
``StrategyInstance`` — backtested, paper-traded and live-traded independently —
so clients can see tangible "+X% if you add these N venues" from the tearsheet
overlay.

The canonical worked example is Elysium (stat-arb basis cash-and-carry):

    ely_base_3cex           OKX + Binance + Bybit                        base
    ely_premium_6cex        + Deribit + Hyperliquid + Aster              premium
    ely_multi_evm           base_3cex U Ethereum + multi-EVM chains      top-tier
    ely_multi_evm_plus_sol  multi_evm + Solana                           apex

Every other archetype has at least one default variant — archetypes without
a meaningful venue-set ladder use a single ``_default`` variant covering their
venue superset.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ARCHETYPE_CAPABILITY_REGISTRY,
    ArchetypeInstrumentType,
)
from unified_api_contracts.internal.architecture_v2.enums import StrategyArchetype

__all__ = [
    "VENUE_SET_VARIANTS",
    "PricingTier",
    "VenueSetVariant",
    "get_venue_set_variant",
    "get_venue_set_variants",
]


class PricingTier(StrEnum):
    """Pricing tier ladder for venue-set upsell."""

    BASE = "base"
    PREMIUM = "premium"
    TOP_TIER = "top_tier"
    APEX = "apex"


@dataclass(frozen=True)
class VenueSetVariant:
    """A named venue-set attached to a strategy archetype.

    ``venues`` and ``instrument_types`` are tuples for frozen-dataclass
    hashability. ``pricing_tier`` drives the upsell ladder the UI renders in
    the ``<FamilyArchetypePicker>`` 3rd cascade.
    """

    id: str
    archetype: StrategyArchetype
    venues: tuple[str, ...]
    instrument_types: tuple[ArchetypeInstrumentType, ...]
    label: str
    pricing_tier: PricingTier


# ---------------------------------------------------------------------------
# Elysium worked example (the variant ladder referenced in Plan A context)
# ---------------------------------------------------------------------------

_ELYSIUM_BASE_VENUES: tuple[str, ...] = ("okx", "binance", "bybit")
_ELYSIUM_PREMIUM_ADD: tuple[str, ...] = ("deribit", "hyperliquid", "aster")
_ELYSIUM_EVM_ADD: tuple[str, ...] = ("ethereum", "arbitrum", "optimism", "base", "polygon")
_ELYSIUM_SOL_ADD: tuple[str, ...] = ("solana",)

_ELYSIUM_INSTRUMENTS: tuple[ArchetypeInstrumentType, ...] = (
    ArchetypeInstrumentType.SPOT,
    ArchetypeInstrumentType.PERP,
    ArchetypeInstrumentType.DATED_FUTURE,
)

_ELYSIUM_VARIANTS: tuple[VenueSetVariant, ...] = (
    VenueSetVariant(
        id="ely_base_3cex",
        archetype=StrategyArchetype.CARRY_BASIS_PERP,
        venues=_ELYSIUM_BASE_VENUES,
        instrument_types=_ELYSIUM_INSTRUMENTS,
        label="Elysium — Base (3 CEX)",
        pricing_tier=PricingTier.BASE,
    ),
    VenueSetVariant(
        id="ely_premium_6cex",
        archetype=StrategyArchetype.CARRY_BASIS_PERP,
        venues=_ELYSIUM_BASE_VENUES + _ELYSIUM_PREMIUM_ADD,
        instrument_types=_ELYSIUM_INSTRUMENTS,
        label="Elysium — Premium (6 CEX)",
        pricing_tier=PricingTier.PREMIUM,
    ),
    VenueSetVariant(
        id="ely_multi_evm",
        archetype=StrategyArchetype.CARRY_BASIS_PERP,
        venues=_ELYSIUM_BASE_VENUES + _ELYSIUM_EVM_ADD,
        instrument_types=_ELYSIUM_INSTRUMENTS,
        label="Elysium — Multi-EVM",
        pricing_tier=PricingTier.TOP_TIER,
    ),
    VenueSetVariant(
        id="ely_multi_evm_plus_sol",
        archetype=StrategyArchetype.CARRY_BASIS_PERP,
        venues=_ELYSIUM_BASE_VENUES + _ELYSIUM_EVM_ADD + _ELYSIUM_SOL_ADD,
        instrument_types=_ELYSIUM_INSTRUMENTS,
        label="Elysium — Multi-EVM + Solana",
        pricing_tier=PricingTier.APEX,
    ),
)


# ---------------------------------------------------------------------------
# Default fallback variant builder — one _default variant per other archetype
# using the capability registry's declared venue superset.
# ---------------------------------------------------------------------------


def _default_variant_for_archetype(archetype: StrategyArchetype) -> VenueSetVariant | None:
    """Build a single _default variant for an archetype from its capability row.

    Returns ``None`` only if the archetype has no capability row at all (which
    should not happen for any archetype enum value — guarded defensively).
    """
    capability = next(
        (c for c in ARCHETYPE_CAPABILITY_REGISTRY if c.archetype_id is archetype),
        None,
    )
    if capability is None:
        return None

    venue_set: set[str] = set()
    instrument_set: set[ArchetypeInstrumentType] = set()
    for cell in capability.cells:
        venue_set.update(cell.venue_ids)
        instrument_set.add(cell.instrument_type)

    return VenueSetVariant(
        id=f"{archetype.value.lower()}_default",
        archetype=archetype,
        venues=tuple(sorted(venue_set)),
        instrument_types=tuple(sorted(instrument_set, key=lambda it: it.value)),
        label=f"{archetype.value} — Default",
        pricing_tier=PricingTier.BASE,
    )


def _build_all_variants() -> tuple[VenueSetVariant, ...]:
    """Seed the full variant table: Elysium ladder + per-archetype defaults."""
    elysium_archetype = StrategyArchetype.CARRY_BASIS_PERP
    variants: list[VenueSetVariant] = list(_ELYSIUM_VARIANTS)
    for archetype in StrategyArchetype:
        if archetype is elysium_archetype:
            continue
        default = _default_variant_for_archetype(archetype)
        if default is not None:
            variants.append(default)
    return tuple(variants)


VENUE_SET_VARIANTS: tuple[VenueSetVariant, ...] = _build_all_variants()
"""Module-level catalogue of all venue-set variants across all archetypes."""


_BY_ID: dict[str, VenueSetVariant] = {v.id: v for v in VENUE_SET_VARIANTS}
_BY_ARCHETYPE: dict[StrategyArchetype, tuple[VenueSetVariant, ...]] = {
    archetype: tuple(v for v in VENUE_SET_VARIANTS if v.archetype is archetype) for archetype in StrategyArchetype
}


def get_venue_set_variants(archetype: StrategyArchetype) -> tuple[VenueSetVariant, ...]:
    """Return the variant ladder for a given archetype."""
    return _BY_ARCHETYPE.get(archetype, ())


def get_venue_set_variant(variant_id: str) -> VenueSetVariant | None:
    """Look up a variant by its ID. Returns ``None`` when unknown."""
    return _BY_ID.get(variant_id)
