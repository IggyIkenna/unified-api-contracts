"""Honest-coverage cluster registries for bundled-shard validation.

SSOT for the per-bundled-data_type cluster taxonomy referenced by the
writegate-honest-coverage end-to-end plan. Consumed by
``unified_trading_library.manifest_writer.ManifestWriter.record_captured``
when ``data_type ∈ BUNDLED_DATA_TYPES`` — cluster validation MANDATORY.

Two SSOTs live here today:

* :data:`BUNDLED_DATA_TYPES` — the closed set of data_types whose
  parquet shards bundle multiple cluster identities into a single
  per-day file. The writer guard at ``record_captured`` requires
  ``expected_root_clusters`` + ``cluster_extractor`` kwargs whenever
  the data_type is in this set; missing kwargs raise
  ``MissingClusterValidationError``.

* :func:`futures_expiry_bucket` — derives a coarse expiry bucket
  (``front`` / ``back`` / ``spread`` / ``unknown``) from a futures
  symbol shape. Used as the ``cluster_extractor`` for ``futures_chain``
  shards where the cluster identity is the expiry window, not the
  underlying root (rows already partition by underlying).

ES.OPT options-chain cluster taxonomy is **NOT** redefined here — its
SSOT is :data:`unified_api_contracts.registry.ES_OPTIONS_CLUSTERS` with
the per-symbol extractor :func:`unified_api_contracts.registry.extract_es_options_cluster`
and the per-day calendar fallback
:func:`unified_api_contracts.registry.get_active_es_options_clusters_for_date`.
This module re-exports those names from the registry for callers who
prefer the ``honest_coverage`` import surface.

This module is the [UAC] half of the layer split per
``shard_granularity_ssot_propagation_2026_05_06.HANDOVER.md``:

* [UAC] — what the clusters ARE (this module + registry).
* [UTL] — runtime guard (``MissingClusterValidationError``) and writer
  enforcement at ``record_captured``.
* [per-service] — adapters pass ``cluster_extractor`` recipes that map
  rows to cluster names.
"""

from __future__ import annotations

import datetime as _dt
import re
from enum import StrEnum
from typing import Final, NamedTuple

from unified_api_contracts.registry import (
    ES_OPTIONS_CLUSTERS,
    ES_OPTIONS_DEFAULT_MIN_ROWS_PER_CLUSTER,
    extract_es_options_cluster,
    get_active_es_options_clusters_for_date,
)

# ---------------------------------------------------------------------------
# EMPTY_CONFIRMED_REASONS — closed-set taxonomy for ``capture_status="empty_confirmed"``.
#
# Operator direction 2026-05-07: every ``empty_confirmed`` manifest row carries
# one of these reason codes so downstream consumers (ML training NaN-fill,
# rolling-window feature denominator adjustment, execution skip-or-trade
# decision) can classify absence without re-querying calendars / coverage
# tables. Adding a new code = adding it here AND to
# ``codex/02-data/honest-absence-downstream-handling.md`` § "Reason taxonomy"
# AND to the per-service consumer-class audit table.
# ---------------------------------------------------------------------------


class EmptyConfirmedReason(StrEnum):
    """Closed-set taxonomy for ``capture_status="empty_confirmed"`` rows.

    See ``codex/02-data/honest-absence-downstream-handling.md`` for the
    write-side decision tree (calendar lookup / coverage_start / paused-league
    / source-returned-zero) and the per-service consumer-class audit that
    spells out NaN-fill vs skip vs propagate per (consumer, reason) pair.

    Members are string-valued so ``record_empty(reason=EmptyConfirmedReason.EXPECTED_HOLIDAY)``
    serialises straight to the ``error_reason`` parquet column without any
    enum-to-str gymnastics. Bare-string callers (``reason="EXPECTED_HOLIDAY"``)
    are validated via membership lookup at the writer boundary.
    """

    EXPECTED_HOLIDAY = "EXPECTED_HOLIDAY"
    """Calendar-pre-skip: venue trading calendar marks the date as a holiday."""

    EXPECTED_WEEKEND = "EXPECTED_WEEKEND"
    """Calendar-pre-skip: weekend day on a Monday-Friday venue (NYSE, CBOE, CME ETH)."""

    EXPECTED_PAUSED_LEAGUE = "EXPECTED_PAUSED_LEAGUE"
    """Sports: league is in a documented pause window (off-season, suspended due to crisis)."""

    EXPECTED_PRE_SOURCE_COVERAGE_START = "EXPECTED_PRE_SOURCE_COVERAGE_START"
    """Date precedes the source's ``SOURCE_COVERAGE_START`` (per UAC sports / databento registries)."""

    EXPECTED_PAST_SOURCE_COVERAGE_END = "EXPECTED_PAST_SOURCE_COVERAGE_END"
    """Date is after the archive's documented coverage end (``InstrumentRecord.source_coverage_end``).
    Example: Drift tradeRecords S3 archive stopped writing 2025-01-08 — any date after that is
    honest-empty by design, not a fetch failure. Sister of ``EXPECTED_PRE_SOURCE_COVERAGE_START``.
    SSOT: ``is_mtds_contract_audit_2026_05_20.md`` Phase 1."""

    EXPECTED_PRE_GENESIS_CHAIN = "EXPECTED_PRE_GENESIS_CHAIN"
    """DeFi: date precedes the chain's genesis block (Solana 2020-03-16, Arbitrum 2021-08-31, etc.)."""

    EXPECTED_PRE_VENUE_LAUNCH = "EXPECTED_PRE_VENUE_LAUNCH"
    """CeFi/Prediction: date precedes the venue's public launch date (Hyperliquid 2023-06, Aster 2024-09, Polymarket
    2020-09, Kalshi 2021-07, etc.). SSOT: ``unified_api_contracts.registry.venue_launch_dates``. Sister of
    ``EXPECTED_PRE_GENESIS_CHAIN`` (DeFi chains) and ``EXPECTED_PRE_SOURCE_COVERAGE_START`` (sports/databento source
    archives) — all three express "no data possible because the venue/chain/source did not exist yet"."""

    EXPECTED_INSTRUMENT_NOT_LISTED = "EXPECTED_INSTRUMENT_NOT_LISTED"
    """Instrument's ``listed_at`` (or weekly options' ``listing_window``) is after the day."""

    EXPECTED_INSTRUMENT_DELISTED = "EXPECTED_INSTRUMENT_DELISTED"
    """Instrument's ``delisted_at`` is on or before the day."""

    EXPECTED_PARTIAL_HALF_DAY = "EXPECTED_PARTIAL_HALF_DAY"
    """Calendar half-session (Thanksgiving Friday, Christmas Eve early close on US equities). SSOT (NEW Wave 3.X):
    ``unified_api_contracts.registry.half_day_sessions.HALF_DAY_SESSIONS`` — populated per CME / NYSE / NASDAQ /
    CBOE published half-day calendar."""

    EXPECTED_OUTSIDE_TRADING_HOURS = "EXPECTED_OUTSIDE_TRADING_HOURS"
    """Intra-day shard (e.g. ``ohlcv_15m`` / ``book_snapshot_5`` / ``trades`` rolled up to a sub-day window) falls
    OUTSIDE the venue's published trading hours for that day. Distinct from EXPECTED_HOLIDAY / EXPECTED_WEEKEND
    (which are whole-day non-trading) and EXPECTED_PARTIAL_HALF_DAY (which is a shorter-than-usual session that's
    still partly open). SSOT (NEW Wave 3.X):
    ``unified_api_contracts.registry.venue_session_hours.VENUE_SESSION_HOURS`` — per-(venue, weekday) open/close
    timestamp ranges. Operator msg 9 audit dimension #13."""

    EXPECTED_OUTSIDE_TRANSFER_WINDOW = "EXPECTED_OUTSIDE_TRANSFER_WINDOW"
    """Sports ``transfer_records`` data_type: shard date is outside the country's published transfer registration
    windows. Transfer activity is concentrated in the summer (Jul-Aug) + winter (Jan) windows per FIFA + national-
    FA rules; outside those windows transfermarkt has nothing to report. SSOT:
    ``unified_api_contracts.canonical.domain.sports.transfer_windows.TRANSFER_WINDOWS`` (already populated for
    20+ countries; classifier wiring is the gap). Operator msg 9 audit dimension #5."""

    EXPECTED_PRE_SEASON = "EXPECTED_PRE_SEASON"
    """Sports per-(league, season): shard date precedes the league season's published kick-off date. Footystats
    league_id changes at season boundaries; api_football fixture catalogs only populate after the season's
    schedule is announced. Distinct from EXPECTED_PRE_SOURCE_COVERAGE_START (which is per-source archive start,
    not per-league-season). SSOT (NEW Wave 3.X): extension to
    ``unified_api_contracts.sports.provider_league_ids.FOOTYSTATS_SEASON_IDS`` adding season_start dates.
    Operator msg 9 audit dimension #6."""

    EXPECTED_POST_SEASON = "EXPECTED_POST_SEASON"
    """Sports per-(league, season): shard date is after the season's documented final fixture. Pair of
    EXPECTED_PRE_SEASON. Same SSOT extension. Operator msg 9 audit dimension #6."""

    EXPECTED_SOURCE_DOES_NOT_COVER_LEAGUE = "EXPECTED_SOURCE_DOES_NOT_COVER_LEAGUE"
    """Sports per-(source, league): the source legitimately doesn't cover this league/season pair. Reference
    case: Understat covers EPL / La Liga / Serie A / Bundesliga / Ligue 1 only — for any other league the
    Understat shard is honest-empty by design, not a fetch failure. SSOT (NEW Wave 3.X):
    ``unified_api_contracts.canonical.domain.sports.understat_coverage.UNDERSTAT_COVERED_LEAGUES``. Operator
    msg 9 audit dimension #7."""

    EXPECTED_OUT_OF_COVERAGE_WINDOW = "EXPECTED_OUT_OF_COVERAGE_WINDOW"
    """Data_type still valid + restorable post-cutover, but currently OUT of the
    operator-acked MVP coverage scope. Distinct from
    ``EXPECTED_DEPRECATED_DATA_TYPE`` (permanent retirement) — this is a scope
    SHRINK that may reverse. Canonical case: TradFi ``trades`` / ``tbbo`` (L1/L2
    tick data) moved to post-cutover per operator direction 2026-05-15. Existing
    captured parquets remain on GCS (audit trail preserved); the manifest row
    flip says "we collected this previously but the current operational scope
    no longer expects it". SSOT:
    ``unified_api_contracts.registry.market_data_categories.TRADFI_TICK_DATA_WINDOWS``
    (empty list = OHLCV-only mode) +
    ``_DEFERRED_VENUE_DATA_TYPE_COVERAGE_WINDOWS`` (restoration source for the
    post-cutover successor plan). Plan:
    ``plans/active/tradfi_ohlcv_only_mvp_backfill_2026_05_15.md``. Added
    2026-05-17 (slot-1-main) when Phase 5 phantom-reconcile needed the typed
    reason; prior `EXPECTED_DEPRECATED_DATA_TYPE` would have falsified the
    permanent-retirement semantic for these row sets."""

    EXPECTED_DEPRECATED_DATA_TYPE = "EXPECTED_DEPRECATED_DATA_TYPE"
    """Refdata-cadence migration: data_type was retired (e.g. LEAGUES daily-dump killed 2026-05-07 because UAC
    ``LeagueDefinition`` + ``provider_league_ids`` already canonicalise the per-season league mappings via code commits,
    making the daily-cadence GCS dump pure waste). Existing manifest rows for retired data_types get flipped to
    ``empty_confirmed`` with this reason rather than left as `captured` (which would mislead consumers into reading
    deleted parquets) or `attempted_failed` (which would force orchestrator backfill VMs to keep retrying a deleted
    write path). Plan: ``manifest_migration_SUPERSEDED_2026_05_21.plan`` § Audit findings 2026-05-07 → C.1."""

    EXPECTED_REFDATA_CADENCE_CHANGE = "EXPECTED_REFDATA_CADENCE_CHANGE"
    """Refdata-cadence migration: data_type's shard cadence was changed (e.g. TEAMS migrated from per-day to
    per-(team, season) — pre-migration daily shards become honest absence under the new cadence). Distinct from
    `EXPECTED_DEPRECATED_DATA_TYPE` (data_type still exists, just at a different cadence). Plan:
    ``manifest_migration_SUPERSEDED_2026_05_21.plan`` § Audit findings 2026-05-07 → C.11."""

    EXPECTED_KNOWN_SOURCE_GAP = "EXPECTED_KNOWN_SOURCE_GAP"
    """Documented mid-history source gap that doesn't fit the venue-launch / source-coverage-start /
    pre-genesis closed-set primitives. Distinct from ``EXPECTED_PRE_SOURCE_COVERAGE_START`` (which is
    "before the source's archive started") and ``EXPECTED_INSTRUMENT_NOT_LISTED`` (which is "the specific
    instrument didn't exist yet"): this is the "the source briefly stopped covering the data_type mid-history"
    semantic.

    Reference uses (operator-approved 2026-05-11):
    * **VIX 15m gap** (``2025-11-13`` to ``today - 60d``) - the rolling Yahoo Finance window cannot reach back
      to those dates and the Barchart historical preload stopped at ``2025-11-12``. Per CLAUDE.md
      "VIX 15m source layering" rule the gap is honest absence (denominator clip), not a coverage hole.
    * **Sports ``KNOWN_COVERAGE_GAPS``** — per UAC ``unified_api_contracts.sports.KNOWN_COVERAGE_GAPS``
      ranges where a sports source had a documented multi-day outage / paused windows that don't fit
      the league-paused / pre-source-launch categories.

    Plan: ``manifest_schema_final_gate_2026_05_09.md`` Phase 1 — operator-approved 2026-05-11 in the
    ``plans/active/issues/wave3x_track_d_findings_2026_05_11.md`` § TL;DR point 2 routing decision."""

    EXPECTED_PROTOCOL_PAUSED = "EXPECTED_PROTOCOL_PAUSED"
    """DeFi protocol pause window — the protocol was operational before and after but paused
    (intentionally or otherwise) during a documented date range. Examples: Aave V2 → V3
    migration windows, Compound V2 wind-down, chain-level outages (Solana, Polygon Bor halts).
    Sister of ``EXPECTED_DEPRECATED_DATA_TYPE`` (permanent retirement) — this is a temporary
    pause with a known resume date.

    Registry SSOT: ``unified_api_contracts.registry.protocol_pause_windows.PROTOCOL_PAUSE_WINDOWS``
    keyed by ``(protocol, chain)`` → list of ``(start, end)`` date tuples. Oracle gate added
    2026-05-20 round 3 per mega-audit Phase A2 gap closure (R8). Operator fills the registry
    when new pauses are discovered."""

    EXPECTED_OUTSIDE_PROCESSING_SCOPE = "EXPECTED_OUTSIDE_PROCESSING_SCOPE"
    """Instrument exists in the instruments-service catalog but is not included in the downstream
    service's subscription_list / MVP-scope configuration. The service explicitly skips it rather
    than treating the absence as a pipeline failure.

    Used by: features batch handlers (delta_one, calendar, onchain, volatility, sports, commodity)
    and ml-training / ml-inference when an instrument is in the catalog but not in
    ``FEATURES_MVP_INSTRUMENTS`` / ``ML_SCOPE_INSTRUMENTS`` respectively.

    Plan: ``expected_unattempted_propagation_chain_2026_05_12.md`` Phase 3.0 / Phase 4."""

    EXPECTED_UPSTREAM_EMPTY = "EXPECTED_UPSTREAM_EMPTY"
    """Downstream service skipped this shard because the upstream service's manifest has
    ``capture_status`` in (``empty_confirmed``, ``expected_unattempted``).  The downstream
    service propagates the honest absence signal rather than attempting to process missing data.

    Used by: MTDS (skips shard when instruments-service manifest is empty/unattempted),
    MDPS (skips shard when MTDS manifest shows empty/unattempted), feature services (when MDPS
    manifest shows empty/unattempted).

    Plan: ``expected_unattempted_propagation_chain_2026_05_12.md`` Phases 1-4."""

    EXPECTED_FIXTURE_POSTPONED = "EXPECTED_FIXTURE_POSTPONED"
    """Sports fixture status PST (postponed): fixture postponed before kickoff with no rescheduled date yet
    (or rescheduled date outside the current pipeline window). Source: API Football ``status.short == "PST"``.
    Instruments-service emits this at the fixture-day grain so downstream features don't treat absence as a
    fetch failure."""

    EXPECTED_FIXTURE_CANCELLED = "EXPECTED_FIXTURE_CANCELLED"
    """Sports fixture status CANC (cancelled): the fixture was cancelled outright (no reschedule). Source: API Football
    ``status.short == "CANC"``. Instruments-service emits this so consumers can distinguish cancelled fixtures from
    data-fetch failures. Pair with ``EXPECTED_FIXTURE_POSTPONED``."""

    EXPECTED_NO_FIXTURE = "EXPECTED_NO_FIXTURE"
    """No fixture scheduled for this ``(league_id, day)`` per the canonical api_football fixtures manifest.

    Fixture-pinned sources (e.g. ``soccer_football_info`` SFI_PROGRESSIVE_STATS,
    ``footystats`` MATCHES/ODDS/PREDICTIONS, ``open_meteo`` WEATHER) cannot emit data without a
    fixture. Without a scheduled fixture for the (league, day), an empty row is the EXPECTED state,
    not a fetch failure.

    Used by:
    - UTL ``legacy_reason_classifier._classify_sports`` for legacy manifest rows missing per-source
      fixture-pin classification (returns this reason when ``is_fixture_scheduled(league_id, day)``
      is False for SFI/footystats/open_meteo sources).
    - instruments-service WEATHER + SFI + footystats write-paths (preventatively skip fetch when no
      fixture exists; `record_empty(reason=EXPECTED_NO_FIXTURE)` so future runs don't retry).

    Plan: ``sports_classifier_sfi_footystats_fixture_pin_2026_05_13.md`` +
    ``sports_classifier_weather_no_fixture_2026_05_13.md`` (slot 4 ownership 2026-05-13)."""

    EXPECTED_LEGACY_MIGRATION_MISSING_EXPIRY = "EXPECTED_LEGACY_MIGRATION_MISSING_EXPIRY"
    """Tradfi futures/options row from a pre-2026-05-13 historical capture that lacks a
    populated ``expiration`` / ``expiry_date`` field, AND cannot be back-filled from
    Databento metadata at migration time (instrument symbol unresolvable to a chain).

    Used by the one-shot manifest migration script per
    ``plans/active/tradfi_canonical_futures_contract_hard_required_fields_2026_05_13.md``
    Phase 3 when walking legacy ``options_chain`` / ``futures_contract`` manifest rows.
    The migration script attempts a Databento RDC (reference-data) lookup first;
    on miss, flips the row to ``empty_confirmed`` with this reason rather than
    silent re-fetching or write-anyway-with-None (the schema flip in UAC@dd407ae
    rejects None expiration at the pydantic boundary).

    Distinct from ``EXPECTED_INSTRUMENT_NOT_LISTED`` (instrument never existed at
    the date) and ``EXPECTED_INSTRUMENT_DELISTED`` (instrument removed AFTER the date):
    this is "data was captured but the historical write-path didn't populate expiration."
    """

    EXPECTED_NO_FUNDING_RATE_TICKS = "EXPECTED_NO_FUNDING_RATE_TICKS"
    """Perp funding rate adapter: MTDS derivative_ticker parquet for this (venue, symbol, day) had zero
    non-null funding_rate rows. Distinct from SOURCE_RETURNED_ZERO (which is a raw fetch that returned
    200+empty at the HTTP layer). This fires when the parquet exists but the funding_rate column is
    all-null for the filtered (venue, symbol) slice. Downstream: NaN-fill with previous day's value
    (rolling window); do not treat as a pipeline failure.

    Used by:
    - features_service.cefi.calculators.perp_funding_rates (CeFi Binance ETH-PERP adapter)
    - features_service.onchain.calculators.perp_funding_rates_defi (DeFi Hyperliquid ETH-PERP adapter)

    Plan: plans/active/phase5_features_streaming_carry_staked_basis_mvp_2026_05_19.md Phase A."""

    SOURCE_RETURNED_ZERO = "SOURCE_RETURNED_ZERO"
    """We expected data, the source returned 200+empty. Distinct from EXPECTED_* — this is data-side honest absence."""

    NO_INPUT_AVAILABLE = "NO_INPUT_AVAILABLE"
    """Downstream feature or model computation skipped because an upstream input had
    ``attempted_failed`` status in the availability manifest. Distinct from
    ``EXPECTED_UPSTREAM_EMPTY`` (which propagates ``empty_confirmed`` / ``expected_unattempted``
    from upstream) — this reason fires when upstream data was ATTEMPTED but FAILED, making
    any downstream derived output unreliable.

    Used by: rolling-window calcs (features-volatility, features-cross-instrument,
    features-onchain), same-day single-sample calcs, strategy allocator skip.

    Plan: ``writegate_honest_coverage_endtoend_2026_05_06.md`` Phase 2.E.3."""

    LEG_ABSENT_LEFT = "LEG_ABSENT_LEFT"
    """Cross-instrument paired calc: the LEFT leg had ``empty_confirmed`` status in the
    manifest for this date. The paired output cannot be computed without both legs present.
    Emitted by: features-cross-instrument ``PairedPriceDispersionCalculator`` and other
    paired / cross-leg calculators when the left leg is absent but the right is present.
    Pair with ``LEG_ABSENT_RIGHT``.

    Plan: ``writegate_honest_coverage_endtoend_2026_05_06.md`` Phase 2.E.3."""

    LEG_ABSENT_RIGHT = "LEG_ABSENT_RIGHT"
    """Cross-instrument paired calc: the RIGHT leg had ``empty_confirmed`` status in the
    manifest for this date. Pair of ``LEG_ABSENT_LEFT``.

    Plan: ``writegate_honest_coverage_endtoend_2026_05_06.md`` Phase 2.E.3."""

    EXPECTED_NO_PNL_STREAM = "EXPECTED_NO_PNL_STREAM"
    """No upstream StrategyPnlStreamEvent received for this date + archetype_id.
    Emitted by features_service.performance_features when strategy-service has not run
    for the given archetype on the given date (expected for archetypes not yet in live/paper
    run mode).

    Plan: trading_agent_service_architecture_unlock_2026_05_22.md Phase 3."""


EMPTY_CONFIRMED_REASONS: Final[frozenset[str]] = frozenset(member.value for member in EmptyConfirmedReason)
"""String-membership view of :class:`EmptyConfirmedReason` for fast O(1) validation.

UTL ``ManifestWriter.record_empty(reason=...)`` validates the kwarg against
this set; unknown reasons raise ``UnknownEmptyConfirmedReasonError``. Use
:class:`EmptyConfirmedReason` members in new code; the bare-string set is for
the validation hot path only.
"""


EXPECTED_EMPTY_REASON_PREFIX: Final[str] = "EXPECTED_"
"""Reason-prefix marker used by ``record_expected_empty`` to distinguish
calendar-pre-skip writes (``EXPECTED_*``) from honest source-returned-zero
writes (``SOURCE_RETURNED_ZERO``). The helper rejects non-prefixed reasons so
calendar callsites can't accidentally emit ``SOURCE_RETURNED_ZERO``.
"""


# ---------------------------------------------------------------------------
# RecordFailedReason — closed-set taxonomy for ``capture_status="attempted_failed"``.
# ---------------------------------------------------------------------------
#
# Sister enum to :class:`EmptyConfirmedReason`. ``record_failed`` historically
# accepted a freeform ``error: str`` value (typically the output of
# ``classify_venue_error()`` or a ``ValueError`` repr); this taxonomy
# codifies the closed set of operationally-actionable failure categories so
# downstream consumers can branch on the reason without string-matching.
#
# Adding a new member = adding it here AND to
# ``codex/02-data/honest-absence-downstream-handling.md`` § "Reason taxonomy"
# AND extending the per-service consumer-class audit table (alerting tier-up
# routing per category; ML NaN-fill vs skip-strict per category).
#
# Migration: ``record_failed(error=...)`` callsites continue accepting bare
# strings during the transition. The structured-reason kwarg lands incrementally
# behind ``hard_schema_enforcement_2026_05_08.md`` Phase 2 (per-row failure
# routing refactor). The closed-set membership check goes live at write
# boundary in the same phase. Adapters that already emit
# ``classify_venue_error()`` strings continue to work — those resolve to
# ``CLASSIFIED_VENUE_ERROR`` here.
# ---------------------------------------------------------------------------


class RecordFailedReason(StrEnum):
    """Closed-set taxonomy for ``capture_status="attempted_failed"`` rows.

    See :class:`EmptyConfirmedReason` for the sister taxonomy covering
    ``empty_confirmed`` rows. The two enums are mutually exclusive — a shard
    is either an honest empty (calendar-pre-skip / source-returned-zero) or
    an attempted failure (schema violation / upstream bug / classified venue
    error). ``record_captured`` writes are neither.

    Migration shape: ``record_failed(error: str, ...)`` keeps the freeform
    string API today; this enum is the canonical taxonomy adapters should
    pass `.value` into. Phase 2 of `hard_schema_enforcement_2026_05_08.md`
    refactors the signature to require enum membership at write time.

    Per the `Four-category empty-output decision` rule (CLAUDE.md): all
    `record_failed` paths route through this enum's members; freeform
    strings deprecate post-Phase-2 cutover.
    """

    SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"
    """Pydantic / TypedDict / dataclass validation rejected the row (hard-
    required field missing or mistyped). Per
    ``hard_schema_enforcement_2026_05_08.md`` Phase 2, instruments-service
    orchestrator + MTDS adapter per-row try/except routes the offending row
    here with ``error_detail={field, expected_type, observed_value}`` so
    downstream tooling (alerting / dashboards) can branch on the field name."""

    UPSTREAM_TIMESTAMP_BIAS = "UPSTREAM_TIMESTAMP_BIAS"
    """Source returned ticks; ALL fall outside the requested day after
    ``interval_idx`` filter. UPSTREAM BUG — partition mislabeled at MTDS
    write-time, source replay covered wrong window, OR clock-skew. Matched
    to the existing ``UpstreamTimestampBiasError`` exception type."""

    MALFORMED_TICK_FIELD = "MALFORMED_TICK_FIELD"
    """Rows in window but downstream calc dropped all rows due to NaN /
    malformed source fields. Data-quality bug worth diagnosing. Matched to
    the existing ``MalformedTickFieldError`` exception type."""

    UPSTREAM_SUBGRAPH_ZERO = "UPSTREAM_SUBGRAPH_ZERO"
    """DeFi subgraph returned zero rows on a date the instruments-service
    catalog reports as alive. Per `Honest absence vs fake placeholders`
    asset-group rule: cefi / defi / tradfi cannot legitimately
    ``empty_confirmed`` at instrument-day grain when catalog says alive —
    must flip to ``attempted_failed``. Matched to the
    ``UpstreamSubgraphZeroError`` exception type (recursive-borrow Phase 1
    Bug 1 fix)."""

    CLUSTER_COVERAGE_VIOLATION = "CLUSTER_COVERAGE_VIOLATION"
    """Bundled shard's `record_captured` validation found fewer clusters
    than declared in `expected_root_clusters`. Examples: ES.OPT 11-cluster
    options-chain shipping with 8 clusters; prediction
    canonical_question_group bundle missing market_ids. Matched to the
    `ClusterCoverageError` exception type."""

    MALFORMED_ROW_KEY = "MALFORMED_ROW_KEY"
    """`ManifestWriter.record_captured` rejected the row_key shape for
    failing the per-asset-group shard-atom invariant (e.g. per-instrument
    shard missing `instrument_id`; bundled shard missing `chain` /
    `options_chain` / `canonical_question_group`). Phase 4 of
    `hard_schema_enforcement_2026_05_08.md`."""

    CLASSIFIED_VENUE_ERROR = "CLASSIFIED_VENUE_ERROR"
    """Catch-all for adapter errors classified via UAC `classify_venue_error()`
    (rate-limit / 5xx / connection-refused / timeout / circuit-tripped).
    Distinct from the structured taxonomy values above — those are
    workspace-side bugs; CLASSIFIED_VENUE_ERROR is venue-side transient or
    operational error that should typically retry. Existing
    ``record_failed(error=classify_venue_error(exc))`` callsites resolve here
    during the migration period."""

    UNCLASSIFIED_ADAPTER_ERROR = "UNCLASSIFIED_ADAPTER_ERROR"
    """Catch-all for adapter exceptions that did NOT pass through
    `classify_venue_error()` before reaching `record_failed`. Used as a
    transition-period bucket; Phase 2 of hard_schema_enforcement forces
    every callsite to either route via classify_venue_error OR pick a
    structured taxonomy member from this enum. Reviewer flag: any
    `record_failed` callsite producing this reason in production is a bug
    in the calling adapter."""

    UPSTREAM_LIVE_GAP = "UPSTREAM_LIVE_GAP"
    """Upstream live-data source (MTDS) emitted ``CONNECTIVITY_GAP_DETECTED``
    for this (venue, data_type) during the processing window. The downstream
    processor (MDPS) detected an ``attempted_failed`` row in the MTDS
    availability manifest with a connectivity-gap classification and propagates
    the gap upstream to avoid silent zero/partial candle output. Downstream
    consumers SHOULD skip or alert rather than retry — the gap will be filled
    when MTDS auto-backfills the window on ``CONNECTIVITY_RECOVERED``.
    SSOT: ``plans/active/mdps_streaming_and_backpressure_2026_05_07.md`` § item 524."""

    INCOMPLETE_PAYLOAD_PRE_FLATTENING = "INCOMPLETE_PAYLOAD_PRE_FLATTENING"
    """Historical shard written before the normalizer flattened nested sub-objects.
    The parquet exists but carries only stub pass-through columns (e.g. ``**raw``),
    not the per-row, per-entity columns the current schema declares.

    Migration shape (B.1 / C.4): flip manifest row to ``attempted_failed`` with this
    reason, delete the thin parquet, then re-fetch via a dedicated backfill VM so the
    normalizer writes the full flattened schema.

    Applies to:
    * instruments-service AF FIXTURE_STATS / FIXTURE_EVENTS / FIXTURE_LINEUPS / INJURIES
      (B.1 — flattening added UAC@c76e6d0)
    * instruments-service STANDINGS (Follow-up #1 — flattening added UAC@ac12d80)
    * instruments-service PLAYER_VALUES (C.4 — per-player flatten added UAC@3b29f7e)

    Downstream: callers SHOULD NOT attempt to join on per-entity columns; re-fetch
    is the only unblock. Re-fetch VMs should emit ``captured`` once the flat schema lands.
    Plan: ``plans/epics/sports_master.md`` § B.1."""

    UPSTREAM_LEG_FAILED = "UPSTREAM_LEG_FAILED"
    """Cross-instrument paired calc: one or both legs had ``attempted_failed`` status in the
    availability manifest for this date. The pairing cannot proceed — the failure propagates
    as ``attempted_failed`` (not ``empty_confirmed``) because the data was attempted but corrupt
    or unavailable, not simply absent due to a calendar gap.

    Emitted by: features-cross-instrument paired / cross-leg calculators when either leg has
    ``attempted_failed`` in the upstream manifest.

    Plan: ``writegate_honest_coverage_endtoend_2026_05_06.md`` Phase 2.E.3."""


RECORD_FAILED_REASONS: Final[frozenset[str]] = frozenset(member.value for member in RecordFailedReason)
"""String-membership view of :class:`RecordFailedReason` for fast O(1)
validation. ``ManifestWriter.record_failed`` Phase 2 refactor validates the
structured-reason kwarg against this set; freeform strings stay accepted
during the migration period (the legacy ``error: str`` arg).
"""


# ---------------------------------------------------------------------------
# Honest-coverage formula — SSOT for "what fraction of expected slots have we
# answered honestly?". Every numerator/denominator computation in the workspace
# MUST flow through :func:`compute_honest_coverage` so that deployment-api,
# deployment-ui, service data-status endpoints, and CI ratchet all agree.
#
# Plan: ``honest_coverage_formula_consolidation_2026_05_19.md``.
# Codified after the 2026-05-19 audit found three plans
# (writegate-endtoend, expected-unattempted-propagation, data-status-drilldown)
# each carried a partial formula with implicit numerator semantics.
# ---------------------------------------------------------------------------


class CaptureStatusCounts(NamedTuple):
    """Per-(asset_group, data_type, ...) capture_status row counts.

    Five fields, not four — the manifest's ``expected_unattempted`` state splits
    into two semantically-different sub-states for the honest-coverage formula:

    * ``expected_unattempted_known_empty`` — Tier-3 sentinel pre-resolved this
      slot to an ``EXPECTED_*`` reason (calendar pre-skip, pre-genesis, pre-listing).
      No fetch will ever land data here, so the slot IS honestly answered.
      Counts toward NUMERATOR.

    * ``expected_unattempted_pending_fetch`` — Tier-3 sentinel says "we expect
      data exists here but no adapter has run yet". This is a GAP. Counts in
      DENOMINATOR only — backfills must run to convert these into ``captured``,
      ``empty_confirmed`` (with ``SOURCE_RETURNED_ZERO``), or ``attempted_failed``.

    Producers (manifest reconcilers, data-status service, deployment-api):
    materialise these counts by grouping manifest rows on
    ``(capture_status, error_reason)``. The split rule is:

        if capture_status == "expected_unattempted":
            if error_reason.startswith("EXPECTED_"):
                bucket = "known_empty"
            else:
                bucket = "pending_fetch"

    Construct positionally or by name; all fields default to 0 for ergonomic
    partial counts (e.g. a freshly-bootstrapped asset_group may have only
    ``expected_unattempted_pending_fetch`` non-zero).
    """

    captured: int = 0
    empty_confirmed: int = 0
    attempted_failed: int = 0
    expected_unattempted_known_empty: int = 0
    expected_unattempted_pending_fetch: int = 0


def compute_honest_coverage(counts: CaptureStatusCounts) -> float:
    """Canonical honest-coverage ratio. Every caller in the workspace uses this.

    Formula (post-2026-05-19 consolidation):

        numerator   = captured + empty_confirmed + expected_unattempted_known_empty
        denominator = numerator + attempted_failed + expected_unattempted_pending_fetch
        coverage    = numerator / denominator     (returns 1.0 if denominator==0)

    Semantics in plain English: a slot is **honestly answered** if we have any
    truthful answer for it — data landed, or we confirmed it's empty, or the
    Tier-3 sentinel resolved it as known-empty-no-fetch-needed
    (``EXPECTED_HOLIDAY`` / ``EXPECTED_PRE_VENUE_LAUNCH`` / etc.). A slot is a
    **gap** if we tried and failed (``attempted_failed``) or if the sentinel
    says "expected to exist but we never tried" (non-``EXPECTED_*``
    ``expected_unattempted`` rows).

    Why ``known_empty`` is in the numerator: the writegate Phase 6.x plan
    states "production-grade >99% means real >99% — denominator clipped to
    legitimately-coverable shards". Equivalent rewording: rows that CAN'T
    have data (pre-genesis dates, holidays, delisted instruments) are not a
    gap, they're an honest answer. Excluding them from the numerator AND
    denominator (clipping) and including them in both (numerator-credit)
    produce the same ratio — we choose numerator-credit so the breakdown
    in the deployment-ui drilldown shows the count.

    SSOTs this function consolidates:

    * ``writegate_honest_coverage_endtoend_2026_05_06.md`` Phase 1B + 6.x
    * ``expected_unattempted_propagation_chain_2026_05_12.md`` Phase 2.A
      (the EXPECTED_/non-EXPECTED_ split for ``expected_unattempted`` rows)
    * ``data_status_drilldown_shard_atom_alignment_2026_05_07.md`` Phase 1
      endpoint (line 170-171: "numerator = manifest rows with
      ``capture_status=captured``" — superseded by this function)

    Callers:

    * ``deployment-api/deployment_api/services/data_status_service.py`` —
      per-(asset_group, data_type) panel rollup
    * ``deployment-api/deployment_api/services/data_status_drilldown_service.py``
      — per-shard drilldown
    * ``instruments-service`` + ``market-tick-data-service`` —
      ``/api/data-status`` endpoints + ``--operation=status`` CLI
    * ``deployment-ui`` — coverage % displayed in data-status panel (one
      formula, no client-side recomputation)
    * ``unified-trading-pm/scripts/qg/honest-coverage-ratchet.sh`` —
      CI gate (when shipped, writegate Phase 6.x follow-up)

    Edge case — empty manifest: returns 1.0 (treat "no expected slots" as
    fully covered). Reconcilers MUST seed expected_unattempted_pending_fetch
    rows before computing coverage; otherwise a brand-new asset_group reports
    a misleading 100%.
    """
    numerator = counts.captured + counts.empty_confirmed + counts.expected_unattempted_known_empty
    denominator = numerator + counts.attempted_failed + counts.expected_unattempted_pending_fetch
    if denominator == 0:
        return 1.0
    return numerator / denominator


HONEST_COVERAGE_GAP_FIELDS: Final[tuple[str, ...]] = (
    "attempted_failed",
    "expected_unattempted_pending_fetch",
)
"""The two ``CaptureStatusCounts`` fields that represent unanswered slots.

Use this when you need to enumerate "what's left to do" in a data-status
panel or backfill orchestrator without re-deriving the gap definition.
Backfill CLIs MUST retry rows in these two states when ``--force`` is OFF;
all other states (``captured`` / ``empty_confirmed`` /
``expected_unattempted_known_empty``) are skipped.
"""


# ---------------------------------------------------------------------------
# Bundled data_types — referenced by the ManifestWriter cluster-validation guard.
# ---------------------------------------------------------------------------


BUNDLED_DATA_TYPES: Final[frozenset[str]] = frozenset(
    {
        "options_chain",
        "futures_chain",
        "prediction_canonical_question_group",
        "sports_fixture_bundle",
        # Phase 3 of cme_polymarket_arb_2026_05_08: CME event-contract
        # shard atom (root, resolution_month, day) with cluster validation
        # on strike_threshold. Registered here so ManifestWriter enforces
        # cluster validation on record_captured calls for this data_type.
        "event_contract",
        # Per-fixture sports data_types — bundle = multiple bookmakers per fixture.
        # cluster_extractor: bookmaker. Registry: SPORTS_FIXTURE_CLUSTERS.
        "odds_snapshot",
        "odds_movement",
        "arbitrage_opportunity",
    }
)
"""Closed set of bundled data_types.

A "bundled" shard packs multiple cluster identities into a single
per-day parquet (e.g. all 11 ES.OPT clusters in one file, all bookmakers
for one fixture in one row group). Cluster validation at
``record_captured`` is mandatory for these types — silent partial
bundles are the failure mode this set guards against.

Adding a new bundled data_type means adding it here AND seeding its
cluster registry (per-root, per-fixture-tier, etc.) in this module or a
neighbouring module. No half-measures: the writer guard fires the
moment the data_type appears, regardless of whether the registry has
been populated.
"""


# ---------------------------------------------------------------------------
# Futures expiry-bucket derivation.
#
# The ``futures_chain`` bundle row schema doesn't natively carry an
# expiry-bucket column — we derive it from the raw symbol so the
# cluster gate can fire meaningfully. Front/back is the analogue of
# ES.OPT's per-root cluster split for the futures bundle.
# ---------------------------------------------------------------------------


_DATED_FUT_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Z0-9]{1,4})([FGHJKMNQUVXZ])(\d{1,2})$")
"""Match a dated futures symbol (``ESM6``, ``NQU24``, ``CLZ5``)."""

_CME_MONTH_MAP: Final[dict[str, int]] = {
    "F": 1,
    "G": 2,
    "H": 3,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "U": 9,
    "V": 10,
    "X": 11,
    "Z": 12,
}


def _expand_two_digit_year(year_token: str) -> int:
    if len(year_token) == 1:
        return 2020 + int(year_token)
    return 2000 + int(year_token)


def parse_futures_expiry(symbol: str) -> _dt.date | None:
    """Parse the expiry date out of a dated futures symbol.

    Returns ``None`` for shapes the parser doesn't handle (combos,
    continuous codes, options, equities) — caller should fall through
    to other parsers (OSI option, ICE, etc.).

    Uses the third Friday of the contract month as the canonical listed
    expiry (CME convention). Callers needing FX-future-grade precision
    must use ``DatabentoClassification.expiry_date`` instead — this
    helper is for cluster bucketing, not order-routing.

    Args:
        symbol: Raw symbol string (e.g. ``"ESM6"``, ``"NQU24"``).

    Returns:
        Expiry ``date`` or ``None`` if unparseable.
    """
    match = _DATED_FUT_RE.match(symbol.strip().upper())
    if match is None:
        return None
    month = _CME_MONTH_MAP[match.group(2)]
    year = _expand_two_digit_year(match.group(3))
    first = _dt.date(year, month, 1)
    first_friday_day = 1 + (4 - first.weekday()) % 7
    return _dt.date(year, month, first_friday_day + 14)


def futures_expiry_bucket(
    symbol: str,
    as_of: _dt.date,
    *,
    front_window_days: int = 60,
) -> str:
    """Bucket a futures symbol's expiry into ``front`` / ``back`` / ``spread`` / ``unknown``.

    Used as the ``cluster_extractor`` for ``futures_chain`` bundle
    validation. Bucket semantics:

    * ``"front"`` — expiry within ``front_window_days`` of ``as_of``
      (default 60d). Most-active contract.
    * ``"back"`` — dated future beyond the front window.
    * ``"spread"`` — calendar spread / combo (symbol contains ``-``).
    * ``"unknown"`` — symbol doesn't parse as a dated future and isn't
      a recognised spread shape (continuous codes, equities, options).

    Args:
        symbol: Raw symbol string.
        as_of: Reference date for the front-vs-back classification
            (typically the partition date).
        front_window_days: Threshold in days for the front bucket.

    Returns:
        Bucket name as a string (one of :data:`FUTURES_CHAIN_BUCKETS`
        plus ``"unknown"``).
    """
    if not symbol:
        return "unknown"
    cleaned = symbol.strip().upper()
    if "-" in cleaned:
        return "spread"
    expiry = parse_futures_expiry(cleaned)
    if expiry is None:
        return "unknown"
    days_to_expiry = (expiry - as_of).days
    if 0 <= days_to_expiry <= front_window_days:
        return "front"
    return "back"


FUTURES_CHAIN_BUCKETS: Final[frozenset[str]] = frozenset({"front", "back", "spread"})
"""Expected cluster set for ``futures_chain`` bundles.

Most roots emit at least a front + back contract on any given day;
spread-only days are rare and treated as honest absence
(``record_empty`` by the adapter, not a cluster failure).
"""


# ---------------------------------------------------------------------------
# DATA_TYPE_TO_CLUSTER_REGISTRY — bundled-data_type → registry-name mapping.
#
# Companion to :data:`BUNDLED_DATA_TYPES`. The UTL ``record_captured`` guard
# (``MissingClusterValidationError``) cites this registry name in the error
# message so adapters know exactly which UAC SSOT to look up. Kept as a
# string→string mapping rather than a string→object to avoid eagerly
# importing every registry module from honest_coverage import paths.
# ---------------------------------------------------------------------------


DATA_TYPE_TO_CLUSTER_REGISTRY: Final[dict[str, str]] = {
    "options_chain": "ES_OPTIONS_CLUSTERS",
    "futures_chain": "FUTURES_CHAIN_BUCKETS",
    "prediction_canonical_question_group": "PREDICTION_GROUPS",
    "sports_fixture_bundle": "SPORTS_FIXTURE_CLUSTERS",
    "event_contract": "EVENT_CONTRACT_ROOT_CLUSTERS",
    "odds_snapshot": "SPORTS_FIXTURE_CLUSTERS",
    "odds_movement": "SPORTS_FIXTURE_CLUSTERS",
    "arbitrage_opportunity": "SPORTS_FIXTURE_CLUSTERS",
}


# ---------------------------------------------------------------------------
# SPORTS_FIXTURE_CLUSTERS — tier-1 EU football seed (greenfield 2026-05-06).
#
# Per-(league_tier) → expected bookmaker set. Used as the cluster registry
# for ``sports_fixture_bundle`` data_types (ODDS_SNAPSHOT / ODDS_MOVEMENT /
# ARBITRAGE per the writegate plan). A bundle that covers fewer bookmakers
# than the league-tier expects flips to ``attempted_failed[ClusterCoverageError]``
# instead of silently passing as ``captured``.
#
# Tier-1 seed: top 5 European football leagues (EPL, LaLiga, Bundesliga,
# Serie A, Ligue 1). Tier-2 / tier-3 expansion is a follow-up plan slot —
# don't pre-build until a real consumer needs it.
# ---------------------------------------------------------------------------


SPORTS_FIXTURE_CLUSTERS: Final[dict[str, dict[str, int]]] = {
    "tier_1_eu_football": {
        # Bookmakers required for a tier-1 EU football fixture odds bundle to
        # count as ``captured``. Numbers are minimum row counts per bookmaker
        # per fixture per snapshot — tuneable per the data_status_multi_axis
        # plan's "feature_group → required_inputs" framework.
        "pinnacle": 1,
        "bet365": 1,
        "william_hill": 1,
        "bwin": 1,
        "betfair_exchange": 1,
    },
}
"""Per-league-tier expected bookmaker sets for sports_fixture_bundle shards.

Tier-1 EU football seed only (writegate plan Phase 1B). Tier-2 / tier-3
expansion deferred to a follow-up plan slot — don't pre-build without a
real consumer.
"""


# ---------------------------------------------------------------------------
# PREDICTION_GROUPS — empty placeholder slot (temporary state).
#
# Populated by ``predictions_canonical_question_group_polymarket_migration_2026_05_06``
# Phase 1A. The slot is reserved here so the UTL writer guard
# (``MissingClusterValidationError``) fires consistently for the
# ``prediction_canonical_question_group`` data_type even before predictions
# Phase 1A lands. Until that plan ships, no caller passes this data_type;
# the guard surface is correct-by-construction.
#
# Documented in the writegate plan's "Temporary states + their canonical
# follow-up plans" section.
# ---------------------------------------------------------------------------


PREDICTION_GROUPS: Final[dict[str, dict[str, int]]] = {
    # Cadenced range-bracket markets — count is min ticks per market_id
    # required for the bundle to count as ``captured``. HOURLY markets
    # tick fast through their 1-hour life (~1000 events typical);
    # DAILY markets tick over 24h (~10000 events typical). Lower bounds
    # are intentionally conservative — adapters that fall short flip
    # the bundle to ``attempted_failed[ClusterCoverageError]`` instead
    # of silently passing.
    #
    # Cluster keys are market_ids; the cluster_extractor lambda is
    # ``lambda row: row["market_id"]``. Per-day expected market_id set
    # is derived at runtime from the lifecycle table
    # (via ``unified_api_contracts.canonical.domain.predictions.lifecycle.expected_market_ids_for_canonical_group``);
    # the registry carries the per-market min row count only.
    "BTC_UP_DOWN_HOURLY": {"_per_market_min_rows": 100},
    "BTC_UP_DOWN_DAILY": {"_per_market_min_rows": 1000},
    "ETH_UP_DOWN_HOURLY": {"_per_market_min_rows": 100},
    "ETH_UP_DOWN_DAILY": {"_per_market_min_rows": 1000},
    "SPX_UP_DOWN_DAILY": {"_per_market_min_rows": 1000},
    # CME event-contract linked groups — predictions_master Phase 5.
    # Min-row floors set conservatively at 500 (daily market, ~30min resolution
    # window before CME 21:00 UTC settlement; Polymarket thinner than BTC/ETH).
    "NDX_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "RUT_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "DJIA_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "GOLD_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "CRUDE_OIL_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "NATGAS_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "EUR_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "FED_RATE_DECISION_PER_FOMC": {"_per_market_min_rows": 100},
    "CPI_PRINT_PER_MONTH": {"_per_market_min_rows": 100},
    "ELECTION_PRESIDENT_2028": {"_per_market_min_rows": 100},
    "OSCARS_BEST_PICTURE": {"_per_market_min_rows": 50},
    # OTHER intentionally absent — markets that classify into OTHER
    # bypass the cluster gate (no expected market_id set), but the
    # manifest still records the capture for audit purposes.
}
"""Per-canonical_question_group expected market_id sets.

Keyed by canonical_question_group name (string form of
:class:`unified_api_contracts.canonical.domain.predictions.canonical_groups.CanonicalQuestionGroup`).
Each group's inner dict carries a ``_per_market_min_rows`` floor — the
cluster gate at ``ManifestWriter.record_captured`` derives the per-day
expected market_id set from the lifecycle table at runtime and applies
this min-rows floor per market_id.

Populated by predictions plan
``predictions_canonical_question_group_polymarket_migration_2026_05_06.plan``
Phase 1A.
"""


# ---------------------------------------------------------------------------
# EVENT_CONTRACT_ROOT_CLUSTERS — CME binary event-contract shard atom.
#
# Shard atom: (asset_group=tradfi, venue=CME, data_type=EVENT_CONTRACT,
#   root, resolution_date, day). Each root (ECES/ECBTC/etc.) bundles
# multiple (resolution_date, strike_threshold) clusters in one per-day
# parquet. The expected cluster set is derived at runtime from the
# instruments-service catalog; this registry carries the per-cluster
# min-rows floor (1 row per (resolution_date, strike_threshold) pair is
# the minimum — each binary is a distinct YES/NO contract).
#
# 9 roots: ECES (SP500) · ECNQ (NASDAQ100) · ECRTY (RUSSELL2000) ·
#   ECYM (DOW) · ECGC (GOLD) · ECCL (CRUDE) · ECNG (NATGAS) ·
#   EC6E (EUR) · ECBTC (BTC).
# Databento coverage starts 2025-09-28 for all roots.
# SSOT: cme_polymarket_arb_2026_05_08.md Phase 3.
# ---------------------------------------------------------------------------


EVENT_CONTRACT_ROOT_CLUSTERS: Final[dict[str, dict[str, int]]] = {
    "ECES": {"_per_cluster_min_rows": 1},
    "ECNQ": {"_per_cluster_min_rows": 1},
    "ECRTY": {"_per_cluster_min_rows": 1},
    "ECYM": {"_per_cluster_min_rows": 1},
    "ECGC": {"_per_cluster_min_rows": 1},
    "ECCL": {"_per_cluster_min_rows": 1},
    "ECNG": {"_per_cluster_min_rows": 1},
    "EC6E": {"_per_cluster_min_rows": 1},
    "ECBTC": {"_per_cluster_min_rows": 1},
}
"""Per-root minimum-rows floor for CME EVENT_CONTRACT bundle shards.

Keyed by CME root symbol (ECES, ECNQ, etc.). The actual expected cluster
set (resolution_date x strike_threshold tuples) is derived at runtime
from the instruments-service catalog — this registry only supplies the
``_per_cluster_min_rows`` floor. A bundle missing any expected cluster
flips to ``attempted_failed[ClusterCoverageError]`` instead of silently
passing as ``captured``.

Registered in :data:`DATA_TYPE_TO_CLUSTER_REGISTRY` under key
``"EVENT_CONTRACT"`` and in :data:`BUNDLED_DATA_TYPES`.
Populated by cme_polymarket_arb_2026_05_08 Phase 3.
"""


class EmptyFromLiveInstrumentError(ValueError):
    """Raised when an adapter tries to ``record_empty(reason=SOURCE_RETURNED_ZERO)`` for a
    ``(venue, instrument_id, day)`` tuple that the instruments-service catalog says was ALIVE on the day.

    Operator directive 2026-05-07 (writegate Phase 3.D.5): when MTDS / MDPS / features-* attempts an
    instrument and the source returns nothing, but the catalog confirms the instrument was listed +
    not-yet-delisted on that day, the writer MUST classify this as a real failure (``attempted_failed``)
    rather than a legitimate empty (``empty_confirmed``). Silent fallback to ``empty_confirmed`` was the
    root cause of the 2026-05-07 RED ALERT incident (5 CeFi VMs writing 96-100% empty rows for
    bitfinex / bitget / kraken — all blank ``error_reason``, all for instruments the catalog confirmed
    alive).

    Adapters / callers see this exception and should re-route the write to
    ``record_failed(EmptyFromLiveInstrumentError(...))`` carrying enough context for the operator to
    diagnose: which instrument, which day, what the source returned (HTTP status / row count / response
    sample). The orchestrator's retry-attempted_failed-by-default logic then re-attempts on next VM run.

    Args:
        venue: The venue the catalog says was alive.
        instrument_id: The specific instrument the catalog says was listed.
        day: ISO YYYY-MM-DD the catalog says the instrument was tradeable on.
        source_evidence: Optional structured detail (HTTP code, raw row count, response sample) for
            operator diagnosis.

    Reference: writegate plan
    ``writegate_honest_coverage_endtoend_2026_05_06.plan`` Phase 3.D.5 Wave 2.
    """

    def __init__(
        self,
        venue: str,
        instrument_id: str,
        day: str,
        source_evidence: str | None = None,
    ) -> None:
        self.venue = venue
        self.instrument_id = instrument_id
        self.day = day
        self.source_evidence = source_evidence
        suffix = f" — source evidence: {source_evidence}" if source_evidence else ""
        super().__init__(
            f"record_empty(reason=SOURCE_RETURNED_ZERO) rejected: instruments-service catalog says "
            f"{instrument_id!r} was ALIVE on {venue}/{day}. Use record_failed("
            f"EmptyFromLiveInstrumentError(...)) instead — this is a real fetch failure, not honest "
            f"absence.{suffix}"
        )


class LegacyBlankErrorReasonError(ValueError):
    """Raised by ``ManifestWriter.record_empty(reason="")`` to surface the silent-fallback bug pattern.

    Pre-2026-05-07 some adapter paths could call ``record_empty()`` with an empty ``reason``, producing
    manifest rows with ``capture_status=empty_confirmed`` AND blank ``error_reason``. This violated the
    Phase 2.E taxonomy contract (every empty_confirmed row must carry a typed reason) AND silently
    masked real fetch failures (e.g. the 2026-05-07 RED ALERT: 5 CeFi VMs at 96-100% empty with all blank
    reasons).

    Wave 2 of writegate Phase 3.D.5 strengthens ``record_empty`` to raise this loudly when ``reason`` is
    empty — adapters MUST always pass a typed reason from the closed set, OR call ``record_failed`` if
    the absence is unexpected. The migration script
    ``reconcile_blank_error_reason_rows.py`` fixes the historical blank-reason rows by reclassifying
    them: catalog-says-alive cases get flipped to ``attempted_failed`` with this exception's repr;
    catalog-says-not-alive cases get a proper ``EXPECTED_*`` reason.
    """

    def __init__(self, callsite_hint: str = "") -> None:
        suffix = f" [{callsite_hint}]" if callsite_hint else ""
        super().__init__(
            "record_empty() called with blank reason. Pass a typed reason from EMPTY_CONFIRMED_REASONS "
            "(EXPECTED_HOLIDAY / EXPECTED_WEEKEND / EXPECTED_PRE_VENUE_LAUNCH / "
            "EXPECTED_PRE_GENESIS_CHAIN / EXPECTED_PRE_SOURCE_COVERAGE_START / "
            "EXPECTED_INSTRUMENT_NOT_LISTED / EXPECTED_INSTRUMENT_DELISTED / "
            "EXPECTED_PARTIAL_HALF_DAY / EXPECTED_PAUSED_LEAGUE / EXPECTED_DEPRECATED_DATA_TYPE / "
            "EXPECTED_REFDATA_CADENCE_CHANGE / EXPECTED_KNOWN_SOURCE_GAP / "
            "SOURCE_RETURNED_ZERO), or use record_failed if the "
            "absence is unexpected." + suffix
        )


__all__ = [
    "BUNDLED_DATA_TYPES",
    "DATA_TYPE_TO_CLUSTER_REGISTRY",
    "EMPTY_CONFIRMED_REASONS",
    "ES_OPTIONS_CLUSTERS",
    "ES_OPTIONS_DEFAULT_MIN_ROWS_PER_CLUSTER",
    "EVENT_CONTRACT_ROOT_CLUSTERS",
    "EXPECTED_EMPTY_REASON_PREFIX",
    "FUTURES_CHAIN_BUCKETS",
    "PREDICTION_GROUPS",
    "SPORTS_FIXTURE_CLUSTERS",
    "EmptyConfirmedReason",
    "EmptyFromLiveInstrumentError",
    "LegacyBlankErrorReasonError",
    "extract_es_options_cluster",
    "futures_expiry_bucket",
    "get_active_es_options_clusters_for_date",
    "parse_futures_expiry",
]
