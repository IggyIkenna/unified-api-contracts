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
        assert len(UNITY_CHILD_BOOKS) == 10, (
            "Unity has 10 child books per quant-portal: 3ET, BETFAIR, BROKER5, CROWN*, "
            "MATCHBOOK, SBO*, SHARPBET, VX, BETDEX, IBC*"
        )

    def test_all_ten_confirmed(self) -> None:
        """All 10 books are confirmed existence from quant-portal 2026-04-17.

        Note: some confirmed books have commission_bps=0 (commercial-pending) —
        that is a DIFFERENT sentinel than unconfirmed. See
        UNITY_COMMERCIAL_PENDING_COMMISSION_BPS.
        """
        confirmed = unity_child_books_confirmed()
        assert len(confirmed) == 10, "10 confirmed child books from quant-portal pull"
        for book in confirmed:
            assert book.confirmed is True

    def test_no_tbd_stub_books_present(self) -> None:
        """Data is fully pulled; no TBD stubs should remain."""
        pending = unity_child_books_pending()
        assert len(pending) == 0, (
            "Unity child-book data was pulled from quant-portal on 2026-04-17; no TBD stubs should remain"
        )

    def test_confirmed_and_pending_partition_full_registry(self) -> None:
        confirmed = {b.child_venue_id for b in unity_child_books_confirmed()}
        pending = {b.child_venue_id for b in unity_child_books_pending()}
        all_ids = {b.child_venue_id for b in UNITY_CHILD_BOOKS}
        assert confirmed.isdisjoint(pending)
        assert confirmed | pending == all_ids

    def test_pending_books_reference_quant_portal(self) -> None:
        """If any TBD book re-appears in the future, its note must point to quant-portal."""
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
        # Real 10 child books per quant-portal 2026-04-17:
        # 3ET, BETFAIR, BROKER5, CROWN, MATCHBOOK, SBO, SHARPBET, VX, BETDEX, IBC
        for expected in ("VX", "SHARPBET", "BETFAIR", "IBC"):
            book = get_unity_child_book(expected)
            assert book is not None, f"{expected} missing from registry"
            assert book.confirmed is True

    def test_get_by_id_returns_none_for_unknown(self) -> None:
        assert get_unity_child_book("DEFINITELY_NOT_A_BOOK") is None

    def test_get_by_id_returns_none_for_retired_placeholders(self) -> None:
        """Placeholder ids used during Phase 13 plumbing must NOT be retrievable
        after the 2026-04-17 data pull — they were never real Unity books."""
        for retired in ("PINNACLE_VIA_UNITY", "BROKER3", "BROKER4", "IBCBET", "TBD_BOOK_9", "TBD_BOOK_10"):
            assert get_unity_child_book(retired) is None, (
                f"{retired} was a Phase-13 placeholder, not a real Unity book; "
                "must not be retrievable after the quant-portal data pull"
            )


@pytest.mark.unit
class TestUnityChildBookCommissionSanity:
    def test_confirmed_commissions_in_range_or_free(self) -> None:
        """Confirmed books: commission_bps in [20, 300] or 0 (commission-free per portal)."""
        for book in unity_child_books_confirmed():
            if book.commission_bps == Decimal("0"):
                # CROWN / SBO are commission-free per Unity pricing 2026-04-17
                assert "commission-free" in book.notes.lower(), (
                    f"{book.child_venue_id}: commission_bps=0 on confirmed book "
                    f"requires notes to document commission-free status"
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
