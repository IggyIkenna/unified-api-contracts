"""Canonical live-mode schemas — real-time event wrappers for live sports trading.

Defines the Pub/Sub message schemas that wrap existing canonical types for live
data flow through the UTS pipeline (MTDS → FSS → strategy → execution).

Also defines the FSS→strategy sports-feature PubSub payload contract for the
``capture_status`` key, which carries the 4-state honest-absence signal so
strategy subscribers can gate directly on the manifest state rather than
using an odds-presence heuristic.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Final, Literal, Self

from pydantic import BaseModel, ConfigDict

from .odds import CanonicalOdds

# ---------------------------------------------------------------------------
# FSS → strategy sports-feature PubSub payload — capture_status contract
#
# The FSS PubSub subscriber (features_service.sports.app.pubsub.subscriber)
# publishes a raw JSON dict to ``features-sports-{feature_group}``.  Strategy
# reads this dict in SportsFeatureSubscriber.  This constant names the key
# under which the 4-state manifest capture_status is stamped, and the type
# alias encodes the closed set of valid values.
#
# Background: honest-absence lives in the GCS manifest; the FSS subscriber
# knows the compute outcome at emit-time (process_sports_record returns None
# for honest-empty payloads). Stamping capture_status directly on the event
# closes the contract gap — strategy can gate on the real 4-state signal
# instead of the odds-presence heuristic added in c2793217.
#
# Strategy fallback rule: when capture_status is absent (in-flight events
# pre-rollout) fall back to _is_honest_empty_vector for backward compat.
# ---------------------------------------------------------------------------

SPORTS_FEATURE_PAYLOAD_CAPTURE_STATUS_KEY: Final[str] = "capture_status"
"""JSON key name for ``capture_status`` in FSS→strategy PubSub feature payloads.

Stamp with a :data:`SportsFeatureCaptureStatus` value before publishing.
"""

SportsFeatureCaptureStatus = Literal[
    "captured",
    "empty_confirmed",
    "attempted_failed",
    "expected_unattempted",
]
"""4-state honest-absence signal stamped on live FSS→strategy feature payloads.

Mirrors the manifest ``capture_status`` column (canonical schema v9).  Strategy
subscribers gate on this value directly; the heuristic fallback
(``_is_honest_empty_vector``) only applies when the key is absent (backward
compat with in-flight events emitted before this contract was added).
"""


class MatchPeriod(StrEnum):
    """Current period of a live match."""

    PRE_MATCH = "pre_match"
    FIRST_HALF = "1H"
    HALF_TIME = "HT"
    SECOND_HALF = "2H"
    EXTRA_TIME_FIRST = "ET1"
    EXTRA_TIME_SECOND = "ET2"
    PENALTIES = "PEN"
    FULL_TIME = "FT"
    ABANDONED = "abandoned"
    POSTPONED = "postponed"


class LiveOddsUpdate(BaseModel):
    """Pub/Sub message wrapping a CanonicalOdds snapshot for live streaming.

    Published by market-tick-data-service (category=sports) whenever a new
    odds snapshot arrives from any tier (Odds API, OpticOdds/OddsJam, own scrapers).
    Consumed by features-sports-service in live mode.
    """

    model_config = ConfigDict(frozen=True)

    event_type: str = "ODDS_UPDATE"
    fixture_id: str
    bookmaker_key: str
    timestamp_utc: datetime
    is_in_play: bool
    match_minute: int | None = None
    odds: CanonicalOdds
    source_tier: str  # "odds_api", "opticodds", "scraper", "exchange"

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)


class LiveMatchState(BaseModel):
    """Unified match state combining score, time, and period.

    Drives feature recomputation triggers in FSS live mode. Published by
    MTDS (from live stats scrapers or API sources) to the coordination topic.
    """

    model_config = ConfigDict(frozen=True)

    fixture_id: str
    timestamp_utc: datetime
    period: MatchPeriod
    match_minute: int
    stoppage_time: int = 0
    is_live: bool
    home_score: int
    away_score: int
    home_red_cards: int = 0
    away_red_cards: int = 0
    home_penalties: int | None = None
    away_penalties: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)


class ScraperVersionMeta(BaseModel):
    """Website version tracking for a bookmaker scraper adapter.

    Stored per bookmaker in USEI. When a scraper fails, the registry flags
    the bookmaker as stale and alerts for CSS selector updates.
    """

    model_config = ConfigDict(frozen=True)

    bookmaker_key: str
    scraper_schema_version: str  # e.g. "bet365-v3"
    css_selector_hash: str  # SHA-256 of the selector set
    last_validated_utc: datetime
    page_structure_version: str  # e.g. "2026-03-01"
    is_stale: bool = False
    last_error: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)
