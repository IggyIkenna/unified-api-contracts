"""Tests for Unity child book registry (Strategy Architecture v2 Phase 13).

Invariants:
- Exactly 10 child books total (8 confirmed + 2 TBD pending from quant-portal)
- Confirmed books have sane commission_bps (20-300) except commercial-pending (0)
- TBD books have ``TBD_BOOK_`` prefix, ``confirmed=False``, and notes mentioning
  the quant-portal URL
- ``unity_child_books_confirmed()`` never returns a TBD book
- ``unity_child_books_pending()`` returns exactly the unconfirmed books
- ``supported_sports`` is a subset of SOCCER/TENNIS/BASKETBALL
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from unified_api_contracts.internal import (
    UNITY_CHILD_BOOKS,
    UNITY_MAX_CONFIRMED_COMMISSION_BPS,
    UNITY_MIN_CONFIRMED_COMMISSION_BPS,
    UNITY_SUPPORTED_SPORTS,
    UNITY_TBD_PREFIX,
    UnityChildVenue,
    get_unity_child_book,
    unity_child_books_confirmed,
    unity_child_books_pending,
    validate_unity_child_book,
)
from unified_api_contracts.internal.architecture_v2 import CommissionStructureType


@pytest.mark.unit
class TestUnityChildBookRegistry:
    def test_total_book_count_is_ten(self) -> None:
        assert len(UNITY_CHILD_BOOKS) == 10, "Unity has 10 child books (8 confirmed + 2 pending from quant-portal)"

    def test_exactly_eight_confirmed(self) -> None:
        confirmed = unity_child_books_confirmed()
        assert len(confirmed) == 8, (
            "8 confirmed child books: Pinnacle, VX, SharpBet, Betfair, Broker3, Broker4, Broker5, IBCBet"
        )
        for book in confirmed:
            assert book.confirmed is True

    def test_exactly_two_pending(self) -> None:
        pending = unity_child_books_pending()
        assert len(pending) == 2, (
            "2 pending child books awaiting data pull from quant-portal.olesportsresearch.com/unity"
        )
        for book in pending:
            assert book.confirmed is False

    def test_confirmed_and_pending_partition_full_registry(self) -> None:
        confirmed = {b.child_venue_id for b in unity_child_books_confirmed()}
        pending = {b.child_venue_id for b in unity_child_books_pending()}
        all_ids = {b.child_venue_id for b in UNITY_CHILD_BOOKS}
        assert confirmed.isdisjoint(pending)
        assert confirmed | pending == all_ids

    def test_pending_books_reference_quant_portal(self) -> None:
        for book in unity_child_books_pending():
            assert "quant-portal.olesportsresearch.com/unity" in book.notes, (
                f"{book.child_venue_id} notes must reference quant-portal URL so "
                f"operators know where to pull final identity from"
            )

    def test_pending_books_have_tbd_prefix(self) -> None:
        for book in unity_child_books_pending():
            assert book.child_venue_id.startswith(UNITY_TBD_PREFIX), (
                f"Unconfirmed book {book.child_venue_id!r} must use {UNITY_TBD_PREFIX!r} prefix"
            )

    def test_pending_books_have_no_supported_sports(self) -> None:
        """TBD books must have empty supported_sports so they are never routable."""
        for book in unity_child_books_pending():
            assert book.supported_sports == [], (
                f"{book.child_venue_id}: supported_sports must be empty for unconfirmed books (identity not yet known)"
            )

    def test_unique_child_venue_ids(self) -> None:
        ids = [b.child_venue_id for b in UNITY_CHILD_BOOKS]
        assert len(ids) == len(set(ids)), "child_venue_id must be unique"


@pytest.mark.unit
class TestUnityChildBookInvariantsForRouting:
    """Routing MUST only hit confirmed books. TBD stubs must be filtered out."""

    def test_confirmed_returns_no_tbd_books(self) -> None:
        confirmed = unity_child_books_confirmed()
        for book in confirmed:
            assert not book.child_venue_id.startswith(UNITY_TBD_PREFIX), (
                f"confirmed() leaked TBD book {book.child_venue_id!r} — consumer routing would hit a stub"
            )

    def test_get_by_id_hits_known_books(self) -> None:
        for expected in ("VX", "SHARPBET", "PINNACLE_VIA_UNITY", "BETFAIR_VIA_UNITY"):
            book = get_unity_child_book(expected)
            assert book is not None, f"{expected} missing from registry"
            assert book.confirmed is True

    def test_get_by_id_returns_none_for_unknown(self) -> None:
        assert get_unity_child_book("DEFINITELY_NOT_A_BOOK") is None

    def test_get_by_id_hits_tbd_stubs(self) -> None:
        """TBD stubs must still be retrievable by id (UI surfaces them)."""
        for tbd in ("TBD_BOOK_9", "TBD_BOOK_10"):
            book = get_unity_child_book(tbd)
            assert book is not None
            assert book.confirmed is False


@pytest.mark.unit
class TestUnityChildBookCommissionSanity:
    def test_confirmed_commissions_in_range_or_pending(self) -> None:
        """Confirmed books: commission_bps in [20, 300] or 0 (commercial-pending)."""
        for book in unity_child_books_confirmed():
            if book.commission_bps == Decimal("0"):
                # Broker3 / Broker4 commercial-pending sentinel
                assert "TBD" in book.notes or "pending" in book.notes.lower(), (
                    f"{book.child_venue_id}: commission_bps=0 on confirmed book "
                    f"requires notes to document commercial-pending status"
                )
            else:
                assert book.commission_bps >= UNITY_MIN_CONFIRMED_COMMISSION_BPS, (
                    f"{book.child_venue_id}: commission {book.commission_bps} below "
                    f"floor {UNITY_MIN_CONFIRMED_COMMISSION_BPS}"
                )
                assert book.commission_bps <= UNITY_MAX_CONFIRMED_COMMISSION_BPS, (
                    f"{book.child_venue_id}: commission {book.commission_bps} above "
                    f"ceiling {UNITY_MAX_CONFIRMED_COMMISSION_BPS}"
                )


@pytest.mark.unit
class TestUnityChildBookSupportedSports:
    def test_all_sports_are_supported_set(self) -> None:
        for book in UNITY_CHILD_BOOKS:
            extras = set(book.supported_sports) - UNITY_SUPPORTED_SPORTS
            assert not extras, (
                f"{book.child_venue_id}: unexpected sports {sorted(extras)} (allowed: {sorted(UNITY_SUPPORTED_SPORTS)})"
            )


@pytest.mark.unit
class TestUnityChildBookRoundTrip:
    def test_model_dump_and_reconstruct(self) -> None:
        for book in UNITY_CHILD_BOOKS:
            dumped = book.model_dump()
            rebuilt = UnityChildVenue.model_validate(dumped)
            assert rebuilt == book, f"round-trip failed for {book.child_venue_id}: {book!r} != {rebuilt!r}"


@pytest.mark.unit
class TestValidateUnityChildBookHelper:
    def test_confirmed_books_are_all_valid(self) -> None:
        for book in UNITY_CHILD_BOOKS:
            errors = validate_unity_child_book(book)
            assert errors == [], f"{book.child_venue_id}: {errors}"

    def test_unknown_sport_flagged(self) -> None:
        bad = UnityChildVenue(
            child_venue_id="FAKE",
            display_name="Fake",
            commission_bps=Decimal("50"),
            commission_type=CommissionStructureType.FLAT,
            supported_sports=["CRICKET"],
            notes="",
            confirmed=True,
        )
        errors = validate_unity_child_book(bad)
        assert any("CRICKET" in e for e in errors)

    def test_below_floor_flagged(self) -> None:
        bad = UnityChildVenue(
            child_venue_id="CHEAP",
            display_name="Too cheap",
            commission_bps=Decimal("5"),
            commission_type=CommissionStructureType.FLAT,
            supported_sports=["SOCCER"],
            notes="",
            confirmed=True,
        )
        errors = validate_unity_child_book(bad)
        assert any("below floor" in e for e in errors)

    def test_above_ceiling_flagged(self) -> None:
        bad = UnityChildVenue(
            child_venue_id="EXPENSIVE",
            display_name="Too expensive",
            commission_bps=Decimal("500"),
            commission_type=CommissionStructureType.FLAT,
            supported_sports=["SOCCER"],
            notes="",
            confirmed=True,
        )
        errors = validate_unity_child_book(bad)
        assert any("above ceiling" in e for e in errors)

    def test_unconfirmed_without_tbd_prefix_flagged(self) -> None:
        bad = UnityChildVenue(
            child_venue_id="BOOK_9",
            display_name="TBD",
            commission_bps=Decimal("0"),
            commission_type=CommissionStructureType.FLAT,
            supported_sports=[],
            notes="pending",
            confirmed=False,
        )
        errors = validate_unity_child_book(bad)
        assert any(UNITY_TBD_PREFIX in e for e in errors)

    def test_unconfirmed_with_supported_sports_flagged(self) -> None:
        bad = UnityChildVenue(
            child_venue_id="TBD_BOOK_X",
            display_name="TBD",
            commission_bps=Decimal("0"),
            commission_type=CommissionStructureType.FLAT,
            supported_sports=["SOCCER"],
            notes="pending",
            confirmed=False,
        )
        errors = validate_unity_child_book(bad)
        assert any("empty supported_sports" in e for e in errors)
