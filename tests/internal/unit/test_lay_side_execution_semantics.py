"""Tests for G2.9 gap #9 — LaySideExecutionSemantics."""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.architecture_v2.lay_side_execution_semantics import (
    CONSUMER_CALL_SITES,
    LAY_SIDE_EXECUTION_SEMANTICS,
    LayBookType,
    LaySideExecutionSemantics,
    LayVenueNotRegisteredError,
    LiabilityFormula,
    _validate_registry_invariants,
    lay_semantics_for,
    mm_quoting_venues,
    venues_by_book_type,
)


class TestRegistryShape:
    def test_registry_not_empty(self) -> None:
        assert len(LAY_SIDE_EXECUTION_SEMANTICS) >= 4

    def test_venue_ids_unique(self) -> None:
        ids = [e.venue_id for e in LAY_SIDE_EXECUTION_SEMANTICS]
        assert len(ids) == len(set(ids))


class TestContent:
    def test_betfair_full_lay(self) -> None:
        entry = lay_semantics_for("betfair")
        assert entry.lay_book_type is LayBookType.FULL_LAY
        assert entry.liability_formula_ref is LiabilityFormula.BETFAIR_STANDARD
        assert entry.commission_basis == "winnings"
        assert entry.supports_mm_quoting is True

    def test_polymarket_binary_clob(self) -> None:
        entry = lay_semantics_for("polymarket")
        assert entry.lay_book_type is LayBookType.BINARY_CLOB
        assert entry.liability_formula_ref is LiabilityFormula.BINARY_FIXED_NOTIONAL
        assert entry.commission_basis == "none"

    def test_unity_back_only_no_mm(self) -> None:
        entry = lay_semantics_for("unity")
        assert entry.lay_book_type is LayBookType.BACK_ONLY
        assert entry.supports_mm_quoting is False
        assert entry.liability_formula_ref is LiabilityFormula.NO_LAY


class TestHelpers:
    def test_unknown_venue_raises(self) -> None:
        with pytest.raises(LayVenueNotRegisteredError):
            lay_semantics_for("nonexistent")

    def test_mm_quoting_venues_excludes_unity(self) -> None:
        results = mm_quoting_venues()
        ids = {e.venue_id for e in results}
        assert "betfair" in ids
        assert "unity" not in ids

    def test_venues_by_full_lay(self) -> None:
        results = venues_by_book_type(LayBookType.FULL_LAY)
        ids = {e.venue_id for e in results}
        assert "betfair" in ids
        assert "matchbook" in ids

    def test_venues_by_back_only(self) -> None:
        results = venues_by_book_type(LayBookType.BACK_ONLY)
        assert {e.venue_id for e in results} == {"unity"}


class TestInvariants:
    def test_duplicate_venue_rejected(self) -> None:
        bad = (
            LaySideExecutionSemantics(
                venue_id="dup",
                lay_book_type=LayBookType.FULL_LAY,
                supports_mm_quoting=True,
                liability_formula_ref=LiabilityFormula.BETFAIR_STANDARD,
                commission_basis="winnings",
                min_quote_refresh_ms=100,
                in_play_policy="unrestricted",
            ),
            LaySideExecutionSemantics(
                venue_id="dup",
                lay_book_type=LayBookType.BINARY_CLOB,
                supports_mm_quoting=True,
                liability_formula_ref=LiabilityFormula.BINARY_FIXED_NOTIONAL,
                commission_basis="none",
                min_quote_refresh_ms=100,
                in_play_policy="unrestricted",
            ),
        )
        with pytest.raises(ValueError, match="duplicate"):
            _validate_registry_invariants(bad)

    def test_back_only_with_mm_rejected(self) -> None:
        bad = (
            LaySideExecutionSemantics(
                venue_id="x",
                lay_book_type=LayBookType.BACK_ONLY,
                supports_mm_quoting=True,
                liability_formula_ref=LiabilityFormula.NO_LAY,
                commission_basis="none",
                min_quote_refresh_ms=0,
                in_play_policy="lock_new_quotes",
            ),
        )
        with pytest.raises(ValueError, match="supports_mm_quoting=True"):
            _validate_registry_invariants(bad)

    def test_back_only_with_real_formula_rejected(self) -> None:
        bad = (
            LaySideExecutionSemantics(
                venue_id="x",
                lay_book_type=LayBookType.BACK_ONLY,
                supports_mm_quoting=False,
                liability_formula_ref=LiabilityFormula.BETFAIR_STANDARD,
                commission_basis="winnings",
                min_quote_refresh_ms=100,
                in_play_policy="unrestricted",
            ),
        )
        with pytest.raises(ValueError, match="NO_LAY"):
            _validate_registry_invariants(bad)

    def test_lay_capable_with_no_lay_formula_rejected(self) -> None:
        bad = (
            LaySideExecutionSemantics(
                venue_id="x",
                lay_book_type=LayBookType.FULL_LAY,
                supports_mm_quoting=True,
                liability_formula_ref=LiabilityFormula.NO_LAY,
                commission_basis="winnings",
                min_quote_refresh_ms=100,
                in_play_policy="unrestricted",
            ),
        )
        with pytest.raises(ValueError, match="real liability formula"):
            _validate_registry_invariants(bad)


class TestConsumerReferences:
    def test_consumer_call_sites_non_empty(self) -> None:
        assert len(CONSUMER_CALL_SITES) >= 1

    def test_betfair_is_consumer(self) -> None:
        assert any("betfair" in site for site in CONSUMER_CALL_SITES)
