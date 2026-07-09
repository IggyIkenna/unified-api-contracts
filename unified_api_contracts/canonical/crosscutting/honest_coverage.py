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

The ``EmptyConfirmedReason`` closed-set taxonomy + the coverage-window
partition (``OUT_OF_COVERAGE_WINDOW_REASONS`` / ``is_out_of_coverage_window``
/ ...) live in
:mod:`unified_api_contracts.canonical.crosscutting._honest_coverage_empty_reasons`
(900-line file-size QG split, 2026-07-09) and are re-exported here — this
module stays the import surface.
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
    EXPECTED_BOOKMAKER_MARKET_SETS,
    PREDICTION_GROUPS,
    SPORTS_FIXTURE_CLUSTERS,
)
from unified_api_contracts.canonical.crosscutting._honest_coverage_empty_reasons import (
    EMPTY_CONFIRMED_REASONS,
    EXPECTED_EMPTY_REASON_PREFIX,
    OUT_OF_COVERAGE_WINDOW_REASONS,
    WITHIN_WINDOW_EXPECTED_ABSENCE_REASONS,
    EmptyConfirmedReason,
    is_out_of_coverage_window,
    is_within_window_absence,
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
    "EXPECTED_BOOKMAKER_MARKET_SETS",
    "EXPECTED_EMPTY_REASON_PREFIX",
    "FUTURES_CHAIN_BUCKETS",
    "HONEST_COVERAGE_GAP_FIELDS",
    "OUT_OF_COVERAGE_WINDOW_REASONS",
    "PREDICTION_GROUPS",
    "SCHEDULE_DEFINING_DATA_TYPES",
    "SPORTS_FIXTURE_CLUSTERS",
    "WITHIN_WINDOW_EXPECTED_ABSENCE_REASONS",
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
    "is_out_of_coverage_window",
    "is_resolved_schedule_empty",
    "is_within_window_absence",
    "parse_futures_expiry",
    "was_instrument_alive",
]
