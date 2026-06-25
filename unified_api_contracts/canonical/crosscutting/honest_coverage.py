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
  underlying root (rows already partition by underlying). Implementation
  (with the coverage-math + instrument-liveness helpers) lives in
  :mod:`unified_api_contracts.canonical.crosscutting._honest_coverage_logic`
  and is re-exported here — this module stays the import surface.

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

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final

from unified_api_contracts.canonical.crosscutting._honest_coverage_clusters import (
    BUNDLED_DATA_TYPES,
    DATA_TYPE_TO_CLUSTER_REGISTRY,
    EVENT_CONTRACT_ROOT_CLUSTERS,
    PREDICTION_GROUPS,
    SPORTS_FIXTURE_CLUSTERS,
)
from unified_api_contracts.canonical.crosscutting._honest_coverage_logic import (
    FUTURES_CHAIN_BUCKETS,
    HONEST_COVERAGE_GAP_FIELDS,
    SCHEDULE_DEFINING_DATA_TYPES,
    CaptureStatusCounts,
    EmptyFromLiveInstrumentError,
    LayeredCoverage,
    LegacyBlankErrorReasonError,
    compute_honest_coverage,
    compute_layered_coverage,
    futures_expiry_bucket,
    is_resolved_schedule_empty,
    parse_futures_expiry,
    was_instrument_alive,
)
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

    EXPECTED_NOT_ENOUGH_TVL = "EXPECTED_NOT_ENOUGH_TVL"
    """DeFi: a pool/market EXISTS on-chain on the day but its TVL is below the MVP TVL
    threshold — so it is outside the capture universe for that day (the TVL filter IS the
    MVP filter; ``defi_instrument_catalogue_and_capture_pipeline_2026_06_23.md``). This is a
    GENUINE honest-empty (the instrument is real, the source could be reached, but we
    deliberately do not capture sub-threshold pools), distinct from:
    ``EXPECTED_INSTRUMENT_NOT_LISTED`` (pool did not exist yet / not in catalogue),
    ``EXPECTED_INSTRUMENT_DELISTED`` (pool removed AFTER the date), and
    ``SOURCE_RETURNED_ZERO`` (the source WAS fetched at-threshold and returned 200+0-rows,
    proven via FetchEvidence). Keystone-exempt: no fetch is warranted for a sub-TVL pool, so
    NO ``FetchEvidence`` is required (mirrors the ``EXPECTED_*`` no-fetch family).
    OUT-of-coverage-window (the TVL floor is a deliberate scope boundary, not a gap) →
    excluded from the completion-% denominator (in ``OUT_OF_COVERAGE_WINDOW_REASONS``)."""

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

    EXPECTED_SOURCE_DOES_NOT_OFFER_DATA_TYPE = "EXPECTED_SOURCE_DOES_NOT_OFFER_DATA_TYPE"
    """Per-(venue/source, data_type): the venue's BATCH source structurally does not offer this data_type at
    all — no historical endpoint / archive prefix / feed exists for it, so a zero-row cell is honest absence by
    design, NOT a fetch failure and NOT a clean 200+empty (no fetch is even warranted). Distinct from
    ``EXPECTED_SOURCE_DOES_NOT_COVER_LEAGUE`` (a source covers the data_type but not a particular league) and
    from ``SOURCE_RETURNED_ZERO`` (the source WAS reached and returned 200+empty — proven via FetchEvidence).
    This is "the source has no way to serve this data_type, ever."

    Reference cases (CeFi on-chain perps, operator-confirmed 2026-06-22):
    * **ASTER ``book_snapshot_5``** — Aster's Binance-compatible REST exposes only a CURRENT-book ``/fapi/v1/depth``
      snapshot; there is NO historical order-book endpoint, so batch book_snapshot_5 can never be sourced (live-WS
      capture only).
    * **HYPERLIQUID ``liquidations``** — Hyperliquid publishes no public liquidation feed (neither the S3 archive
      nor the REST API exposes one).

    Coverage: OUT-of-window (never collectable) → excluded from the data-status completion-% denominator (in
    ``OUT_OF_COVERAGE_WINDOW_REASONS``). SSOT:
    ``plans/active/issues/cefi_hl_aster_batch_data_gaps_2026_06_22.md`` BUG #3."""

    EXPECTED_BOOKMAKER_NO_LEAGUE_COVERAGE = "EXPECTED_BOOKMAKER_NO_LEAGUE_COVERAGE"
    """Sports ODDS per-(bookmaker, league): an Odds-API bookmaker legitimately doesn't price this league —
    the OBSERVED captured corpus shows the (book, league) pair has never produced an odds row, so a zero-row
    fixture there is honest absence, not a fetch failure. Distinct from ``EXPECTED_SOURCE_DOES_NOT_COVER_LEAGUE``
    (a feed *source* like Understat with a fixed league whitelist): here the *source* is Odds-API and the axis is
    the per-BOOKMAKER (book x league) observed-coverage map. Closes the ~72% ``attempted_failed`` over-count
    where the per-bookmaker x per-fixture sentinel fan-out forced every niche book's no-coverage zero-row to
    ``attempted_failed`` via the live-instrument guard. SSOT:
    ``unified_api_contracts.registry.sports_bookmaker_league_coverage.is_bookmaker_league_covered``."""

    EXPECTED_NO_PROVIDER_COVERAGE = "EXPECTED_NO_PROVIDER_COVERAGE"
    """Sports per-(league, per-fixture-entity): API-Football legitimately doesn't provide this enrichment
    entity (``PLAYER_STATS`` / ``FIXTURE_LINEUPS`` / ``FIXTURE_EVENTS`` / ``FIXTURE_STATS`` / ``TEAMS`` /
    ``STANDINGS`` / ``INJURIES``) for this league — the OBSERVED captured corpus shows the (league, entity)
    pair has NEVER produced a row, so the per-fixture enrichment for that (league, entity) is honest absence
    (a zero-row fixture there is NOT a fetch failure). Old/lower-division leagues commonly have no
    player-stats / lineups coverage in API-Football (measured: ~57% of ``/fixtures/players`` calls return 0,
    729 of 790 leagues never yield PLAYER_STATS). The instruments-service enrichment SKIPS the API call for
    an out-of-coverage (league, entity) entirely (kills the wasted fan-out) and records this reason so the
    cell reads honest-empty instead of the live-instrument guard forcing ``attempted_failed``.

    Distinct from ``EXPECTED_BOOKMAKER_NO_LEAGUE_COVERAGE`` (per-BOOKMAKER, source=Odds-API odds) and
    ``EXPECTED_SOURCE_DOES_NOT_COVER_LEAGUE`` (a whole feed *source* like Understat with a fixed league
    whitelist): here the source is API-Football and the axis is per-(league, ENTITY) observed-coverage — the
    SAME source covers some entities but not others for the same league. SSOT:
    ``unified_api_contracts.registry.sports_league_entity_coverage.is_league_entity_covered``."""

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

    EXPECTED_NO_MAPPING = "EXPECTED_NO_MAPPING"
    """A canonical entity exists for the (source, day) but the source-specific provider mapping
    required to fetch it is absent, so no fetch was attempted. The data is a *legitimate expected
    absence for this run* — not a calendar gap and not a fetch failure — because the source cannot
    address the entity without the mapping.

    Distinct from ``EXPECTED_NO_FIXTURE`` (a fixture genuinely was not scheduled — a calendar gap)
    and from ``attempted_failed`` (a fetch was attempted and errored). Use this when the absence
    cause is "we have no provider id/route for this entity", e.g. a Transfermarkt league with no
    ``provider_league_ids["transfermarkt"]`` mapping. If/when the mapping is added, the entity
    becomes fetchable — so consumers may surface this as "coverage-extendable" rather than
    "permanently empty".

    Used by: instruments-service sports write-paths when a per-league provider mapping is missing.
    Added 2026-06-01 (capture_status write-path audit — manifest_master)."""

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


# ---------------------------------------------------------------------------
# Coverage-denominator partition (operator direction 2026-06-12) — split the
# ``empty_confirmed`` reasons into OUT-OF-WINDOW (the (entity, date, scope) tuple
# is OUTSIDE what could ever have data: chain/venue/source didn't exist yet or
# stopped, instrument not listed / delisted, league season not started / ended,
# data_type out-of-MVP-scope / deprecated / out-of-processing-scope, or no fixture
# that day) vs WITHIN-WINDOW expected absence (entity existed + in scope, cell
# legitimately empty: weekend / holiday / paused / postponed / ...).
#
# Out-of-window cells are NOT coverage gaps — there was nothing to capture — so the
# data-status completion-% EXCLUDES them. Counting them made defi read 22% when the
# true in-window coverage was ~2x, and surfaced "731 dates missing (2018-01-01...)" for
# chains that launched 2021-2023 (operator eyeball 2026-06-12). The raw manifest rows
# are UNTOUCHED (still honestly ``empty_confirmed`` + reason for ML NaN-fill /
# feature-window / execution consumers) — only the coverage AGGREGATION reclassifies
# them into a separate non-counting ``out_of_window`` bucket. Conservative default:
# calendar-empties (weekend/holiday/half-day/outside-hours/paused/postponed) stay IN
# the denominator (a covered venue's weekend gap is part of the coverable universe).
# ---------------------------------------------------------------------------

OUT_OF_COVERAGE_WINDOW_REASONS: Final[frozenset[str]] = frozenset(
    {
        EmptyConfirmedReason.EXPECTED_PRE_GENESIS_CHAIN.value,
        EmptyConfirmedReason.EXPECTED_PRE_VENUE_LAUNCH.value,
        EmptyConfirmedReason.EXPECTED_PRE_SOURCE_COVERAGE_START.value,
        EmptyConfirmedReason.EXPECTED_PAST_SOURCE_COVERAGE_END.value,
        EmptyConfirmedReason.EXPECTED_INSTRUMENT_NOT_LISTED.value,
        EmptyConfirmedReason.EXPECTED_INSTRUMENT_DELISTED.value,
        EmptyConfirmedReason.EXPECTED_NOT_ENOUGH_TVL.value,
        EmptyConfirmedReason.EXPECTED_PRE_SEASON.value,
        EmptyConfirmedReason.EXPECTED_POST_SEASON.value,
        EmptyConfirmedReason.EXPECTED_SOURCE_DOES_NOT_COVER_LEAGUE.value,
        EmptyConfirmedReason.EXPECTED_SOURCE_DOES_NOT_OFFER_DATA_TYPE.value,
        EmptyConfirmedReason.EXPECTED_NO_PROVIDER_COVERAGE.value,
        EmptyConfirmedReason.EXPECTED_OUT_OF_COVERAGE_WINDOW.value,
        EmptyConfirmedReason.EXPECTED_DEPRECATED_DATA_TYPE.value,
        EmptyConfirmedReason.EXPECTED_OUTSIDE_PROCESSING_SCOPE.value,
        EmptyConfirmedReason.EXPECTED_NO_FIXTURE.value,
        EmptyConfirmedReason.EXPECTED_NO_MAPPING.value,
        EmptyConfirmedReason.EXPECTED_LEGACY_MIGRATION_MISSING_EXPIRY.value,
    }
)
"""``empty_confirmed`` reasons OUTSIDE the coverable window/scope — excluded from the
data-status completion-% denominator (never collectable). SSOT for the coverage
``out_of_window`` bucket. See module note above + ``codex/02-data/honest-absence-downstream-handling.md``."""

WITHIN_WINDOW_EXPECTED_ABSENCE_REASONS: Final[frozenset[str]] = frozenset(
    EMPTY_CONFIRMED_REASONS - OUT_OF_COVERAGE_WINDOW_REASONS
)
"""``empty_confirmed`` reasons where the entity existed + was in scope but the cell is a
legitimate gap (weekend/holiday/paused/postponed/...). These COUNT in the denominator."""


def is_out_of_coverage_window(reason: str | None, data_type: str | None = None) -> bool:
    """True if a cell is OUTSIDE the coverable window/scope (never collectable →
    excluded from the coverage-% denominator).

    Two paths to out-of-window:

    * ``reason`` is one of :data:`OUT_OF_COVERAGE_WINDOW_REASONS` (lifecycle /
      scope cells: pre-genesis, pre-launch, delisted, no-fixture, …). Blank/None
      reason → a within-window absence by default (counts).
    * **schedule-defining empty** (operator direction 2026-06-23): when
      ``data_type`` is supplied AND it is a schedule-DEFINING data_type (sports
      ``FIXTURES`` — the API-Football schedule), a ``SOURCE_RETURNED_ZERO`` cell
      means "no matches that day = complete" → RESOLVED, out-of-window. This is
      DATA-TYPE-AWARE: ``SOURCE_RETURNED_ZERO`` for an ENRICHMENT data_type stays
      a within-window gap (its zero may be real). See
      :func:`is_resolved_schedule_empty`.

    Callers that have the ``data_type`` for the row SHOULD pass it so FIXTURES
    no-match-day empties stop counting as gaps; callers without it (legacy
    reason-only scope) get the unchanged reason-set behaviour.
    """
    if bool(reason) and reason in OUT_OF_COVERAGE_WINDOW_REASONS:
        return True
    return is_resolved_schedule_empty(data_type, reason)


def is_within_window_absence(reason: str | None, data_type: str | None = None) -> bool:
    """Complement of :func:`is_out_of_coverage_window` — the cell IS in the coverable
    universe and counts in the denominator (blank/None or any non-out-of-window reason).
    Pass ``data_type`` so a schedule-defining FIXTURES no-match-day empty is correctly
    treated as out-of-window (resolved), not an in-window absence."""
    return not is_out_of_coverage_window(reason, data_type)


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

    REFERENCE_STATUS_DISCREPANCY = "REFERENCE_STATUS_DISCREPANCY"
    """A reference-data source (e.g. api_football FIXTURES) reported a fixture
    as terminal (``CANCELLED`` / ``POSTPONED``) but a cross-source ground truth
    (footystats / SFI / understat) shows the fixture has real match data
    (lineups + stats + events present). The cross-source verifier
    (``unified_trading_library.fixtures.verify_fixture_status``) flips the
    status to ``POSTPONED_RESCHEDULED`` and re-emits the corrected row as
    ``captured``; the ORIGINAL mis-flagged row is recorded ``attempted_failed``
    with this reason so consumers can audit the override. Pairs with the
    ``FIXTURES_STATUS_DISCREPANCY`` lifecycle event.

    Plan: ``plans/epics/sports_master.md`` § "Cross-source fixture status
    verifier". SSOT: ``codex/02-data/sports-fixtures-lifecycle.md``."""


RECORD_FAILED_REASONS: Final[frozenset[str]] = frozenset(member.value for member in RecordFailedReason)
"""String-membership view of :class:`RecordFailedReason` for fast O(1)
validation. ``ManifestWriter.record_failed`` Phase 2 refactor validates the
structured-reason kwarg against this set; freeform strings stay accepted
during the migration period (the legacy ``error: str`` arg).
"""


# ---------------------------------------------------------------------------
# Proof-of-honest-absence — FetchEvidence value-object + disqualifying signals.
#
# Failure class C1 (data_pipeline_hardening_self_monitoring_2026_06_22.md
# Phase 1, KEYSTONE): ``record_empty(reason=SOURCE_RETURNED_ZERO)`` is today
# taken on TRUST — nothing proves the HTTP call returned 200+empty rather than
# a 401 / 403 / 429 / 5xx / timeout / exception that fell through to the
# honest-absence recorder. The 2026-05-07 RED ALERT (5 CeFi VMs at 96-100%
# empty with blank reasons) was the first instance; subsequent incidents
# (sports API-Football errors→empty, odds_api_ws nonexistent-key→0 rows,
# Databento WS key unresolved→mis-stamped) all share the same root cause:
# an error/missing-key path masquerading as legitimate honest absence.
#
# :class:`FetchEvidence` makes honest-absence a PROVEN state. The UTL writer
# gate (Phase 1 P0) requires accompanying evidence whose
# :meth:`FetchEvidence.proves_honest_absence` is True before accepting a
# ``SOURCE_RETURNED_ZERO`` empty; otherwise it raises
# :class:`UnprovenHonestAbsenceError`, steering the adapter to
# ``record_failed`` instead. The ``EXPECTED_*`` calendar reasons are EXEMPT
# (no fetch was attempted — they are calendar-pre-skips).
#
# Registry SSOT: DP-FETCH-001 in
# ``codex/05-infrastructure/data-pipeline-alerts.registry.yaml``.
# ---------------------------------------------------------------------------


class FetchErrorSignal(StrEnum):
    """Closed-set vocabulary of ``FetchEvidence.error_signal`` values that
    DISQUALIFY a fetch from proving honest absence.

    Any member present on a :class:`FetchEvidence` means the source was NOT
    cleanly reached-and-empty — the adapter MUST ``record_failed`` (typically
    via :class:`RecordFailedReason`) rather than
    ``record_empty(SOURCE_RETURNED_ZERO)``. The empty ``error_signal=""``
    (no member) is the ONLY value compatible with honest absence.

    Mirrors how :data:`EMPTY_CONFIRMED_REASONS` derives from
    :class:`EmptyConfirmedReason`: :data:`DISQUALIFYING_FETCH_SIGNALS` is the
    string-membership view of this enum for the writer hot path.
    """

    HTTP_NON_2XX = "HTTP_NON_2XX"
    """The HTTP response carried a status outside the 2xx range (and not one of
    the more-specific signals below) — the body's emptiness is meaningless."""

    AUTH_401 = "AUTH_401"
    """HTTP 401 Unauthorized — missing/invalid auth; zero rows is an auth bug,
    not honest absence."""

    AUTH_403 = "AUTH_403"
    """HTTP 403 Forbidden — credential lacks permission for this resource."""

    RATE_LIMITED_429 = "RATE_LIMITED_429"
    """HTTP 429 / rate-limit — the source throttled us; retry with backoff
    (DP-FETCH-003 auto-recover) rather than recording the throttle as empty."""

    SERVER_5XX = "SERVER_5XX"
    """HTTP 5xx server error — upstream fault; empty body is not honest
    absence."""

    TIMEOUT = "TIMEOUT"
    """The request timed out before a response was received."""

    CONNECT_ERROR = "CONNECT_ERROR"
    """Connection-level failure (DNS / TCP / TLS) — the source was never
    reached."""

    ADAPTER_EXCEPTION = "ADAPTER_EXCEPTION"
    """An exception was raised inside the adapter while fetching/parsing —
    the zero-row result is a side effect of the crash, not honest absence."""

    MISSING_CREDENTIAL = "MISSING_CREDENTIAL"
    """The required credential / API key resolved empty (e.g. unresolved Secret
    Manager secret, blank env) so no authenticated call could be made
    (DP-FETCH-005)."""

    SOURCE_UNREACHABLE = "SOURCE_UNREACHABLE"
    """The source endpoint was never reached at all (circuit open, no route,
    pre-flight abort) — ``response_received`` is False."""


DISQUALIFYING_FETCH_SIGNALS: Final[frozenset[str]] = frozenset(member.value for member in FetchErrorSignal)
"""String-membership view of :class:`FetchErrorSignal` for fast O(1) validation.

The closed set of ``error_signal`` values that mean a fetch is NOT honest
absence. A :class:`FetchEvidence` with any of these (or a non-2xx status, no
response, or rows > 0) fails :meth:`FetchEvidence.proves_honest_absence` and
must route to ``record_failed``. Mirror of :data:`EMPTY_CONFIRMED_REASONS`.
"""


@dataclass(frozen=True)
class FetchEvidence:
    """Proof that a zero-row fetch was a legitimate 200+empty honest absence.

    Threaded from the adapter HTTP layer (the UAC ``classify_venue_error()``
    site that already exists per-adapter) into the manifest writer. The writer
    gate at ``record_empty(reason=SOURCE_RETURNED_ZERO)`` accepts the empty
    ONLY when :meth:`proves_honest_absence` is True; otherwise it raises
    :class:`UnprovenHonestAbsenceError` and the adapter must ``record_failed``.

    Fields:
        http_status: The HTTP status code of the response (e.g. ``200``).
        response_received: Whether ANY response was received from the source
            (False ⇒ timeout / connect-error / never-reached).
        rows_in_response: Number of data rows the response yielded. Honest
            absence requires exactly ``0``.
        source: The vendor/source token (``databento`` / ``polymarket_clob`` /
            ``odds_api`` / ...). For provenance + the daily re-probe.
        endpoint: The concrete endpoint/URL hit. For the daily re-probe to
            re-hit the same source (DP-FETCH-006).
        attempted_at: UTC timestamp of the fetch attempt.
        error_signal: One of :class:`FetchErrorSignal` (as a string) when a
            disqualifying condition occurred, else ``""`` (clean fetch). The
            adapter sets this from its ``classify_venue_error()`` result.
    """

    http_status: int
    response_received: bool
    rows_in_response: int
    source: str
    endpoint: str
    attempted_at: datetime
    error_signal: str = ""

    def proves_honest_absence(self) -> bool:
        """True iff this evidence proves a legitimate 200+empty honest absence.

        ALL of: the HTTP status is in the 2xx range, a response was received,
        the response carried exactly zero rows, and no disqualifying
        ``error_signal`` was set. Any disqualifying signal (auth / rate-limit /
        5xx / timeout / exception / missing-credential / unreachable), a
        non-2xx status, a missing response, or rows > 0 → False (the adapter
        must ``record_failed`` instead).
        """
        return (
            200 <= self.http_status < 300
            and self.response_received
            and self.rows_in_response == 0
            and self.error_signal == ""
        )


class UnprovenHonestAbsenceError(ValueError):
    """Raised when ``record_empty(reason=SOURCE_RETURNED_ZERO)`` is called
    without :class:`FetchEvidence` that :meth:`~FetchEvidence.proves_honest_absence`.

    The keystone guard for failure class C1: a 401 / 403 / 429 / 5xx / timeout /
    exception / missing-credential path that previously fell through to
    ``record_empty(SOURCE_RETURNED_ZERO)`` now fails LOUDLY at the writer
    boundary and must route to ``record_failed`` (typically with a
    :class:`RecordFailedReason` derived from the disqualifying signal).
    Calendar ``EXPECTED_*`` reasons are exempt — no fetch was attempted.

    Sister of :class:`LegacyBlankErrorReasonError` (blank reason) and
    :class:`EmptyFromLiveInstrumentError` (catalog-says-alive empty). Registry
    SSOT: DP-FETCH-001 (CRITICAL). Plan:
    ``data_pipeline_hardening_self_monitoring_2026_06_22.md`` Phase 1.
    """

    def __init__(self, callsite_hint: str, evidence: FetchEvidence | None) -> None:
        if evidence is None:
            detail = "no FetchEvidence supplied"
        else:
            detail = (
                f"http_status={evidence.http_status}, "
                f"response_received={evidence.response_received}, "
                f"rows_in_response={evidence.rows_in_response}, "
                f"error_signal={evidence.error_signal!r}, "
                f"source={evidence.source!r}, endpoint={evidence.endpoint!r}"
            )
        suffix = f" [{callsite_hint}]" if callsite_hint else ""
        super().__init__(
            "record_empty(reason=SOURCE_RETURNED_ZERO) requires FetchEvidence proving a clean 200+empty "
            "fetch (http_status in 2xx AND response_received AND rows_in_response == 0 AND error_signal == "
            '""). The supplied evidence does NOT prove honest absence (' + detail + "). This is most likely "
            "an auth / rate-limit / 5xx / timeout / exception / missing-credential path masquerading as "
            "honest absence — call record_failed (e.g. with a RecordFailedReason mapped from the "
            "disqualifying FetchErrorSignal) instead." + suffix
        )


def fetch_error_signal_for_status(http_status: int) -> str:
    """Map an HTTP status code to the matching :class:`FetchErrorSignal` value.

    Returns ``""`` (the empty / honest-absence-compatible signal) for any 2xx
    status. Outside 2xx, returns the most specific disqualifying signal:
    ``AUTH_401`` / ``AUTH_403`` / ``RATE_LIMITED_429`` / ``SERVER_5XX`` /
    ``HTTP_NON_2XX`` (the catch-all for 3xx + other 4xx). Threaded from an
    adapter's HTTP layer into :func:`build_fetch_evidence` so a non-2xx zero-row
    response is provably NOT honest absence (keystone class C1).
    """
    if 200 <= http_status < 300:
        return ""
    if http_status == 401:
        return FetchErrorSignal.AUTH_401.value
    if http_status == 403:
        return FetchErrorSignal.AUTH_403.value
    if http_status == 429:
        return FetchErrorSignal.RATE_LIMITED_429.value
    if 500 <= http_status < 600:
        return FetchErrorSignal.SERVER_5XX.value
    return FetchErrorSignal.HTTP_NON_2XX.value


def fetch_error_signal_for_exception(exc: BaseException) -> str:
    """Map an adapter-fetch exception to the matching :class:`FetchErrorSignal`.

    A timeout-shaped exception (``TimeoutError`` / asyncio timeout / a class name
    containing ``Timeout``) maps to ``TIMEOUT``; a connection-level failure
    (``ConnectionError`` / DNS / TCP / TLS) maps to ``CONNECT_ERROR``; everything
    else is the generic ``ADAPTER_EXCEPTION``. Any of these DISQUALIFIES the
    fetch from proving honest absence — the adapter must ``record_failed``.
    """
    if isinstance(exc, TimeoutError) or "timeout" in type(exc).__name__.lower():
        return FetchErrorSignal.TIMEOUT.value
    if isinstance(exc, ConnectionError) or any(
        token in type(exc).__name__.lower() for token in ("connect", "dns", "socket", "tls", "ssl")
    ):
        return FetchErrorSignal.CONNECT_ERROR.value
    return FetchErrorSignal.ADAPTER_EXCEPTION.value


def build_fetch_evidence(
    *,
    source: str,
    endpoint: str,
    attempted_at: datetime,
    rows_in_response: int = 0,
    http_status: int | None = None,
    response_received: bool = True,
    exception: BaseException | None = None,
    error_signal: str | None = None,
    missing_credential: bool = False,
) -> FetchEvidence:
    """Construct a :class:`FetchEvidence` from what an adapter knows at a fetch site.

    The single mapping every adapter reuses so the keystone gate
    (``record_empty(reason=SOURCE_RETURNED_ZERO)``) sees a value-object that
    truthfully reflects the HTTP outcome. The ``error_signal`` is resolved with
    this precedence (first non-empty wins):

    1. an explicit ``error_signal`` argument (the adapter already classified);
    2. ``MISSING_CREDENTIAL`` when ``missing_credential`` is True (DP-FETCH-005);
    3. ``SOURCE_UNREACHABLE`` when ``response_received`` is False;
    4. the exception-derived signal when ``exception`` is not None
       (:func:`fetch_error_signal_for_exception`);
    5. the HTTP-status-derived signal when ``http_status`` is not None
       (:func:`fetch_error_signal_for_status`);
    6. ``""`` (clean — only a genuine 2xx + 0-rows reaches here).

    A clean call ``build_fetch_evidence(source=..., endpoint=..., attempted_at=...,
    rows_in_response=0, http_status=200)`` yields evidence that
    :meth:`FetchEvidence.proves_honest_absence` accepts. Anything else (auth /
    rate-limit / 5xx / timeout / exception / missing-credential / unreachable /
    non-2xx / rows>0) yields evidence that the writer REJECTS, steering the
    adapter to ``record_failed``. Keystone plan:
    ``data_pipeline_hardening_self_monitoring_2026_06_22.md`` Phase 1.
    """
    resolved_status = (
        http_status if http_status is not None else (200 if (response_received and exception is None) else 0)
    )
    if error_signal:
        signal = error_signal
    elif missing_credential:
        signal = FetchErrorSignal.MISSING_CREDENTIAL.value
    elif exception is not None:
        # An exception is MORE SPECIFIC than the generic "no response" — a
        # TimeoutError/ConnectionError naturally has response_received=False, so
        # the exception-derived signal (TIMEOUT/CONNECT_ERROR/ADAPTER_EXCEPTION)
        # MUST win over SOURCE_UNREACHABLE (fixed 2026-06-22: precedence bug).
        signal = fetch_error_signal_for_exception(exception)
    elif not response_received:
        signal = FetchErrorSignal.SOURCE_UNREACHABLE.value
    elif http_status is not None:
        signal = fetch_error_signal_for_status(http_status)
    else:
        signal = ""
    return FetchEvidence(
        http_status=resolved_status,
        response_received=response_received and exception is None,
        rows_in_response=rows_in_response,
        source=source,
        endpoint=endpoint,
        attempted_at=attempted_at,
        error_signal=signal,
    )


__all__ = [
    "BUNDLED_DATA_TYPES",
    "DATA_TYPE_TO_CLUSTER_REGISTRY",
    "DISQUALIFYING_FETCH_SIGNALS",
    "EMPTY_CONFIRMED_REASONS",
    "ES_OPTIONS_CLUSTERS",
    "ES_OPTIONS_DEFAULT_MIN_ROWS_PER_CLUSTER",
    "EVENT_CONTRACT_ROOT_CLUSTERS",
    "EXPECTED_EMPTY_REASON_PREFIX",
    "FUTURES_CHAIN_BUCKETS",
    "HONEST_COVERAGE_GAP_FIELDS",
    "PREDICTION_GROUPS",
    "SCHEDULE_DEFINING_DATA_TYPES",
    "SPORTS_FIXTURE_CLUSTERS",
    "CaptureStatusCounts",
    "EmptyConfirmedReason",
    "EmptyFromLiveInstrumentError",
    "FetchErrorSignal",
    "FetchEvidence",
    "LayeredCoverage",
    "LegacyBlankErrorReasonError",
    "UnprovenHonestAbsenceError",
    "build_fetch_evidence",
    "compute_honest_coverage",
    "compute_layered_coverage",
    "extract_es_options_cluster",
    "fetch_error_signal_for_exception",
    "fetch_error_signal_for_status",
    "futures_expiry_bucket",
    "get_active_es_options_clusters_for_date",
    "is_resolved_schedule_empty",
    "parse_futures_expiry",
    "was_instrument_alive",
]
