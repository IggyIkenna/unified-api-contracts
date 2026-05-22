"""Matchbook schema stubs — sportsbook scope post-cutover.

Full schema definitions ship with the matchbook adapter plan.
These stubs satisfy the venue-manifest parity tests.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MatchbookAuthResponse:
    pass


@dataclass
class MatchbookErrorResponse:
    pass


@dataclass
class MatchbookBackPrice:
    pass


@dataclass
class MatchbookPrices:
    pass


@dataclass
class MatchbookRunner:
    pass


@dataclass
class MatchbookMarket:
    pass


@dataclass
class MatchbookEvent:
    pass


@dataclass
class MatchbookEventsResponse:
    pass


@dataclass
class MatchbookMarketsResponse:
    pass


@dataclass
class MatchbookOfferResponse:
    pass


@dataclass
class MatchbookBalanceInfo:
    pass


@dataclass
class MatchbookAccountResponse:
    pass


@dataclass
class MatchbookOdds:
    pass


__all__ = [
    "MatchbookAccountResponse",
    "MatchbookAuthResponse",
    "MatchbookBackPrice",
    "MatchbookBalanceInfo",
    "MatchbookErrorResponse",
    "MatchbookEvent",
    "MatchbookEventsResponse",
    "MatchbookMarket",
    "MatchbookMarketsResponse",
    "MatchbookOdds",
    "MatchbookOfferResponse",
    "MatchbookPrices",
    "MatchbookRunner",
]
