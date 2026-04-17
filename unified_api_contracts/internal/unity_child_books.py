"""Unity meta-broker child book declarations.

SSOT for Unity's 10 child books. 8 confirmed with commissions as of 2026-04-17;
2 pending from https://quant-portal.olesportsresearch.com/unity.

See codex/02-venues/unity-integration.md for the full commercial + technical
spec (single TCP connection, Java Feed Connector sidecar, 3 sports enabled,
USD share class, $10.8k deposit, $2.6k/mo subscription).
"""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.internal.architecture_v2 import (
    CommissionStructureType,
    UnityChildVenue,
)

UNITY_CHILD_BOOKS: list[UnityChildVenue] = [
    UnityChildVenue(
        child_venue_id="PINNACLE_VIA_UNITY",
        display_name="Pinnacle (via Unity)",
        commission_bps=Decimal("40"),  # 0.4%
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER", "TENNIS", "BASKETBALL"],
        notes="Sharp book via Unity — lower limits than direct Pinnacle",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="VX",
        display_name="VX",
        commission_bps=Decimal("20"),  # 0.2%
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER", "TENNIS", "BASKETBALL"],
        notes="Cheapest child book; preferred first",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="SHARPBET",
        display_name="SharpBet",
        commission_bps=Decimal("20"),  # 0.2%
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER", "TENNIS", "BASKETBALL"],
        notes="Cheapest child book; preferred first",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="BETFAIR_VIA_UNITY",
        display_name="Betfair (via Unity)",
        commission_bps=Decimal("50"),  # 0.5% on winnings
        commission_type=CommissionStructureType.COMMISSION_ON_WIN,
        supported_sports=["SOCCER", "TENNIS", "BASKETBALL"],
        notes="Back+lay exchange via Unity aggregated book",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="BROKER3",
        display_name="Broker 3 (confidential)",
        commission_bps=Decimal("0"),  # TBD per commercial agreement
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER"],
        notes="Commission TBD per commercial; existence confirmed",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="BROKER4",
        display_name="Broker 4 (confidential)",
        commission_bps=Decimal("0"),  # TBD per commercial agreement
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER"],
        notes="Commission TBD per commercial; existence confirmed",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="BROKER5",
        display_name="Broker 5 (confidential)",
        commission_bps=Decimal("300"),  # 3.0% — avoid unless spread justifies
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER", "TENNIS", "BASKETBALL"],
        notes="High commission; only route if spread justifies",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="IBCBET",
        display_name="IBCBet",
        commission_bps=Decimal("150"),  # 1.5%
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER", "BASKETBALL"],
        notes="Mid-commission; Asian handicap specialist",
        confirmed=True,
    ),
    # 2 PENDING from quant-portal.olesportsresearch.com/unity — stub entries so
    # the registry can surface the TBD state in UI without shipping fake data.
    UnityChildVenue(
        child_venue_id="TBD_BOOK_9",
        display_name="TBD — pending from quant-portal",
        commission_bps=Decimal("0"),
        commission_type=CommissionStructureType.FLAT,
        supported_sports=[],
        notes="Commission + identity pending from quant-portal.olesportsresearch.com/unity",
        confirmed=False,
    ),
    UnityChildVenue(
        child_venue_id="TBD_BOOK_10",
        display_name="TBD — pending from quant-portal",
        commission_bps=Decimal("0"),
        commission_type=CommissionStructureType.FLAT,
        supported_sports=[],
        notes="Commission + identity pending from quant-portal.olesportsresearch.com/unity",
        confirmed=False,
    ),
]


def get_unity_child_book(child_venue_id: str) -> UnityChildVenue | None:
    for book in UNITY_CHILD_BOOKS:
        if book.child_venue_id == child_venue_id:
            return book
    return None


def unity_child_books_confirmed() -> list[UnityChildVenue]:
    return [b for b in UNITY_CHILD_BOOKS if b.confirmed]


__all__ = [
    "UNITY_CHILD_BOOKS",
    "get_unity_child_book",
    "unity_child_books_confirmed",
]
