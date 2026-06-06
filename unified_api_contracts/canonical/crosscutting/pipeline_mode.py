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

    Batch values mirror :data:`~unified_api_contracts.canonical.crosscutting.source_priority.SOURCE_PRIORITY`
    source strings (one batch enum per source). The single live value
    :attr:`LIVE_WEBSOCKET` covers all websocket-streaming paths — per-venue
    WS-vs-poll fallback is an operational concern, not a manifest dimension.
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
    BATCH_HYPERLIQUID_REST = "batch_hyperliquid_rest"
    BATCH_MASSIVE = "batch_massive"
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


_BATCH_PREFIX: Final[str] = "batch_"


def is_batch(mode: PipelineMode) -> bool:
    """True if ``mode`` is a batch-source value."""

    return mode.value.startswith(_BATCH_PREFIX)


def is_live(mode: PipelineMode) -> bool:
    """True if ``mode`` is the live-websocket value."""

    return mode is PipelineMode.LIVE_WEBSOCKET


def source_string_for(mode: PipelineMode) -> str | None:
    """Return the SOURCE_PRIORITY source string this batch mode maps to.

    Returns ``None`` for :attr:`PipelineMode.LIVE_WEBSOCKET` since live mode
    is not represented in ``SOURCE_PRIORITY`` — live emission is a runtime
    concern, not a per-source archival concern.
    """

    if not is_batch(mode):
        return None
    return mode.value.removeprefix(_BATCH_PREFIX)


def pipeline_mode_for_source(source: str) -> PipelineMode:
    """Return the batch :class:`PipelineMode` matching a SOURCE_PRIORITY source string.

    Raises :class:`ValueError` if the source has no corresponding batch mode —
    the closed-set round-trip rule is bidirectional, so an unknown source means
    either the source string is misspelled or a new ``PipelineMode`` value is
    needed.
    """

    target = f"{_BATCH_PREFIX}{source}"
    for mode in PipelineMode:
        if mode.value == target:
            return mode
    raise ValueError(
        f"No PipelineMode for source {source!r}; "
        "add a BATCH_<SOURCE> value to PipelineMode (closed-set round-trip required)."
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
# Reconciliation-class (Mode) + operational-cadence axes
# (pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md — M1/M8)
# ---------------------------------------------------------------------------


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
    "is_batch",
    "is_live",
    "mode_of",
    "pipeline_mode_for_source",
    "pipeline_mode_for_sports_entity",
    "source_string_for",
]
