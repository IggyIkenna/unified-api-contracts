"""Venue-set variants — the 3rd cascade dimension of the strategy-instance catalogue.

Every strategy archetype is offered at multiple pricing tiers by varying the set
of venues (and/or venue categories) the strategy trades on. Each variant is a
separate ``StrategyInstance`` — backtested, paper-traded and live-traded
independently — so clients can see tangible "+X% if you add these N venues"
from the tearsheet overlay.

The CARRY_BASIS_PERP archetype ladder is the worked example named in the
2026-04-21 model (Elysium's offering):

    base_cex                OKX + Binance + Bybit                       base
    premium_cex             + Deribit + Hyperliquid + full CEX panel    premium
    multicat                primary category + one adjacent category    top_tier
    full                    primary + all adjacent categories           apex

The **same pattern applies to every archetype**. A generic builder derives the
tiers for each archetype from its ``ArchetypeCapability`` cells:

  1. Primary category = the category with the most supported venues.
  2. ``base_{primary}``       = the 3 canonical venues within the primary category.
  3. ``premium_{primary}``    = every venue within the primary category.
  4. ``multicat_{primary}_{secondary}``
                              = primary + the next category (by venue count).
  5. ``full``                 = every venue across every supported category.

Single-category archetypes collapse to {base, premium} (2 tiers). Dual-category
archetypes produce {base, premium, multicat} (3 tiers). Tri-or-more-category
archetypes produce all four tiers.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ARCHETYPE_CAPABILITY_REGISTRY,
    ArchetypeCapability,
    ArchetypeInstrumentType,
    CoverageStatus,
)
from unified_api_contracts.internal.architecture_v2.enums import (
    StrategyArchetype,
    VenueCategoryV2,
)

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
# Generic per-archetype variant builder
# ---------------------------------------------------------------------------


# Canonical "first three" venues per category. Used as the ``base`` variant's
# venue subset when the archetype supports venues in that category. Ordering
# reflects liquidity / usage rank, not alphabetical.
_BASE_VENUES_BY_CATEGORY: dict[VenueCategoryV2, tuple[str, ...]] = {
    VenueCategoryV2.CEFI: ("okx", "binance", "bybit"),
    VenueCategoryV2.DEFI: ("aave_v3", "uniswap_v3", "lido"),
    VenueCategoryV2.TRADFI: ("cme", "ibkr", "ice"),
    VenueCategoryV2.SPORTS: ("betfair_direct", "smarkets_direct", "matchbook_direct"),
    VenueCategoryV2.PREDICTION: ("polymarket",),
}


def _archetype_slug(archetype: StrategyArchetype) -> str:
    """Stable lowercase slug used as a variant-id prefix."""
    return archetype.value.lower()


def _category_slug(category: VenueCategoryV2) -> str:
    return category.value.lower()


def _venues_and_instruments_by_category(
    capability: ArchetypeCapability,
) -> tuple[dict[VenueCategoryV2, set[str]], dict[VenueCategoryV2, set[ArchetypeInstrumentType]]]:
    """Group supported venues / instrument types per category for one archetype."""
    venues_by_cat: dict[VenueCategoryV2, set[str]] = defaultdict(set)
    instr_by_cat: dict[VenueCategoryV2, set[ArchetypeInstrumentType]] = defaultdict(set)
    for cell in capability.cells:
        if cell.status is CoverageStatus.BLOCKED:
            continue
        venues_by_cat[cell.category].update(cell.venue_ids)
        instr_by_cat[cell.category].add(cell.instrument_type)
    return venues_by_cat, instr_by_cat


def _base_subset(category: VenueCategoryV2, supported_venues: set[str]) -> tuple[str, ...]:
    """Pick the canonical ``base`` venues for a category, preserving rank order.

    Falls back to the top 3 supported venues (alphabetical) if none of the
    canonical picks are supported for this archetype.
    """
    preferred = [v for v in _BASE_VENUES_BY_CATEGORY.get(category, ()) if v in supported_venues]
    if preferred:
        return tuple(preferred)
    return tuple(sorted(supported_venues)[:3])


def _build_variants_for_archetype(capability: ArchetypeCapability) -> list[VenueSetVariant]:
    """Derive base/premium/multicat/full variants from an archetype's capability row."""
    archetype = capability.archetype_id
    slug = _archetype_slug(archetype)
    venues_by_cat, instr_by_cat = _venues_and_instruments_by_category(capability)
    if not venues_by_cat:
        return []

    # Rank categories by venue count so the "primary" tier is the most-covered
    # category for this archetype. Ties broken alphabetically by category name
    # for determinism.
    sorted_cats = sorted(venues_by_cat, key=lambda c: (-len(venues_by_cat[c]), c.value))
    primary = sorted_cats[0]

    def _sorted_instr(cats: tuple[VenueCategoryV2, ...]) -> tuple[ArchetypeInstrumentType, ...]:
        merged: set[ArchetypeInstrumentType] = set()
        for c in cats:
            merged.update(instr_by_cat[c])
        return tuple(sorted(merged, key=lambda it: it.value))

    variants: list[VenueSetVariant] = []

    # Tier 1 — base: canonical 3 venues within the primary category.
    base_venues = _base_subset(primary, venues_by_cat[primary])
    variants.append(
        VenueSetVariant(
            id=f"{slug}_base_{_category_slug(primary)}",
            archetype=archetype,
            venues=base_venues,
            instrument_types=_sorted_instr((primary,)),
            label=f"{archetype.value} — Base ({len(base_venues)} {primary.value})",
            pricing_tier=PricingTier.BASE,
        )
    )

    # Tier 2 — premium: all supported venues within the primary category.
    primary_venues_sorted = tuple(sorted(venues_by_cat[primary]))
    if primary_venues_sorted != base_venues:
        variants.append(
            VenueSetVariant(
                id=f"{slug}_premium_{_category_slug(primary)}",
                archetype=archetype,
                venues=primary_venues_sorted,
                instrument_types=_sorted_instr((primary,)),
                label=(f"{archetype.value} — Premium ({len(primary_venues_sorted)} {primary.value})"),
                pricing_tier=PricingTier.PREMIUM,
            )
        )

    # Tier 3 — multicat: primary + one adjacent category.
    if len(sorted_cats) >= 2:
        secondary = sorted_cats[1]
        merged = tuple(sorted(venues_by_cat[primary] | venues_by_cat[secondary]))
        variants.append(
            VenueSetVariant(
                id=f"{slug}_multicat_{_category_slug(primary)}_{_category_slug(secondary)}",
                archetype=archetype,
                venues=merged,
                instrument_types=_sorted_instr((primary, secondary)),
                label=(f"{archetype.value} — {primary.value}+{secondary.value} ({len(merged)} venues)"),
                pricing_tier=PricingTier.TOP_TIER,
            )
        )

    # Tier 4 — full: every supported venue across every supported category.
    if len(sorted_cats) >= 3:
        all_cats = tuple(sorted_cats)
        all_venues = tuple(sorted({v for c in all_cats for v in venues_by_cat[c]}))
        variants.append(
            VenueSetVariant(
                id=f"{slug}_full",
                archetype=archetype,
                venues=all_venues,
                instrument_types=_sorted_instr(all_cats),
                label=f"{archetype.value} — Full ({len(all_venues)} venues, {len(all_cats)} categories)",
                pricing_tier=PricingTier.APEX,
            )
        )

    return variants


def _build_all_variants() -> tuple[VenueSetVariant, ...]:
    """Build the full variant table by walking the capability registry."""
    variants: list[VenueSetVariant] = []
    for capability in ARCHETYPE_CAPABILITY_REGISTRY:
        variants.extend(_build_variants_for_archetype(capability))
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
