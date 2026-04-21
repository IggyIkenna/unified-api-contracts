"""Strategy-instance catalogue — the 5-dim possibility space shown to clients.

One ``StrategyInstance`` = one ``(family, archetype, venue_set_variant_id,
instrument_type_set, share_class)`` tuple. The full ``STRATEGY_INSTANCE_CATALOGUE``
is the cross-product driven by ``ARCHETYPE_CAPABILITY_REGISTRY`` x the venue-set
variant ladder x the allowed share-class set — ~200-300 instances post-expansion
versus the ~96 slot-label strategies in the pre-Plan-A ``STRATEGY_REGISTRY``.

This catalogue is immutable (the set of possibilities is fixed by the registries).
Runtime-mutable state per instance — maturity phase, product routing, series
refs — lives in ``StrategyInstanceLifecycle`` (owned by Firestore, hot-reloaded
via ``LifecycleReloader`` in ``unified-trading-library``).

Consumers:
  * Plan B — ``<FamilyArchetypePicker>`` in ``unified-trading-system-ui`` reads
    the materialised JSON at ``lib/registry/ui-reference-data.json`` (regenerated
    by ``unified-trading-pm/scripts/propagation/generate-ui-reference-data.py``
    on every UAC merge to main).
  * Plan C — ``<PerformanceOverlay>`` uses ``instance_id`` as the series key for
    the continuous backtest → paper → live timeline.
  * Plan D — DART research-fork versioning reads ``version_lineage`` from the
    ``StrategyInstanceLifecycle`` keyed on ``instance_id``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ARCHETYPE_CAPABILITY_REGISTRY,
    ArchetypeInstrumentType,
    CoverageStatus,
)
from unified_api_contracts.internal.architecture_v2.enums import (
    ARCHETYPE_TO_FAMILY,
    ShareClass,
    StrategyArchetype,
    StrategyFamily,
)
from unified_api_contracts.internal.domain.strategy_service.venue_set_variants import (
    VENUE_SET_VARIANTS,
    VenueSetVariant,
)

__all__ = [
    "STRATEGY_INSTANCE_CATALOGUE",
    "StrategyInstance",
    "StrategyInstanceCatalogue",
    "compute_instance_id",
]


# Canonical share-class set offered per archetype by default. Each variant-archetype
# pair combines with every entry here to seed the catalogue. ``ShareClass`` itself
# has more members (GBP / EUR / SOL / etc.) — the MVP catalogue deliberately ships
# with the four primary collateral currencies mentioned in the 2026-04-21 model.
_DEFAULT_SHARE_CLASSES: tuple[ShareClass, ...] = (
    ShareClass.BTC,
    ShareClass.ETH,
    ShareClass.USD,
    ShareClass.USDT,
)


def compute_instance_id(
    family: StrategyFamily,
    archetype: StrategyArchetype,
    venue_set_variant_id: str,
    instrument_type_set: tuple[ArchetypeInstrumentType, ...],
    share_class: ShareClass | None,
) -> str:
    """Deterministic instance_id from the 5-dim tuple.

    The ID is stable across runs so the catalogue, the Firestore lifecycle doc,
    and the materialised UI JSON all reference the same instance by value. Format
    is ``<archetype>__<variant_id>__<share_class>__<hash>`` where hash covers
    the instrument-type set and the family (defence against future archetype
    remapping — family serves as a tamper seal).
    """
    share_class_token = share_class.value if share_class is not None else "null"
    instrument_token = ",".join(sorted(it.value for it in instrument_type_set))
    seed = f"{family.value}|{archetype.value}|{venue_set_variant_id}|{instrument_token}|{share_class_token}"
    short_hash = hashlib.blake2b(seed.encode("utf-8"), digest_size=4).hexdigest()
    return f"{archetype.value.lower()}__{venue_set_variant_id}__{share_class_token.lower()}__{short_hash}"


@dataclass(frozen=True)
class StrategyInstance:
    """One catalogue instance in the 5-dim possibility space.

    Identity tuple: ``(family, archetype, venue_set_variant_id, instrument_type_set,
    share_class)``. ``instance_id`` is a deterministic hash of those five fields —
    immutable across the instance's lifetime.

    ``share_class`` is nullable when the archetype's variant has only one
    meaningful collateral currency (e.g. a USDT-only arbitrage strategy); most
    variants fan out across the four default share classes.

    ``coverage_status`` mirrors the capability-registry cell status (SUPPORTED /
    PARTIAL / BLOCKED). BLOCKED cells are excluded from the catalogue entirely.
    """

    instance_id: str
    family: StrategyFamily
    archetype: StrategyArchetype
    venue_set_variant_id: str
    instrument_type_set: tuple[ArchetypeInstrumentType, ...]
    share_class: ShareClass | None
    coverage_status: CoverageStatus


class StrategyInstanceCatalogue:
    """Queryable catalogue of the full 5-dim instance space."""

    def __init__(self, instances: list[StrategyInstance] | None = None) -> None:
        entries = instances if instances is not None else _default_catalogue_entries()
        self._by_id: dict[str, StrategyInstance] = {s.instance_id: s for s in entries}

    # -- Lookups -----------------------------------------------------------

    def get(self, instance_id: str) -> StrategyInstance | None:
        return self._by_id.get(instance_id)

    def all(self) -> list[StrategyInstance]:
        return list(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    # -- Filtering ---------------------------------------------------------

    def by_family(self, family: StrategyFamily) -> list[StrategyInstance]:
        return [s for s in self._by_id.values() if s.family is family]

    def by_archetype(self, archetype: StrategyArchetype) -> list[StrategyInstance]:
        return [s for s in self._by_id.values() if s.archetype is archetype]

    def by_variant(self, variant_id: str) -> list[StrategyInstance]:
        return [s for s in self._by_id.values() if s.venue_set_variant_id == variant_id]

    # -- Serialisation -----------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        """Serialise for the UI-reference-data JSON pipeline."""
        return {
            "instances": [
                {
                    "instance_id": s.instance_id,
                    "family": s.family.value,
                    "archetype": s.archetype.value,
                    "venue_set_variant_id": s.venue_set_variant_id,
                    "instrument_type_set": [it.value for it in s.instrument_type_set],
                    "share_class": s.share_class.value if s.share_class else None,
                    "coverage_status": s.coverage_status.value,
                }
                for s in self._by_id.values()
            ],
        }


# ---------------------------------------------------------------------------
# Catalogue builder — cross-product archetype x variant x share-class
# ---------------------------------------------------------------------------


def _cells_by_instrument(
    archetype: StrategyArchetype,
) -> dict[ArchetypeInstrumentType, CoverageStatus]:
    """Map instrument type → best coverage status for an archetype."""
    capability = next(
        (c for c in ARCHETYPE_CAPABILITY_REGISTRY if c.archetype_id is archetype),
        None,
    )
    if capability is None:
        return {}
    best: dict[ArchetypeInstrumentType, CoverageStatus] = {}
    for cell in capability.cells:
        if cell.status is CoverageStatus.BLOCKED:
            continue
        prev = best.get(cell.instrument_type)
        if prev is None or _status_better(cell.status, prev):
            best[cell.instrument_type] = cell.status
    return best


def _status_better(a: CoverageStatus, b: CoverageStatus) -> bool:
    rank = {CoverageStatus.SUPPORTED: 2, CoverageStatus.PARTIAL: 1, CoverageStatus.BLOCKED: 0}
    return rank[a] > rank[b]


def _variant_coverage_status(
    variant: VenueSetVariant,
    cells: dict[ArchetypeInstrumentType, CoverageStatus],
) -> CoverageStatus:
    """Fold the capability-cell statuses over the variant's instrument-type set.

    A variant inherits the best status among its instrument types; if none are
    SUPPORTED-or-PARTIAL the variant is excluded (caller should filter on
    ``BLOCKED``).
    """
    statuses: list[CoverageStatus] = []
    for it in variant.instrument_types:
        status = cells.get(it)
        if status is not None:
            statuses.append(status)
    if not statuses:
        return CoverageStatus.BLOCKED
    if any(s is CoverageStatus.SUPPORTED for s in statuses):
        return CoverageStatus.SUPPORTED
    return CoverageStatus.PARTIAL


def _default_catalogue_entries() -> list[StrategyInstance]:
    """Cross-product (variant x share-class), filtered by coverage status."""
    entries: list[StrategyInstance] = []
    for variant in VENUE_SET_VARIANTS:
        family = ARCHETYPE_TO_FAMILY.get(variant.archetype)
        if family is None:
            continue
        cells = _cells_by_instrument(variant.archetype)
        coverage = _variant_coverage_status(variant, cells)
        if coverage is CoverageStatus.BLOCKED:
            continue
        for share_class in _DEFAULT_SHARE_CLASSES:
            instance_id = compute_instance_id(
                family=family,
                archetype=variant.archetype,
                venue_set_variant_id=variant.id,
                instrument_type_set=variant.instrument_types,
                share_class=share_class,
            )
            entries.append(
                StrategyInstance(
                    instance_id=instance_id,
                    family=family,
                    archetype=variant.archetype,
                    venue_set_variant_id=variant.id,
                    instrument_type_set=variant.instrument_types,
                    share_class=share_class,
                    coverage_status=coverage,
                )
            )
    return entries


STRATEGY_INSTANCE_CATALOGUE = StrategyInstanceCatalogue()
"""Module-level 5-dim catalogue singleton — import this for UI/admin lookups."""
