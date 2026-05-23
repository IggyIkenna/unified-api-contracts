"""1xBet schema stubs — sportsbook scope post-cutover.

Full schema definitions ship with the 1xBet adapter plan.
These stubs satisfy the venue-manifest parity tests.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OneXBetOutcome:
    pass


@dataclass
class OneXBetMarket:
    pass


@dataclass
class OneXBetOddsResponse:
    pass


@dataclass
class OneXBetEvent:
    pass


__all__ = [
    "OneXBetEvent",
    "OneXBetMarket",
    "OneXBetOddsResponse",
    "OneXBetOutcome",
]
