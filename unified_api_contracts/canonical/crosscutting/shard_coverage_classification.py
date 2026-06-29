"""Windowed shard-coverage classifier — RUNNABLE / INSUFFICIENT_HISTORY / HONEST_EMPTY.

SSOT for the per-(asset_group, venue, data_type, instrument) **windowed** coverage
trichotomy used by the honest-coverage smoke-test harness (plan:
``plans/active/honest_coverage_smoke_harness_2026_06_28.md``; codex:
``codex/02-data/shard-coverage-classification.md``).

The existing :mod:`unified_api_contracts.canonical.crosscutting.honest_coverage`
contract classifies a SINGLE manifest cell via the 4-state ``capture_status`` +
typed ``EmptyConfirmedReason`` taxonomy. THIS module lifts that per-cell
semantic up to a **window verdict**: given the per-day rows over a required
window, decide whether the downstream consumer (MDPS / features / a smoke
runner) should:

* **RUNNABLE** — proceed (continuous coverage; legitimate within-window absences
  in the gaps);
* **INSUFFICIENT_HISTORY** — refuse to run (a partial window — the safety
  property the harness exists to enforce); or
* **HONEST_EMPTY** — tolerate absence without crashing (the entire window is
  legitimately empty: pre-launch / paused-league / source-doesn't-cover / …).

The crux is the third class **not collapsing** into the second: a
``empty_confirmed`` cell with an OUT-of-coverage-window reason (chain
pre-genesis, instrument not listed, source doesn't cover, fixture cancelled,
…) is **honest-empty**, while a ``attempted_failed`` or pending
``expected_unattempted`` cell is **insufficient-history**. UAC's existing
:func:`is_out_of_coverage_window` /
:data:`OUT_OF_COVERAGE_WINDOW_REASONS` partition supplies the typed taxonomy;
this module composes it into a window verdict.

Decision table (per-day bucketing → window verdict):

================================  =====================================================
Per-day bucket                    Origin
================================  =====================================================
``C``  — captured                 ``capture_status == "captured"``
``WE`` — within-window empty      ``capture_status == "empty_confirmed"`` and
                                  :func:`is_within_window_absence` (weekend / holiday /
                                  paused / postponed / source-returned-zero / …)
``OOW``— out-of-window empty      ``capture_status == "empty_confirmed"`` and
                                  :func:`is_out_of_coverage_window` (pre-genesis /
                                  pre-venue-launch / not-listed / delisted /
                                  source-doesn't-cover / no-fixture / not-enough-tvl /…)
``UK`` — known-empty unattempted  ``capture_status == "expected_unattempted"`` and
                                  ``error_reason.startswith("EXPECTED_")`` — Tier-3
                                  sentinel pre-resolved to no-fetch-needed (treated as
                                  OOW for window classification)
``F``  — attempted-failed         ``capture_status == "attempted_failed"`` (fetch
                                  attempted + raised — venue-side error, retry next run)
``U``  — pending unattempted      ``capture_status == "expected_unattempted"`` and NOT
                                  ``EXPECTED_*`` — sentinel says "data expected but
                                  never tried" (the gap that backfills must close)
``M``  — missing row              date ∈ window AND no manifest row at all (writer was
                                  supposed to materialise an ``expected_unattempted``
                                  row; its absence is a writer bug we MUST NOT silently
                                  absorb — Data-Pipeline-Correctness HARD RULE
                                  "never silent placeholders")
================================  =====================================================

Window verdict (in priority order):

1. **any F > 0  OR  U > 0  OR  M > 0**  →  ``INSUFFICIENT_HISTORY``.
   A single failed / pending / missing day in the required window means the
   downstream consumer must REFUSE to run — that is the half-window safety
   property: a partial window must NEVER produce a green smoke test. The
   classifier surfaces the offending dates on
   :attr:`ShardCoverageReport.holes` so the harness can fail loudly with the
   first ~5 hole dates in the rationale.

2. **C > 0**  (and remaining days are WE / OOW / UK only)  →  ``RUNNABLE``.
   Continuous coverage — every day in the window is either real data or a
   legitimate within-/out-of-window absence (weekend, holiday, paused, pre-
   venue-launch, …). The downstream path runs; sub-path correctness is
   asserted by the smoke-runner (right-edge / no-look-ahead — Plan 4 guard).

3. **C == 0  AND  F == U == M == 0**  →  ``HONEST_EMPTY``.
   The entire window is OOW / UK / WE only — the cell is legitimately empty
   over the full window (pre-launch shard, paused-league off-season, a
   source-doesn't-cover league, etc.). The downstream path must tolerate the
   absence without crashing and without writing silent placeholders.

The trichotomy is total: every (window, manifest projection) lands in
exactly one class. The classifier carries the per-bucket counts on the
report so callers can drill into WHY a verdict came out the way it did
without re-querying the manifest.

This module is the **[UAC] contract** half (decision table + typed
result + pure-logic core :func:`classify_from_capture_counts`). The
**[per-service] implementation** half — walking the consolidated
availability index, projecting per-shard-atom rows into capture counts,
fanning out across the MVP universe — lives in the smoke harness
(``e2e-testing/scripts/build_smoke/...``) per the IMPLEMENT P1 todo of
the smoke-harness plan.

Plan: ``plans/active/honest_coverage_smoke_harness_2026_06_28.md``
(Todo P1 [DESIGN] — defined this contract).
Codex SSOT: ``codex/02-data/shard-coverage-classification.md``.
Related: ``codex/02-data/honest-coverage-model.md`` (Layer-1 / Layer-2 +
``EMPTY_CONFIRMED_REASONS`` taxonomy) and
``codex/02-data/availability-manifest-and-data-status.md`` (the
4-state ``capture_status`` write contract + manifest schema).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Final, Literal, Protocol

from unified_api_contracts.canonical.crosscutting._honest_coverage_logic import (
    CaptureStatusCounts,
)
from unified_api_contracts.canonical.crosscutting.honest_coverage import (
    EXPECTED_EMPTY_REASON_PREFIX,
    is_out_of_coverage_window,
    is_within_window_absence,
)

# ---------------------------------------------------------------------------
# Required-window kinds — product-shaped axes per
# ``codex/02-data/shard-coverage-classification.md`` § Required window is
# product-shaped (and the plan's ``Required-window is product-shaped`` section).
# ---------------------------------------------------------------------------


RequiredWindowKind = Literal[
    "seasonal_continuous",
    "max_daily_aggregation",
    "lookback_n",
]
"""Closed-set taxonomy for the kind of required window a downstream consumer
needs:

* ``seasonal_continuous`` — sports / seasonal data_types where the smoke
  test exercises a continuous instrument-and-market pipeline across the
  league season (e.g. EPL golden window ``2025-09-01 .. 2025-11-30``).
  Boundary dates come from the sports league registry, never magic numbers.

* ``max_daily_aggregation`` — data_types whose path only ever aggregates
  WITHIN a day (e.g. ``ohlcv_24h`` produced from intraday ticks). A single
  day is enough to exercise the path end-to-end.

* ``lookback_n`` — everything else: a lookback window driven by the
  ``max over feature families of (lookback_periods x coarsest_timeframe)``
  that consumes the shard. Pinned-200-period 24h features over a 15s base
  need ~200 trading days even though the writer's grain is 15s; the
  required-window registry computes this from the live feature config.
"""


@dataclass(frozen=True)
class RequiredWindow:
    """A required-window for the windowed classifier.

    ``start`` / ``end`` are inclusive UTC dates; ``kind`` records which of the
    three product-shaped sources the boundaries came from (sports league
    registry / max-daily-aggregation contract / lookback-N feature config).
    The classifier treats ``end - start + 1`` calendar days as the universe
    of cells to look up — calendar-closed days (weekends, holidays) inside
    the window are EXPECTED to land on the within-window-empty bucket via
    ``EXPECTED_HOLIDAY`` / ``EXPECTED_WEEKEND`` ``EmptyConfirmedReason``
    members, not on the missing-row bucket.
    """

    start: date
    end: date
    kind: RequiredWindowKind

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(
                f"RequiredWindow end ({self.end.isoformat()}) is before start "
                f"({self.start.isoformat()}) — required windows are inclusive "
                "and must be non-empty.",
            )

    @property
    def calendar_days(self) -> int:
        """Number of inclusive calendar days the window spans (>= 1)."""
        return (self.end - self.start).days + 1


# ---------------------------------------------------------------------------
# Verdict enum — the trichotomy the harness emits per shard.
# ---------------------------------------------------------------------------


class ShardCoverageClass(StrEnum):
    """Per-shard, per-window coverage verdict for the smoke-test harness.

    Closed set of three. The trichotomy is total: every (window, manifest
    projection) lands in exactly one class per :func:`classify_from_capture_counts`.

    Members are string-valued so verdicts serialise straight into the smoke
    matrix artifact + JSON payloads without enum-to-str gymnastics.
    """

    RUNNABLE = "RUNNABLE"
    """Continuous coverage over the required window — the downstream consumer
    (MDPS / features / smoke-runner) MUST proceed. Days inside the window
    that are ``empty_confirmed`` with a within-window (calendar / paused /
    postponed / source-returned-zero) reason or an out-of-coverage-window
    reason ARE allowed — they are part of the legitimate distribution. The
    consumer is responsible for asserting right-edge / no-look-ahead via the
    Plan-4 guard."""

    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    """The required window is only partially covered — the downstream
    consumer MUST REFUSE to run. At least one day is ``attempted_failed``
    (venue-side error needing retry), ``expected_unattempted`` with a
    non-``EXPECTED_*`` reason (sentinel pending fetch), or has NO manifest
    row at all (writer bug — see ``codex/02-data/data-pipeline-correctness-
    hard-rule.md`` "never silent placeholders"). This class IS the safety
    property the harness exists to enforce: a half-window MUST NOT produce
    a green smoke test."""

    HONEST_EMPTY = "HONEST_EMPTY"
    """The entire window is legitimately empty — no day in the window has
    captured data, AND no day is ``attempted_failed`` / pending-unattempted /
    missing. Every day resolves to an ``empty_confirmed`` cell with a typed
    within-window or out-of-coverage-window reason (pre-genesis, pre-venue-
    launch, paused-league, source-doesn't-cover, no-fixture, …) or to a
    Tier-3 known-empty ``expected_unattempted`` cell with an ``EXPECTED_*``
    reason. The downstream consumer MUST tolerate this absence without
    crashing and without writing silent placeholders."""


# ---------------------------------------------------------------------------
# WindowCaptureCounts — the bucketed per-day projection the classifier
# operates over. The wrapper :func:`classify_shard_coverage` builds this from
# the consolidated availability index; the pure-logic core
# :func:`classify_from_capture_counts` consumes it.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WindowCaptureCounts:
    """Per-bucket day counts over a required window.

    Mirror of :class:`CaptureStatusCounts` lifted to the window-level
    classifier vocabulary. The decision table in this module's docstring
    documents which manifest cell maps to which bucket. The sum of all
    fields MUST equal :attr:`RequiredWindow.calendar_days` for a
    fully-covered window — :meth:`total` exposes that sum so callers can
    sanity-check.
    """

    captured: int = 0
    """``C`` — days where ``capture_status == "captured"``."""

    within_window_empty: int = 0
    """``WE`` — ``empty_confirmed`` days with a within-window reason
    (calendar / paused / postponed / source-returned-zero / …)."""

    out_of_coverage_window_empty: int = 0
    """``OOW`` — ``empty_confirmed`` days with an out-of-coverage-window
    reason (pre-genesis / pre-venue-launch / not-listed / delisted /
    source-doesn't-cover / no-fixture / not-enough-tvl / …)."""

    known_empty_unattempted: int = 0
    """``UK`` — ``expected_unattempted`` days with an ``EXPECTED_*`` reason
    (Tier-3 sentinel pre-resolved as no-fetch-needed). Treated as honest
    absence for window classification (sister of OOW)."""

    attempted_failed: int = 0
    """``F`` — days where ``capture_status == "attempted_failed"`` (venue-
    side error; retry expected)."""

    pending_unattempted: int = 0
    """``U`` — ``expected_unattempted`` days with a NON-``EXPECTED_*``
    reason (sentinel says "expected to exist but not yet attempted")."""

    missing_rows: int = 0
    """``M`` — days in the required window with NO manifest row at all.
    The writer was supposed to materialise an ``expected_unattempted`` row;
    its absence is a writer bug we MUST NOT silently absorb."""

    def total(self) -> int:
        """Sum of all per-bucket day counts (should equal window calendar days)."""
        return (
            self.captured
            + self.within_window_empty
            + self.out_of_coverage_window_empty
            + self.known_empty_unattempted
            + self.attempted_failed
            + self.pending_unattempted
            + self.missing_rows
        )


# ---------------------------------------------------------------------------
# ShardCoverageReport — what the classifier returns.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShardCoverageReport:
    """Full classifier output for one (asset_group, venue, data_type,
    instrument, required_window) tuple.

    The verdict (:attr:`classification`) is the harness's primary signal;
    the breakdown (:attr:`counts`, :attr:`holes`, :attr:`rationale`) lets
    callers drill into WHY without re-reading the manifest.
    """

    asset_group: str
    """Asset group ("cefi" / "defi" / "tradfi" / "sports" / "prediction")."""

    venue: str
    """Writer-grain venue token (e.g. ``BINANCE-FUTURES`` / ``DERIBIT`` /
    ``UNISWAP_V3-ETH`` / ``api_football`` / ``polymarket``)."""

    data_type: str
    """Writer-grain ``data_type`` (e.g. ``trades`` / ``book_snapshot_5`` /
    ``derivative_ticker`` / ``dex_pool_swaps`` / ``ohlcv_1m`` /
    ``match_odds``)."""

    instrument_id: str | None
    """Per-asset-group instrument identifier when the shard atom carries
    one. ``None`` for bundled shards (``options_chain``, ``futures_chain``,
    sports league-day, prediction question-group) — the bundle key is in
    :attr:`bundle_key`."""

    required_window: RequiredWindow
    """The window the classification was made against."""

    classification: ShardCoverageClass
    """The verdict — RUNNABLE / INSUFFICIENT_HISTORY / HONEST_EMPTY."""

    counts: WindowCaptureCounts
    """Per-bucket day counts the verdict was derived from."""

    bundle_key: tuple[str, ...] = field(default_factory=tuple)
    """Extra shard-atom dimensions for bundled shards (e.g.
    ``(underlying,)`` for ``options_chain`` / ``(chain,)`` for defi pools /
    ``(league_id,)`` for sports / ``(canonical_question_group,)`` for
    prediction). Empty tuple for per-instrument shards."""

    holes: tuple[date, ...] = field(default_factory=tuple)
    """Sorted dates inside the required window that caused
    ``INSUFFICIENT_HISTORY`` — i.e. dates that landed on
    ``attempted_failed``, pending-``expected_unattempted``, or missing-row.
    Empty for RUNNABLE / HONEST_EMPTY verdicts. Bounded to the first
    :data:`MAX_HOLES_IN_REPORT` entries so a totally-failed window doesn't
    bloat memory; the count truth lives on
    :attr:`WindowCaptureCounts.attempted_failed` /
    :attr:`WindowCaptureCounts.pending_unattempted` /
    :attr:`WindowCaptureCounts.missing_rows`."""

    rationale: str = ""
    """Human-readable one-liner explaining the verdict — e.g.
    ``"INSUFFICIENT_HISTORY: 3 attempted_failed + 2 pending_unattempted + "
    "1 missing day(s) in window (first holes: 2025-09-04, 2025-09-12, ...)"``.
    Surfaced in the harness's smoke matrix artifact for the operator
    audit."""


MAX_HOLES_IN_REPORT: Final[int] = 5
"""Upper bound on :attr:`ShardCoverageReport.holes` length — a fully-failed
window's hole-set is bounded to the first N dates so the report stays
serialisable; truth-counts live on :class:`WindowCaptureCounts`."""


# ---------------------------------------------------------------------------
# Pure-logic core — the decision table, no IO. Implementable + testable
# today; the manifest-reading wrapper (:func:`classify_shard_coverage`)
# composes this with the IS catalogue + ``read_availability_index()``
# projection per the IMPLEMENT P1 todo of the smoke-harness plan.
# ---------------------------------------------------------------------------


def classify_from_capture_counts(counts: WindowCaptureCounts) -> ShardCoverageClass:
    """Apply the window-verdict decision table to per-bucket day counts.

    Pure function — no IO, no manifest knowledge — so it is exhaustively
    testable from a bag of integers. The wrapper
    :func:`classify_shard_coverage` builds :class:`WindowCaptureCounts`
    from the consolidated availability index, then delegates here for the
    verdict.

    Decision (in priority order, total over all non-negative count tuples):

    1. ``F + U + M > 0``  → :attr:`ShardCoverageClass.INSUFFICIENT_HISTORY`
       (any hole forbids running — the half-window safety property);
    2. ``C > 0``          → :attr:`ShardCoverageClass.RUNNABLE`
       (continuous coverage; WE / OOW / UK are legitimate absences);
    3. otherwise          → :attr:`ShardCoverageClass.HONEST_EMPTY`
       (window is OOW / UK / WE only; the path must tolerate absence).

    Note that the rule is symmetric in WE vs OOW vs UK at the WINDOW
    level — they all count as "this day is honestly accounted for" — but
    the typed taxonomy is PRESERVED on the report's
    :class:`WindowCaptureCounts` so consumers can drill into the WHY.
    """
    if counts.attempted_failed + counts.pending_unattempted + counts.missing_rows > 0:
        return ShardCoverageClass.INSUFFICIENT_HISTORY
    if counts.captured > 0:
        return ShardCoverageClass.RUNNABLE
    return ShardCoverageClass.HONEST_EMPTY


def bucket_capture_status_cell(
    *,
    capture_status: str,
    error_reason: str | None,
    data_type: str | None = None,
) -> Literal["C", "WE", "OOW", "UK", "F", "U"]:
    """Bucket a single manifest cell into the classifier's per-day vocabulary.

    The wrapper :func:`classify_shard_coverage` calls this once per
    manifest row inside the required window; missing-row days (``M``) are
    detected by the wrapper as window dates with NO row at all (this
    function only operates on rows that exist).

    Mapping:

    * ``capture_status == "captured"`` → ``C``.
    * ``capture_status == "empty_confirmed"`` →
      ``OOW`` if :func:`is_out_of_coverage_window` (out-of-coverage-window
      reason — pre-genesis / pre-venue-launch / not-listed / delisted /
      source-doesn't-cover / no-fixture / not-enough-tvl / …); else ``WE``.
    * ``capture_status == "expected_unattempted"`` →
      ``UK`` if ``error_reason`` starts with ``EXPECTED_`` (Tier-3 sentinel
      pre-resolved); else ``U`` (pending fetch).
    * ``capture_status == "attempted_failed"`` → ``F``.

    Raises :class:`ValueError` on an unknown ``capture_status`` — the 4-state
    set is closed per ``codex/02-data/availability-manifest-and-data-status.md``.
    """
    if capture_status == "captured":
        return "C"
    if capture_status == "empty_confirmed":
        if is_out_of_coverage_window(error_reason, data_type):
            return "OOW"
        return "WE"
    if capture_status == "expected_unattempted":
        if error_reason and error_reason.startswith(EXPECTED_EMPTY_REASON_PREFIX):
            return "UK"
        return "U"
    if capture_status == "attempted_failed":
        return "F"
    raise ValueError(
        f"Unknown capture_status {capture_status!r}; expected one of "
        '{"captured", "empty_confirmed", "expected_unattempted", "attempted_failed"} '
        "per codex/02-data/availability-manifest-and-data-status.md § 4-state taxonomy.",
    )


# ---------------------------------------------------------------------------
# Manifest-row protocol — what the classifier wrapper reads.
# ---------------------------------------------------------------------------


class ShardManifestCell(Protocol):
    """Read-projection of a single manifest row consumed by the classifier.

    The wrapper :func:`classify_shard_coverage` does NOT depend on the full
    v9 manifest schema — only on these fields. The harness implementation
    in e2e-testing reads the consolidated availability index via UTL
    ``read_availability_index(bucket, columns=[...])`` with the
    bounded-column projection per
    ``codex/02-data/honest-coverage-model.md`` § Layer-2 read grain, and
    materialises a sequence of objects matching this protocol.

    Keeping this a :class:`typing.Protocol` (structural) lets callers pass
    Pandas rows, Pydantic models, dataclasses, or NamedTuples without
    forcing a copy.
    """

    @property
    def date(self) -> date: ...

    @property
    def capture_status(self) -> str: ...

    @property
    def error_reason(self) -> str | None: ...


# ---------------------------------------------------------------------------
# Manifest-walking wrapper — IO-bearing; impl lives in the e2e-testing
# IMPLEMENT P1 todo of the smoke-harness plan. The signature is FROZEN
# here so the IMPLEMENT worker has a complete typed contract to fill in.
# ---------------------------------------------------------------------------


def classify_shard_coverage(
    *,
    asset_group: str,
    venue: str,
    data_type: str,
    instrument_id: str | None,
    required_window: RequiredWindow,
    manifest_cells: Sequence[ShardManifestCell],
    bundle_key: tuple[str, ...] = (),
) -> ShardCoverageReport:
    """Classify one shard's coverage over a required window.

    Walks ``manifest_cells`` (the per-day rows the writer emitted for this
    (asset_group, venue, data_type, instrument, bundle_key) tuple inside
    ``required_window``), buckets each cell via
    :func:`bucket_capture_status_cell`, detects missing-row days (window
    dates with NO row at all), and delegates the verdict to
    :func:`classify_from_capture_counts`.

    Returns a :class:`ShardCoverageReport` whose
    :attr:`~ShardCoverageReport.classification` is one of:

    * :attr:`ShardCoverageClass.RUNNABLE`
    * :attr:`ShardCoverageClass.INSUFFICIENT_HISTORY`
    * :attr:`ShardCoverageClass.HONEST_EMPTY`

    Args:
        asset_group:    Asset group of the shard.
        venue:          Writer-grain venue token.
        data_type:      Writer-grain ``data_type``.
        instrument_id:  Per-instrument identifier for per-instrument shards;
                        ``None`` for bundled shards.
        required_window: The inclusive UTC date range to classify over.
        manifest_cells: All manifest rows for this shard inside the window
                        (deduped, one per date — the consolidator's
                        last-writer-wins is assumed). Cells outside the
                        window are ignored. Date duplicates are a writer
                        invariant violation and raise :class:`ValueError`.
        bundle_key:     Extra shard-atom dimensions for bundled shards
                        (defaults to empty tuple).

    Raises:
        ValueError: ``manifest_cells`` contains duplicate dates or a row with
            an unknown ``capture_status`` value.

    Note:
        Implementation is gated behind the IMPLEMENT P1 todo of
        ``plans/active/honest_coverage_smoke_harness_2026_06_28.md`` —
        the wrapper is intentionally left as ``NotImplementedError`` until
        the e2e-testing impl wires the consolidated availability-index
        read. The decision-table half (:func:`classify_from_capture_counts`
        + :func:`bucket_capture_status_cell`) IS implemented + tested at
        the contract level so the IMPLEMENT worker only has to compose the
        IO around the verified pure-logic core.
    """
    raise NotImplementedError(
        "classify_shard_coverage IO half not implemented yet — see plan "
        "plans/active/honest_coverage_smoke_harness_2026_06_28.md "
        "IMPLEMENT P1 todo. Pure-logic core is "
        "classify_from_capture_counts + bucket_capture_status_cell.",
    )


__all__ = [
    "MAX_HOLES_IN_REPORT",
    "CaptureStatusCounts",
    "RequiredWindow",
    "RequiredWindowKind",
    "ShardCoverageClass",
    "ShardCoverageReport",
    "ShardManifestCell",
    "WindowCaptureCounts",
    "bucket_capture_status_cell",
    "classify_from_capture_counts",
    "classify_shard_coverage",
    "is_out_of_coverage_window",
    "is_within_window_absence",
]
