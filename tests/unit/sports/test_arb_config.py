"""Regression tests for arb_config bugs measured live 2026-08-08.

These tests specifically use CANONICAL UPPERCASE venue spellings — a test
written in lowercase would have passed against the broken code and would not
have caught the production bug.

Bugs fixed:
  - Bug 1: VENUE_OPERATOR_GROUPS keyed on lowercase vendor spellings, so
    canonical UPPERCASE venues (the form MTDS/MDPS actually emit) resolved
    to the identity fallback and arb_legs_are_independent returned True for
    same-counterparty leg pairs.
  - Bug 2: SMARKETS absent from EXCHANGE_VENUES and EXCHANGE_COMMISSION_RATES,
    so commission was modelled as 0% on every SMARKETS arb leg.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.domain.sports.arb_config import (
    EXCHANGE_COMMISSION_RATES,
    EXCHANGE_VENUES,
    arb_legs_are_independent,
    get_operator,
)
from unified_api_contracts.registry.venue_constants import (
    BETFAIR,
    BETFAIR_EX_EU,
    BETFAIR_EX_UK,
    SMARKETS,
    UNIBET,
)


@pytest.mark.unit
class TestArbLegIndependenceBug1Regression:
    """Canonical-case guard: same-operator legs must be rejected (Bug 1 regression)."""

    def test_betfair_exchange_skins_are_not_independent(self) -> None:
        # Was: True (bug) — BETFAIR_EX_UK not found in the lowercase-keyed map,
        # so both legs resolved to their own string as the operator → distinct → True.
        assert arb_legs_are_independent([BETFAIR_EX_UK, BETFAIR_EX_EU]) is False

    def test_unibet_and_unibet_uk_are_not_independent(self) -> None:
        # Was: True (bug) — same root cause: "UNIBET_UK" not in the lowercase map,
        # fell back to identity, became its own operator.
        assert arb_legs_are_independent(["UNIBET_UK", UNIBET]) is False

    def test_betfair_three_legs_same_group_rejected(self) -> None:
        assert arb_legs_are_independent([BETFAIR_EX_UK, BETFAIR_EX_EU, "BETFAIR_EX_AU"]) is False

    def test_lowercase_input_also_resolves_correctly(self) -> None:
        # Belt-and-suspenders: lowercase was already working pre-fix; confirm no regression.
        assert arb_legs_are_independent(["betfair_ex_uk", "betfair_ex_eu"]) is False

    def test_genuinely_independent_legs_pass(self) -> None:
        # Different operator groups → should still return True.
        assert arb_legs_are_independent([BETFAIR_EX_UK, UNIBET]) is True

    def test_single_leg_is_always_independent(self) -> None:
        assert arb_legs_are_independent([BETFAIR_EX_UK]) is True


@pytest.mark.unit
class TestGetOperatorBug1Regression:
    """get_operator must map canonical venue → operator group, not identity."""

    def test_betfair_ex_uk_maps_to_betfair(self) -> None:
        # Was: 'BETFAIR_EX_UK' (identity fallback — the bug).
        assert get_operator(BETFAIR_EX_UK) == BETFAIR

    def test_betfair_ex_eu_maps_to_betfair(self) -> None:
        assert get_operator(BETFAIR_EX_EU) == BETFAIR

    def test_unibet_uk_maps_to_unibet(self) -> None:
        # Was: 'UNIBET_UK' (identity fallback — the bug).
        assert get_operator("UNIBET_UK") == UNIBET

    def test_lowercase_normalization_still_works(self) -> None:
        assert get_operator("betfair_ex_uk") == BETFAIR

    def test_standalone_venue_is_its_own_operator(self) -> None:
        # A venue with no operator-group mapping should fall back to itself.
        assert get_operator("PINNACLE") == "PINNACLE"


@pytest.mark.unit
class TestSmarketsCommissionBug2Regression:
    """SMARKETS must appear in EXCHANGE_VENUES and carry a non-zero commission (Bug 2)."""

    def test_smarkets_in_exchange_venues(self) -> None:
        # Was: absent — commission was always 0.
        assert SMARKETS in EXCHANGE_VENUES

    def test_smarkets_commission_is_nonzero(self) -> None:
        # Was: missing key → commission contribution of 0.
        rate = EXCHANGE_COMMISSION_RATES.get(SMARKETS, 0.0)
        assert rate > 0, f"SMARKETS commission rate must be > 0, got {rate}"

    def test_smarkets_commission_rate_is_two_percent(self) -> None:
        # Operator pre-specified 0.02 on 2026-08-08.
        assert EXCHANGE_COMMISSION_RATES[SMARKETS] == 0.02
