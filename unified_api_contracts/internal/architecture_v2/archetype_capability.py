"""Archetype capability registry — queryable (archetype -> category x instrument) support map.

G1.8 of ``stage-3e-refactor-plan`` / ``uac-registry-gaps.md`` gap #1. Mirrors
the canonical ``unified-trading-system-ui/lib/architecture-v2/coverage.ts``
matrix so Python consumers (strategy-service instruction validation, derivation
engine formulas, service-family scope rules) can ask "which archetypes support
(CeFi, Perp)?" without reaching into UI TypeScript or parsing codex markdown.

SSOT flow:
  ``archetype_capability_manifest.json`` (committed, deterministic serialised
  form)  →  loaded at module import into
  ``ARCHETYPE_CAPABILITY_REGISTRY``  →  UI ``coverage.ts`` regenerated from
  this manifest by ``unified-trading-pm/scripts/propagation/
  sync-archetype-capability-to-ui.sh`` (wired into UI quality-gates so every
  push catches drift).

Codex markdown (`codex/09-strategy/architecture-v2/category-instrument-
coverage.md`) remains the human-authored narrative — a separate parity test
(Phase 10 / future wave) enforces it against this manifest.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from enum import StrEnum
from importlib import resources
from typing import Final

from pydantic import BaseModel, ConfigDict

from unified_api_contracts.internal.architecture_v2.enums import (
    StrategyArchetypeV2,
    StrategyFamilyV2,
    VenueCategoryV2,
)


class ArchetypeInstrumentType(StrEnum):
    """Instrument-type vocabulary used by the capability matrix.

    Intentionally narrower than ``unified_api_contracts._instrument_enums.
    InstrumentType`` — the capability matrix is per-archetype support, not
    per-venue instrument catalogue. See ``coverage.ts`` for the TS mirror.
    """

    SPOT = "spot"
    PERP = "perp"
    DATED_FUTURE = "dated_future"
    OPTION = "option"
    LENDING = "lending"
    STAKING = "staking"
    LP = "lp"
    EVENT_SETTLED = "event_settled"


class CoverageStatus(StrEnum):
    """Per-cell coverage state. ``NOT_APPLICABLE`` is implicit by absence."""

    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"


class RollMode(StrEnum):
    """Roll-mode for cells that touch ``dated_future``.

    ``ROLLING`` = ``-dated-`` slot convention (auto-roll via
    representative-future-service). ``FIXED`` = explicit expiry slot
    ``-fixed-{contract}-``. ``BOTH`` = archetype supports both patterns.
    ``NOT_APPLICABLE`` = archetype doesn't touch dated futures on this cell.
    """

    ROLLING = "rolling"
    FIXED = "fixed"
    BOTH = "both"
    NOT_APPLICABLE = "n/a"


class ArchetypeCapabilityCell(BaseModel):
    """One (archetype, category, instrument_type) cell."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    category: VenueCategoryV2
    instrument_type: ArchetypeInstrumentType
    status: CoverageStatus
    venue_ids: tuple[str, ...]
    signal_variants: tuple[str, ...]
    roll_mode: RollMode
    block_list_refs: tuple[str, ...]
    representative_slot_labels: tuple[str, ...]
    notes: str


class ArchetypeCapability(BaseModel):
    """Per-archetype capability row — all its (category, instrument) cells.

    Consumers use the derived frozensets (``supported_pairs`` /
    ``partial_pairs`` / ``blocked_pairs`` / ``supported_venues``) for O(1)
    membership queries. Cells are kept in declaration order to match the
    codex narrative flow.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    archetype_id: StrategyArchetypeV2
    family: StrategyFamilyV2
    uses_rolling_futures: bool
    cells: tuple[ArchetypeCapabilityCell, ...]

    @property
    def supported_pairs(self) -> frozenset[tuple[VenueCategoryV2, ArchetypeInstrumentType]]:
        return frozenset((c.category, c.instrument_type) for c in self.cells if c.status == CoverageStatus.SUPPORTED)

    @property
    def partial_pairs(self) -> frozenset[tuple[VenueCategoryV2, ArchetypeInstrumentType]]:
        return frozenset((c.category, c.instrument_type) for c in self.cells if c.status == CoverageStatus.PARTIAL)

    @property
    def blocked_pairs(self) -> frozenset[tuple[VenueCategoryV2, ArchetypeInstrumentType]]:
        return frozenset((c.category, c.instrument_type) for c in self.cells if c.status == CoverageStatus.BLOCKED)

    @property
    def supported_venues(self) -> frozenset[str]:
        result: set[str] = set()
        for cell in self.cells:
            if cell.status != CoverageStatus.BLOCKED:
                result.update(cell.venue_ids)
        return frozenset(result)


_MANIFEST_FILENAME: Final[str] = "archetype_capability_manifest.json"


def _load_registry() -> tuple[ArchetypeCapability, ...]:
    data = (
        resources.files("unified_api_contracts.internal.architecture_v2")
        .joinpath(_MANIFEST_FILENAME)
        .read_text(encoding="utf-8")
    )
    payload = json.loads(data)
    archetypes = payload["archetypes"]
    return tuple(ArchetypeCapability.model_validate(entry) for entry in archetypes)


ARCHETYPE_CAPABILITY_REGISTRY: Final[tuple[ArchetypeCapability, ...]] = _load_registry()


def capability_for(archetype_id: StrategyArchetypeV2) -> ArchetypeCapability | None:
    """Return the capability row for ``archetype_id`` or ``None`` if absent."""

    for entry in ARCHETYPE_CAPABILITY_REGISTRY:
        if entry.archetype_id == archetype_id:
            return entry
    return None


def all_capabilities() -> tuple[ArchetypeCapability, ...]:
    """Return every registered archetype capability, declaration-ordered."""

    return ARCHETYPE_CAPABILITY_REGISTRY


def archetypes_for_pair(
    category: VenueCategoryV2,
    instrument_type: ArchetypeInstrumentType,
    *,
    include_partial: bool = True,
) -> tuple[ArchetypeCapability, ...]:
    """Return archetypes that support the ``(category, instrument_type)`` pair.

    ``include_partial=True`` (default) includes PARTIAL cells alongside
    SUPPORTED — callers validating whether an instruction can be routed
    generally want both. Pass ``False`` to restrict to SUPPORTED only.
    """

    pair = (category, instrument_type)
    out: list[ArchetypeCapability] = []
    for entry in ARCHETYPE_CAPABILITY_REGISTRY:
        if pair in entry.supported_pairs or (include_partial and pair in entry.partial_pairs):
            out.append(entry)
    return tuple(out)


def archetypes_for_venue(venue_id: str) -> tuple[ArchetypeCapability, ...]:
    """Return archetypes declaring ``venue_id`` in any non-BLOCKED cell."""

    return tuple(entry for entry in ARCHETYPE_CAPABILITY_REGISTRY if venue_id in entry.supported_venues)


def iter_cells() -> Iterator[tuple[StrategyArchetypeV2, ArchetypeCapabilityCell]]:
    """Flat iterator over every (archetype, cell) pair. Used by serialisers."""

    for entry in ARCHETYPE_CAPABILITY_REGISTRY:
        for cell in entry.cells:
            yield (entry.archetype_id, cell)


__all__ = [
    "ARCHETYPE_CAPABILITY_REGISTRY",
    "ArchetypeCapability",
    "ArchetypeCapabilityCell",
    "ArchetypeInstrumentType",
    "CoverageStatus",
    "RollMode",
    "all_capabilities",
    "archetypes_for_pair",
    "archetypes_for_venue",
    "capability_for",
    "iter_cells",
]
