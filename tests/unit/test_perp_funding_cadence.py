"""Tests for per-venue perp funding cadence + annualisation math."""

from __future__ import annotations

from decimal import Decimal

import pytest

from unified_api_contracts.registry.perp_funding_cadence import (
    FUNDING_ACCRUAL_MODEL,
    FUNDING_CADENCE_SECONDS,
    SECONDS_PER_YEAR,
    FundingAccrualModel,
    annualise_funding_rate_bps,
    cadence_seconds,
    funding_accrual_model,
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

    def test_coinbase_one_hour(self) -> None:
        # Coinbase (COINBASE-FUTURES / Coinbase International Exchange) funds every
        # 1h -- confirmed both via official docs (help.coinbase.com/en/derivatives/
        # perpetual-style-futures/funding-rate) AND empirically 2026-07-28 against
        # real captured `derivative_ticker.funding_timestamp` (24 distinct values/day,
        # spaced exactly 3600s apart across 6 spot-checked shards). 1h cadence ->
        # 24/day x 365 = 8760/year, like Hyperliquid/Lighter.
        assert FUNDING_CADENCE_SECONDS["coinbase"] == 1 * 3600
        assert fundings_per_year("coinbase") == Decimal("8760")

    def test_extended_starknet_one_hour(self) -> None:
        # EXTENDED-STARKNET (StarkNet perp DEX) funds every 1h -- confirmed both
        # via official docs (docs.extended.exchange/extended-resources/trading/
        # funding-payments: "charged every hour") AND empirically 2026-07-28
        # against real captured derivative_ticker shards (24 distinct
        # settlements/day, cross-instrument-identical timestamps, minute=0 UTC
        # anchor, <=0.95s jitter). Key form is the FULL compound venue string
        # ("extended-starknet"), not a bare "extended" -- see module docstring.
        assert FUNDING_CADENCE_SECONDS["extended-starknet"] == 1 * 3600
        assert fundings_per_year("EXTENDED-STARKNET") == Decimal("8760")
        assert is_supported_venue("EXTENDED-STARKNET")
        # Regression guard for the key-form gotcha: a bare "extended" key would
        # NOT be found by real callers, which always pass the compound venue
        # string. Confirm the SHORT form is deliberately absent (never silently
        # re-added as a second, redundant key that could drift from this one).
        assert "extended" not in FUNDING_CADENCE_SECONDS

    def test_fundings_per_day(self) -> None:
        # SSOT replacement for the deleted UTL FUNDING_PERIODS_PER_DAY dict.
        assert fundings_per_day("binance") == Decimal("3")
        assert fundings_per_day("aster") == Decimal("3")  # 8h, NOT 24
        assert fundings_per_day("deribit") == Decimal("3")  # 8h figure, NOT 24
        assert fundings_per_day("hyperliquid") == Decimal("24")
        assert fundings_per_day("coinbase") == Decimal("24")  # 1h, like Hyperliquid
        assert fundings_per_day("EXTENDED-STARKNET") == Decimal("24")  # 1h
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
        assert fundings_per_year("COINBASE-FUTURES") == fundings_per_year("coinbase")
        assert is_supported_venue("COINBASE-FUTURES")
        # EXTENDED-STARKNET is the key-form exception: its "GCS venue-dir form"
        # IS its bare canonical venue value (no instrument-type suffix to
        # strip) -- the registry key must already be the full compound string.
        assert is_supported_venue("EXTENDED-STARKNET")
        assert fundings_per_day("EXTENDED-STARKNET") == Decimal("24")

    def test_unknown_venue_raises(self) -> None:
        with pytest.raises(KeyError):
            fundings_per_year("ftx-rip")


class TestCadenceSeconds:
    def test_matches_registry_value(self) -> None:
        assert cadence_seconds("binance") == 8 * 3600
        assert cadence_seconds("hyperliquid") == 1 * 3600
        assert cadence_seconds("kraken") == 4 * 3600
        assert cadence_seconds("deribit") == 8 * 3600

    def test_extended_starknet_gcs_venue_dir_form(self) -> None:
        assert cadence_seconds("EXTENDED-STARKNET") == 1 * 3600

    def test_case_and_dir_form_insensitive(self) -> None:
        assert cadence_seconds("BINANCE-FUTURES") == cadence_seconds("binance")

    def test_unknown_venue_raises(self) -> None:
        with pytest.raises(KeyError):
            cadence_seconds("ftx-rip")


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


class TestFundingAccrualModel:
    """Per-venue funding SETTLEMENT MECHANICS classification (DISCRETE vs
    CONTINUOUS_TIME_WEIGHTED) — see
    plans/active/issues/perp_funding_data_semantics_and_cadence_2026_06_16.md
    Finding 4 (DERIBIT) + Finding 5 (EXTENDED-STARKNET) for the evidence trail.
    """

    def test_every_cadence_venue_has_a_classification(self) -> None:
        # A venue with a registered cadence but no accrual-model classification
        # would be a registry bug (the model is meaningless without a cadence,
        # and every registered cadence venue should be classified one way or
        # the other — no silent gaps).
        missing = FUNDING_CADENCE_SECONDS.keys() - FUNDING_ACCRUAL_MODEL.keys()
        assert not missing, f"Venues with a cadence but no FundingAccrualModel: {missing}"

    def test_deribit_is_the_sole_continuous_time_weighted_venue(self) -> None:
        # DERIBIT is the confirmed exception (Finding 4): no discrete
        # fundingTime/nextFundingTime charge instant exists — funding is
        # computed and transferred continuously. Every OTHER registered venue
        # is DISCRETE (a genuine charge instant, whether TWAP-then-settled at
        # 8h/4h like Binance/Bybit/OKX/Aster/Bitget/Bitfinex/Kraken, or
        # computed-then-settled hourly like Hyperliquid/Lighter/Coinbase/
        # EXTENDED-STARKNET).
        continuous = {v for v, m in FUNDING_ACCRUAL_MODEL.items() if m is FundingAccrualModel.CONTINUOUS_TIME_WEIGHTED}
        assert continuous == {"deribit"}

    def test_funding_accrual_model_deribit(self) -> None:
        assert funding_accrual_model("deribit") == FundingAccrualModel.CONTINUOUS_TIME_WEIGHTED
        assert funding_accrual_model("DERIBIT") == FundingAccrualModel.CONTINUOUS_TIME_WEIGHTED

    def test_funding_accrual_model_discrete_venues(self) -> None:
        for venue in ("binance", "bybit", "okx", "aster", "kraken", "hyperliquid", "coinbase"):
            assert funding_accrual_model(venue) == FundingAccrualModel.DISCRETE, venue

    def test_gcs_venue_dir_form_resolves(self) -> None:
        assert funding_accrual_model("BINANCE-FUTURES") == FundingAccrualModel.DISCRETE
        assert funding_accrual_model("EXTENDED-STARKNET") == FundingAccrualModel.DISCRETE

    def test_unknown_venue_raises(self) -> None:
        with pytest.raises(KeyError):
            funding_accrual_model("ftx-rip")


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
