"""Era-B legacy-read retirement — closed-set round-trip purge guard.

ERA-B (operator 2026-06-07): ``options_chain`` / ``futures_chain`` are
INSTRUMENT_TYPES (per-underlying chain bundles) captured as ``data_type=trades``,
NOT data_types. The legacy ``data_type=options_chain`` / ``data_type=futures_chain``
entries are RETAINED in the closed-set registries (:data:`SOURCE_PRIORITY` +
:data:`AVAILABILITY_AT_SEMANTICS`) ONLY to (a) parse pre-migration v8 rows and
(b) keep the bidirectional ``SOURCE_PRIORITY`` ↔ ``AVAILABILITY_AT_SEMANTICS``
round-trip closed while both Era-A and Era-B rows coexist.

Per the master coordinator's "Era-B legacy retirement" todo
(``master_data_canonicalisation_migration_catalogue_2026_06_07.md`` — the
``[UAC+MTDS]`` item), each per-AG v8→v9 migrator drops these entries as its FINAL
ATOMIC STEP, right after it relabels the on-disk rows to ``trades``. Dropping them
BEFORE the relabel would loud-fail every read of un-migrated v8 data (the
deployment-api / preflight ``KeyError`` / unknown-DataType heartbeat break), so the
drop is sequenced AFTER, inside the same migrator walk.

This module is the SHARED SAFETY GUARD the per-AG migrators call — at plan-time and
again immediately before the atomic drop — to confirm that removing the legacy
entries does NOT break any closed-set round-trip. It simulates the purge IN-MEMORY
(it NEVER mutates the live registries) and asserts that, post-purge:

1. the bidirectional ``SOURCE_PRIORITY`` ↔ ``AVAILABILITY_AT_SEMANTICS`` symmetry
   still holds (both registries' legacy entries are dropped together);
2. every source that remains still round-trips to a :class:`PipelineMode` and still
   has an emission-latency entry (no source is stranded by the purge);
3. no emission-latency entry is orphaned (no source was used ONLY by the purged
   ``options_chain`` / ``futures_chain`` entries).

A migrator that calls :func:`assert_era_b_purge_safe` before its final atomic drop
can never strand a ``PipelineMode``, an emission-latency entry, or the registry
symmetry. The companion unit test (``tests/unit/test_era_b_purge.py``) proves the
guard passes for the live registries TODAY, so the closed-set is purge-ready.
"""

from __future__ import annotations

from typing import Final

#: The legacy chain ``data_type`` tokens that Era-B retires (they become
#: INSTRUMENT_TYPES captured as ``data_type=trades``).
ERA_B_LEGACY_DATA_TYPES: Final[frozenset[str]] = frozenset({"options_chain", "futures_chain"})

#: The asset_groups whose registries carry the legacy chain ``data_type`` entries.
ERA_B_LEGACY_ASSET_GROUPS: Final[frozenset[str]] = frozenset({"cefi", "tradfi"})

#: The ``(asset_group, data_type)`` keys a per-AG Era-B migrator drops as its final
#: atomic step. Pass an asset_group-scoped subset (e.g. ``{("cefi", ...)}``) to
#: :func:`assert_era_b_purge_safe` to model a single-AG drop; the default models the
#: full fleet-wide purge.
ERA_B_PURGEABLE_KEYS: Final[frozenset[tuple[str, str]]] = frozenset(
    (ag, dt) for ag in ERA_B_LEGACY_ASSET_GROUPS for dt in ERA_B_LEGACY_DATA_TYPES
)


def assert_era_b_purge_safe(
    purge_keys: frozenset[tuple[str, str]] = ERA_B_PURGEABLE_KEYS,
) -> None:
    """Assert dropping ``purge_keys`` keeps every closed-set round-trip intact.

    Simulates the Era-B legacy purge IN-MEMORY (never mutates the live registries)
    and raises :class:`AssertionError` if the drop would break the
    ``SOURCE_PRIORITY`` ↔ ``AVAILABILITY_AT_SEMANTICS`` symmetry, strand a source's
    ``PipelineMode`` / emission-latency entry, or orphan an emission-latency entry.

    Called by each per-AG v8→v9 migrator immediately before the final atomic drop of
    its ``options_chain`` / ``futures_chain`` ``data_type`` entries.

    Args:
        purge_keys: ``(asset_group, data_type)`` keys to model as dropped from BOTH
            :data:`SOURCE_PRIORITY` and :data:`AVAILABILITY_AT_SEMANTICS`. Defaults
            to :data:`ERA_B_PURGEABLE_KEYS` (the full cefi+tradfi legacy set).

    Raises:
        AssertionError: If the purge would break any closed-set round-trip.
    """
    # Imports are local to avoid a module-load import cycle (this module is a thin
    # consumer of the three registries; they must not import it at module load).
    from unified_api_contracts.canonical.crosscutting.availability_semantics import (
        AVAILABILITY_AT_SEMANTICS,
    )
    from unified_api_contracts.canonical.crosscutting.pipeline_mode import (
        pipeline_mode_for_source,
    )
    from unified_api_contracts.canonical.crosscutting.source_priority import (
        EMISSION_LATENCY_MS_BY_SOURCE,
        SOURCE_PRIORITY,
    )

    # In-memory purge of BOTH registries (NEVER mutate the live dicts).
    purged_priority: dict[tuple[str, str], list[str]] = {
        key: sources for key, sources in SOURCE_PRIORITY.items() if key not in purge_keys
    }
    purged_availability: set[tuple[str, str]] = {key for key in AVAILABILITY_AT_SEMANTICS if key not in purge_keys}

    # 1. Bidirectional symmetry survives the purge (both registries dropped together).
    priority_keys = set(purged_priority)
    priority_only = priority_keys - purged_availability
    availability_only = purged_availability - priority_keys
    if priority_only or availability_only:
        raise AssertionError(
            "Era-B purge would break SOURCE_PRIORITY <-> AVAILABILITY_AT_SEMANTICS "
            f"symmetry. SOURCE_PRIORITY-only: {sorted(priority_only)[:10]}; "
            f"AVAILABILITY-only: {sorted(availability_only)[:10]}. Drop the legacy "
            "options_chain/futures_chain entries from BOTH registries together."
        )

    # 2. Every surviving source still round-trips to a PipelineMode + has a latency.
    remaining_sources: set[str] = set()
    for sources in purged_priority.values():
        remaining_sources.update(sources)
    for source in sorted(remaining_sources):
        pipeline_mode_for_source(source)  # raises ValueError on a missing PipelineMode
        if source not in EMISSION_LATENCY_MS_BY_SOURCE:
            raise AssertionError(
                f"Era-B purge would strand source={source!r}: no emission-latency entry survives the legacy drop."
            )

    # 3. No emission-latency entry is orphaned (no source was used ONLY by the purged
    #    entries) — mirrors assert_emission_latency_round_trip on the post-purge set.
    orphan_latency = set(EMISSION_LATENCY_MS_BY_SOURCE) - remaining_sources
    if orphan_latency:
        raise AssertionError(
            f"Era-B purge would orphan emission-latency entries: {sorted(orphan_latency)}. "
            "A source used ONLY by the purged options_chain/futures_chain entries must "
            "have its latency entry dropped in the same atomic migrator step."
        )


__all__ = [
    "ERA_B_LEGACY_ASSET_GROUPS",
    "ERA_B_LEGACY_DATA_TYPES",
    "ERA_B_PURGEABLE_KEYS",
    "assert_era_b_purge_safe",
]
