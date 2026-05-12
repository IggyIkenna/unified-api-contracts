"""Canonical match status taxonomy for sports fixtures.

Defines the closed-set ``MatchStatus`` StrEnum used across all sports adapters
and pipeline consumers.  The values are **canonical grouped states**, NOT raw
API-Football ``status.short`` codes.  See ``AF_STATUS_SHORT_MAP`` for the
mapping from raw codes to canonical states.

SSOT: ``plans/epics/sports_master_2026_05_07.md`` § "Cross-source fixture
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
    def from_af_short(cls, code: str | None) -> "MatchStatus":
        """Map an API-Football ``status.short`` code to canonical MatchStatus.

        Falls back to ``SCHEDULED`` for unknown / empty codes so callers never
        receive a ``KeyError`` on unexpectedly new API codes.
        """
        if not code:
            return cls.SCHEDULED
        return AF_STATUS_SHORT_MAP.get(code.upper(), cls.SCHEDULED)


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

# ---------------------------------------------------------------------------
# Convenience grouping sets — use these instead of ad-hoc frozensets in callers
# ---------------------------------------------------------------------------

COMPLETED_STATUSES: frozenset[MatchStatus] = frozenset(
    {MatchStatus.FINISHED}
)
"""Fixtures where all regulation + extra-time + penalty play is over."""

IN_PROGRESS_STATUSES: frozenset[MatchStatus] = frozenset(
    {MatchStatus.LIVE, MatchStatus.HALFTIME}
)
"""Fixtures currently being played (including halftime break)."""

PRE_MATCH_STATUSES: frozenset[MatchStatus] = frozenset(
    {MatchStatus.SCHEDULED}
)
"""Fixtures not yet kicked off."""

TERMINAL_STATUSES: frozenset[MatchStatus] = frozenset(
    {MatchStatus.POSTPONED, MatchStatus.CANCELLED, MatchStatus.ABANDONED}
)
"""Fixtures that will not (or may not) produce a result today."""

# Raw API-Football codes that map to COMPLETED (used in existing status_short comparisons).
AF_COMPLETED_CODES: frozenset[str] = frozenset({"FT", "AET", "PEN"})
