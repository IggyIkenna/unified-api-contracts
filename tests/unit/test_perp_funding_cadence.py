"""Tests for per-venue perp funding cadence + annualisation math."""

from __future__ import annotations

from decimal import Decimal

import pytest

from unified_api_contracts.registry.perp_funding_cadence import (
    FUNDING_CADENCE_SECONDS,
    SECONDS_PER_YEAR,
    annualise_funding_rate_bps,
    fundings_per_day,
    fundings_per_year,
    is_supported_venue,
)


class TestCadenceRegistry:
    def test_all_major_perp_venues_present(self) -> None:
        # The MVP MUST cover at minimum the carry_staked_basis target venues
        # — adding/removing here is a deliberate scope change, not a casual
        # edit, so this test pins the contract.
        required = {
            "binance",
            "bybit",
            "okx",
            "deribit",
            "hyperliquid",
            "aster",
            "kraken",
        }
        missing = required - FUNDING_CADENCE_SECONDS.keys()
        assert not missing, f"Missing perp venues in cadence registry: {missing}"

    def test_cadences_in_seconds_not_zero(self) -> None:
        for venue, cadence in FUNDING_CADENCE_SECONDS.items():
            assert cadence > 0, f"{venue} cadence must be positive, got {cadence}"
            # Sanity: nothing slower than 24h (anything that slow isn't a perp)
            assert cadence <= 24 * 3600, f"{venue} cadence {cadence}s exceeds 24h"

    def test_seconds_per_year_constant(self) -> None:
        assert SECONDS_PER_YEAR == 365 * 24 * 3600


class TestFundingsPerYear:
    def test_binance_eight_hour(self) -> None:
        # 8h cadence -> 3 fundings/day x 365 = 1095/year
        assert fundings_per_year("binance") == Decimal("1095")

    def test_hyperliquid_one_hour(self) -> None:
        # 1h cadence -> 24/day x 365 = 8760/year
        assert fundings_per_year("hyperliquid") == Decimal("8760")

    def test_kraken_four_hour(self) -> None:
        # 4h cadence -> 6/day x 365 = 2190/year
        assert fundings_per_year("kraken") == Decimal("2190")

    def test_aster_eight_hour(self) -> None:
        # Aster funds every 8h (fundingTime spacing = 28 800 s, verified 2026-06-16),
        # like Binance — NOT 1h. Regression guard vs the deleted UTL FUNDING_PERIODS_PER_DAY
        # which had ASTER=24 (1h) and over-stated Aster funding 8x.
        assert fundings_per_year("aster") == Decimal("1095")

    def test_deribit_annualises_at_eight_hour_figure(self) -> None:
        # Deribit CHARGES hourly but the stored derivative_ticker.funding_rate is the
        # 8h FIGURE (verified 2026-06-16/17). The annualisation period must match the
        # stored figure (8h -> 1095/yr), NOT the 1h charge cadence (8760/yr). Using 1h
        # over-stated Deribit funding APY by 8x — this is the regression guard.
        assert FUNDING_CADENCE_SECONDS["deribit"] == 8 * 3600
        assert fundings_per_year("deribit") == Decimal("1095")

    def test_fundings_per_day(self) -> None:
        # SSOT replacement for the deleted UTL FUNDING_PERIODS_PER_DAY dict.
        assert fundings_per_day("binance") == Decimal("3")
        assert fundings_per_day("aster") == Decimal("3")  # 8h, NOT 24
        assert fundings_per_day("deribit") == Decimal("3")  # 8h figure, NOT 24
        assert fundings_per_day("hyperliquid") == Decimal("24")
        assert fundings_per_day("kraken") == Decimal("6")

    def test_case_insensitive_lookup(self) -> None:
        assert fundings_per_year("BINANCE") == fundings_per_year("binance")
        assert fundings_per_year("Hyperliquid") == fundings_per_year("hyperliquid")

    def test_gcs_venue_dir_form_resolves(self) -> None:
        # SSOT venue-dir normalisation: callers pass GCS dirs (BINANCE-FUTURES,
        # OKX-SWAP) directly — no per-consumer dir->key dict (the deleted UTL
        # FUNDING_PERIODS_PER_DAY anti-pattern).
        assert fundings_per_year("BINANCE-FUTURES") == fundings_per_year("binance")
        assert fundings_per_year("OKX-SWAP") == fundings_per_year("okx")
        assert fundings_per_day("BINANCE-FUTURES") == Decimal("3")
        assert is_supported_venue("OKX-SWAP")
        assert annualise_funding_rate_bps(Decimal("0.0001"), "OKX-SWAP") == Decimal("1095.0000")

    def test_unknown_venue_raises(self) -> None:
        with pytest.raises(KeyError):
            fundings_per_year("ftx-rip")


class TestAnnualisation:
    """Strategy-relevant cases. Output is APY in basis points."""

    def test_binance_one_basis_point_per_cycle(self) -> None:
        # 0.0001 raw rate (= 1bp per 8h cycle = 0.01%)
        # Annualised: 0.0001 x 1095 x 10000 = 1095 bps APY = 10.95%
        # This is a typical mid-range ETH-PERP funding.
        result = annualise_funding_rate_bps(Decimal("0.0001"), "binance")
        assert result == Decimal("1095.0000"), f"got {result}"

    def test_hyperliquid_one_basis_point_per_cycle(self) -> None:
        # Same 0.0001 raw rate on Hyperliquid (1h cadence, 8x more accruals)
        # 0.0001 x 8760 x 10000 = 8760 bps APY = 87.6%
        # Hourly cadence venues see ~8x the same raw rate's annualised APY
        # vs an 8h venue — drives the carry advantage of CeFi-vs-DeFi perps.
        result = annualise_funding_rate_bps(Decimal("0.0001"), "hyperliquid")
        assert result == Decimal("8760.0000")

    def test_negative_funding_short_side_receives(self) -> None:
        # When funding < 0, longs PAY shorts. Annualised stays negative.
        # -0.00005 x 1095 x 10000 = -547.5 bps APY = -5.475%
        result = annualise_funding_rate_bps(Decimal("-0.00005"), "binance")
        assert result == Decimal("-547.50000")
        assert result < 0

    def test_zero_funding(self) -> None:
        assert annualise_funding_rate_bps(Decimal("0"), "binance") == Decimal("0")
        assert annualise_funding_rate_bps(Decimal("0"), "hyperliquid") == Decimal("0")

    def test_carry_staked_basis_realistic_inputs(self) -> None:
        # Strategy sees something like 11% APY funding on ETH-PERP Binance.
        # Reverse derivation:
        #   11% APY = 1100 bps
        #   rate x 1095 fundings_per_year x 10000 = 1100
        #   rate = 1100 / (1095 x 10000) = 0.00010046...
        # Forward verification: 0.0001005 x 1095 x 10000 = 1100.475 bps ~= 11.00% APY
        result = annualise_funding_rate_bps(Decimal("0.0001005"), "binance")
        assert Decimal("1100") < result < Decimal("1101")


class TestIsSupportedVenue:
    @pytest.mark.parametrize(
        "venue",
        ["binance", "BYBIT", "Okx", "deribit", "hyperliquid"],
    )
    def test_known_venues(self, venue: str) -> None:
        assert is_supported_venue(venue)

    @pytest.mark.parametrize("venue", ["", "ftx", "mango-perps"])
    def test_unknown_venues(self, venue: str) -> None:
        assert not is_supported_venue(venue)
