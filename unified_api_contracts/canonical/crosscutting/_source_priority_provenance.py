"""Write-time provenance: external-source enumeration + live-venue routing.

Split out of ``source_priority.py`` (900-line file-size QG, 2026-07-09) —
pure file-organization move, no behavior change. ``source_priority.py``
re-exports everything here so the public import path
(``unified_api_contracts.canonical.crosscutting.source_priority``) is
unchanged.

Two cohesive concerns live here:

* :func:`external_sources_for` / :func:`source_required` / :func:`default_source`
  / :func:`valid_manifest_sources` / :func:`is_valid_manifest_source` — the
  WRITE-TIME provenance surface (which source(s) may legitimately stamp a
  manifest row for a cell), distinct from :data:`SOURCE_PRIORITY`'s READ-TIME
  resolution order.
* :func:`live_source_for_venue` / :func:`live_pipeline_mode_for_venue` — the
  live/replay writer's venue → source resolver (operator 2026-06-19 / bug#9 /
  bug#14: the live-stamp source is often NOT ``SOURCE_PRIORITY[0]``, e.g. a
  CeFi CEX live capture stamps the exchange vendor while the batch primary is
  ``tardis``).
"""

from __future__ import annotations

from functools import cache

from unified_api_contracts.canonical.crosscutting._source_priority_core import (
    get_primary_source,
    has_source_priority,
)
from unified_api_contracts.canonical.crosscutting._source_priority_data import (
    CEFI_LIVE_VENUES,
    COMPUTED_SOURCES,
    SOURCE_MODE_CAPABILITY,
    SOURCE_PRIORITY,
)
from unified_api_contracts.canonical.crosscutting.pipeline_mode import (
    Mode,
    PipelineMode,
    pipeline_mode_for_source,
)


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

    * TradFi ``ohlcv_1m`` (databento + yahoo)        → True (explicit needed)
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


# Per-venue LIVE/REPLAY source overrides consulted by live_source_for_venue BEFORE the
# data_type-level SOURCE_PRIORITY primary (so a shard is never mis-attributed to priority[0]).
# Prediction: vendor IS the venue; KALSHI→kalshi, Polymarket→polymarket_clob (Gamma metadata
# via its explicit venue). The data_type primary polymarket_clob would mis-stamp KALSHI.
_PREDICTION_LIVE_SOURCE_FOR_VENUE: dict[str, str] = {
    "kalshi": "kalshi",
    "polymarket": "polymarket_clob",
    "polymarket_gamma": "polymarket_gamma_api",
}

# CeFi crypto-perp venue (hyphen) → its own underscore WS-feed source token. The hyphen venue
# never matches CEFI_LIVE_VENUES (underscore form) so it would fall through to the batch-only
# `tardis` book_snapshot primary (no LIVE_ PipelineMode → live_pipeline_mode_for_venue raises).
_CEFI_PERP_LIVE_SOURCE_FOR_VENUE: dict[str, str] = {
    "kalshi-perp": "kalshi_perp",
    "polymarket-perp": "polymarket_perp",
}

# CeFi CEX venue → bare exchange VENDOR (the live source), keyed by the venue's vendor PREFIX
# (segment before the first ``-``). The live/replay writer venue carries a market-type suffix
# (``BINANCE-FUTURES`` / ``OKX-SWAP`` / ``BYBIT-LINEAR`` …) but the live source is the bare
# vendor, which is what CEFI_LIVE_VENUES + SOURCE_MODE_CAPABILITY + LIVE_<vendor> hold. Unlike
# hyperliquid (venue == vendor), a CEX venue ≠ its vendor, so the bare CEFI_LIVE_VENUES check
# missed ``binance-futures`` → fell through to batch-only ``tardis`` (no ``live_`` PipelineMode
# → raised "No PipelineMode for source 'tardis' in mode 'live'"; bug#9: no CEX live capture).
# tardis stays the index-0 BATCH source for these venues; this map is LIVE/REPLAY only.
_CEFI_CEX_VENDOR_FOR_VENUE_PREFIX: dict[str, str] = {
    "binance": "binance",
    "okx": "okx",
    "bybit": "bybit",
    "kraken": "kraken",
    "deribit": "deribit",
}


@cache
def _live_vendors_for_asset_group(asset_group: str) -> frozenset[str]:
    """Return the live/replay-capable VENDOR sources that serve ``asset_group``.

    The WRITE-TIME provenance gate (:func:`is_valid_manifest_source`) must accept
    a vendor that genuinely serves the asset_group LIVE even though it is absent
    from the cell's batch :data:`SOURCE_PRIORITY` list (bug#14: a CeFi CEX live
    capture stamps ``source=binance``, but ``binance`` ∉
    ``SOURCE_PRIORITY[("cefi","trades")]`` because that list is the BATCH
    read-priority — CeFi batch = ``tardis``; the live vendor IS the exchange).

    DATA-DRIVEN — reuses the EXISTING venue→vendor resolution maps consulted by
    :func:`live_source_for_venue` (no hardcoded duplication):

    * **CeFi**: the bare exchange vendors from :data:`_CEFI_CEX_VENDOR_FOR_VENUE_PREFIX`
      (bug#9 — binance/okx/bybit/kraken/deribit), the crypto-perp WS-feed sources
      from :data:`_CEFI_PERP_LIVE_SOURCE_FOR_VENUE` (kalshi_perp/polymarket_perp),
      and the bare-vendor live venues in :data:`CEFI_LIVE_VENUES`
      (adds hyperliquid/aster).
    * **prediction**: the venue-disambiguated vendors from
      :data:`_PREDICTION_LIVE_SOURCE_FOR_VENUE` (kalshi / polymarket_clob /
      polymarket_gamma_api).
    * every other asset_group has no per-venue live-vendor override map → no
      extra live vendors (its live source already IS the
      :data:`SOURCE_PRIORITY` primary, so the batch list covers it).

    A candidate qualifies ONLY when :data:`SOURCE_MODE_CAPABILITY` marks it
    live-OR-replay-capable (so a batch-only entry like ``polymarket_gamma_api``
    is dropped — it can never legitimately stamp a row the batch list does not
    already permit).

    Memoised — the maps are immutable at runtime.
    """
    ag = asset_group.lower()
    candidates: set[str] = set()
    if ag == "cefi":
        candidates.update(_CEFI_CEX_VENDOR_FOR_VENUE_PREFIX.values())
        candidates.update(_CEFI_PERP_LIVE_SOURCE_FOR_VENUE.values())
        candidates.update(CEFI_LIVE_VENUES)
    elif ag == "prediction":
        candidates.update(_PREDICTION_LIVE_SOURCE_FOR_VENUE.values())
    return frozenset(
        src for src in candidates if SOURCE_MODE_CAPABILITY.get(src, frozenset()) & {Mode.LIVE, Mode.REPLAY}
    )


def valid_manifest_sources(asset_group: str, data_type: str) -> frozenset[str]:
    """Return the full set of sources a manifest WRITE may stamp for a cell.

    The WRITE-TIME provenance set =
    ``SOURCE_PRIORITY[(asset_group, data_type)]`` (the batch read-priority
    sources) UNION :func:`_live_vendors_for_asset_group` (the live/replay
    vendors that serve the asset_group). :data:`SOURCE_PRIORITY` itself is UNCHANGED —
    it stays the READ-time batch resolution order; this UNION is the broader
    write-validation surface (a live shard stamps the EXCHANGE vendor, which is
    not in the batch list — bug#14).

    Returns ``frozenset()`` when the pair is unregistered AND the asset_group has
    no live vendors (nothing to validate against).
    """
    batch_sources: frozenset[str] = frozenset(SOURCE_PRIORITY.get((asset_group.lower(), data_type), ()))
    return batch_sources | _live_vendors_for_asset_group(asset_group)


def is_valid_manifest_source(asset_group: str, data_type: str, source: str) -> bool:
    """Return whether ``source`` is a legitimate WRITE-TIME provenance stamp for a cell.

    The write-gate predicate behind the UTL ``ManifestWriter`` source validation
    (replaces the bare ``source in get_source_priority(...)`` membership check,
    which rejected a CeFi CEX live vendor — bug#14). ``True`` iff ``source`` is in
    :func:`valid_manifest_sources` (the batch read-priority list UNION the
    asset_group's live/replay vendors). Case-insensitive on the source string.

    This is ADDITIVE — it accepts live vendors that genuinely serve the
    asset_group live; an unregistered / unknown source is still rejected (the
    mis-stamp protection from the VX/CFE incident is preserved: an unknown source
    never validates). Never consults priority ORDER (read-time only).
    """
    valid = {s.lower() for s in valid_manifest_sources(asset_group, data_type)}
    return source.lower() in valid


def live_source_for_venue(asset_group: str, venue: str, data_type: str) -> str:
    """Resolve the LIVE/REPLAY ``source`` string that serves a ``(asset_group, venue,
    data_type)`` shard.

    The live writer stamps the source-aware ``live_<source>``/``replay_<source>``
    pipeline_mode, so it needs the SOURCE. **CeFi**: source IS the exchange (the venue;
    Tardis is batch-only) → a venue in :data:`CEFI_LIVE_VENUES` resolves to itself.
    **Every other asset_group** (defi/tradfi/prediction/sports/reference): the
    :data:`SOURCE_PRIORITY` PRIMARY (same vendor batch+live), else the normalised venue
    (vendor venue whose name IS its source, e.g. ``chainlink``). Returns a VENDOR source
    (operator R4); pair with :func:`pipeline_mode_for_source`.

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
    # CeFi crypto-perp venues (KALSHI-PERP/POLYMARKET-PERP): hyphen venue → underscore
    # source token (their own WS feed). Checked before CEFI_LIVE_VENUES so the perp venue
    # is never mis-resolved to the batch-only `tardis` book_snapshot primary.
    if ag_norm == "cefi" and venue_norm in _CEFI_PERP_LIVE_SOURCE_FOR_VENUE:
        return _CEFI_PERP_LIVE_SOURCE_FOR_VENUE[venue_norm]
    if ag_norm == "cefi" and venue_norm in CEFI_LIVE_VENUES:
        return venue_norm
    # CeFi CEX venue → vendor source by PREFIX (the segment before the first ``-``): the
    # live/replay writer venue carries a market-type suffix (``BINANCE-FUTURES`` /
    # ``OKX-SWAP`` / ``BYBIT-LINEAR`` …) but the live source is the bare exchange vendor.
    # tardis remains the index-0 BATCH source for these venues; this resolves LIVE/REPLAY
    # only (the (cefi, …) SOURCE_PRIORITY primary ``tardis`` has no ``live_`` PipelineMode).
    if ag_norm == "cefi":
        vendor = _CEFI_CEX_VENDOR_FOR_VENUE_PREFIX.get(venue_norm.split("-", 1)[0])
        if vendor is not None:
            return vendor
    # Prediction is venue-disambiguated like CeFi: the data VENDOR IS the venue. The
    # data_type-level SOURCE_PRIORITY primary (polymarket_clob) would mis-attribute KALSHI
    # live/replay data to polymarket — so resolve KALSHI→kalshi (and the explicit Gamma venue)
    # by venue first. POLYMARKET falls through to the priority primary (polymarket_clob).
    if ag_norm == "prediction" and venue_norm in _PREDICTION_LIVE_SOURCE_FOR_VENUE:
        return _PREDICTION_LIVE_SOURCE_FOR_VENUE[venue_norm]
    # TradFi live = databento (sole tradfi WS producer); the batch primary is also
    # databento (databento-first; massive routing removed 2026-07-19). Batch path
    # unchanged (get_primary_source).
    if ag_norm == "tradfi":
        return "databento"
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

    The live-writer resolver: returns the source-aware live pipeline_mode
    (``live_<source>``) for a shard. Composes
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
