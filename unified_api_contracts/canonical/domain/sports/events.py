"""Canonical fixture-event schema — goals, cards, substitutions, VAR decisions."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict


class CanonicalFixtureEvent(BaseModel):
    """Normalised in-game event (goal, card, substitution, VAR) across all data sources.

    Per CLAUDE.md "available_at is per-row, write-time" rule for sports,
    fixture_events stamp ``available_at`` from the per-row ``event_time``
    (the absolute UTC instant when the event occurred). Adapters MUST
    populate ``event_time`` on every event row; historical writes that
    pre-date this column may carry null and rely on
    ``kickoff_time + minute*60 + extra_time*60`` as a fallback. The
    write-time stamp is canonical — readers MUST NOT re-derive
    ``available_at`` from ``minute`` at read time.

    Plan reference: writegate_honest_coverage_endtoend_2026_05_06.md
    Phase 2.D — net schema bump after amendments B/C/D dropped 3 others.
    """

    model_config = ConfigDict(frozen=True)

    fixture_id: str
    team_id: str
    player_id: str | None = None
    player_name: str | None = None
    minute: int
    extra_time: int | None = None
    event_type: str  # goal, card, substitution, var
    detail: str | None = None
    comments: str | None = None
    event_time: datetime | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)
