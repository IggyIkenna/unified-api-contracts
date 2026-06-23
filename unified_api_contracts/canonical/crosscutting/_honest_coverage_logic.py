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


# ---------------------------------------------------------------------------
# Schedule-defining data_types — "empty source response == complete" (operator
# direction 2026-06-23).
#
# A schedule-defining data_type IS the source-of-truth for whether anything
# exists to capture on a (entity, day). API-Football ``FIXTURES`` is the sports
# schedule: when its fixtures endpoint returns 200 + zero rows for a
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
# fixture DOES exist is a real enrichment gap. So only ``FIXTURES`` qualifies.
# SSOT: ``codex/02-data/honest-absence-downstream-handling.md`` + the operator
# directive 2026-06-23.
# ---------------------------------------------------------------------------

SCHEDULE_DEFINING_DATA_TYPES: Final[frozenset[str]] = frozenset({"FIXTURES"})
"""Closed set of schedule-DEFINING data_types — the source-of-truth for whether
anything exists to capture on a (entity, day). For these, a clean
``SOURCE_RETURNED_ZERO`` (200 + zero rows) means "no matches that day = complete"
→ RESOLVED, not a gap (see :func:`is_resolved_schedule_empty`). Today only
sports ``FIXTURES`` (API-Football, the schedule). Enrichment data_types are NOT
here — their zero-row responses may be real gaps."""

_SCHEDULE_EMPTY_RESOLVED_REASON: Final[str] = "SOURCE_RETURNED_ZERO"
"""The ONLY ``empty_confirmed`` reason a schedule-defining data_type resolves
via :func:`is_resolved_schedule_empty`: a proven clean 200+empty fetch (no
matches that day). ``EXPECTED_*`` calendar reasons are already out-of-window."""


def is_resolved_schedule_empty(data_type: str | None, reason: str | None) -> bool:
    """True iff a schedule-DEFINING data_type's empty cell is RESOLVED (complete).

    A schedule-defining data_type (today only sports ``FIXTURES``, the
    API-Football schedule) that is ``empty_confirmed`` with reason
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
