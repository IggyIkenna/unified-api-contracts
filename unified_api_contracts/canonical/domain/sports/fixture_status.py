"""Canonical match status taxonomy for sports fixtures.

Defines the closed-set ``MatchStatus`` StrEnum used across all sports adapters
and pipeline consumers.  The values are **canonical grouped states**, NOT raw
API-Football ``status.short`` codes.  See ``AF_STATUS_SHORT_MAP`` for the
mapping from raw codes to canonical states.

SSOT: ``plans/epics/sports_master.md`` § "Cross-source fixture
status verifier + status enum".
"""

from __future__ import annotations

from enum import StrEnum


class MatchStatus(StrEnum):
    """Canonical closed-set match status.

    Values are grouped canonical states that normalise across data sources
    (API-Football, FootyStats, SFI, Understat).  Raw API-Football
    ``status.short`` codes are mapped via ``AF_STATUS_SHORT_MAP``.

    Groups:
    - Pre-match:  SCHEDULED
    - In-play:    LIVE, HALFTIME
    - Finished:   FINISHED
    - Interrupted: SUSPENDED, INTERRUPTED
    - Terminal:   POSTPONED, CANCELLED, ABANDONED
    """

    SCHEDULED = "scheduled"
    LIVE = "live"
    HALFTIME = "halftime"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    ABANDONED = "abandoned"
    SUSPENDED = "suspended"
    INTERRUPTED = "interrupted"

    @classmethod
    def from_af_short(cls, code: str | None) -> MatchStatus:
        """Map an API-Football ``status.short`` code to canonical MatchStatus.

        Falls back to ``SCHEDULED`` for unknown / empty codes so callers never
        receive a ``KeyError`` on unexpectedly new API codes.
        """
        if not code:
            return cls.SCHEDULED
        return AF_STATUS_SHORT_MAP.get(code.upper(), cls.SCHEDULED)

    @classmethod
    def from_footystats_status(cls, status: str | None) -> MatchStatus:
        """Map a FootyStats ``status`` field to canonical MatchStatus.

        FootyStats uses lower-case strings: ``scheduled`` / ``live`` /
        ``complete`` / ``cancelled`` / ``postponed`` / ``suspended``.
        Less granular than API-Football (no HALFTIME / extra-time distinction
        at status grain); ``live`` covers all in-play states including HT.
        Falls back to ``SCHEDULED`` for unknown / empty values.
        """
        if not status:
            return cls.SCHEDULED
        return FS_STATUS_MAP.get(status.strip().lower(), cls.SCHEDULED)

    @classmethod
    def from_sfi_state(
        cls,
        *,
        timer_seconds: int | None,
        ht_start_timer: int | None = None,
        ht_end_timer: int | None = None,
        frozen: bool = False,
    ) -> MatchStatus:
        """Derive canonical MatchStatus from SFI progressive-stats state.

        SFI doesn't publish a discrete status code — match phase is inferred
        from the progressive-stats timer state per the lifecycle SSOT
        (``codex/02-data/sports-fixtures-lifecycle.md``):

        - No row yet (``timer_seconds is None``) → SCHEDULED
        - Timer frozen (caller signals ``frozen=True`` after freeze-detect) → FINISHED
        - Within halftime window (``ht_start_timer <= ts <= ht_end_timer``) → HALFTIME
        - Otherwise → LIVE (regulation 1H/2H or extra time)

        ``frozen`` is the freeze-detect signal from
        ``unified_trading_library.fixtures.resolve_match_end_time()`` or the
        SFI adapter's ``_detect_match_end_time()`` helper.
        """
        if timer_seconds is None:
            return cls.SCHEDULED
        if frozen:
            return cls.FINISHED
        if ht_start_timer is not None and ht_end_timer is not None and ht_start_timer <= timer_seconds <= ht_end_timer:
            return cls.HALFTIME
        return cls.LIVE


AF_STATUS_SHORT_MAP: dict[str, MatchStatus] = {
    # Pre-match
    "NS": MatchStatus.SCHEDULED,
    "TBD": MatchStatus.SCHEDULED,
    # In-play
    "1H": MatchStatus.LIVE,
    "2H": MatchStatus.LIVE,
    "ET": MatchStatus.LIVE,
    "BT": MatchStatus.LIVE,
    "P": MatchStatus.LIVE,
    "LIVE": MatchStatus.LIVE,
    # Halftime break (kept distinct — important for in-play strategy gates)
    "HT": MatchStatus.HALFTIME,
    # Finished
    "FT": MatchStatus.FINISHED,
    "AET": MatchStatus.FINISHED,
    "PEN": MatchStatus.FINISHED,
    "AWD": MatchStatus.FINISHED,
    "WO": MatchStatus.FINISHED,
    # Interrupted
    "SUSP": MatchStatus.SUSPENDED,
    "INT": MatchStatus.INTERRUPTED,
    # Terminal
    "PST": MatchStatus.POSTPONED,
    "CANC": MatchStatus.CANCELLED,
    "ABD": MatchStatus.ABANDONED,
}

FS_STATUS_MAP: dict[str, MatchStatus] = {
    # FootyStats lowercase status strings (per the post-2025-10 schema).
    # FootyStats does NOT distinguish HT from regular play — all in-play is "live".
    "scheduled": MatchStatus.SCHEDULED,
    "live": MatchStatus.LIVE,
    "complete": MatchStatus.FINISHED,
    "finished": MatchStatus.FINISHED,  # alternate spelling seen in older responses
    "cancelled": MatchStatus.CANCELLED,
    "canceled": MatchStatus.CANCELLED,  # American spelling sometimes appears
    "postponed": MatchStatus.POSTPONED,
    "suspended": MatchStatus.SUSPENDED,
    "abandoned": MatchStatus.ABANDONED,
}

# ---------------------------------------------------------------------------
# Convenience grouping sets — use these instead of ad-hoc frozensets in callers
# ---------------------------------------------------------------------------

COMPLETED_STATUSES: frozenset[MatchStatus] = frozenset({MatchStatus.FINISHED})
"""Fixtures where all regulation + extra-time + penalty play is over."""

IN_PROGRESS_STATUSES: frozenset[MatchStatus] = frozenset({MatchStatus.LIVE, MatchStatus.HALFTIME})
"""Fixtures currently being played (including halftime break)."""

PRE_MATCH_STATUSES: frozenset[MatchStatus] = frozenset({MatchStatus.SCHEDULED})
"""Fixtures not yet kicked off."""

TERMINAL_STATUSES: frozenset[MatchStatus] = frozenset(
    {MatchStatus.POSTPONED, MatchStatus.CANCELLED, MatchStatus.ABANDONED}
)
"""Fixtures that will not (or may not) produce a result today."""

# Raw API-Football codes that map to COMPLETED (used in existing status_short comparisons).
# Includes regulation-end (FT), extra-time (AET), penalties (PEN), and the two
# awarded-result codes (AWD = technical walkover, WO = walkover) — both produce
# a final result row even though no play occurred. Reference: instruments-service
# scripts/audit_fixtures_via_api_football.py:94 source comment "AWD=tech-walkover,
# WO=walkover". Mirrors the AF_STATUS_SHORT_MAP entries that resolve to
# MatchStatus.FINISHED.
AF_COMPLETED_CODES: frozenset[str] = frozenset({"FT", "AET", "PEN", "AWD", "WO"})
