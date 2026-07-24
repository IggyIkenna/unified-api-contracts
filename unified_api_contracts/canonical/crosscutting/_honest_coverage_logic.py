"""Imperative helpers behind the honest-coverage taxonomy facade.

Logic split out of :mod:`unified_api_contracts.canonical.crosscutting.honest_coverage`
(2026-06-11 >900-line ratchet) so the facade stays the declarative
taxonomy/registry SSOT. Three concerns live here:

* **Coverage math** — :class:`CaptureStatusCounts` +
  :func:`compute_honest_coverage` + :data:`HONEST_COVERAGE_GAP_FIELDS`.
* **Futures expiry bucketing** — :func:`parse_futures_expiry` +
  :func:`futures_expiry_bucket` + :data:`FUTURES_CHAIN_BUCKETS`.
* **Instrument-liveness validation** — :func:`was_instrument_alive` +
  :class:`EmptyFromLiveInstrumentError` + :class:`LegacyBlankErrorReasonError`.

Import surface is UNCHANGED for consumers: every name here is re-exported by
``honest_coverage`` (and the crosscutting/root facades) — import from there.
"""

from __future__ import annotations

import datetime as _dt
import re
from typing import Final, NamedTuple

from unified_api_contracts.canonical.domain.sports.fixture_lifecycle import FIXTURES_SCHEDULE

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
      No fetch will ever land data here. DENOMINATOR only (as of the
      2026-07-22 Part 4.1 formula consolidation — see
      :func:`compute_honest_coverage`'s docstring; pre-4.1 this counted
      toward the numerator, a distinction the new formula deliberately drops
      to match ``instruments-service``'s production formula exactly).

    * ``expected_unattempted_pending_fetch`` — Tier-3 sentinel says "we expect
      data exists here but no adapter has run yet". This is a GAP. Counts in
      DENOMINATOR only — backfills must run to convert these into ``captured``,
      ``empty_confirmed`` (with ``SOURCE_RETURNED_ZERO``), or ``attempted_failed``.
      Also the ONE sub-bucket :data:`HONEST_COVERAGE_GAP_FIELDS` lists as
      backfill-actionable (``known_empty`` never converts — there's nothing
      to retry, the calendar has already spoken).

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
    out_of_window: int = 0
    """Count of ``empty_confirmed`` cells that are OUTSIDE the coverable
    window/scope (a SUBSET of :attr:`empty_confirmed`; reason ∈
    :data:`OUT_OF_COVERAGE_WINDOW_REASONS` — instrument-not-listed / delisted /
    pre-venue-launch / no-fixture / …, OR a schedule-defining
    ``FIXTURES_SCHEDULE`` no-match-day). Since 2026-07-22 (Part 4.1 global
    formula consolidation)
    :func:`compute_honest_coverage` excludes ALL of ``empty_confirmed`` from
    both numerator and denominator regardless of this sub-classification, so
    this field no longer changes the computed ratio — it is retained purely
    as a reporting breakdown (the deployment-ui drilldown shows how much of
    the excluded ``empty_confirmed`` total was out-of-life vs in-window).
    MUST satisfy ``0 <= out_of_window <= empty_confirmed``."""


def compute_honest_coverage(counts: CaptureStatusCounts) -> float:
    """Canonical honest-coverage ratio. Every caller in the workspace uses this.

    Formula (2026-07-22 Part 4.1 global consolidation — the ONE formula for
    every asset_group; supersedes the 2026-05-19/2026-06-23 numerator-credit
    formula below):

        numerator   = captured
        denominator = captured + attempted_failed
                      + expected_unattempted_known_empty
                      + expected_unattempted_pending_fetch
        coverage    = numerator / denominator     (returns 1.0 if denominator==0)

    ``empty_confirmed`` (legitimate absence — source attempted, returned
    zero rows, whether or not it also happens to be ``out_of_window``) is
    now EXCLUDED from both numerator and denominator, matching
    ``instruments-service/scripts/measure_honest_coverage.py::_count_statuses``
    (the ``coverage.json`` / ``HonestCoverageCard.tsx`` formula) and
    ``codex/02-data/honest-coverage-model.md``'s ``reachable_coverage``
    (`captured / (captured + attempted_failed + expected_unattempted)`).
    ``out_of_window`` is now a pure reporting subset of the excluded
    ``empty_confirmed`` total — it no longer changes the ratio (see its
    field docstring).

    Semantics in plain English: a slot is **honestly answered** ONLY if data
    actually landed (``captured``) — this is a narrower bar than the
    pre-2026-07-22 formula. A slot is a **gap** for every other state:
    ``attempted_failed``, ``expected_unattempted_pending_fetch`` ("expected
    to exist but we never tried"), ``expected_unattempted_known_empty``
    ("the calendar/lifecycle sentinel pre-resolved this before any fetch —
    a holiday, a pre-genesis date"), and ``empty_confirmed`` ("the source
    was attempted and affirmatively returned zero rows"). Matching
    ``instruments-service``'s ``_count_statuses`` exactly: that function
    never splits ``expected_unattempted`` by reason at all, so a
    known-empty-shaped row and a pending-fetch-shaped row are equally
    denominator-only there — Part 4.1 preserves that equivalence rather
    than inventing a numerator credit ``_count_statuses`` doesn't have.
    This is a REVERSAL of the pre-2026-07-22 formula's "known_empty is an
    honest answer, credit it" stance for that one field, made in the same
    global decision that stops crediting ``empty_confirmed`` (measured
    2026-07-22: every asset_group drops when ``empty_confirmed`` stops
    being credited — CEFI -11.50pp, TRADFI -8.96pp, SPORTS -10.19pp,
    PREDICTION -5.19pp, DEFI -0.05pp; see
    ``unified-trading-pm/plans/active/issues/sports_shard_enumeration_cartesian_blowup_2026_07_20.md``
    §4.1 for the full measured table and decision record). The
    ``known_empty``/``pending_fetch`` split (:class:`CaptureStatusCounts`'s
    docstring) remains useful for OTHER purposes — reporting, and
    :data:`HONEST_COVERAGE_GAP_FIELDS` deliberately still lists only
    ``pending_fetch`` (not ``known_empty``) as "actionable, retry this on
    backfill" — but neither sub-bucket earns numerator credit here.

    SSOTs this function consolidates:

    * ``sports_shard_enumeration_cartesian_blowup_2026_07_20.md`` §4.1 — the
      2026-07-22 decision to adopt the EXCLUDE-``empty_confirmed`` formula
      globally (all asset groups, not sports-scoped)
    * ``codex/02-data/honest-coverage-model.md`` — ``reachable_coverage``
    * ``writegate_honest_coverage_endtoend_2026_05_06.md`` Phase 1B + 6.x
      (superseded numerator-credit formula, kept for history)
    * ``expected_unattempted_propagation_chain_2026_05_12.md`` Phase 2.A
      (the EXPECTED_/non-EXPECTED_ split for ``expected_unattempted`` rows —
      still load-bearing under the new formula)

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
    numerator = counts.captured
    denominator = (
        numerator
        + counts.attempted_failed
        + counts.expected_unattempted_known_empty
        + counts.expected_unattempted_pending_fetch
    )
    if denominator == 0:
        return 1.0
    return numerator / denominator


# ---------------------------------------------------------------------------
# Layered coverage — TWO numbers per (asset_group, venue, ...), BOTH via
# :func:`compute_honest_coverage` (operator direction 2026-06-24, the
# instruments-foundation standard §2). The SSOT arithmetic is unchanged: a
# producer buckets the SAME manifest rows two ways and calls the SAME function,
# so day vs depth can NEVER diverge from the single formula the deployment-UI
# renders.
#
# * ``day_coverage`` — grain = the venue-DAY cell. Numerator/denominator count
#   one unit per expected ``(venue, day)`` (the manifest row for an
#   instruments-capture shard, or the per-day rollup of a market-data shard).
#   Catches "a day has nothing" — day-gaps that were silently ABSENT (the
#   2026-06-24 cefi 06-19/20/21 holes) once the expected-universe materialises
#   them as ``expected_unattempted_pending_fetch``.
#
# * ``depth_coverage`` — grain = the INSTRUMENT within a venue-day. The producer
#   weights each ``CaptureStatusCounts`` field by the instrument count (captured
#   = Σ ``instrument_count`` of honestly-answered cells; the
#   ``expected_unattempted_pending_fetch`` / ``attempted_failed`` weight = the
#   §2.1 oracle's EXPECTED depth for that venue-day). Catches "the day is there
#   but thin" — a venue-day ``captured`` with 41 of thousands.
#
# A green ``day_coverage`` with a low ``depth_coverage`` is the explicit
# "every day present, but days are under-populated" signal. Both surface
# together: manifest → ``/data-status`` → deployment-api → deployment-ui.
# ---------------------------------------------------------------------------


class LayeredCoverage(NamedTuple):
    """The two honest-coverage layers + the counts each was computed from.

    Both :attr:`day_coverage` and :attr:`depth_coverage` are produced by
    :func:`compute_honest_coverage` over a :class:`CaptureStatusCounts` — the
    ONLY coverage formula in the workspace — so the deployment-ui drilldown and
    every CLI/QG read the same two numbers off the same manifest. The
    `*_counts` fields are carried so a consumer can render the breakdown
    (captured / empty / failed / pending) behind each %, never recomputing.

    Construct via :func:`compute_layered_coverage` (which guarantees the floats
    match the counts); the positional NamedTuple shape is for ergonomic
    destructuring at the call site.
    """

    day_coverage: float
    depth_coverage: float
    day_counts: CaptureStatusCounts
    depth_counts: CaptureStatusCounts


def compute_layered_coverage(
    day_counts: CaptureStatusCounts,
    depth_counts: CaptureStatusCounts,
) -> LayeredCoverage:
    """Compute the day + depth coverage layers, BOTH through the SSOT formula.

    The single seam every layered-coverage producer (UTL ``read_capture_status_counts``,
    deployment-api coverage rollup) MUST go through so the two numbers can never
    drift from :func:`compute_honest_coverage`. ``day_counts`` are venue-day-cell
    grain (one unit per expected ``(venue, day)``); ``depth_counts`` are
    instrument-weighted (each field summed over ``instrument_count`` / the §2.1
    oracle's expected depth). See the module note above + the instruments-
    foundation standard §2 (``codex/02-data/instruments-foundation-and-catalogue-completeness.md``).

    Args:
        day_counts: Capture-status counts at venue-day-cell grain.
        depth_counts: Capture-status counts weighted by instrument depth.

    Returns:
        A :class:`LayeredCoverage` carrying both ratios + both count tuples.
    """
    return LayeredCoverage(
        day_coverage=compute_honest_coverage(day_counts),
        depth_coverage=compute_honest_coverage(depth_counts),
        day_counts=day_counts,
        depth_counts=depth_counts,
    )


# ---------------------------------------------------------------------------
# Schedule-defining data_types — "empty source response == complete" (operator
# direction 2026-06-23).
#
# A schedule-defining data_type IS the source-of-truth for whether anything
# exists to capture on a (entity, day). API-Football ``FIXTURES_SCHEDULE`` is
# the sports schedule: when its fixtures endpoint returns 200 + zero rows for a
# (league, day), there genuinely are NO matches that day — that cell is
# CORRECTLY RESOLVED (complete), not a coverage gap. The 2026-06-23 audit found
# 233 golden-window FIXTURES cells at ``empty_confirmed(SOURCE_RETURNED_ZERO)``
# for cup / lower-league competitions (Scottish Cup, Greek Super League 2,
# Copa Sudamericana, …) on dates they simply didn't play — wrongly counted as
# gaps, understating FIXTURES coverage to ~93.7% when it is really ~100%.
#
# This is DATA-TYPE-AWARE on purpose: ``SOURCE_RETURNED_ZERO`` is NOT blanket-
# resolved. For an ENRICHMENT data_type (FIXTURE_STATS / PLAYER_STATS / ODDS /
# MATCHES / …) a zero-row response WHEN A FIXTURE EXISTS may be a real gap, so
# its ``SOURCE_RETURNED_ZERO`` stays an in-window absence. Only the
# schedule-DEFINING data_type is definitionally "empty == complete" — because
# the schedule endpoint IS the universe.
#
# NOTE on MATCHES (FootyStats): NOT schedule-defining. FootyStats is
# fixture-PINNED — it records ``EXPECTED_NO_FIXTURE`` (already out-of-window)
# when no API-Football fixture exists, and a genuine zero from FootyStats when a
# fixture DOES exist is a real enrichment gap. So only ``FIXTURES_SCHEDULE``
# qualifies. SSOT: ``codex/02-data/honest-absence-downstream-handling.md`` + the
# operator directive 2026-06-23.
#
# ``FIXTURES`` → ``FIXTURES_SCHEDULE`` atom migration (2026-07-24,
# ``plans/active/sports_closeout_batch1_ao_ready_2026_07_24.md`` todo 1): the
# manifest atom this constant matches was renamed at every writer/reader call
# site in instruments-service THAT HAS MIGRATED SO FAR — but pre-cutover
# manifest rows PERMANENTLY carry ``data_type="FIXTURES"`` (no historical
# dual-write ever existed, see ``fixture_lifecycle.py``'s module docstring),
# and at least one writer call site (``sports_fixture_status_refresh.py``)
# still stamps the legacy literal as of 2026-07-24. A 2026-07-24 same-day
# REPLACE of this set (``uac@6d9c7b59``, ``{"FIXTURES"}`` -> ``{FIXTURES_SCHEDULE}``)
# silently stopped resolving every legacy-atom empty_confirmed row as
# out-of-window — a real coverage-math regression, not just test drift (caught
# by deployment-api's ``tests/unit/data_status/test_oow_denominator.py`` going
# RED on ``live-defi-rollout``). Kept ADDITIVE here instead — same pattern as
# ``gcs_paths.SPORTS_DATA_TYPE_TO_FOLDER``/``candidate_parquet_paths()``, which
# keep resolving legacy ``"FIXTURES"`` callers across the cutover rather than
# replacing them. Drop the legacy literal from this set only once todo 1's
# corpus-wide migration is verified complete AND historical rows are confirmed
# out of scope for this formula (unlikely, since coverage aggregates full
# history).
# ---------------------------------------------------------------------------

SCHEDULE_DEFINING_DATA_TYPES: Final[frozenset[str]] = frozenset({"FIXTURES", FIXTURES_SCHEDULE})
"""Closed set of schedule-DEFINING data_types — the source-of-truth for whether
anything exists to capture on a (entity, day). For these, a clean
``SOURCE_RETURNED_ZERO`` (200 + zero rows) means "no matches that day = complete"
→ RESOLVED, not a gap (see :func:`is_resolved_schedule_empty`). Today sports
``FIXTURES_SCHEDULE`` (API-Football, the schedule, post-2026-07-14 cutover)
PLUS the legacy ``FIXTURES`` literal (pre-cutover manifest rows + any writer
call site not yet migrated by
``plans/active/sports_closeout_batch1_ao_ready_2026_07_24.md`` todo 1) — both
name the SAME schedule source, just at different points in the atom
migration. Enrichment data_types are NOT here — their zero-row responses may
be real gaps."""

_SCHEDULE_EMPTY_RESOLVED_REASON: Final[str] = "SOURCE_RETURNED_ZERO"
"""The ONLY ``empty_confirmed`` reason a schedule-defining data_type resolves
via :func:`is_resolved_schedule_empty`: a proven clean 200+empty fetch (no
matches that day). ``EXPECTED_*`` calendar reasons are already out-of-window."""


def is_resolved_schedule_empty(data_type: str | None, reason: str | None) -> bool:
    """True iff a schedule-DEFINING data_type's empty cell is RESOLVED (complete).

    A schedule-defining data_type (today sports ``FIXTURES_SCHEDULE`` post-cutover
    plus the legacy ``FIXTURES`` literal pre-cutover — see
    :data:`SCHEDULE_DEFINING_DATA_TYPES`, the API-Football schedule) that is
    ``empty_confirmed`` with reason
    ``SOURCE_RETURNED_ZERO`` means the fixtures endpoint returned 200 + zero
    rows → there genuinely were NO matches that (league, day) → the cell is
    CORRECTLY RESOLVED, NOT a coverage gap. Such cells are OUT-of-coverage-window
    (nothing was collectable) and MUST be excluded from the completion-%
    denominator — exactly like the ``EXPECTED_NO_FIXTURE`` lifecycle reason.

    DATA-TYPE-AWARE (operator direction 2026-06-23): returns ``False`` for any
    NON-schedule-defining data_type even on ``SOURCE_RETURNED_ZERO`` — an
    enrichment (FIXTURE_STATS / PLAYER_STATS / ODDS / …) returning zero when a
    fixture exists is a genuine gap, so it stays an in-window absence.

    Args:
        data_type: The manifest ``data_type`` token (case-insensitive match
            against :data:`SCHEDULE_DEFINING_DATA_TYPES`).
        reason: The ``error_reason`` on the ``empty_confirmed`` row.

    Returns:
        ``True`` only when ``data_type`` is schedule-defining AND ``reason`` is
        ``SOURCE_RETURNED_ZERO``. Blank/None data_type or reason → ``False``.
    """
    if not data_type or not reason:
        return False
    return (
        data_type.strip().upper() in SCHEDULE_DEFINING_DATA_TYPES and reason.strip() == _SCHEDULE_EMPTY_RESOLVED_REASON
    )


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


def _to_date(value: _dt.datetime | _dt.date | str) -> _dt.date | None:
    """Coerce a datetime / date / ISO-string to a ``date`` (None if unparseable)."""
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if value:  # remaining type is a non-empty ISO string
        try:
            return _dt.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def was_instrument_alive(
    *,
    available_from: _dt.datetime | _dt.date | str | None,
    available_to: _dt.datetime | _dt.date | str | None,
    day: _dt.datetime | _dt.date | str,
) -> bool:
    """AFFIRMATIVELY confirm an instrument was listed-and-not-yet-delisted on ``day``.

    The lifecycle primitive behind the :class:`EmptyFromLiveInstrumentError` backstop (DeFi-plan A10 /
    operator directive 2026-05-07): when a source returns zero rows for an instrument the
    instruments-service catalog confirms was alive on ``day``, the writer must record ``attempted_failed``
    (a real fetch failure), NOT ``empty_confirmed`` (honest absence). Inputs are
    ``InstrumentRecord.available_from_datetime`` / ``available_to_datetime`` (``available_to=None`` ⇒ still
    active) and the shard ``day``.

    CONSERVATIVE by design: returns ``False`` whenever liveness cannot be CONFIRMED (missing/unparseable
    ``available_from`` or ``day``) — so the backstop fires only on a positive catalog confirmation, never
    on an unknown (an unknown stays ``empty_confirmed``, the less-disruptive default). The per-asset-group
    "expected universe" oracle (sports fixtures, CeFi/DeFi/TradFi instrument lifecycle) feeds this; the
    routing (was-expected → ``attempted_failed`` else ``empty_confirmed``) is the UTL helper that calls it.
    """
    if available_from is None:
        return False
    day_d = _to_date(day)
    from_d = _to_date(available_from)
    if day_d is None or from_d is None:
        return False
    if day_d < from_d:
        return False  # before listing
    if available_to is not None:
        to_d = _to_date(available_to)
        if to_d is not None and day_d >= to_d:
            return False  # on/after delisting
    return True


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
