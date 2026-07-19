"""possible_manifest.py — the canonical *could-exist* manifest SSOT (CF-15).

This module is the **single authority for "what shard keys could maximally exist"**
per asset_group, and the **single SSOT for the canonical GCS path shapes** the
manifest/data lives under. It is the upstream foundation the migration-verification
harness (CF-16…CF-21) consumes:

* the **catalogue-seeded denominator** (``enumerate_expected_universe.py``) crosses
  the IS catalogue against the valid ``(instrument_type x data_type)`` space;
* the **orphan sweep** (GCS→manifest) calls :func:`is_valid_shard_key` to decide
  whether a GCS object's hive-key is inside the valid space (an out-of-space key is
  an orphan / junk, an in-space key with no manifest row is a class-(E) hole);
* the **phantom reconciler** (manifest→GCS) and the orphan sweep both derive their
  GCS prefix templates from :func:`canonical_path_templates` — **NO hand-maintained
  per-consumer ``prefix_tpls``** (the Axis-10 drift bug: a new pipeline_mode source
  silently missing from one consumer's hand-list flips real captured rows to
  ``attempted_failed`` on ``--apply``);
* the deployment-api could-exist denominator reads the same valid space.

**Composition, NOT redeclaration (the "delete deprecated code" rule).** This module
imports + crosses the three pre-existing layers — it does not restate the taxonomy:

1. **Axis names** — :data:`SHARD_AXIS_MATRIX` (``data_status_axis_matrix``): which
   columns are shard axes per (service, asset_group).
2. **Axis value-domains** — :data:`VENUES_BY_ASSET_GROUP` /
   :data:`DATA_TYPES_BY_ASSET_GROUP` + the DeFi ``PROTOCOL_CAPABILITIES`` lazy
   derivation (``market_data_categories``); the external-source registry
   (``source_priority`` / ``pipeline_mode``).
3. **Validity** — :func:`valid_data_types_for_instrument_type` +
   :func:`grain_for_instrument_type` / :func:`bundle_instrument_type_for_leaf`
   (the G1-ENUM ``(instrument_type x data_type)`` matrix + bundle-grain axis).

The single new primitive is :func:`canonical_path_templates`, which **generates**
the ``pipeline_mode=batch_<source>/`` prefixes from the source registry — so a newly
added external source automatically yields a prefix in every consumer, closing the
Axis-10 hand-maintenance hole at the root.

SSOT: ``plans/active/migration_verification_orphan_safety_2026_06_10.md`` (V0/CF-15)
+ ``codex/02-data/availability-manifest-and-data-status.md`` +
``codex/02-data/pipeline-mode-partition.md``.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import NamedTuple

from unified_api_contracts.canonical.crosscutting.pipeline_mode import (
    Mode,
    default_transport_for_source,
    pipeline_mode_for_source,
)
from unified_api_contracts.canonical.crosscutting.source_priority import (
    SOURCE_PRIORITY,
    external_sources_for,
)
from unified_api_contracts.registry.data_status_axis_matrix import (
    CEFI,
    DEFI,
    PREDICTION,
    SPORTS,
    TRADFI,
    get_shard_axes,
)
from unified_api_contracts.registry.market_data_categories import (
    DATA_TYPES_BY_ASSET_GROUP,
    GRAIN_BUNDLE_BY_UNDERLYING,
    VENUES_BY_ASSET_GROUP,
    bundle_instrument_type_for_leaf,
    grain_for_instrument_type,
    valid_data_types_for_instrument_type,
)

logger = logging.getLogger(__name__)

# Asset groups that carry a market-data corpus (sports/prediction included; the
# pseudo-group "shared" is excluded — it has no raw-tick bucket).
POSSIBLE_MANIFEST_ASSET_GROUPS: tuple[str, ...] = (CEFI, DEFI, TRADFI, SPORTS, PREDICTION)

# The market-data service whose shard atom the raw-tick corpus is keyed by. The
# could-exist universe + the GCS path shape are both keyed to this service's axes.
_MARKET_DATA_SERVICE: str = "market-tick-data-service"


# ---------------------------------------------------------------------------
# ShardKey — the could-exist atom (CF-15)
# ---------------------------------------------------------------------------


class ShardKey(NamedTuple):
    """A single point in an asset_group's could-exist manifest space.

    The DATE axis is intentionally NOT part of the key — a ShardKey is the
    venue/instrument/data_type cell; the date axis is crossed in separately by
    the lifecycle-aware enumerator (``enumerate_expected_universe.py``) which owns
    per-instrument ``available_from``/``available_to`` windows. Keeping date out
    of the ShardKey keeps this module lifecycle-free (it answers "could this cell
    exist at all", not "on which days") and avoids double-implementing the
    enumerator's calendar logic.

    Fields mirror the canonical shard axes (``SHARD_AXIS_MATRIX``):

    - ``asset_group`` — lowercase key (cefi/defi/tradfi/sports/prediction).
    - ``venue`` — venue/protocol token; "" for sports (league-grain, venue-less).
    - ``chain`` — DeFi chain key; "" for non-DeFi.
    - ``instrument_type`` — canonical instrument-type token (may be "" where the
      AG's shard atom carries no instrument_type segment, e.g. sports/prediction).
    - ``data_type`` — the market data_type.
    - ``instrument_id`` — the leaf instrument / league_id / canonical_question_group;
      "" at FAMILY grain (when enumerated without a catalogue).
    """

    asset_group: str
    venue: str
    chain: str
    instrument_type: str
    data_type: str
    instrument_id: str = ""


class CatalogueLeaf(NamedTuple):
    """The minimal instrument-lifecycle shape :func:`enumerate_possible_shard_keys`
    needs to bind instrument-grain leaves.

    This is a structural subset of the instruments-service ``InstrumentCatalogEntry``
    (and the ``catalog.parquet`` columns) — any object exposing these attributes is
    accepted (duck-typed), so the IS catalogue rows can be passed directly without a
    cross-repo type import. Date/lifecycle fields are deliberately absent: this module
    enumerates the cell space, not the per-day calendar.
    """

    instrument_id: str
    instrument_type: str
    venue: str
    chain: str = ""
    league_id: str = ""
    underlying: str = ""


# ---------------------------------------------------------------------------
# Canonical GCS path shape per asset_group
# ---------------------------------------------------------------------------
#
# The on-disk hive-segment ORDER after the ``asset_group=`` key, per asset_group.
# Mirrors the market-tick-data-service shard atom (``SHARD_AXIS_MATRIX``) + the
# physical writer layout. ``{placeholder}`` tokens are filled per-row by a consumer
# (the phantom reconciler / orphan sweep), so these are TEMPLATES, not paths.
#   CeFi / TradFi: venue → instrument_type → data_type
#   DeFi:          venue → chain → instrument_type → data_type
#   Sports / Prediction: day-level only (per-league / per-cqg segments vary by
#       source; the sweep substring-matches venue/data_type within the day prefix —
#       sports has its own UAC ``candidate_parquet_paths`` SSOT).
_AG_SEGMENT_SHAPE: dict[str, str] = {
    CEFI: "venue={venue}/instrument_type={instrument_type}/data_type={data_type}/",
    TRADFI: "venue={venue}/instrument_type={instrument_type}/data_type={data_type}/",
    DEFI: "venue={venue}/chain={chain}/instrument_type={instrument_type}/data_type={data_type}/",
    SPORTS: "",
    PREDICTION: "",
}

# The canonical day-prefix every raw-tick object lives under (post Phase-3 migration
# the ``pipeline_mode={mode}_{source}/`` key sits LEFT of ``asset_group=``).
_DAY_PREFIX: str = "raw_tick_data/by_date/day={date}/"

# Transitional / legacy path SHAPES that coexist on disk until the gated per-AG
# migrators rewrite every object (copy-not-move). These are NOT generated from the
# source registry — they are the historical hive vocabularies. A consumer MUST probe
# them too, else real captured rows at a legacy shape false-positive as phantoms /
# orphans (incident log: cefi 130k 2026-05-03; AAVE_V3 29,782 2026-05-07; EIGENLAYER
# 597 2026-05-04). Each entry is appended AFTER the canonical pipeline_mode prefixes.
#   {seg} is filled with the AG segment shape; {date} stays a placeholder.
_LEGACY_SHAPE_TPLS: tuple[str, ...] = (
    # bare asset_group= hive, no pipeline_mode (the on-disk TODAY shape pre-apply)
    "raw_tick_data/by_date/day={date}/asset_group={ag}/{seg}",
    # legacy category= hive (pre asset_group= vocabulary)
    "raw_tick_data/by_date/day={date}/category={ag}/{seg}",
    # top-level day= (older Tardis adapter via build_partition_path, no by_date prefix)
    "day={date}/asset_group={ag}/{seg}",
    "day={date}/category={ag}/{seg}",
)

# DeFi-only extra legacy shapes (the segment differs from the generic {seg}).
_DEFI_EXTRA_LEGACY_TPLS: tuple[str, ...] = (
    # 2024-05-era DeFi paths skipped the asset-group hive segment entirely.
    "raw_tick_data/by_date/day={date}/venue={venue}/chain={chain}/"
    "instrument_type={instrument_type}/data_type={data_type}/",
    # Legacy ``venue=PROTOCOL-CHAIN`` overload (pre-2026-04-29 EIGENLAYER restaking
    # etc.) — combined venue-chain segment, no separate chain= key.
    "raw_tick_data/by_date/day={date}/asset_group=defi/venue={venue}-{chain}/"
    "instrument_type={instrument_type}/data_type={data_type}/",
    "raw_tick_data/by_date/day={date}/category=defi/venue={venue}-{chain}/"
    "instrument_type={instrument_type}/data_type={data_type}/",
)

# Authoritative per-AG batch SOURCE set — the CONSOLIDATED SSOT (CF-15) that
# replaces the hand-maintained ``prefix_tpls`` source lists scattered across the
# phantom reconciler (and the new orphan sweep). This is the de-scatter: ONE place
# names the batch sources that physically write each AG's raw-tick corpus, instead of
# every consumer keeping its own copy (the Axis-10 drift bug).
#
# It is NOT redundant with ``external_sources_for``: that registry encodes data-type
# *provenance priority*, which is only wired for tradfi + prediction today (cefi /
# defi / sports source-provenance are RED gaps — operator 2026-06-01) → deriving
# cefi sources purely from ``SOURCE_PRIORITY`` UNDER-generates (yields only
# ``tardis``, dropping ``databento`` / ``hyperliquid`` → real captured rows would
# false-phantom on ``--apply``). So this map is the floor; the registry derivation is
# UNIONED on top (future-proofing: when cefi/defi provenance lands, new sources
# auto-appear without editing this map). Ground-truth sourced from the migrated
# reconciler ``prefix_tpls`` (verified superset by the unit test).
_KNOWN_BATCH_SOURCES_BY_AG: dict[str, frozenset[str]] = {
    CEFI: frozenset({"databento", "tardis", "hyperliquid"}),
    DEFI: frozenset(
        {"onchain_rpc", "onchain_subgraph", "hyperliquid", "chainlink", "pyth_hermes", "helius_rpc", "solana_rpc"}
    ),
    # NOTE: "massive" is KEPT here even though it was dropped from SOURCE_PRIORITY /
    # SOURCE_MODE_CAPABILITY on 2026-07-19 — the historical ``pipeline_mode=batch_massive/``
    # GCS objects still exist, so possible_manifest MUST keep emitting the batch_massive
    # prefix (via the retained PipelineMode.BATCH_MASSIVE member) or the phantom-audit
    # would flag ~1.47M real objects as orphans. TODO(purge): drop after batch_massive
    # GCS purge (issue tradfi_canonical_path_migration_design_2026_07_19.md § Massive removal).
    TRADFI: frozenset({"databento", "massive", "yahoo", "eia"}),  # barchart retired 2026-06-24
    PREDICTION: frozenset({"polymarket_clob", "polymarket_gamma_api"}),
    # sports has its own UAC ``candidate_parquet_paths`` SSOT — no pipeline_mode prefixes here.
    SPORTS: frozenset(),
}

# Legacy/transitional pipeline_mode SOURCE tokens that coexist on disk but are NOT
# canonical (so neither the registry derivation nor the known-set names them). The R4
# (2026-06-07) standardisation retired the glued-transport ``<source>_<transport>``
# antipattern (``hyperliquid_rest`` -> ``hyperliquid``) — but on-disk objects keep the
# legacy token until the gated migrator rewrites them, so consumers must still probe
# it. Keyed by asset_group -> extra source tokens.
_LEGACY_PIPELINE_MODE_SOURCES: dict[str, tuple[str, ...]] = {
    CEFI: ("hyperliquid_rest",),
    DEFI: ("hyperliquid_rest",),
}

# Extra ``live_<source>`` probe prefixes to enumerate for an asset_group EVEN WHEN the
# source's ``SOURCE_MODE_CAPABILITY`` does not register :attr:`Mode.LIVE` (so the
# generated batch+live loop cannot emit them). PREDICTION §5 UNION (operator
# 2026-07-18): a batch manifest row is satisfied by live-only object evidence, so the
# phantom-existence probe must ALSO look under every prediction source's ``live_``
# prefix — including ``polymarket_gamma_api``, which is registered BATCH-only ("market
# metadata; not a tick series") and therefore has NO ``LIVE_POLYMARKET_GAMMA_API``
# member in the shared ``PipelineMode`` enum. Emitting the probe prefix here keeps the
# shared enum / capability matrix HONEST (gamma_api stays batch-only) while still
# probing the live shape. Per the batch+live rationale in
# :func:`_canonical_pipeline_mode_prefixes`, adding a probe prefix can only REDUCE
# false-demotion, never introduce one. ``kalshi`` / ``polymarket_clob`` live prefixes
# are ALREADY emitted by that loop (both are LIVE-capable) — listing them here makes
# the operator's UNION decision explicit + self-documenting; the emitter de-dups so
# they are not duplicated. PREDICTION-SCOPED ONLY: no entry for cefi/tradfi/defi/sports,
# so their template sets are byte-for-byte unchanged.
_EXTRA_LIVE_PROBE_SOURCES_BY_AG: dict[str, tuple[str, ...]] = {
    PREDICTION: ("kalshi", "polymarket_clob", "polymarket_gamma_api"),
    # CeFi live-WS CEX venues archive under pipeline_mode=live_{source}, but their BATCH source is
    # `tardis` (deep history), so they are never standalone registry sources and
    # `_canonical_pipeline_mode_prefixes` would omit their live_ prefixes — causing the phantom-auditor
    # to false-flag real live_binance/live_kraken/… shards as phantom_captured_no_parquet_at_canonical_path
    # (measured 2026-07-18: 20 live_kraken + 15 live_binance real shards mis-demoted;
    # non_tardis_dexperp_venue_data_status_smoketest). Adding a live-probe prefix can only REDUCE
    # false-demotion, never introduce one (a prefix that finds nothing is a no-op), so the full
    # valid-cefi-live-source set is safe + future-proof. Operator-ruled 2026-07-19 to relax the
    # prediction-scoped RULE 11 baseline (below) to cover cefi too.
    CEFI: ("binance", "bybit", "kraken", "okx"),
}


def external_batch_sources_for_asset_group(asset_group: str) -> tuple[str, ...]:
    """Return the deduped, sorted external batch SOURCES for an asset_group.

    Unions THREE inputs so the set is complete regardless of provenance wiring:
    (1) the authoritative :data:`_KNOWN_BATCH_SOURCES_BY_AG` consolidated SSOT;
    (2) :func:`external_sources_for` across every canonical data_type of the AG
    (``DATA_TYPES_BY_ASSET_GROUP``); (3) every ``SOURCE_PRIORITY`` key for the AG.
    Computed/service-emitter sources are filtered by :func:`external_sources_for`.
    (1) is the floor (covers the cefi/defi/sports provenance RED gaps); (2)+(3)
    future-proof it (new provenance-wired sources appear automatically).
    """
    ag = asset_group.lower()
    sources: set[str] = set(_KNOWN_BATCH_SOURCES_BY_AG.get(ag, frozenset()))
    for dt in DATA_TYPES_BY_ASSET_GROUP.get(ag, []):
        sources.update(external_sources_for(ag, dt))
    # Also sweep SOURCE_PRIORITY directly (catches data_types not in the canonical
    # market-data list, e.g. reference/derived cells that still write raw objects).
    for (sp_ag, sp_dt), _sources in SOURCE_PRIORITY.items():
        if sp_ag == ag:
            sources.update(external_sources_for(ag, sp_dt))
    return tuple(sorted(sources))


def _canonical_pipeline_mode_prefixes(asset_group: str) -> list[str]:
    """The generated ``raw_tick_data/by_date/day={date}/pipeline_mode=batch_<source>/
    asset_group={ag}/`` prefixes for every external batch source of the AG.

    This is the heart of the Axis-10 fix: the prefixes are DERIVED from the source
    registry, never hand-listed. A source with no ``Mode.BATCH`` pipeline_mode (a
    live-only source) is legitimately skipped.
    """
    ag = asset_group.lower()
    seg = _AG_SEGMENT_SHAPE.get(ag, "")
    legacy = set(_LEGACY_PIPELINE_MODE_SOURCES.get(ag, ()))
    sources = set(external_batch_sources_for_asset_group(ag)) | legacy
    prefixes: list[str] = []
    for source in sorted(sources):
        pmodes: list[str] = []
        if source in legacy:
            # Legacy/transitional token (e.g. ``hyperliquid_rest``) — retired from the
            # canonical ``PipelineMode`` enum by R4, so ``pipeline_mode_for_source``
            # would raise. The on-disk objects still carry ``batch_<token>`` until the
            # gated migrator rewrites them, so emit the raw legacy prefix directly.
            pmodes.append(f"{Mode.BATCH.value}_{source}")
        else:
            # BOTH batch AND live prefixes: the phantom-existence probe must find an
            # object at EITHER — a ``captured`` cell has data whether it was written by
            # the batch backfill or the live writer (live=batch spine; CF-12 batch=live
            # symmetry says the CELL has data either way). Enumerating ONLY ``batch_``
            # false-phantomed every LIVE-captured cell whose object lives under
            # ``pipeline_mode=live_<source>/`` (the 2026-07-11 prediction CF-15 finding:
            # 13,292 KALSHI/POLYMARKET ``book_snapshot_5``/``trades`` rows). Adding a
            # probe prefix can only REDUCE false-demotion (never introduce one), so this
            # is safe cross-AG.
            for mode in (Mode.BATCH, Mode.LIVE):
                try:
                    pmodes.append(pipeline_mode_for_source(source, mode).value)
                except ValueError:
                    # Source has no pipeline_mode for this mode (live-only / batch-only /
                    # unregistered) — it cannot own an object there, so it owns no prefix.
                    logger.debug(
                        "possible_manifest: source %r for asset_group %r has no %s "
                        "pipeline_mode — skipping that prefix",
                        source,
                        ag,
                        mode.name,
                    )
        for pmode_value in pmodes:
            prefixes.append(f"{_DAY_PREFIX}pipeline_mode={pmode_value}/asset_group={ag}/{seg}")
    # PREDICTION §5 UNION extra live-probe prefixes (see _EXTRA_LIVE_PROBE_SOURCES_BY_AG):
    # append every ``live_<source>`` shape the operator's union requires that the
    # capability-derived loop above could not emit (e.g. batch-only polymarket_gamma_api).
    # Append-if-absent so the LIVE-capable sources already emitted above are not
    # duplicated; the dict has no entry for non-prediction AGs, so this is a no-op there.
    for source in _EXTRA_LIVE_PROBE_SOURCES_BY_AG.get(ag, ()):
        extra = f"{_DAY_PREFIX}pipeline_mode={Mode.LIVE.value}_{source}/asset_group={ag}/{seg}"
        if extra not in prefixes:
            prefixes.append(extra)
    return prefixes


def canonical_path_templates(asset_group: str) -> list[str]:
    """Return the canonical + legacy GCS path TEMPLATES for an asset_group's raw-tick
    corpus (CF-15 / CF-17).

    The returned strings carry ``{date}`` / ``{venue}`` / ``{chain}`` /
    ``{instrument_type}`` / ``{data_type}`` placeholders a consumer fills per
    manifest-row or per GCS-object. The list is ordered canonical-first
    (pipeline_mode-keyed, source-derived) then transitional legacy shapes.

    This is the SINGLE SSOT for the phantom reconciler's ``prefix_tpls`` and the
    orphan sweep's prefix set — replacing every hand-maintained per-consumer copy
    (the Axis-10 drift bug). De-scattered: a new external source auto-yields its
    prefix here, so no consumer can silently miss it.

    Sports is intentionally template-less here — it has its own UAC SSOT
    (``unified_api_contracts.sports.candidate_parquet_paths``); a sports consumer
    dispatches there. Returned as an empty list for ``sports`` so a caller treats it
    as "use the sports dispatcher", never "no paths".
    """
    ag = asset_group.lower()
    if ag == SPORTS:
        return []
    seg = _AG_SEGMENT_SHAPE.get(ag, "")
    templates: list[str] = list(_canonical_pipeline_mode_prefixes(ag))
    for shape in _LEGACY_SHAPE_TPLS:
        templates.append(shape.format(date="{date}", ag=ag, seg=seg))
    if ag == DEFI:
        templates.extend(_DEFI_EXTRA_LEGACY_TPLS)
    return templates


# ---------------------------------------------------------------------------
# Valid shard-key space + enumeration (CF-15)
# ---------------------------------------------------------------------------


def _data_types_for(asset_group: str, instrument_type: str) -> frozenset[str] | None:
    """The valid data_type set for an (asset_group, instrument_type), composing the
    G1-ENUM validity matrix. ``None`` = unmapped instrument_type (the caller treats
    every AG data_type as admissible — never silently drops an unknown shape)."""
    return valid_data_types_for_instrument_type(asset_group, instrument_type)


def is_valid_shard_key(asset_group: str, key: ShardKey) -> bool:
    """Return whether ``key`` is inside the asset_group's valid could-exist space.

    A GCS object's hive-key is an ORPHAN candidate (or junk) when this returns False;
    an in-space key with no manifest row is the class-(E) hole the migration must
    backfill. The check is the (instrument_type x data_type) validity join:

    * ``data_type`` must be in the valid set for ``(asset_group, instrument_type)``,
      OR the instrument_type is unmapped (validity ``None`` → admit, never silently
      reject an unknown shape), OR the data_type is not a canonical AG data_type at
      all (a test/non-standard type passes through — same rule as the enumerator's
      ``_row_data_types``).
    * ``asset_group`` must be a known market-data group.

    Venue is intentionally tolerant (not gated): a ``venue=UNKNOWN`` object or a
    not-yet-registered venue is still a *valid-shape* object whose membership is
    decided by data_type — gating on the venue domain would false-flag legitimately
    captured rows for venues added since the registry snapshot.
    """
    ag = asset_group.lower()
    if ag not in POSSIBLE_MANIFEST_ASSET_GROUPS:
        return False
    if not key.data_type:
        return False
    # Sports/prediction shard atoms carry no instrument_type segment — validity is
    # by data_type membership in the AG's canonical set.
    if ag in (SPORTS, PREDICTION) and not key.instrument_type:
        return key.data_type in frozenset(DATA_TYPES_BY_ASSET_GROUP.get(ag, []))
    valid = _data_types_for(ag, key.instrument_type)
    if valid is None:
        return True  # unmapped instrument_type → admit (never silently reject)
    if key.data_type in valid:
        return True
    # A data_type outside BOTH the valid set AND the AG's canonical set is a
    # test/non-standard type → pass through (matches the enumerator's rule).
    return key.data_type not in frozenset(DATA_TYPES_BY_ASSET_GROUP.get(ag, []))


def enumerate_possible_shard_keys(
    asset_group: str,
    *,
    catalogue: Iterable[CatalogueLeaf] | None = None,
) -> Iterator[ShardKey]:
    """Yield the complete set of valid ShardKeys for an asset_group (CF-15).

    Two modes:

    * **Instrument grain** (``catalogue`` provided) — cross each catalogue leaf
      against its valid data_types (the G1-ENUM validity matrix), rolling bundle-grain
      leaves (cefi/tradfi option/combo) up into the per-underlying chain bundle so an
      options leaf yields ONE ``options_chain`` candidate, not one per contract. This
      is the could-exist atom the catalogue-seeded denominator enumerates (the
      lifecycle/date axis is layered on by ``enumerate_expected_universe.py``).
    * **Family grain** (``catalogue=None``) — cross the AG's venue domain
      (``VENUES_BY_ASSET_GROUP``) x instrument_types x valid data_types. Used where
      no catalogue is available (the maximal venue/data_type space — e.g. an orphan
      validator that only needs cell-shape validity, or a zero-catalogue smoke).

    Sports/prediction enumerate at the AG data_type grain (their shard atoms carry no
    instrument_type/venue leaf in the static space); a richer per-league/per-cqg
    enumeration uses the catalogue path with league_id/cqg carried in instrument_id.
    """
    ag = asset_group.lower()
    if ag not in POSSIBLE_MANIFEST_ASSET_GROUPS:
        return
    if catalogue is not None:
        yield from _enumerate_from_catalogue(ag, catalogue)
        return
    yield from _enumerate_family_grain(ag)


def _enumerate_from_catalogue(asset_group: str, catalogue: Iterable[CatalogueLeaf]) -> Iterator[ShardKey]:
    """Instrument-grain crossing of catalogue leaves x valid data_types, with the
    G1-ENUM bundle roll-up (option/combo leaves → one per-underlying chain bundle)."""
    ag = asset_group.lower()
    seen_bundles: set[tuple[str, str, str, str]] = set()
    for leaf in catalogue:
        it = leaf.instrument_type
        # Bundle-grain roll-up: an option/combo leaf collapses into ONE per-underlying
        # bundle entry (instrument_type=options_chain/futures_chain, id=underlying).
        bundle_it = bundle_instrument_type_for_leaf(ag, it, leaf.venue)
        if bundle_it is not None and grain_for_instrument_type(ag, it, leaf.venue) == GRAIN_BUNDLE_BY_UNDERLYING:
            underlying = leaf.underlying or _underlying_of(leaf.instrument_id)
            if not underlying:
                continue  # cannot key a bundle → skip rather than mis-key
            bundle_id = underlying
            dedup = (leaf.venue, leaf.chain, bundle_it, bundle_id)
            if dedup in seen_bundles:
                continue
            seen_bundles.add(dedup)
            it = bundle_it
            leaf_id = bundle_id
        else:
            leaf_id = leaf.instrument_id
        valid = _data_types_for(ag, it)
        known = frozenset(DATA_TYPES_BY_ASSET_GROUP.get(ag, []))
        if valid is None:
            dts: Sequence[str] = sorted(known)
        else:
            dts = sorted(valid)
        for dt in dts:
            yield ShardKey(
                asset_group=ag,
                venue=leaf.venue,
                chain=leaf.chain,
                instrument_type=it,
                data_type=dt,
                instrument_id=leaf_id,
            )


def _enumerate_family_grain(asset_group: str) -> Iterator[ShardKey]:
    """Family-grain crossing: venue domain x instrument_types x valid data_types."""
    ag = asset_group.lower()
    if ag in (SPORTS, PREDICTION):
        for dt in sorted(frozenset(DATA_TYPES_BY_ASSET_GROUP.get(ag, []))):
            yield ShardKey(asset_group=ag, venue="", chain="", instrument_type="", data_type=dt)
        return
    venues = VENUES_BY_ASSET_GROUP.get(ag, [])
    instrument_types = _candidate_instrument_types(ag)
    for venue in sorted(venues):
        chain = ""  # family grain carries no concrete chain; DeFi binds it per-leaf
        for it in sorted(instrument_types):
            valid = _data_types_for(ag, it)
            if valid is None:
                continue  # unmapped at family grain → no concrete cell to assert
            for dt in sorted(valid):
                yield ShardKey(asset_group=ag, venue=venue, chain=chain, instrument_type=it, data_type=dt)


def _candidate_instrument_types(asset_group: str) -> frozenset[str]:
    """The instrument_types that have a validity-matrix entry for the AG (the keys of
    the G1-ENUM matrix for this asset_group), used for family-grain enumeration."""
    from unified_api_contracts.registry.market_data_categories import (
        VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE,
    )

    ag = asset_group.lower()
    return frozenset(it for (mag, it) in VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE if mag == ag)


def _underlying_of(instrument_id: str) -> str:
    """Base asset (token before the first ``-``); "" when un-keyable. Mirrors the IS
    enumerator's ``_derive_underlying`` so the bundle roll-up agrees cross-repo."""
    iid = instrument_id.strip()
    return iid.split("-", 1)[0] if "-" in iid else ""


# ---------------------------------------------------------------------------
# PossibleManifestSpec — the per-AG authority object (CF-15)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PossibleManifestSpec:
    """The composed could-exist authority for one asset_group.

    Carries the three pre-existing layers (axis names, value-domains, validity) +
    the canonical path templates, and exposes the enumeration/validation surface.
    Construct via :func:`get_possible_manifest_spec` (do not instantiate directly —
    the factory wires the registry lookups).
    """

    asset_group: str
    shard_axes: tuple[str, ...]
    venues: tuple[str, ...]
    data_types: tuple[str, ...]
    external_sources: tuple[str, ...]
    path_templates: tuple[str, ...]
    instrument_types: frozenset[str] = field(default_factory=frozenset)

    def is_valid(self, key: ShardKey) -> bool:
        """Whether ``key`` is in this AG's valid could-exist space."""
        return is_valid_shard_key(self.asset_group, key)

    def enumerate_shard_keys(self, *, catalogue: Iterable[CatalogueLeaf] | None = None) -> Iterator[ShardKey]:
        """Enumerate this AG's could-exist ShardKeys (see
        :func:`enumerate_possible_shard_keys`)."""
        return enumerate_possible_shard_keys(self.asset_group, catalogue=catalogue)


def get_possible_manifest_spec(asset_group: str) -> PossibleManifestSpec:
    """Build the :class:`PossibleManifestSpec` for an asset_group by composing the
    registry layers. Raises ``ValueError`` for an unknown asset_group (closed set)."""
    ag = asset_group.lower()
    if ag not in POSSIBLE_MANIFEST_ASSET_GROUPS:
        raise ValueError(f"unknown asset_group {asset_group!r} — expected one of {POSSIBLE_MANIFEST_ASSET_GROUPS}")
    return PossibleManifestSpec(
        asset_group=ag,
        shard_axes=get_shard_axes(_MARKET_DATA_SERVICE, ag),
        venues=tuple(VENUES_BY_ASSET_GROUP.get(ag, [])),
        data_types=tuple(DATA_TYPES_BY_ASSET_GROUP.get(ag, [])),
        external_sources=external_batch_sources_for_asset_group(ag),
        path_templates=tuple(canonical_path_templates(ag)),
        instrument_types=_candidate_instrument_types(ag),
    )


# Re-export the transport resolver so a consumer building a manifest COLUMN (not a
# path key) reads it from the same SSOT (transport is a column, never a path suffix
# unless a source runs >1 transport/shard — none today). Pure pass-through.
__all__ = [
    "POSSIBLE_MANIFEST_ASSET_GROUPS",
    "CatalogueLeaf",
    "PossibleManifestSpec",
    "ShardKey",
    "canonical_path_templates",
    "default_transport_for_source",
    "enumerate_possible_shard_keys",
    "external_batch_sources_for_asset_group",
    "get_possible_manifest_spec",
    "is_valid_shard_key",
]
