"""Per-(asset_group, data_type) source priority registry.

SSOT for the ordered list of source keys that may serve a given
``(asset_group, data_type)``. The top entry is the primary — the source
whose emission time defines ``available_at`` for live and batch (per the
workspace ``Live = batch`` rule).

Per the workspace CLAUDE.md ``Live = batch — same data, same fields,
same timing semantics, different sources OK`` rule:

> Historical writes MUST be timestamped with the ``available_at`` we'd
> actually have in live mode (the ``SOURCE_PRIORITY`` top entry's
> emission time, NOT the canonical historical source's slower archive
> time).

Phase 2 (multi-source merge) is implemented in
``plans/active/tradfi_massive_dual_source_2026_05_28.md`` (archived once
complete). The helpers :func:`get_all_sources_with_priority`,
:func:`select_primary_available_source`, and
:func:`detect_dual_source_conflicts` land the merge-logic building blocks.
The ``multi_source_priority_merge_2026_*`` placeholder is resolved.

Tie-breaker rules (when multiple sources are listed):

1. **Timestamp-availability** — sources that emit at live-time win over
   archive-only sources.
2. **Coverage** — sources with broader date / instrument coverage win.
3. **Information richness** — sources with more fields per row win.
4. **Merge-different-fields** — when two sources cover non-overlapping
   field sets, both stay in the list and consumers union.

The :data:`SOURCE_PRIORITY` registry below records the *single
authoritative source* for each pair today. When a second source becomes
available for the same pair, the writer-side merge logic must land
before the dict gets a multi-entry list (otherwise live=batch breaks).

Phase 1C (2026-05-08) — ``pipeline_mode`` per-source mapping
============================================================

Per ``gcs_migration_bundle_pipeline_mode_2026_05_08`` Phase 1C, each row
selected via :func:`read_with_source_priority` returns ``(source,
pipeline_mode)`` so downstream consumers know which on-disk
``pipeline_mode=`` partition serves the row, enabling the batch-vs-live
reconciliation gate in
``live_pipeline_mtds_mdps_features_2026_05_08`` Phase 12.

**Design choice — Option B (chosen over Option A).** ``pipeline_mode``
is a property of the *source string itself*, not of the
``(asset_group, data_type, source)`` triple — every source has
exactly one batch ``PipelineMode`` value via the closed-set round-trip
already enforced in
:mod:`unified_api_contracts.canonical.crosscutting.pipeline_mode`. So
rather than restructuring :data:`SOURCE_PRIORITY`'s value type from
``list[str]`` to ``list[SourcePriorityEntry]`` (Option A), we keep the
existing shape and look up the ``PipelineMode`` for each source via the
existing :func:`pipeline_mode_for_source` helper. This:

* Avoids breaking every existing consumer of ``list[str]`` semantics.
* Composes with the existing closed-set test
  (``tests/unit/test_pipeline_mode.py``) which already asserts every
  source string in ``SOURCE_PRIORITY`` round-trips to a
  ``PipelineMode``.
* Keeps the SSOT surface narrow — adding new sources = one entry in
  ``SOURCE_PRIORITY`` + one ``PipelineMode`` member, not two coupled
  mutations of the same triple.

The :func:`read_with_source_priority` reader returned tuple is
``(source, pipeline_mode)`` and the live-priority-over-batch behaviour
is enforced by callers stratifying rows by ``pipeline_mode`` first
(live wins if a live row exists for the same
``(asset_group, venue, day)``); the SSOT lookup itself returns the
single primary batch source.

Module layout (900-line file-size QG split, 2026-07-09; pure
file-organization move, no behavior change — every name below is
re-exported here unchanged so the public import path
``unified_api_contracts.canonical.crosscutting.source_priority`` is
byte-identical for every caller):
    * ``_source_priority_core.py``        — ``get_source_priority`` /
      ``get_primary_source`` / ``has_source_priority`` (dependency-free
      foundation every other submodule builds on).
    * ``_source_priority_capability.py``  — ``modes_for`` /
      ``modes_for_source`` / ``source_supports`` / ``sources_supporting``
      (per-source and per-(source, data_type) :class:`Mode` resolution).
    * ``_source_priority_provenance.py``  — external-source enumeration
      (``external_sources_for`` / ``source_required`` / ``default_source``
      / ``valid_manifest_sources`` / ``is_valid_manifest_source``) + the
      live/replay venue → source resolver (``live_source_for_venue`` /
      ``live_pipeline_mode_for_venue``).
"""

from __future__ import annotations

import logging
from collections.abc import Hashable
from enum import StrEnum

from unified_api_contracts.canonical.crosscutting._source_priority_capability import (
    modes_for,
    modes_for_source,
    source_supports,
    sources_supporting,
)
from unified_api_contracts.canonical.crosscutting._source_priority_core import (
    get_primary_source,
    get_source_priority,
    has_source_priority,
)
from unified_api_contracts.canonical.crosscutting._source_priority_data import (
    BATCH_CAPABLE_CEFI_VENUES,
    CEFI_LIVE_VENUES,
    COMPUTED_SOURCES,
    EMISSION_LATENCY_MS_BY_SOURCE,
    MOCK_SOURCE,
    SOURCE_MODE_CAPABILITY,
    SOURCE_PRIORITY,
)
from unified_api_contracts.canonical.crosscutting._source_priority_provenance import (
    default_source,
    external_sources_for,
    is_valid_manifest_source,
    live_pipeline_mode_for_venue,
    live_source_for_venue,
    source_required,
    valid_manifest_sources,
)
from unified_api_contracts.canonical.crosscutting.pipeline_mode import (
    PipelineMode,
    pipeline_mode_for_source,
)

logger = logging.getLogger(__name__)


class DivergenceKind(StrEnum):
    """Closed-set reasons a manifest row is flagged as a cross-source divergence.

    Written into the manifest ``divergence_kind`` column (nullable; ``None``
    means no divergence). Per Phase 2 of
    ``tradfi_massive_dual_source_2026_05_28.md``:

    * ``DUAL_SOURCE_DUPLICATE`` — the same ``(asset_group, venue, day, ticker,
      ts)`` row-key appears in two or more sources. The sources agree on the
      key but may differ on values (price, volume). Logged + counted; do NOT
      silently drop either source's row — downstream reconciliation decides
      the winner via :func:`select_primary_available_source`.

    Future values (extend this enum, do NOT add bare strings):
    * ``TEMPORAL_GAP`` — source A has the day; source B is absent.
    * ``FIELD_UNION`` — sources have non-overlapping field sets (rule 4 of
      the tie-breaker docstring); consumer unions both rows.
    """

    DUAL_SOURCE_DUPLICATE = "DUAL_SOURCE_DUPLICATE"


def emission_latency_ms_for_source(source: str) -> int:
    """Return the live-emission latency (ms) for ``source``.

    Args:
        source: A source string from :data:`SOURCE_PRIORITY` (e.g. ``"tardis"``,
            ``"databento"``, ``"api_football"``).

    Returns:
        Latency in milliseconds — wall-clock delta from event-at-source to
        row-in-pipeline.

    Raises:
        KeyError: If the source is not registered in
            :data:`EMISSION_LATENCY_MS_BY_SOURCE`. Failing loud is intentional —
            silent fallback would mask schema-drift bugs in the closed-set
            round-trip with :data:`SOURCE_PRIORITY`.
    """
    if source not in EMISSION_LATENCY_MS_BY_SOURCE:
        msg = (
            f"No emission latency registered for source={source!r}. "
            f"Add an entry to EMISSION_LATENCY_MS_BY_SOURCE before use. "
            f"Every source in SOURCE_PRIORITY must have a latency entry "
            f"(closed-set round-trip rule)."
        )
        raise KeyError(msg)
    return EMISSION_LATENCY_MS_BY_SOURCE[source]


def get_primary_source_with_latency(
    asset_group: str,
    data_type: str,
) -> tuple[str, int]:
    """Return ``(primary_source, emission_latency_ms)`` for an ``(asset_group, data_type)``.

    The latency-aware companion to :func:`get_primary_source`. Stamping helpers
    use this to compute ``available_at = tick_event_time + latency_ms`` per the
    live=batch invariant.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / ``prediction``
            / ``sports`` / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        Tuple of ``(primary_source_string, emission_latency_ms)``.

    Raises:
        KeyError: If the ``(asset_group, data_type)`` pair is not registered
            (delegated from :func:`get_primary_source`) OR if the primary source
            has no latency entry (delegated from
            :func:`emission_latency_ms_for_source`). Both raise paths are
            prevented in CI by :func:`assert_emission_latency_round_trip`.
    """
    primary_source = get_primary_source(asset_group, data_type)
    latency_ms = emission_latency_ms_for_source(primary_source)
    return primary_source, latency_ms


def assert_emission_latency_round_trip() -> None:
    """Closed-set round-trip: every SOURCE_PRIORITY source has a latency entry.

    Mirrors :func:`pipeline_mode.assert_pipeline_mode_source_priority_round_trip`.
    Wired into the UAC unit-test suite via
    ``tests/unit/test_source_priority.py::test_emission_latency_round_trip``.

    Raises:
        AssertionError: If any source in :data:`SOURCE_PRIORITY` is missing from
            :data:`EMISSION_LATENCY_MS_BY_SOURCE`, or if any latency entry refers
            to a source not used in :data:`SOURCE_PRIORITY`.
    """
    sources_in_priority: set[str] = set()
    for source_list in SOURCE_PRIORITY.values():
        sources_in_priority.update(source_list)
    sources_in_latency: set[str] = set(EMISSION_LATENCY_MS_BY_SOURCE.keys())

    missing_latency = sources_in_priority - sources_in_latency
    if missing_latency:
        msg = (
            f"Sources in SOURCE_PRIORITY without emission latency entries: "
            f"{sorted(missing_latency)}. Add to EMISSION_LATENCY_MS_BY_SOURCE."
        )
        raise AssertionError(msg)

    orphan_latency = sources_in_latency - sources_in_priority
    if orphan_latency:
        msg = (
            f"Sources in EMISSION_LATENCY_MS_BY_SOURCE not used in SOURCE_PRIORITY: "
            f"{sorted(orphan_latency)}. Remove orphan latency entries or wire the "
            f"source into SOURCE_PRIORITY."
        )
        raise AssertionError(msg)


def read_with_source_priority(
    asset_group: str,
    data_type: str,
) -> tuple[str, PipelineMode]:
    """Return ``(primary_source, pipeline_mode)`` for an ``(asset_group, data_type)``.

    The pipeline-mode-aware companion to :func:`get_primary_source`. Per Phase 1C
    of ``gcs_migration_bundle_pipeline_mode_2026_05_08``, every read of the
    primary source is paired with the source's batch :class:`PipelineMode` so
    callers can:

    * Tag rows with the on-disk ``pipeline_mode=`` hive partition value
      (matches the partition the migration bundle writes).
    * Stratify batch-vs-live reconciliation in
      ``live_pipeline_mtds_mdps_features_2026_05_08`` Phase 12 — live rows
      (the source-aware ``live_<source>`` pipeline_mode) win over batch rows
      with the same row-key.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / ``prediction``
            / ``sports`` / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        Tuple of ``(primary_source_string, pipeline_mode)``. ``pipeline_mode``
        is always a batch value (e.g. :attr:`PipelineMode.BATCH_TARDIS`); the
        source-aware live pipeline_mode (``live_<source>``) is set by the
        streaming writer at write-time, not derived from this registry.

    Raises:
        KeyError: If the ``(asset_group, data_type)`` pair is not registered
            in :data:`SOURCE_PRIORITY` (delegated from
            :func:`get_primary_source`).
        ValueError: If the primary source string has no corresponding
            :class:`PipelineMode` value — closed-set round-trip violation.
            Existing test
            ``tests/unit/test_pipeline_mode.py::test_every_source_priority_source_has_pipeline_mode``
            prevents this from firing in CI.
    """
    primary_source = get_primary_source(asset_group, data_type)
    pipeline_mode = pipeline_mode_for_source(primary_source)
    return primary_source, pipeline_mode


def detect_dual_source_conflicts(
    source_a: str,
    keys_a: set[tuple[Hashable, ...]],
    source_b: str,
    keys_b: set[tuple[Hashable, ...]],
    *,
    asset_group: str,
    data_type: str,
) -> list[tuple[Hashable, ...]]:
    """Return row keys present in both source_a and source_b.

    Per Phase 2 of ``tradfi_massive_dual_source_2026_05_28.md`` conflict
    detection: when the same ``(asset_group, venue, day, ticker, ts)``
    row-key appears in two sources, this function detects the overlap, logs
    the count at WARNING level, and returns the duplicate keys so callers can
    emit ``divergence_kind=DUAL_SOURCE_DUPLICATE`` into the manifest.

    DO NOT silently drop either source's row — downstream reconciliation
    (e.g. :func:`select_primary_available_source`) decides which source wins.

    Args:
        source_a: First source string (e.g. ``"databento"``).
        keys_a: Set of row-key tuples for source_a (e.g.
            ``{(venue, day, ticker, ts), ...}``). Any hashable tuple shape is
            accepted — the caller owns the row-key definition.
        source_b: Second source string (e.g. ``"massive"``).
        keys_b: Set of row-key tuples for source_b.
        asset_group: Used in log messages only.
        data_type: Used in log messages only.

    Returns:
        Sorted list of row-key tuples present in both ``keys_a`` and
        ``keys_b``. Empty list when there are no conflicts.
    """
    duplicates = keys_a & keys_b
    if duplicates:
        logger.warning(
            "DUAL_SOURCE_DUPLICATE: %d row-key(s) in (%s, %s) appear in both "
            "source=%r and source=%r. Mark manifest rows with "
            "divergence_kind=DUAL_SOURCE_DUPLICATE. Sample (up to 3): %s",
            len(duplicates),
            asset_group,
            data_type,
            source_a,
            source_b,
            sorted(duplicates)[:3],
        )
    return sorted(duplicates)


def select_primary_available_source(
    asset_group: str,
    data_type: str,
    available_sources: set[str],
) -> tuple[str, PipelineMode]:
    """Return the highest-priority available source for ``(asset_group, data_type)``.

    Applies the Phase 2 tie-breaker rules from the module docstring in priority
    order. The :data:`SOURCE_PRIORITY` list encodes the tie-breaker: index 0 is
    the winner when all sources are present. When only a subset is available
    (e.g. Databento has a gap but Massive has the day), this function falls
    through to the next registered source.

    Tie-breaker rules (in order):

    1. **Timestamp-availability** — sources that emit at live-time win
       (encoded as lower emission latency in :data:`EMISSION_LATENCY_MS_BY_SOURCE`).
    2. **Coverage** — broader date / instrument coverage wins.
    3. **Information richness** — more fields per row wins.
    4. **Merge-different-fields** — non-overlapping field sets: callers
       *union* rather than pick, so both sources remain in
       :data:`SOURCE_PRIORITY` (handled at the consumer / writer layer,
       not here).

    Rules 1-3 are resolved at registry-design time by the ordering in
    :data:`SOURCE_PRIORITY`; this helper enforces that ordering at runtime
    when not all sources have data.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / etc.
        data_type: Canonical data_type string.
        available_sources: Set of source strings that have data for the
            requested ``(asset_group, data_type, day)`` cell (e.g. from
            a manifest query or filesystem scan).

    Returns:
        ``(source_string, pipeline_mode)`` for the highest-priority source
        found in ``available_sources``.

    Raises:
        KeyError: If ``(asset_group, data_type)`` is not registered, OR if
            none of the registered sources appear in ``available_sources``.
    """
    priority_list = get_source_priority(asset_group, data_type)
    for source in priority_list:
        if source in available_sources:
            return source, pipeline_mode_for_source(source)
    raise KeyError(
        f"No registered source for ({asset_group!r}, {data_type!r}) is available. "
        f"Registered (priority order): {priority_list}. "
        f"Available: {sorted(available_sources)}."
    )


def get_all_sources_with_priority(
    asset_group: str,
    data_type: str,
) -> list[tuple[str, PipelineMode]]:
    """Return all registered sources for ``(asset_group, data_type)`` in priority order.

    Phase 2 of ``tradfi_massive_dual_source_2026_05_28.md`` — multi-source
    merge building block. Unlike :func:`read_with_source_priority` (which
    returns only the primary source), this function returns the full ordered
    list so callers can:

    * Iterate over all available sources for a cell (e.g. ``databento`` +
      ``massive`` for TradFi trades).
    * Apply tie-breaker logic at the consumer layer (timestamp-availability
      → coverage → information richness → field-union per module docstring).
    * Detect conflicts when the same ``(ticker, ts)`` appears in multiple
      source parquets.

    The returned list is ordered by priority (index 0 = highest priority,
    the same as ``read_with_source_priority`` returns). Each element pairs
    the source string with its batch :class:`PipelineMode`.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / ``prediction``
            / ``sports`` / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        Ordered list of ``(source_string, pipeline_mode)`` tuples, highest
        priority first. Always non-empty (enforced by
        ``test_every_source_priority_entry_has_at_least_one_source``).

    Raises:
        KeyError: If the ``(asset_group, data_type)`` pair is not registered
            in :data:`SOURCE_PRIORITY`.
        ValueError: If any source string in the list has no corresponding
            :class:`PipelineMode` — closed-set round-trip violation prevented
            in CI by ``test_every_source_priority_source_round_trips_to_pipeline_mode``.
    """
    sources = get_source_priority(asset_group, data_type)
    return [(source, pipeline_mode_for_source(source)) for source in sources]


# ---------------------------------------------------------------------------
# Venue → source capability (write-time provenance fail-closed validation)
# ---------------------------------------------------------------------------
# SOURCE_PRIORITY[(asset_group, data_type)] is the READ-TIME resolution ORDER —
# never the WRITE-TIME provenance stamp (operator 2026-06-19). A backfill that
# fetches a shard with a chosen vendor MUST stamp THAT vendor; using
# SOURCE_PRIORITY[0] to stamp mis-attributes data (the VX/CFE incident: Databento
# fetched CFE, but priority[0]=massive mis-stamped it batch_massive, and Massive
# carries NOTHING on CFE).
#
# Most venues can be served by any source in SOURCE_PRIORITY for the data_type,
# but a few are NARROWER than the data_type-level priority list: a venue may have
# NO coverage from a source that otherwise serves the data_type. This map records
# the per-venue EXCLUSIONS (source physically cannot serve this venue x data_type),
# so the ``--source`` selector validator can fail closed before a single byte is
# fetched-or-mis-stamped. Keys are (UPPER_VENUE, data_type); value = sources that
# are NOT capable for that cell (subset of SOURCE_PRIORITY[(ag, dt)]).
#
# CBOE (Cboe Futures Exchange / VX-VIX futures): Massive carries no CFE data
# (issue massive_does_not_carry_vix_vx_futures_cfe_2026_06_17.md) → only Databento
# is capable. This MIRRORS the UTL ``_VENUE_DT_OVERRIDES`` (CBOE ohlcv_1m/1s →
# batch_databento) so the validator and the write-stamp agree.
# SSOT: codex/02-data/tradfi-databento-sourcing-ssot.md.
_VENUE_SOURCE_EXCLUSIONS: dict[tuple[str, str], frozenset[str]] = {
    ("CBOE", "ohlcv_1m"): frozenset({"massive"}),
    ("CBOE", "ohlcv_1s"): frozenset({"massive"}),
    ("CBOE", "trades"): frozenset({"massive"}),
    ("CBOE", "tbbo"): frozenset({"massive"}),
    # KRX (Korea Exchange) single stocks are Yahoo-ONLY (2026-06-24) — neither
    # databento nor massive carry KRX. Exclude both so the write-time --source
    # selector resolves KRX cells to ``yahoo`` and a stray --source databento/
    # massive fails closed (SourceNotCapableForVenueError) rather than mis-stamping.
    ("KRX", "ohlcv_1m"): frozenset({"databento", "massive"}),
    ("KRX", "ohlcv_15m"): frozenset({"databento", "massive"}),
    ("KRX", "ohlcv_24h"): frozenset({"databento", "massive"}),
}


class SourceNotCapableForVenueError(ValueError):
    """Raised when a chosen ``source`` cannot serve a ``(asset_group, venue,
    data_type)`` cell — fail-closed before fetch/stamp.

    Two failure modes:

    * the source is not in ``SOURCE_PRIORITY[(asset_group, data_type)]`` at all
      (the data_type is not served by that vendor), OR
    * the source is excluded for the SPECIFIC venue via
      :data:`_VENUE_SOURCE_EXCLUSIONS` (e.g. ``--source massive`` for CBOE/VX
      futures — Massive carries no CFE).
    """


def is_source_capable_for_venue(asset_group: str, data_type: str, venue: str, source: str) -> bool:
    """Return whether ``source`` can serve a ``(asset_group, venue, data_type)`` cell.

    Capability = ``source ∈ SOURCE_PRIORITY[(asset_group, data_type)]`` AND
    ``source`` is not excluded for the venue via
    :data:`_VENUE_SOURCE_EXCLUSIONS`. Used by the write-time ``--source`` selector
    to drive both fetch-adapter selection and the provenance stamp; never consults
    priority ORDER (that is read-time only).

    Returns ``False`` (never raises) when the ``(asset_group, data_type)`` pair is
    unregistered — call :func:`assert_source_capable_for_venue` to get the loud
    diagnostic.
    """
    ag = asset_group.lower()
    src = source.lower()
    if not has_source_priority(ag, data_type):
        return False
    if src not in {s.lower() for s in get_source_priority(ag, data_type)}:
        return False
    excluded = _VENUE_SOURCE_EXCLUSIONS.get((venue.upper(), data_type), frozenset())
    return src not in excluded


def assert_source_capable_for_venue(asset_group: str, data_type: str, venue: str, source: str) -> None:
    """Fail-closed: raise :class:`SourceNotCapableForVenueError` if ``source``
    cannot serve the ``(asset_group, venue, data_type)`` cell.

    The write-time validator behind the MTDS OHLCV backfill ``--source`` selector:
    the operator picks ``databento`` / ``massive`` and this asserts the choice is
    physically capable BEFORE any fetch or provenance stamp, so a mis-stamp (the
    VX/CFE ``batch_massive`` incident) is impossible. SOURCE_PRIORITY stays the
    READ-time resolution order; this is the WRITE-time gate.

    Raises:
        SourceNotCapableForVenueError: source not in SOURCE_PRIORITY for the
            data_type, or excluded for this venue.
    """
    ag = asset_group.lower()
    src = source.lower()
    if not has_source_priority(ag, data_type):
        raise SourceNotCapableForVenueError(
            f"No SOURCE_PRIORITY registered for asset_group={ag!r}, data_type={data_type!r}; "
            f"cannot validate --source={source!r} for venue={venue!r}."
        )
    registered = {s.lower() for s in get_source_priority(ag, data_type)}
    if src not in registered:
        raise SourceNotCapableForVenueError(
            f"--source={source!r} is not a registered source for "
            f"({ag!r}, {data_type!r}); capable sources: {sorted(registered)}."
        )
    excluded = _VENUE_SOURCE_EXCLUSIONS.get((venue.upper(), data_type), frozenset())
    if src in excluded:
        raise SourceNotCapableForVenueError(
            f"--source={source!r} cannot serve venue={venue.upper()!r} for "
            f"data_type={data_type!r} (the source carries no data for this venue — "
            f"e.g. Massive has no Cboe/CFE coverage). Use a capable source: "
            f"{sorted(registered - excluded)}. "
            f"SSOT: codex/02-data/tradfi-databento-sourcing-ssot.md."
        )


__all__ = [
    "BATCH_CAPABLE_CEFI_VENUES",
    "CEFI_LIVE_VENUES",
    "COMPUTED_SOURCES",
    "EMISSION_LATENCY_MS_BY_SOURCE",
    "MOCK_SOURCE",
    "SOURCE_MODE_CAPABILITY",
    "SOURCE_PRIORITY",
    "DivergenceKind",
    "SourceNotCapableForVenueError",
    "assert_emission_latency_round_trip",
    "assert_source_capable_for_venue",
    "default_source",
    "detect_dual_source_conflicts",
    "emission_latency_ms_for_source",
    "external_sources_for",
    "get_all_sources_with_priority",
    "get_primary_source",
    "get_primary_source_with_latency",
    "get_source_priority",
    "has_source_priority",
    "is_source_capable_for_venue",
    "is_valid_manifest_source",
    "live_pipeline_mode_for_venue",
    "live_source_for_venue",
    "modes_for",
    "modes_for_source",
    "read_with_source_priority",
    "select_primary_available_source",
    "source_required",
    "source_supports",
    "sources_supporting",
    "valid_manifest_sources",
]
