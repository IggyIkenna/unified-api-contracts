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
        child_venue_id="3ET",
        display_name="3ET",
        commission_bps=Decimal("0"),  # 0%
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER", "TENNIS", "BASKETBALL"],
        notes="Commission TBD per commercial agreement; existence confirmed from quant-portal 2026-04-17",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="BETFAIR",
        display_name="Betfair (via Unity)",
        commission_bps=Decimal("50"),  # 0.5%
        commission_type=CommissionStructureType.COMMISSION_ON_WIN,
        supported_sports=["SOCCER", "TENNIS", "BASKETBALL"],
        notes="Back+lay exchange via Unity aggregated book; 0.5% on winnings",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="BROKER5",
        display_name="Broker 5",
        commission_bps=Decimal("300"),  # 3%
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER", "TENNIS", "BASKETBALL"],
        notes="High commission (3.0%); only route if spread justifies",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="CROWN",
        display_name="Crown (Asian)",
        commission_bps=Decimal("0"),  # 0%
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER", "BASKETBALL"],
        notes="Asian market operator (marked * on portal); Asian handicap specialist. Commission TBD per commercial.",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="MATCHBOOK",
        display_name="Matchbook (via Unity)",
        commission_bps=Decimal("0"),  # 0%
        commission_type=CommissionStructureType.COMMISSION_ON_WIN,
        supported_sports=["SOCCER", "TENNIS", "BASKETBALL"],
        notes="Exchange via Unity; commission TBD per commercial",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="SBO",
        display_name="SBO (Asian)",
        commission_bps=Decimal("0"),  # 0%
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER", "BASKETBALL"],
        notes=(
            "Asian market operator (marked * on portal; SBOBet); "
            "Asian handicap specialist. Commission TBD per commercial."
        ),
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="SHARPBET",
        display_name="SharpBet",
        commission_bps=Decimal("20"),  # 0.2%
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER", "TENNIS", "BASKETBALL"],
        notes="Cheapest child book (0.2%); preferred first",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="VX",
        display_name="VX",
        commission_bps=Decimal("20"),  # 0.2%
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER", "TENNIS", "BASKETBALL"],
        notes="Cheapest child book (0.2%); preferred first",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="BETDEX",
        display_name="Betdex",
        commission_bps=Decimal("0"),  # 0%
        commission_type=CommissionStructureType.COMMISSION_ON_WIN,
        supported_sports=["SOCCER", "TENNIS", "BASKETBALL"],
        notes="Decentralized betting exchange via Unity; commission TBD per commercial",
        confirmed=True,
    ),
    UnityChildVenue(
        child_venue_id="IBC",
        display_name="IBC (Asian)",
        commission_bps=Decimal("150"),  # 1.5%
        commission_type=CommissionStructureType.FLAT,
        supported_sports=["SOCCER", "BASKETBALL"],
        notes="Asian market operator (marked * on portal; IBCBet); Asian handicap specialist. 1.5% commission.",
        confirmed=True,
    ),
]


#: Minimum sane commission (bps) for a *confirmed* Unity child book.
#: VX and SharpBet sit at 20 bps (0.2%). Below this = suspect data entry error.
UNITY_MIN_CONFIRMED_COMMISSION_BPS: Decimal = Decimal("20")
#: Maximum sane commission (bps) for a *confirmed* Unity child book.
#: Broker 5 sits at 300 bps (3.0%). Above this = suspect data entry error.
UNITY_MAX_CONFIRMED_COMMISSION_BPS: Decimal = Decimal("300")
#: Allowed values for ``UnityChildVenue.supported_sports``. Unity has 3 sports
#: enabled (soccer, tennis, basketball). Adding a new sport requires a UAC
#: schema bump + contract with Unity.
UNITY_SUPPORTED_SPORTS: frozenset[str] = frozenset({"SOCCER", "TENNIS", "BASKETBALL"})
#: Commission-TBD-per-commercial-agreement sentinel. Broker 3 and Broker 4 are
#: confirmed-existence but commission was not disclosed at time of schema landing.
#: ``commission_bps`` set to 0 is the documented sentinel; callers must treat
#: 0 on a confirmed book as "commercial-pending" not "free".
UNITY_COMMERCIAL_PENDING_COMMISSION_BPS: Decimal = Decimal("0")
#: Sentinel prefix for stub books pending identity pull from quant-portal.
UNITY_TBD_PREFIX: str = "TBD_BOOK_"


def get_unity_child_book(child_venue_id: str) -> UnityChildVenue | None:
    for book in UNITY_CHILD_BOOKS:
        if book.child_venue_id == child_venue_id:
            return book
    return None


def unity_child_books_confirmed() -> list[UnityChildVenue]:
    """Return only confirmed child books.

    Consumers routing live orders MUST use this, NOT :data:`UNITY_CHILD_BOOKS`
    directly — otherwise TBD stub books will be treated as routable venues.
    """
    return [b for b in UNITY_CHILD_BOOKS if b.confirmed]


def unity_child_books_pending() -> list[UnityChildVenue]:
    """Return only unconfirmed (TBD) child books.

    Used by UIs to surface pending-identity state. Routing MUST skip these.
    """
    return [b for b in UNITY_CHILD_BOOKS if not b.confirmed]


def validate_unity_child_book(book: UnityChildVenue) -> list[str]:
    """Return a list of validation error strings. Empty list == valid.

    Invariants enforced:
    - ``supported_sports`` must be a subset of :data:`UNITY_SUPPORTED_SPORTS`
    - If ``confirmed`` AND ``commission_bps > 0``: must be in
      ``[UNITY_MIN_CONFIRMED_COMMISSION_BPS, UNITY_MAX_CONFIRMED_COMMISSION_BPS]``
    - If not ``confirmed``: ``child_venue_id`` must start with ``TBD_BOOK_`` and
      ``supported_sports`` must be empty (do not route).
    """
    errors: list[str] = []
    unknown_sports = set(book.supported_sports) - UNITY_SUPPORTED_SPORTS
    if unknown_sports:
        errors.append(
            f"{book.child_venue_id}: unsupported sports {sorted(unknown_sports)} "
            f"(allowed: {sorted(UNITY_SUPPORTED_SPORTS)})"
        )
    if book.confirmed and book.commission_bps > Decimal("0"):
        if book.commission_bps < UNITY_MIN_CONFIRMED_COMMISSION_BPS:
            errors.append(
                f"{book.child_venue_id}: commission_bps {book.commission_bps} "
                f"below floor {UNITY_MIN_CONFIRMED_COMMISSION_BPS}"
            )
        if book.commission_bps > UNITY_MAX_CONFIRMED_COMMISSION_BPS:
            errors.append(
                f"{book.child_venue_id}: commission_bps {book.commission_bps} "
                f"above ceiling {UNITY_MAX_CONFIRMED_COMMISSION_BPS}"
            )
    if not book.confirmed:
        if not book.child_venue_id.startswith(UNITY_TBD_PREFIX):
            errors.append(
                f"{book.child_venue_id}: unconfirmed books must use child_venue_id prefix {UNITY_TBD_PREFIX!r}"
            )
        if book.supported_sports:
            errors.append(
                f"{book.child_venue_id}: unconfirmed books must have empty supported_sports (pending identity)"
            )
    return errors


__all__ = [
    "UNITY_CHILD_BOOKS",
    "UNITY_COMMERCIAL_PENDING_COMMISSION_BPS",
    "UNITY_MAX_CONFIRMED_COMMISSION_BPS",
    "UNITY_MIN_CONFIRMED_COMMISSION_BPS",
    "UNITY_SUPPORTED_SPORTS",
    "UNITY_TBD_PREFIX",
    "get_unity_child_book",
    "unity_child_books_confirmed",
    "unity_child_books_pending",
    "validate_unity_child_book",
]
