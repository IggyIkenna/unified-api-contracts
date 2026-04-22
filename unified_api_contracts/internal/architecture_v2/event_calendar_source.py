"""Event-calendar source capability registry — G2.9 gap #5.

Stage 3E § 2.9 gap #5 from ``codex/09-strategy/architecture-v2/uac-registry-gaps.md``.
``EVENT_DRIVEN`` strategies fire on scheduled external events — macro
releases (NFP / CPI / FOMC), earnings, token unlocks, governance
votes, slashing events, sports news. Each source has different
coverage, ingestion latency, and auth model.

Before this module these were referenced ad-hoc across services with
no single declaration of "which source covers which category on which
markets?" — ``EVENT_DRIVEN x {CeFi, DeFi, Sports, TradFi}`` cells in
the matrix lived at PARTIAL even when sources existed, because
strategy-service couldn't mechanically verify coverage.

Consumer integration:

* features-event-service (absent from this workspace — tracked below)
  queries ``source_for(source_id)`` + ``sources_covering(category)``.
* strategy-service config validator asserts every ``EVENT_DRIVEN`` slot
  has at least one calendar source covering its target markets.
* Data-freshness monitors read ``ingestion_latency_sla_seconds`` to
  gate signal dispatch.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field


class EventSourceType(StrEnum):
    """Upstream provider type for an event calendar source."""

    MACRO_CONSENSUS = "macro_consensus"
    """Bloomberg, TradingEconomics — consensus forecasts + releases."""

    EARNINGS_CALENDAR = "earnings_calendar"
    """Bloomberg, Refinitiv — corporate earnings dates."""

    TOKEN_UNLOCKS = "token_unlocks"
    """TokenUnlocks.io / on-chain vesting trackers."""

    PROTOCOL_GOVERNANCE = "protocol_governance"
    """Snapshot, Tally, Aave governance feeds."""

    SLASHING_FEED = "slashing_feed"
    """Lido oracle, Rocket Pool feeds."""

    SPORTS_NEWS = "sports_news"
    """SharpAPI, SFI — lineup releases + injury news."""


class EventCategory(StrEnum):
    """Categories of event this source surfaces."""

    MACRO_RELEASE = "macro_release"
    """NFP, CPI, FOMC, GDP, unemployment."""

    EARNINGS = "earnings"
    """Quarterly corporate earnings."""

    TOKEN_UNLOCK = "token_unlock"
    """Scheduled supply unlock events."""

    GOVERNANCE_VOTE = "governance_vote"
    """On-chain DAO proposal resolution."""

    SLASHING_EVENT = "slashing_event"
    """Validator slashing."""

    SPORTS_LINEUP_RELEASE = "sports_lineup_release"
    """Confirmed starting lineups."""

    SPORTS_INJURY_NEWS = "sports_injury_news"
    """Player injury reports."""


AuthModel = Literal["api_key", "oauth", "public"]


class EventCalendarSource(BaseModel):
    """One event-calendar source declaration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    source_type: EventSourceType
    covered_categories: tuple[EventCategory, ...]
    """Sub-categories this source covers."""

    covered_markets: tuple[str, ...]
    """Markets covered: country ISO codes for macro, exchange IDs for
    earnings, chain:token for tokens, league IDs for sports."""

    ingestion_latency_sla_seconds: int = Field(ge=0)
    """p95 latency from event occurrence to ingestion — the SLA the
    source commits to (not our downstream processing latency)."""

    data_freshness_ref: str
    """Features-service data-freshness key for downstream monitoring."""

    api_auth_model: AuthModel
    notes: str = ""


EVENT_CALENDAR_SOURCES: Final[tuple[EventCalendarSource, ...]] = (
    # ── Macro consensus ────────────────────────────────────────────────
    EventCalendarSource(
        source_id="bloomberg_macro",
        source_type=EventSourceType.MACRO_CONSENSUS,
        covered_categories=(EventCategory.MACRO_RELEASE,),
        covered_markets=("US", "GB", "EU", "JP", "CN", "IN"),
        ingestion_latency_sla_seconds=5,
        data_freshness_ref="features-event/bloomberg_macro",
        api_auth_model="api_key",
        notes="Bloomberg TERM — primary macro consensus source.",
    ),
    EventCalendarSource(
        source_id="trading_economics_macro",
        source_type=EventSourceType.MACRO_CONSENSUS,
        covered_categories=(EventCategory.MACRO_RELEASE,),
        covered_markets=("US", "GB", "EU", "JP", "CN", "IN", "BR", "MX", "AU"),
        ingestion_latency_sla_seconds=30,
        data_freshness_ref="features-event/trading_economics",
        api_auth_model="api_key",
        notes="TradingEconomics — broader EM coverage, slower than Bloomberg.",
    ),
    # ── Earnings ───────────────────────────────────────────────────────
    EventCalendarSource(
        source_id="bloomberg_earnings",
        source_type=EventSourceType.EARNINGS_CALENDAR,
        covered_categories=(EventCategory.EARNINGS,),
        covered_markets=("NASDAQ", "NYSE", "LSE", "TSE", "NSE"),
        ingestion_latency_sla_seconds=60,
        data_freshness_ref="features-event/bloomberg_earnings",
        api_auth_model="api_key",
    ),
    # ── Token unlocks ──────────────────────────────────────────────────
    EventCalendarSource(
        source_id="token_unlocks_io",
        source_type=EventSourceType.TOKEN_UNLOCKS,
        covered_categories=(EventCategory.TOKEN_UNLOCK,),
        covered_markets=(
            "ETHEREUM:ARB",
            "ETHEREUM:OP",
            "ETHEREUM:APE",
            "ETHEREUM:STRK",
            "SOLANA:JTO",
        ),
        ingestion_latency_sla_seconds=3600,
        data_freshness_ref="features-event/token_unlocks",
        api_auth_model="public",
        notes="TokenUnlocks.io — scheduled in advance, latency is hours.",
    ),
    # ── Governance ─────────────────────────────────────────────────────
    EventCalendarSource(
        source_id="snapshot_gov",
        source_type=EventSourceType.PROTOCOL_GOVERNANCE,
        covered_categories=(EventCategory.GOVERNANCE_VOTE,),
        covered_markets=(
            "ETHEREUM:AAVE",
            "ETHEREUM:COMP",
            "ETHEREUM:UNI",
            "ETHEREUM:MKR",
        ),
        ingestion_latency_sla_seconds=120,
        data_freshness_ref="features-event/snapshot",
        api_auth_model="public",
    ),
    # ── Slashing ───────────────────────────────────────────────────────
    EventCalendarSource(
        source_id="lido_slashing",
        source_type=EventSourceType.SLASHING_FEED,
        covered_categories=(EventCategory.SLASHING_EVENT,),
        covered_markets=("ETHEREUM:stETH",),
        ingestion_latency_sla_seconds=60,
        data_freshness_ref="features-event/lido_slashing",
        api_auth_model="public",
    ),
    # ── Sports ─────────────────────────────────────────────────────────
    EventCalendarSource(
        source_id="sharp_api_sports",
        source_type=EventSourceType.SPORTS_NEWS,
        covered_categories=(
            EventCategory.SPORTS_LINEUP_RELEASE,
            EventCategory.SPORTS_INJURY_NEWS,
        ),
        covered_markets=("NFL", "NBA", "MLB", "EPL", "CHAMPIONS_LEAGUE"),
        ingestion_latency_sla_seconds=15,
        data_freshness_ref="features-event/sharp_api",
        api_auth_model="api_key",
    ),
    EventCalendarSource(
        source_id="sfi_sports_news",
        source_type=EventSourceType.SPORTS_NEWS,
        covered_categories=(EventCategory.SPORTS_LINEUP_RELEASE,),
        covered_markets=("EPL", "LA_LIGA", "BUNDESLIGA"),
        ingestion_latency_sla_seconds=30,
        data_freshness_ref="features-event/sfi",
        api_auth_model="api_key",
    ),
)


class EventSourceNotFoundError(LookupError):
    """Raised when ``source_for(source_id)`` can't resolve."""


def source_for(
    source_id: str,
    *,
    registry: Iterable[EventCalendarSource] = EVENT_CALENDAR_SOURCES,
) -> EventCalendarSource:
    """Resolve a source by id. Fail-loud on miss."""

    for entry in registry:
        if entry.source_id == source_id:
            return entry
    raise EventSourceNotFoundError(
        f"source_id={source_id!r} not in EVENT_CALENDAR_SOURCES",
    )


def sources_covering(
    category: EventCategory,
    *,
    registry: Iterable[EventCalendarSource] = EVENT_CALENDAR_SOURCES,
) -> tuple[EventCalendarSource, ...]:
    """All sources declaring coverage for ``category``."""

    return tuple(entry for entry in registry if category in entry.covered_categories)


def sources_covering_market(
    market: str,
    *,
    registry: Iterable[EventCalendarSource] = EVENT_CALENDAR_SOURCES,
) -> tuple[EventCalendarSource, ...]:
    """All sources declaring coverage for a specific market identifier."""

    return tuple(entry for entry in registry if market in entry.covered_markets)


def _validate_registry_invariants(
    registry: Iterable[EventCalendarSource] = EVENT_CALENDAR_SOURCES,
) -> None:
    """Invariants:

    * ``source_id`` unique.
    * ``covered_categories`` + ``covered_markets`` both non-empty.
    * ``data_freshness_ref`` non-empty.
    """

    seen: set[str] = set()
    for entry in registry:
        if entry.source_id in seen:
            raise ValueError(
                f"duplicate source_id in EVENT_CALENDAR_SOURCES: {entry.source_id!r}",
            )
        seen.add(entry.source_id)
        if not entry.covered_categories:
            raise ValueError(
                f"{entry.source_id!r}: covered_categories must be non-empty",
            )
        if not entry.covered_markets:
            raise ValueError(
                f"{entry.source_id!r}: covered_markets must be non-empty",
            )
        if not entry.data_freshness_ref:
            raise ValueError(
                f"{entry.source_id!r}: data_freshness_ref must be non-empty",
            )


_validate_registry_invariants()


# NOTE: features-event-service is NOT present in this workspace as of
# 2026-04-22. G2.3 Data Catalogue plan will scaffold it; this module
# declares the SSOT for that service to consume. strategy-service
# validation call-site remains the anchor consumer.
CONSUMER_CALL_SITES: Final[tuple[str, ...]] = (
    "strategy-service/strategy_service/validation/data_certification.py",
    "strategy-service/strategy_service/validation/freshness_gate.py",
    # features-event-service (pending scaffold via G2.3):
    "features-event-service/features_event_service/sources.py",
)


__all__ = [
    "CONSUMER_CALL_SITES",
    "EVENT_CALENDAR_SOURCES",
    "AuthModel",
    "EventCalendarSource",
    "EventCategory",
    "EventSourceNotFoundError",
    "EventSourceType",
    "source_for",
    "sources_covering",
    "sources_covering_market",
]
