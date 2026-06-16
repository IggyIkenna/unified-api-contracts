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
"""

from __future__ import annotations

import logging
from collections.abc import Hashable
from enum import StrEnum

from unified_api_contracts.canonical.crosscutting._source_priority_data import (
    BATCH_CAPABLE_CEFI_VENUES,
    CEFI_LIVE_VENUES,
    COMPUTED_SOURCES,
    EMISSION_LATENCY_MS_BY_SOURCE,
    MOCK_SOURCE,
    SOURCE_MODE_CAPABILITY,
    SOURCE_PRIORITY,
)
from unified_api_contracts.canonical.crosscutting.pipeline_mode import (
    Mode,
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


def get_source_priority(asset_group: str, data_type: str) -> list[str]:
    """Return the ordered source list for a ``(asset_group, data_type)`` pair.

    Returns a copy so callers cannot mutate the registry.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / ``prediction``
            / ``sports`` / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        Ordered list of source keys. Top entry is primary (the
        live-time-winning source).

    Raises:
        KeyError: If the pair is not registered. Failing loud is intentional
            — silent fallback would mask schema-drift bugs.
    """
    key = (asset_group, data_type)
    if key not in SOURCE_PRIORITY:
        msg = (
            f"No source priority registered for "
            f"asset_group={asset_group!r}, data_type={data_type!r}. "
            "Register the pair in SOURCE_PRIORITY before use."
        )
        raise KeyError(msg)
    return list(SOURCE_PRIORITY[key])


def get_primary_source(asset_group: str, data_type: str) -> str:
    """Return the primary (top-of-list) source key for a pair.

    Convenience for callers that don't need the full list — most stamping
    helpers just need the live-time source name to compute available_at.
    """
    return get_source_priority(asset_group, data_type)[0]


def has_source_priority(asset_group: str, data_type: str) -> bool:
    """Check whether the pair is registered (non-raising membership test)."""
    return (asset_group, data_type) in SOURCE_PRIORITY


def modes_for_source(source: str) -> frozenset[Mode]:
    """Return the set of :class:`Mode`s ``source`` can run. ``mock`` ⇒ all modes
    (a fixture can stand in for any). Unregistered external source ⇒ ``{BATCH}``
    (the safe default — everything is at least batch-archivable).

    The per-source mode sets are RATIFIED + load-bearing (the
    ``source_mode_capability_matrix_2026_06_07.md`` rows). The REMAINING
    refinement (next tranche) is the per-``(source, data_type)`` KEYING — e.g.
    hyperliquid is LIVE for ``trades``/``l2_book`` (``ws_*`` ops) but REST/BATCH
    for ``funding_rates`` — to be added as ``modes_for(source, data_type)``
    derived from ``registry/capability_declarations`` ``SourceCapability``
    (per-operation REST/WS). SSOT:
    ``pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md``
    § M2 REFINEMENT."""
    if source == MOCK_SOURCE:
        return frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY})
    return SOURCE_MODE_CAPABILITY.get(source, frozenset({Mode.BATCH}))


def source_supports(source: str, mode: Mode) -> bool:
    """True if ``source`` can run in reconciliation ``mode`` (M2 guardrail)."""
    return mode in modes_for_source(source)


def sources_supporting(mode: Mode) -> set[str]:
    """All registered sources capable of ``mode`` (e.g. the replay-capable set)."""
    return {src for src, modes in SOURCE_MODE_CAPABILITY.items() if mode in modes}


def external_sources_for(asset_group: str, data_type: str) -> list[str]:
    """Return the external-vendor sources for a cell (computed sources removed).

    A cell's :data:`SOURCE_PRIORITY` list may mix external vendors with
    internal computed emitters (see :data:`COMPUTED_SOURCES`). This returns
    only the external entries, preserving priority order. Empty list when the
    pair is unregistered OR every source is a computed/service emitter.
    """
    return [s for s in SOURCE_PRIORITY.get((asset_group, data_type), ()) if s not in COMPUTED_SOURCES]


def source_required(asset_group: str, data_type: str) -> bool:
    """Return True when the writer MUST be *passed* an explicit ``source``.

    SSOT for the multi-source disambiguation half of the writer-side gate in
    ``unified_trading_library.manifest_writer`` (record_captured / add). A cell
    requires an explicit source ONLY when it has **more than one external
    source** — because the writer cannot otherwise know which provider served
    the row.

    Single-source external cells do NOT require an explicit source: the writer
    auto-stamps the sole registered external source via :func:`default_source`
    (universal stamping — every external cell carries ``source`` for
    swap-resilience, per the 2026-06-01 operator decision). Computed/service
    cells (:data:`COMPUTED_SOURCES`) and unregistered pairs are exempt.

    * TradFi ``trades`` (databento + massive)        → True (explicit needed)
    * DeFi ``oracle_prices`` (pyth_hermes+chainlink) → True
    * DeFi ``native_staking_rates`` (solana+helius)  → True
    * Sports ``FIXTURES`` (api_football+footystats)  → True
    * CeFi ``trades`` (tardis)                        → False (auto-stamped)
    * Prediction ``trades`` (polymarket_clob)         → False (auto-stamped)
    * DeFi ``execution_fills`` (execution_service)    → False (computed-exempt)
    * Unregistered pair                               → False

    Args:
        asset_group: ``cefi`` / ``defi`` / ``tradfi`` / ``prediction`` /
            ``sports`` / ``reference``. (The writer passes its ``category``.)
        data_type: Canonical data_type string.

    Returns:
        ``True`` iff the pair has >1 external source.
    """
    return len(external_sources_for(asset_group, data_type)) > 1


def default_source(asset_group: str, data_type: str) -> str | None:
    """Return the auto-stampable source for a single-source external cell.

    Universal-stamping helper (``data_source_provenance_all_asset_groups_2026_06_01.md``):
    when a cell has exactly **one** external source, the writer auto-stamps it
    so the row carries provenance even though only one vendor exists today
    (swap-resilience — when a 2nd vendor or a replacement lands, pre-existing
    rows stay distinguishable from the new source).

    Returns:
        The sole external source string when the cell has exactly one external
        source; ``None`` when the cell is multi-source (caller must pass an
        explicit source), computed/service-only, or unregistered (nothing to
        auto-stamp).
    """
    external = external_sources_for(asset_group, data_type)
    return external[0] if len(external) == 1 else None


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
      (``pipeline_mode=PipelineMode.LIVE_WEBSOCKET``) win over batch rows
      with the same row-key.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / ``prediction``
            / ``sports`` / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        Tuple of ``(primary_source_string, pipeline_mode)``. ``pipeline_mode``
        is always a batch value (e.g. :attr:`PipelineMode.BATCH_TARDIS`); the
        live mode :attr:`PipelineMode.LIVE_WEBSOCKET` is set by the streaming
        writer at write-time, not derived from this registry.

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


def live_source_for_venue(asset_group: str, venue: str, data_type: str) -> str:
    """Resolve the LIVE/REPLAY ``source`` string that serves a ``(asset_group, venue,
    data_type)`` shard.

    The live writer has ``(asset_group, venue, data_type)`` in scope but stamps the
    source-aware ``live_<source>`` / ``replay_<source>`` ``pipeline_mode`` — so it
    needs the SOURCE, not the venue. The mapping is asset-group-shaped (M2/M3 model,
    ``pipeline_mode.py`` CeFi-venue block):

    * **CeFi**: ``live``/``replay`` source IS the EXCHANGE (the ``venue``) — Tardis is
      the CeFi *batch* archive, never the live source. So a CeFi venue in
      :data:`CEFI_LIVE_VENUES` resolves to ``venue`` itself (lowercased).
    * **Every other asset_group** (defi / tradfi / prediction / sports / reference):
      the live source is the :data:`SOURCE_PRIORITY` PRIMARY source for the cell —
      the same vendor serves batch + live (e.g. ``databento`` live ticks). When the
      pair is unregistered, fall back to the normalised ``venue`` (a vendor venue
      whose name IS its source, e.g. ``chainlink`` / ``pyth_hermes``).

    The returned string is a VENDOR source (operator R4 — never a transport-glued
    name). Pair with :func:`pipeline_mode_for_source` ``(source, Mode.LIVE|REPLAY)``
    to obtain the concrete :class:`PipelineMode`.

    Args:
        asset_group: ``cefi`` / ``defi`` / ``tradfi`` / ``prediction`` / ``sports`` /
            ``reference`` (case-insensitive).
        venue: The shard venue (e.g. ``BINANCE`` / ``DATABENTO`` — any case).
        data_type: Canonical data_type string.

    Returns:
        The vendor ``source`` string for the live/replay shard.
    """
    venue_norm = venue.lower()
    ag_norm = asset_group.lower()
    if ag_norm == "cefi" and venue_norm in CEFI_LIVE_VENUES:
        return venue_norm
    if has_source_priority(ag_norm, data_type):
        return get_primary_source(ag_norm, data_type)
    # Unregistered pair: the venue name IS the vendor source for the per-vendor
    # asset_groups (chainlink / pyth_hermes / solana_rpc / ...).
    return venue_norm


def live_pipeline_mode_for_venue(
    asset_group: str,
    venue: str,
    data_type: str,
    mode: Mode = Mode.LIVE,
) -> PipelineMode:
    """Resolve the source-aware ``live_<source>`` / ``replay_<source>`` :class:`PipelineMode`
    for a ``(asset_group, venue, data_type)`` shard.

    The M1 migration target for live writers: replaces the single
    ``PipelineMode.LIVE_WEBSOCKET`` literal with the source-aware value. Composes
    :func:`live_source_for_venue` (venue→source) with
    :func:`pipeline_mode_for_source` ``(source, mode)``.

    Args:
        asset_group: ``cefi`` / ``defi`` / ``tradfi`` / ``prediction`` / ``sports`` /
            ``reference`` (case-insensitive).
        venue: The shard venue (any case).
        data_type: Canonical data_type string.
        mode: :attr:`Mode.LIVE` (default) or :attr:`Mode.REPLAY`.

    Returns:
        The concrete ``live_<source>`` / ``replay_<source>`` :class:`PipelineMode`.

    Raises:
        ValueError: when the resolved source has no ``{mode}_<source>``
            :class:`PipelineMode` member (the source does not support that mode per
            :data:`SOURCE_MODE_CAPABILITY`, or the source string is misspelled) —
            delegated from :func:`pipeline_mode_for_source`.
    """
    source = live_source_for_venue(asset_group, venue, data_type)
    return pipeline_mode_for_source(source, mode)


__all__ = [
    "BATCH_CAPABLE_CEFI_VENUES",
    "CEFI_LIVE_VENUES",
    "COMPUTED_SOURCES",
    "EMISSION_LATENCY_MS_BY_SOURCE",
    "SOURCE_PRIORITY",
    "DivergenceKind",
    "assert_emission_latency_round_trip",
    "default_source",
    "detect_dual_source_conflicts",
    "emission_latency_ms_for_source",
    "external_sources_for",
    "get_all_sources_with_priority",
    "get_primary_source",
    "get_primary_source_with_latency",
    "get_source_priority",
    "has_source_priority",
    "live_pipeline_mode_for_venue",
    "live_source_for_venue",
    "read_with_source_priority",
    "select_primary_available_source",
    "source_required",
]
