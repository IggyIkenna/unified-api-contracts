"""Pipeline-mode SSOT — closed-set values describing how a row was produced.

Every parquet row written by MTDS / MDPS / features-service / instruments-service
is tagged with a ``pipeline_mode`` value. The value identifies the source-and-mode
that produced it (batch source vs live websocket). The ``pipeline_mode`` column is
a manifest dimension (extends the v5 row primary-key) and a hive partition segment
on disk (sits LEFT of ``asset_group=`` for partition-pruning efficiency, since
batch-vs-live reconciliation queries pivot on pipeline_mode first).

Per the workspace CLAUDE.md ``Live = batch — same data, same fields, same timing
semantics, different sources OK`` rule:

* Batch and live produce IDENTICAL parquet schemas.
* The ONLY thing that legitimately differs is which SOURCE serves a given
  ``(asset_group, data_type)``.
* Historical writes get the live-pipeline ``available_at`` they'd actually have
  in live mode (the SOURCE_PRIORITY top entry's emission time).

So ``pipeline_mode`` is the on-disk + manifest-row tag that records WHICH source
served each row, allowing batch-vs-live reconciliation queries (live-pipeline
plan Phase 12) to pivot cleanly.

Closed-set rule: every batch ``PipelineMode`` value MUST correspond to an entry
in :data:`~unified_api_contracts.canonical.crosscutting.source_priority.SOURCE_PRIORITY`,
and every source string in ``SOURCE_PRIORITY`` MUST have a matching ``PipelineMode``
value. The :func:`assert_pipeline_mode_source_priority_round_trip` helper enforces
this and is wired into the UAC unit-test suite.

Plans:

* ``gcs_migration_bundle_pipeline_mode_2026_05_08`` Phase 1A — owns this enum +
  the manifest schema column extension.
* ``live_pipeline_mtds_mdps_features_2026_05_08`` Phase 1 — consumes this enum
  on the streaming ``CandleBoundaryCrossedEvent`` / ``CandleComputedEvent``
  payloads.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class PipelineMode(StrEnum):
    """Closed-set source-and-mode tag for every persisted row.

    The canonical form is ``{mode}_{source}[_{transport}]`` (M1) where
    ``mode ∈ {batch, live, replay}``. ``batch``/``live``/``replay`` are the SAME
    logical data, same schema, on the same GCS/bus paths — three CAPTURE MODES:

    * ``batch_<source>`` — the T+1 floor (deep history).
    * ``live_<source>`` — a live-mode generator streamed to disk as it happens.
    * ``replay_<source>`` — an intraday re-fetch of a window ``live`` missed
      (cold start / live-service down), written with the SAME schema but tagged
      ``replay`` purely for the audit trail.

    Read precedence (M4, mode-contextual): a live consumer reads
    ``live > replay > batch``; a batch consumer reads ``batch > replay > live``;
    ``replay`` is always the middle (gap-fill) tier. Whether a ``(source,
    data_type)`` is replay-capable is a FACT encoded in
    :data:`~unified_api_contracts.canonical.crosscutting.source_priority.SOURCE_MODE_CAPABILITY`
    (M2) — a source that cannot re-fetch intraday simply means a live-downtime
    gap waits for batch (honest absence), NOT a decision.

    Closed-set rule: a ``LIVE_<SOURCE>`` / ``REPLAY_<SOURCE>`` member exists iff
    the source's :data:`SOURCE_MODE_CAPABILITY` set contains :attr:`Mode.LIVE` /
    :attr:`Mode.REPLAY` — enforced by ``test_source_mode_capability.py``. Every
    ``BATCH_<SOURCE>`` member still mirrors a ``SOURCE_PRIORITY`` source string.

    :attr:`LIVE_WEBSOCKET` is a TRANSITIONAL alias kept for the not-yet-migrated
    streaming objects/writers/readers — its migration to ``live_<source>`` is the
    next tranche (M1 breaking step). Do NOT delete it.

    Source-aware live/replay members are landed per
    ``pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md``
    (M1/M2), ratifying ``source_mode_capability_matrix_2026_06_07.md``.
    """

    BATCH_API_FOOTBALL = "batch_api_football"
    BATCH_BARCHART = "batch_barchart"
    BATCH_CHAINLINK = "batch_chainlink"
    BATCH_CROSS_INSTRUMENT = "batch_cross_instrument"
    BATCH_DATABENTO = "batch_databento"
    BATCH_EIA = "batch_eia"
    BATCH_EXECUTION_SERVICE = "batch_execution_service"
    BATCH_FEATURES_ONCHAIN_SERVICE = "batch_features_onchain_service"
    BATCH_FOOTYSTATS = "batch_footystats"
    # greeks-service computed outputs (greeks_snapshot / implied_vol_surface) —
    # in-house BS greeks + IV-surface from the canonical options_chain. Internal
    # computed source: batch=live symmetry (same kernel both modes), re-run=replay.
    BATCH_GREEKS_SERVICE = "batch_greeks_service"
    # hyperliquid is a UNIFIED vendor (operator R4 2026-06-07): the former
    # ``hyperliquid_rest`` source glued the REST transport into the source name (the
    # M1 antipattern). source=``hyperliquid``, transport=``rest`` (a column, not the
    # name). It is BOTH a DeFi batch source (perp_funding/solana_defi via REST
    # candleSnapshot) AND a CeFi/DeFi live+replay venue — so it carries BATCH here
    # plus LIVE_HYPERLIQUID / REPLAY_HYPERLIQUID (in the CeFi-venue block below).
    BATCH_HYPERLIQUID = "batch_hyperliquid"
    BATCH_MASSIVE = "batch_massive"
    # MTDS L2 microstructure computed outputs (order_flow_imbalance /
    # depth_of_book_10 / queue_position) — derived from the canonical
    # book_snapshot_5. Internal computed source: batch=live symmetry, re-run=replay.
    BATCH_MTDS_MICROSTRUCTURE = "batch_mtds_microstructure"
    BATCH_MDPS_ODDS_HORIZON_BUCKET = "batch_mdps_odds_horizon_bucket"
    BATCH_INSTRUMENTS_SERVICE = "batch_instruments_service"
    BATCH_ODDS_API = "batch_odds_api"
    BATCH_ONCHAIN_RPC = "batch_onchain_rpc"
    BATCH_ONCHAIN_SUBGRAPH = "batch_onchain_subgraph"
    BATCH_OPEN_METEO = "batch_open_meteo"
    BATCH_POLYMARKET_CLOB = "batch_polymarket_clob"
    BATCH_POLYMARKET_GAMMA_API = "batch_polymarket_gamma_api"
    BATCH_HELIUS_RPC = "batch_helius_rpc"
    BATCH_PYTH_HERMES = "batch_pyth_hermes"
    BATCH_SOCCER_FOOTBALL_INFO = "batch_soccer_football_info"
    BATCH_SOLANA_RPC = "batch_solana_rpc"
    BATCH_STRATEGY_SERVICE = "batch_strategy_service"
    BATCH_TARDIS = "batch_tardis"
    BATCH_TRANSFERMARKT = "batch_transfermarkt"
    BATCH_UNDERSTAT = "batch_understat"
    BATCH_YAHOO = "batch_yahoo"

    LIVE_WEBSOCKET = "live_websocket"

    # ------------------------------------------------------------------
    # M1 source-aware live/replay members — a LIVE_/REPLAY_ member exists iff
    # SOURCE_MODE_CAPABILITY[source] contains Mode.LIVE / Mode.REPLAY (the
    # ratified matrix; enforced by test_source_mode_capability.py).
    # ------------------------------------------------------------------
    # {batch, live, replay} sources — both live + replay members.
    LIVE_DATABENTO = "live_databento"
    REPLAY_DATABENTO = "replay_databento"
    LIVE_MASSIVE = "live_massive"
    REPLAY_MASSIVE = "replay_massive"
    LIVE_PYTH_HERMES = "live_pyth_hermes"
    REPLAY_PYTH_HERMES = "replay_pyth_hermes"
    # hyperliquid live/replay members live in the CeFi-venue block below — the same
    # unified ``hyperliquid`` vendor serves DeFi batch AND CeFi/DeFi live+replay
    # (transport differs by mode: batch=rest candleSnapshot, live=ws — a column,
    # never the source name). No ``*_HYPERLIQUID_REST`` members (operator R4).
    LIVE_SOLANA_RPC = "live_solana_rpc"
    REPLAY_SOLANA_RPC = "replay_solana_rpc"
    LIVE_HELIUS_RPC = "live_helius_rpc"
    REPLAY_HELIUS_RPC = "replay_helius_rpc"
    LIVE_ONCHAIN_RPC = "live_onchain_rpc"
    REPLAY_ONCHAIN_RPC = "replay_onchain_rpc"
    # onchain_subgraph: live = short-interval poll (no native push), replay ✓.
    LIVE_ONCHAIN_SUBGRAPH = "live_onchain_subgraph"
    REPLAY_ONCHAIN_SUBGRAPH = "replay_onchain_subgraph"
    LIVE_CHAINLINK = "live_chainlink"
    REPLAY_CHAINLINK = "replay_chainlink"
    LIVE_POLYMARKET_CLOB = "live_polymarket_clob"
    REPLAY_POLYMARKET_CLOB = "replay_polymarket_clob"
    # Internal service sources — batch=live symmetry; re-run = replay.
    LIVE_INSTRUMENTS_SERVICE = "live_instruments_service"
    REPLAY_INSTRUMENTS_SERVICE = "replay_instruments_service"
    LIVE_EXECUTION_SERVICE = "live_execution_service"
    REPLAY_EXECUTION_SERVICE = "replay_execution_service"
    LIVE_STRATEGY_SERVICE = "live_strategy_service"
    REPLAY_STRATEGY_SERVICE = "replay_strategy_service"
    LIVE_FEATURES_ONCHAIN_SERVICE = "live_features_onchain_service"
    REPLAY_FEATURES_ONCHAIN_SERVICE = "replay_features_onchain_service"
    LIVE_GREEKS_SERVICE = "live_greeks_service"
    REPLAY_GREEKS_SERVICE = "replay_greeks_service"
    LIVE_CROSS_INSTRUMENT = "live_cross_instrument"
    REPLAY_CROSS_INSTRUMENT = "replay_cross_instrument"
    LIVE_MTDS_MICROSTRUCTURE = "live_mtds_microstructure"
    REPLAY_MTDS_MICROSTRUCTURE = "replay_mtds_microstructure"
    LIVE_MDPS_ODDS_HORIZON_BUCKET = "live_mdps_odds_horizon_bucket"
    REPLAY_MDPS_ODDS_HORIZON_BUCKET = "replay_mdps_odds_horizon_bucket"
    # {batch, replay} sources — replay member only (no live stream).
    REPLAY_ODDS_API = "replay_odds_api"
    REPLAY_API_FOOTBALL = "replay_api_football"
    REPLAY_FOOTYSTATS = "replay_footystats"
    REPLAY_UNDERSTAT = "replay_understat"
    REPLAY_TRANSFERMARKT = "replay_transfermarkt"
    REPLAY_SOCCER_FOOTBALL_INFO = "replay_soccer_football_info"
    REPLAY_OPEN_METEO = "replay_open_meteo"
    REPLAY_EIA = "replay_eia"

    # ------------------------------------------------------------------
    # CeFi per-venue live/replay sources (M2/M3). CeFi `batch` source = tardis;
    # CeFi `live`/`replay` source = the EXCHANGE. The SAME shard carries
    # source=tardis in batch and source=<venue> in live/replay (the row-level
    # `source` column models this). There is NO batch_<venue> member — the venue
    # is not a batch/archive source. Bybit/Aster are LIVE-only: their public REST
    # is recent-only (no time-range tick), so a live-downtime gap waits for batch
    # (T+1) — replay is ABSENT, a FACT, not a pending decision.
    # ------------------------------------------------------------------
    LIVE_BINANCE = "live_binance"
    REPLAY_BINANCE = "replay_binance"
    LIVE_OKX = "live_okx"
    REPLAY_OKX = "replay_okx"
    LIVE_DERIBIT = "live_deribit"
    REPLAY_DERIBIT = "replay_deribit"
    LIVE_KRAKEN = "live_kraken"
    REPLAY_KRAKEN = "replay_kraken"
    LIVE_HYPERLIQUID = "live_hyperliquid"
    REPLAY_HYPERLIQUID = "replay_hyperliquid"
    LIVE_BYBIT = "live_bybit"
    LIVE_ASTER = "live_aster"


_BATCH_PREFIX: Final[str] = "batch_"
_LIVE_PREFIX: Final[str] = "live_"
_REPLAY_PREFIX: Final[str] = "replay_"


class Mode(StrEnum):
    """The data-class / reconciliation axis — what a reader unions + prioritises.

    Distinct from :class:`PipelineMode` (which is ``mode``-by-``source``): ``Mode`` is
    the abstract reconciliation class. The full target ``pipeline_mode`` form is
    ``{mode}_{source}[_{transport}]`` (M1) — e.g. ``batch_databento`` /
    ``live_tardis`` / ``replay_onchain_rpc``. Precedence is mode-CONTEXTUAL (M4):
    a live consumer reads ``live > replay > batch``; a batch consumer reads
    ``batch > replay > live``; ``replay`` is always the middle (gap-fill) tier.
    """

    BATCH = "batch"
    LIVE = "live"
    REPLAY = "replay"


class Transport(StrEnum):
    """The wire transport a source used to serve a shard — the M1 ``[_{transport}]``
    segment, a SEPARATE axis from ``source`` (the vendor).

    Operator R4 (2026-06-07): ``source`` is the VENDOR ONLY and transport is NEVER
    glued into it (the retired ``hyperliquid_rest`` source was that antipattern —
    now ``source=hyperliquid`` + ``transport=rest``). Two rules:

    * The ``[_{transport}]`` SUFFIX appears in the ``pipeline_mode`` PATH KEY *only*
      where a source genuinely runs >1 transport for the SAME shard (else OMITTED —
      no noise). No source does today, so no member carries a suffix yet.
    * A separate ``transport`` COLUMN is ALWAYS populated on every manifest row,
      regardless of whether the suffix is in the key (via
      :func:`default_transport_for_source` unless the writer is passed an explicit
      value). ``rpc`` / ``graphql`` / ``sse`` all resolve over HTTP → ``rest`` for
      the column; ``tardis`` T+1 archives are ``flat_file``.
    """

    REST = "rest"
    WEBSOCKET = "websocket"
    FLAT_FILE = "flat_file"


# Sources whose PRIMARY (batch/archive) transport is a flat-file download rather
# than a REST/HTTP call (ratified ``source_mode_capability_matrix_2026_06_07.md``).
# Tardis ships T+1 archives as flat files; every other batch source is REST-family.
_FLAT_FILE_SOURCES: Final[frozenset[str]] = frozenset({"tardis"})


def _split_transport(remainder: str) -> tuple[str, str | None]:
    """Split a ``{source}[_{transport}]`` remainder into ``(source, transport|None)``.

    ``transport`` is the trailing ``_rest`` / ``_websocket`` / ``_flat_file`` token
    when present (the M1 >1-transport suffix), else ``None``. No registered source
    name ends in a transport token, so the split is unambiguous.
    """
    for transport in Transport:
        suffix = f"_{transport.value}"
        if remainder.endswith(suffix) and len(remainder) > len(suffix):
            return remainder[: -len(suffix)], transport.value
    return remainder, None


def is_batch(mode: PipelineMode) -> bool:
    """True if ``mode`` is a batch-source value."""

    return mode.value.startswith(_BATCH_PREFIX)


def is_live(mode: PipelineMode) -> bool:
    """True if ``mode`` is any live value (``LIVE_WEBSOCKET`` or ``live_<source>``)."""

    return mode.value.startswith(_LIVE_PREFIX)


def is_replay(mode: PipelineMode) -> bool:
    """True if ``mode`` is a ``replay_<source>`` value (M1 intraday gap-fill mode)."""

    return mode.value.startswith(_REPLAY_PREFIX)


def source_string_for(mode: PipelineMode) -> str | None:
    """Return the source string this ``pipeline_mode`` maps to.

    Strips the leading ``{mode}_`` segment (``batch_`` / ``live_`` / ``replay_``)
    and returns the remaining source string — e.g. ``batch_tardis`` → ``tardis``,
    ``live_databento`` → ``databento``, ``replay_onchain_rpc`` → ``onchain_rpc``.

    Returns ``None`` for :attr:`PipelineMode.LIVE_WEBSOCKET` alone — the
    transitional alias has no concrete source (its migration to ``live_<source>``
    is the next tranche).
    """

    if mode is PipelineMode.LIVE_WEBSOCKET:
        return None
    if is_batch(mode):
        remainder = mode.value.removeprefix(_BATCH_PREFIX)
    elif is_replay(mode):
        remainder = mode.value.removeprefix(_REPLAY_PREFIX)
    elif is_live(mode):
        remainder = mode.value.removeprefix(_LIVE_PREFIX)
    else:
        return None
    # Strip any trailing transport suffix so ``source`` round-trips to the VENDOR
    # only (operator R4). No member carries a suffix today, so this is a no-op now;
    # it keeps the round-trip correct once a >1-transport source adds one.
    source, _transport = _split_transport(remainder)
    return source


def transport_of(mode: PipelineMode) -> str | None:
    """Return the explicit transport SUFFIX in ``mode``'s value, or ``None``.

    Per the ratified transport rule (operator R4 2026-06-07) the ``[_{transport}]``
    suffix appears in a ``pipeline_mode`` value ONLY where a source genuinely runs
    >1 transport for the SAME shard — no source does today, so this returns ``None``
    for every current member. The manifest ``transport`` COLUMN is populated
    regardless, via :func:`default_transport_for_source` (or an explicit writer
    value). ``None`` for :attr:`PipelineMode.LIVE_WEBSOCKET` (transitional alias —
    no concrete source/transport).
    """
    if mode is PipelineMode.LIVE_WEBSOCKET:
        return None
    for prefix in (_BATCH_PREFIX, _LIVE_PREFIX, _REPLAY_PREFIX):
        if mode.value.startswith(prefix):
            _source, transport = _split_transport(mode.value.removeprefix(prefix))
            return transport
    return None


def default_transport_for_source(source: str) -> str:
    """Return the PRIMARY (batch/archive) :class:`Transport` value for ``source``.

    The value the manifest writer stamps in the ``transport`` column when no explicit
    transport is supplied and the ``pipeline_mode`` carries no transport suffix (the
    common case — see :func:`transport_of`). Ratified matrix
    ``source_mode_capability_matrix_2026_06_07.md``: ``tardis`` batch is a flat-file
    archive; every other batch source is REST-family (``rpc`` / ``graphql`` / ``sse``
    resolve over HTTP). Live-websocket transport for the gated ``live_<source>``
    tranche is stamped explicitly by live writers, not defaulted here.
    """
    if source in _FLAT_FILE_SOURCES:
        return Transport.FLAT_FILE.value
    return Transport.REST.value


def pipeline_mode_for_source(source: str, mode: Mode = Mode.BATCH) -> PipelineMode:
    """Return the :class:`PipelineMode` for a source string in reconciliation ``mode``.

    Builds the closed-set ``{mode}_{source}`` value and resolves it. ``mode``
    defaults to :attr:`Mode.BATCH` so existing batch callers are unchanged.

    Raises :class:`ValueError` if no member exists for ``(source, mode)`` — the
    closed-set round-trip rule is bidirectional, so this means either the source
    string is misspelled, the source does not support that mode (per
    :data:`~unified_api_contracts.canonical.crosscutting.source_priority.SOURCE_MODE_CAPABILITY`),
    or a new ``PipelineMode`` value is needed.
    """

    target = f"{mode.value}_{source}"
    for member in PipelineMode:
        if member.value == target:
            return member
    raise ValueError(
        f"No PipelineMode for source {source!r} in mode {mode.value!r}; "
        f"either add a {mode.name}_<SOURCE> value to PipelineMode, or the source "
        "does not support that mode (closed-set round-trip required)."
    )


# Canonical mapping from sports_reference entity name (lowercase) to PipelineMode.
# Lifted verbatim from instruments-service ``_ENTITY_NAME_TO_PIPELINE_MODE`` (the
# verified-correct source, committed at IS@4459799d).  Keyed by the GCS partition
# key used in sports_reference/by_date/day={D}/entity={E}/ paths.
# Unknown entity → BATCH_INSTRUMENTS_SERVICE (the instruments-service batch pipeline).
_SPORTS_ENTITY_TO_PIPELINE_MODE: dict[str, PipelineMode] = {
    # API Football entities
    "fixtures": PipelineMode.BATCH_API_FOOTBALL,
    "injuries": PipelineMode.BATCH_API_FOOTBALL,
    "fixture_stats": PipelineMode.BATCH_API_FOOTBALL,
    "fixture_events": PipelineMode.BATCH_API_FOOTBALL,
    "fixture_lineups": PipelineMode.BATCH_API_FOOTBALL,
    "player_stats": PipelineMode.BATCH_API_FOOTBALL,
    "teams": PipelineMode.BATCH_API_FOOTBALL,
    "standings": PipelineMode.BATCH_API_FOOTBALL,
    # FootyStats entities
    "footystats_predictions": PipelineMode.BATCH_FOOTYSTATS,
    "footystats_matches": PipelineMode.BATCH_FOOTYSTATS,
    "footystats_odds": PipelineMode.BATCH_ODDS_API,
    # Understat entities
    "understat_xg": PipelineMode.BATCH_UNDERSTAT,
    "understat_xg_shots": PipelineMode.BATCH_UNDERSTAT,
    # Transfermarkt entities
    "player_values": PipelineMode.BATCH_TRANSFERMARKT,
    # SFI entities
    "progressive_stats": PipelineMode.BATCH_SOCCER_FOOTBALL_INFO,
    # Open Meteo entities
    "weather": PipelineMode.BATCH_OPEN_METEO,
}


def pipeline_mode_for_sports_entity(entity_name: str) -> PipelineMode:
    """Return the batch :class:`PipelineMode` for a sports_reference entity name.

    The entity name is the GCS partition key used in the
    ``sports_reference/by_date/day={D}/entity={E}/`` hive path (lowercase).
    Unknown entities fall back to :attr:`PipelineMode.BATCH_INSTRUMENTS_SERVICE`
    (the instruments-service batch pipeline).

    This is the workspace SSOT for sports_reference ``pipeline_mode`` derivation —
    instruments-service, market-tick-data-service (migration), and features-service
    all import from here instead of maintaining their own maps.
    """
    return _SPORTS_ENTITY_TO_PIPELINE_MODE.get(entity_name.lower(), PipelineMode.BATCH_INSTRUMENTS_SERVICE)


# ---------------------------------------------------------------------------
# Operational-cadence axis (Mode lives near the top, beside PipelineMode)
# (pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md — M8)
# ---------------------------------------------------------------------------


class Cadence(StrEnum):
    """Operational cadence / deployment topology — an OBSERVABILITY axis that is
    ORTHOGONAL to :class:`Mode`/`PipelineMode` and must NOT be folded into the
    reconciliation `pipeline_mode` (M8).

    The same logical query (e.g. the same Tardis endpoint for a nightly T+1 and a
    long-term historical backfill) is the SAME ``pipeline_mode`` (``batch_tardis``)
    — one pipeline to union — but a DIFFERENT cadence. Cadence lives as a manifest
    column + the deployment registry (NOT a GCS path key), so it never fragments
    the data or the union; it powers "what ran / what failed / where backfills
    started+stopped" in data-status drilldowns.
    """

    ONE_OFF_BACKFILL = "one_off_backfill"
    T1_DAILY = "t1_daily"
    SCHEDULED_RECURRING = "scheduled_recurring"
    CONTINUOUS_LIVE = "continuous_live"
    RECOVERY_REPLAY = "recovery_replay"


def mode_of(pipeline_mode: PipelineMode) -> Mode:
    """Return the abstract :class:`Mode` for a concrete :class:`PipelineMode`.

    Today only ``batch_*`` and ``live_websocket`` exist; once M1 lands
    ``live_<source>`` / ``replay_<source>``, this keys off the leading segment.
    """

    value = pipeline_mode.value
    if value.startswith("live"):
        return Mode.LIVE
    if value.startswith("replay"):
        return Mode.REPLAY
    return Mode.BATCH


__all__ = [
    "_SPORTS_ENTITY_TO_PIPELINE_MODE",
    "Cadence",
    "Mode",
    "PipelineMode",
    "Transport",
    "default_transport_for_source",
    "is_batch",
    "is_live",
    "is_replay",
    "mode_of",
    "pipeline_mode_for_source",
    "pipeline_mode_for_sports_entity",
    "source_string_for",
    "transport_of",
]
