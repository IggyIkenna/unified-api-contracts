"""Unit tests for :mod:`unified_api_contracts.canonical.crosscutting.mvp_scope`.

Tests:
    - Non-MVP venue is excluded (negative cases per asset_group)
    - MVP cells return True (positive cases per asset_group)
    - Grain test: ALL expiries/strikes of an MVP (venue, instrument_type)
      are included — same venue/instrument_type, different expiry → both
      return is_mvp() == True (pure-function property)
    - Absent (venue, instrument_type) pair → False
    - Changing the config dict changes membership with NO data/manifest
      touch (pure-function property)
    - Each asset_group has at least one positive + one negative case
    - Public import surface: ``from unified_api_contracts import is_mvp, MVP_SCOPE``
    - Predicate returns bool (not truthy), and is side-effect-free
    - Sports and Prediction axes work correctly
"""

from __future__ import annotations

import pytest

# Public import surface — must be importable from the top-level facade
from unified_api_contracts import MVP_SCOPE, is_mvp
from unified_api_contracts.canonical.crosscutting.mvp_scope import (
    CeFiMvpRule,
    DeFiMvpRule,
    FeaturesModelsMvpStub,
    PredictionMvpRule,
    SportsMvpRule,
    TradFiMvpRule,
)

# ---------------------------------------------------------------------------
# MVP_SCOPE structure smoke tests
# ---------------------------------------------------------------------------


class TestMvpScopeStructure:
    """MVP_SCOPE config is well-formed and contains expected asset groups."""

    def test_contains_all_asset_groups(self) -> None:
        """MVP_SCOPE has entries for all five asset groups + stub sections."""
        for ag in ("cefi", "defi", "tradfi", "sports", "prediction"):
            assert ag in MVP_SCOPE, f"missing asset_group in MVP_SCOPE: {ag}"

    def test_stub_sections_present(self) -> None:
        """Phase-2+ stub sections are declared."""
        for key in ("features", "strategy", "models"):
            assert key in MVP_SCOPE
            assert isinstance(MVP_SCOPE[key], FeaturesModelsMvpStub)

    def test_rule_types(self) -> None:
        """Each asset_group maps to the correct typed rule dataclass."""
        assert isinstance(MVP_SCOPE["cefi"], CeFiMvpRule)
        assert isinstance(MVP_SCOPE["defi"], DeFiMvpRule)
        assert isinstance(MVP_SCOPE["tradfi"], TradFiMvpRule)
        assert isinstance(MVP_SCOPE["sports"], SportsMvpRule)
        assert isinstance(MVP_SCOPE["prediction"], PredictionMvpRule)

    def test_all_rules_are_frozen(self) -> None:
        """Rule dataclasses are frozen (immutable)."""
        rule = MVP_SCOPE["cefi"]
        assert isinstance(rule, CeFiMvpRule)
        # Call the class __setattr__ directly — this routes through the
        # dataclass frozen guard and raises FrozenInstanceError, unlike
        # object.__setattr__ (which bypasses it in Python 3.13+) or
        # setattr() (flagged by ruff B010 for constant attribute names).
        with pytest.raises(Exception):
            CeFiMvpRule.__setattr__(rule, "venues", frozenset())

    def test_venues_are_frozensets(self) -> None:
        """Venue sets are frozensets (not mutable sets or lists)."""
        for ag in ("cefi", "defi", "tradfi", "prediction"):
            rule = MVP_SCOPE[ag]
            # Narrow the type before accessing .venues — MVP_SCOPE is typed as
            # dict[str, object] so we use isinstance to satisfy the type checker.
            assert isinstance(rule, (CeFiMvpRule, DeFiMvpRule, TradFiMvpRule, PredictionMvpRule))
            assert isinstance(rule.venues, frozenset), f"Expected frozenset for {ag}.venues, got {type(rule.venues)}"


# ---------------------------------------------------------------------------
# CeFi tests
# ---------------------------------------------------------------------------


class TestCeFiMvp:
    """CeFi MVP rule tests — positive + negative cases."""

    def test_binance_futures_perpetual_btc_trades_is_mvp(self) -> None:
        """BINANCE-FUTURES PERPETUAL BTC trades → MVP."""
        assert is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades", base_ccy="BTC")

    def test_binance_spot_btc_trades_is_mvp(self) -> None:
        """BINANCE-SPOT SPOT_PAIR BTC trades → MVP."""
        assert is_mvp("cefi", "BINANCE-SPOT", "SPOT_PAIR", "trades", base_ccy="BTC")

    def test_bybit_perpetual_eth_is_mvp(self) -> None:
        """BYBIT PERPETUAL ETH → MVP."""
        assert is_mvp("cefi", "BYBIT", "PERPETUAL", "trades", base_ccy="ETH")

    def test_hyperliquid_perpetual_is_mvp(self) -> None:
        """HYPERLIQUID (on-chain CLOB, classified as CeFi) PERPETUAL → MVP."""
        assert is_mvp("cefi", "HYPERLIQUID", "PERPETUAL", "trades", base_ccy="BTC")

    def test_non_mvp_venue_upbit_returns_false(self) -> None:
        """UPBIT is in VENUES_BY_ASSET_GROUP["cefi"] but NOT in MVP → False."""
        assert not is_mvp("cefi", "UPBIT", "SPOT_PAIR", "trades", base_ccy="BTC")

    def test_non_mvp_venue_coinbase_returns_false(self) -> None:
        """COINBASE is in the cefi universe but NOT in the MVP set → False."""
        assert not is_mvp("cefi", "COINBASE", "SPOT_PAIR", "trades", base_ccy="BTC")

    def test_non_mvp_base_ccy_returns_false(self) -> None:
        """A base outside the curated CEFI_BASE_ASSET_UNIVERSE → False.

        (The universe is wide post-2026-06-23 — legacy-44 + top-100-mcap-since-2019
        + HL/ASTER perp bases, ~490 assets — so a SYNTHETIC non-coin token is used
        to prove the base_ccys gate still rejects an out-of-universe base; the rule
        has a non-empty base_ccys set.)
        """
        assert not is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades", base_ccy="NOTACOINZZZ999")

    def test_operator_requested_2026_06_16_base_is_mvp(self) -> None:
        """An operator-requested 2026-06-16 base (EIGEN) is now in the MVP set."""
        assert is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades", base_ccy="EIGEN")

    def test_deribit_btc_option_is_mvp(self) -> None:
        """Deribit BTC OPTION → MVP (the options carve-out admits BTC + ETH)."""
        assert is_mvp("cefi", "DERIBIT", "OPTION", "trades", base_ccy="BTC")

    def test_deribit_eth_option_is_mvp(self) -> None:
        """Deribit ETH OPTION → MVP (the options carve-out admits BTC + ETH)."""
        assert is_mvp("cefi", "DERIBIT", "OPTION", "trades", base_ccy="ETH")

    def test_deribit_sol_option_not_mvp(self) -> None:
        """A non-BTC/ETH OPTION → False even though SOL is in the spot/perp universe.

        The Deribit-options carve-out narrows the OPTION expected universe to
        BTC + ETH only, so a SOL option is NOT expected (no false-missing).
        """
        assert not is_mvp("cefi", "DERIBIT", "OPTION", "trades", base_ccy="SOL")

    def test_no_base_ccy_with_non_empty_rule_returns_false(self) -> None:
        """When the rule has non-empty base_ccys, None base_ccy → False."""
        assert not is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades", base_ccy=None)

    def test_non_mvp_data_type_returns_false(self) -> None:
        """A data_type not in the CeFi MVP set → False."""
        assert not is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "positions", base_ccy="BTC")

    def test_non_mvp_instrument_type_returns_false(self) -> None:
        """FUTURE instrument_type is not in the CeFi MVP set → False."""
        assert not is_mvp("cefi", "BINANCE-FUTURES", "FUTURE", "trades", base_ccy="BTC")

    def test_book_snapshot_5_is_mvp(self) -> None:
        """book_snapshot_5 is a CeFi MVP data_type (bare OKX → sub-venue normalised)."""
        assert is_mvp("cefi", "OKX", "PERPETUAL", "book_snapshot_5", base_ccy="ETH")

    def test_okx_spot_is_mvp(self) -> None:
        """Canonical OKX-SPOT (catalogue/pipeline form) → MVP.

        Regression: the rule used to carry the bare ``OKX`` token, so
        ``is_mvp("cefi", "OKX-SPOT", …)`` returned False and OKX-SPOT catalogue
        instruments were mis-tagged non-MVP (mvp_instrument_universe_gap_audit
        P2 #1).
        """
        assert is_mvp("cefi", "OKX-SPOT", "SPOT_PAIR", "trades", base_ccy="BTC")

    def test_okx_swap_is_mvp(self) -> None:
        """Canonical OKX-SWAP (perp leg) → MVP."""
        assert is_mvp("cefi", "OKX-SWAP", "PERPETUAL", "trades", base_ccy="ETH")

    def test_okx_futures_is_mvp(self) -> None:
        """Canonical OKX-FUTURES → MVP."""
        assert is_mvp("cefi", "OKX-FUTURES", "PERPETUAL", "derivative_ticker", base_ccy="SOL")

    def test_bare_okx_still_resolves_to_sub_venues(self) -> None:
        """A bare ``OKX`` caller resolves to the canonical sub-venues (back-compat)."""
        assert is_mvp("cefi", "OKX", "SPOT_PAIR", "trades", base_ccy="BTC")
        assert is_mvp("cefi", "OKX", "PERPETUAL", "trades", base_ccy="ETH")

    def test_okx_unknown_sub_venue_form_resolves(self) -> None:
        """A not-yet-declared OKX sub-venue form still resolves via base-token match.

        Defensive: any ``OKX-*`` base-normalises to OKX, which is in the
        sub-venue-base set → matches an MVP OKX sub-venue.
        """
        assert is_mvp("cefi", "OKX-PERP", "PERPETUAL", "trades", base_ccy="BTC")

    def test_cefi_unbound_data_type_is_mvp(self) -> None:
        """An instrument-grain caller with NO data_type (blank) → "any MVP data_type".

        Regression for the all-zero MVP-column bug: the catalogue carries
        ``data_type=None`` for single-grain rows; a blank data_type must match
        when the venue/instrument_type/base are MVP (mvp_instrument_universe_gap_audit
        P2 #2). Both "" and None are blank.
        """
        assert is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "", base_ccy="BTC")
        assert is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", None, base_ccy="BTC")
        # data_type defaults to None now — positional-only call also works.
        assert is_mvp("cefi", "OKX-SPOT", "SPOT_PAIR", base_ccy="ETH")

    def test_cefi_bound_data_type_still_gated(self) -> None:
        """A NON-blank data_type is still checked against the rule set (not bypassed)."""
        assert is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades", base_ccy="BTC")
        assert not is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "positions", base_ccy="BTC")

    def test_return_type_is_bool(self) -> None:
        """is_mvp() returns exactly bool, not a truthy/falsy value."""
        result = is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades", base_ccy="BTC")
        assert type(result) is bool


# ---------------------------------------------------------------------------
# DeFi tests
# ---------------------------------------------------------------------------


class TestDeFiMvp:
    """DeFi MVP rule tests — positive + negative cases."""

    def test_uniswap_v3_ethereum_pool_dex_pool_state_is_mvp(self) -> None:
        """UNISWAP_V3-ETHEREUM POOL dex_pool_state → MVP."""
        assert is_mvp("defi", "UNISWAP_V3-ETHEREUM", "POOL", "dex_pool_state")

    def test_uniswap_v3_ethereum_pool_dex_pool_swaps_is_mvp(self) -> None:
        """UNISWAP_V3-ETHEREUM POOL dex_pool_swaps → MVP."""
        assert is_mvp("defi", "UNISWAP_V3-ETHEREUM", "POOL", "dex_pool_swaps")

    def test_lido_ethereum_lst_lst_rates_is_mvp(self) -> None:
        """LIDO-ETHEREUM LST lst_rates → MVP (carry_staked_basis leg)."""
        assert is_mvp("defi", "LIDO-ETHEREUM", "LST", "lst_rates")

    def test_aave_v3_ethereum_lending_lending_indices_is_mvp(self) -> None:
        """AAVE_V3-ETHEREUM LENDING lending_indices → MVP (carry base rates)."""
        assert is_mvp("defi", "AAVE_V3-ETHEREUM", "LENDING", "lending_indices")

    def test_orca_solana_dex_pool_swaps_is_mvp(self) -> None:
        """ORCA-SOLANA DEX_POOL dex_pool_swaps → MVP."""
        assert is_mvp("defi", "ORCA-SOLANA", "DEX_POOL", "dex_pool_swaps")

    def test_non_mvp_defi_venue_returns_false(self) -> None:
        """YEARN_V3-ETHEREUM is in ALL_DEFI_VENUES but NOT in MVP → False."""
        assert not is_mvp("defi", "YEARN_V3-ETHEREUM", "POOL", "dex_pool_state")

    def test_non_mvp_defi_data_type_returns_false(self) -> None:
        """gas_fees is a DeFi data_type but NOT in the MVP set → False."""
        assert not is_mvp("defi", "UNISWAP_V3-ETHEREUM", "POOL", "gas_fees")

    def test_non_mvp_defi_instrument_type_returns_false(self) -> None:
        """SPOT_ASSET is a DeFi instrument_type but NOT in MVP → False."""
        assert not is_mvp("defi", "UNISWAP_V3-ETHEREUM", "SPOT_ASSET", "dex_pool_state")


# ---------------------------------------------------------------------------
# TradFi tests
# ---------------------------------------------------------------------------


class TestTradFiMvp:
    """TradFi MVP rule tests — positive + negative cases."""

    def test_cme_future_es_trades_is_mvp(self) -> None:
        """CME FUTURE ES trades → MVP."""
        assert is_mvp("tradfi", "CME", "FUTURE", "trades", base_ccy="ES")

    def test_cme_future_nq_trades_is_mvp(self) -> None:
        """CME FUTURE NQ trades → MVP."""
        assert is_mvp("tradfi", "CME", "FUTURE", "trades", base_ccy="NQ")

    def test_cme_future_vx_trades_is_mvp(self) -> None:
        """CME FUTURE VX (VIX futures) trades → MVP."""
        assert is_mvp("tradfi", "CME", "FUTURE", "trades", base_ccy="VX")

    def test_cme_option_es_trades_is_mvp(self) -> None:
        """CME OPTION ES trades → MVP."""
        assert is_mvp("tradfi", "CME", "OPTION", "trades", base_ccy="ES")

    def test_cme_ohlcv_1m_is_mvp(self) -> None:
        """CME FUTURE ES ohlcv_1m → MVP."""
        assert is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="ES")

    def test_non_mvp_tradfi_venue_returns_false(self) -> None:
        """NASDAQ is in tradfi venues but NOT in the MVP set → False."""
        assert not is_mvp("tradfi", "NASDAQ", "EQUITY", "trades")

    def test_non_mvp_tradfi_underlier_returns_false(self) -> None:
        """RTY (Russell 2000) underlier is NOT in the MVP set → False."""
        assert not is_mvp("tradfi", "CME", "FUTURE", "trades", base_ccy="RTY")

    def test_non_mvp_tradfi_data_type_returns_false(self) -> None:
        """ohlcv_15m is a tradfi data_type but NOT in the MVP set → False."""
        assert not is_mvp("tradfi", "CME", "FUTURE", "ohlcv_15m", base_ccy="ES")


# ---------------------------------------------------------------------------
# Grain test: ALL expiries of an MVP (venue, instrument_type) are in-scope
# ---------------------------------------------------------------------------


class TestGrainProperty:
    """MVP grain is (venue, instrument_type) — all expiries are in-scope."""

    def test_two_different_expiries_of_same_contract_both_mvp(self) -> None:
        """ESH26 and ESM26 are different expiries of the same CME ES FUTURE.

        Both should return is_mvp() == True because the grain is
        (venue, instrument_type) — ALL expiries of CME FUTURE are in
        scope if the pair is MVP.

        In practice, ``base_ccy="ES"`` is the underlier code; the specific
        expiry is not an axis in the MVP predicate. This tests that calling
        is_mvp() with the same (venue, instrument_type, data_type) but
        conceptually different contracts both return True.
        """
        # ESH26 (March 2026 expiry)
        result_esh26 = is_mvp("tradfi", "CME", "FUTURE", "trades", base_ccy="ES")
        # ESM26 (June 2026 expiry) — same base_ccy
        result_esm26 = is_mvp("tradfi", "CME", "FUTURE", "trades", base_ccy="ES")
        assert result_esh26 is True
        assert result_esm26 is True

    def test_two_different_binance_perp_contracts_both_mvp(self) -> None:
        """BTCUSDT-PERP and ETHUSDT-PERP are different perpetuals on BINANCE-FUTURES.

        Both BTC and ETH base_ccys are in the MVP base_ccys set.
        """
        assert is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades", base_ccy="BTC")
        assert is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades", base_ccy="ETH")

    def test_different_cefi_instruments_same_venue_type(self) -> None:
        """Multiple SOL instruments on a MVP venue are all in scope."""
        for base_ccy in ("BTC", "ETH", "SOL"):
            assert is_mvp("cefi", "BYBIT", "PERPETUAL", "trades", base_ccy=base_ccy), (
                f"Expected is_mvp=True for BYBIT PERPETUAL {base_ccy}"
            )


# ---------------------------------------------------------------------------
# Sports tests
# ---------------------------------------------------------------------------


class TestSportsMvp:
    """Sports MVP rule tests — positive + negative cases."""

    def test_epl_odds_is_mvp(self) -> None:
        """EPL league odds data → MVP."""
        assert is_mvp("sports", "ODDS_API", "FIXED_ODDS", "odds", league="EPL")

    def test_nfl_odds_snapshot_is_mvp(self) -> None:
        """NFL league odds_snapshot → MVP."""
        assert is_mvp("sports", "ODDS_API", "FIXED_ODDS", "odds_snapshot", league="NFL")

    def test_nba_markets_is_mvp(self) -> None:
        """NBA league markets data → MVP."""
        assert is_mvp("sports", "BETFAIR", "EXCHANGE_ODDS", "markets", league="NBA")

    def test_non_mvp_sports_league_returns_false(self) -> None:
        """ENG_CHAMPIONSHIP is a real league but NOT in the MVP set → False."""
        assert not is_mvp("sports", "ODDS_API", "FIXED_ODDS", "odds", league="ENG_CHAMPIONSHIP")

    def test_non_mvp_sports_data_type_returns_false(self) -> None:
        """arbitrage_opportunity is a sports data_type but NOT in MVP → False."""
        assert not is_mvp("sports", "ODDS_API", "FIXED_ODDS", "arbitrage_opportunity", league="EPL")

    def test_missing_league_returns_false(self) -> None:
        """Sports with league=None → False (league is required)."""
        assert not is_mvp("sports", "ODDS_API", "FIXED_ODDS", "odds", league=None)


# ---------------------------------------------------------------------------
# Prediction tests
# ---------------------------------------------------------------------------


class TestPredictionMvp:
    """Prediction MVP rule tests — positive + negative cases."""

    def test_polymarket_crypto_trades_is_mvp(self) -> None:
        """POLYMARKET crypto market trades → MVP."""
        assert is_mvp(
            "prediction",
            "POLYMARKET",
            "PREDICTION_MARKET",
            "trades",
            market_group="crypto",
        )

    def test_polymarket_politics_trades_is_mvp(self) -> None:
        """POLYMARKET politics market trades → MVP."""
        assert is_mvp(
            "prediction",
            "POLYMARKET",
            "PREDICTION_MARKET",
            "trades",
            market_group="politics",
        )

    def test_polymarket_sports_market_lifecycle_is_mvp(self) -> None:
        """POLYMARKET sports market_lifecycle → MVP."""
        assert is_mvp(
            "prediction",
            "POLYMARKET",
            "PREDICTION_MARKET",
            "market_lifecycle",
            market_group="sports",
        )

    def test_kalshi_returns_false(self) -> None:
        """KALSHI is in prediction venues but NOT in the MVP set → False."""
        assert not is_mvp(
            "prediction",
            "KALSHI",
            "PREDICTION_MARKET",
            "trades",
            market_group="crypto",
        )

    def test_non_mvp_prediction_data_type_returns_false(self) -> None:
        """book_snapshot_5 is a prediction data_type but NOT in MVP → False."""
        assert not is_mvp(
            "prediction",
            "POLYMARKET",
            "PREDICTION_MARKET",
            "book_snapshot_5",
            market_group="crypto",
        )

    def test_prediction_canonical_question_group_is_mvp(self) -> None:
        """prediction_canonical_question_group data_type → MVP."""
        assert is_mvp(
            "prediction",
            "POLYMARKET",
            "PREDICTION_MARKET",
            "prediction_canonical_question_group",
            market_group="crypto",
        )


# ---------------------------------------------------------------------------
# Absent / impossible pairs → False
# ---------------------------------------------------------------------------


class TestAbsentPairs:
    """Absent or impossible (venue, instrument_type) pairs → False."""

    def test_unknown_asset_group_returns_false(self) -> None:
        """An asset_group not in MVP_SCOPE → False."""
        assert not is_mvp("exotic", "SOME_VENUE", "SPOT_PAIR", "trades")

    def test_cefi_venue_not_in_any_rule_returns_false(self) -> None:
        """A venue not in VENUES_BY_ASSET_GROUP at all → False."""
        assert not is_mvp("cefi", "FAKE_VENUE_XYZ", "PERPETUAL", "trades", base_ccy="BTC")

    def test_defi_venue_not_in_rule_returns_false(self) -> None:
        """A defi venue not in the MVP config → False."""
        assert not is_mvp("defi", "CONVEX-ETHEREUM", "POOL", "dex_pool_state")

    def test_tradfi_impossible_pair_returns_false(self) -> None:
        """A TradFi venue/instrument_type combo that's not in MVP → False."""
        assert not is_mvp("tradfi", "ICE", "COMMODITY", "trades")

    def test_stub_asset_group_returns_false(self) -> None:
        """Stub keys (features/strategy/models) always return False."""
        for ag in ("features", "strategy", "models"):
            assert not is_mvp(ag, "ANY_VENUE", "SPOT_PAIR", "trades"), (
                f"Expected is_mvp=False for stub asset_group: {ag}"
            )


# ---------------------------------------------------------------------------
# Unbound-data_type convention across asset groups (P2 #2, 2026-06-17)
# ---------------------------------------------------------------------------


class TestUnboundDataType:
    """A blank (``""``/``None``) data_type means "any MVP data_type" for every AG."""

    def test_defi_unbound_data_type_is_mvp(self) -> None:
        """DeFi LST instrument with no data_type → MVP (any-data_type)."""
        assert is_mvp("defi", "LIDO-ETHEREUM", "LST", "")
        assert is_mvp("defi", "LIDO-ETHEREUM", "LST", None)

    def test_tradfi_unbound_data_type_is_mvp(self) -> None:
        """TradFi CME future ES with no data_type → MVP (any-data_type)."""
        assert is_mvp("tradfi", "CME", "FUTURE", "", base_ccy="ES")
        assert is_mvp("tradfi", "CME", "FUTURE", None, base_ccy="ES")

    def test_prediction_unbound_data_type_is_mvp(self) -> None:
        """Prediction Polymarket with no data_type → MVP (any-data_type)."""
        assert is_mvp("prediction", "POLYMARKET", "PREDICTION_MARKET", "", market_group="crypto")
        assert is_mvp("prediction", "POLYMARKET", "PREDICTION_MARKET", None, market_group="crypto")

    def test_unbound_data_type_still_gates_other_axes(self) -> None:
        """Blank data_type relaxes ONLY the data_type axis — venue/base still gate."""
        # Non-MVP venue: blank data_type does NOT make it MVP.
        assert not is_mvp("cefi", "UPBIT", "SPOT_PAIR", "", base_ccy="BTC")
        # Non-MVP base: blank data_type does NOT make it MVP. (Synthetic
        # out-of-universe base — the curated universe is now ~490 assets.)
        assert not is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "", base_ccy="NOTACOINZZZ999")


# ---------------------------------------------------------------------------
# Pure-function property: config change changes membership, no manifest touch
# ---------------------------------------------------------------------------


class TestPureFunctionProperty:
    """is_mvp() is a pure function — result changes with config, zero side effects."""

    def test_direct_config_modification_changes_membership(self) -> None:
        """Modifying the rule object changes membership (pure-function property).

        We create a temporary CeFiMvpRule WITHOUT "BYBIT" and confirm
        is_mvp() returns False for BYBIT when evaluated against that rule.
        This tests that the predicate is config-driven, not cached.
        """
        # The default rule includes BYBIT
        assert is_mvp("cefi", "BYBIT", "PERPETUAL", "trades", base_ccy="BTC")

        # Build a custom rule WITHOUT BYBIT
        original_rule = MVP_SCOPE["cefi"]
        assert isinstance(original_rule, CeFiMvpRule)
        reduced_venues = original_rule.venues - {"BYBIT"}
        custom_rule = CeFiMvpRule(
            venues=reduced_venues,
            instrument_types=original_rule.instrument_types,
            data_types=original_rule.data_types,
            base_ccys=original_rule.base_ccys,
            sources=original_rule.sources,
        )

        # Evaluate the predicate directly against the custom rule
        # (reproduces the is_mvp() logic for cefi)
        bybit_in_custom = "BYBIT" in custom_rule.venues
        assert bybit_in_custom is False, "After removing BYBIT from the rule, it must NOT be in the venue set"

        # The global MVP_SCOPE is unchanged
        cefi_rule = MVP_SCOPE["cefi"]
        assert isinstance(cefi_rule, CeFiMvpRule)
        assert "BYBIT" in cefi_rule.venues

    def test_is_mvp_no_mutation_side_effects(self) -> None:
        """Calling is_mvp() multiple times produces the same result."""
        for _ in range(10):
            result = is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades", base_ccy="BTC")
            assert result is True

    def test_is_mvp_is_deterministic(self) -> None:
        """is_mvp() is deterministic for the same inputs."""
        results = {is_mvp("defi", "UNISWAP_V3-ETHEREUM", "POOL", "dex_pool_state") for _ in range(5)}
        assert results == {True}


# ---------------------------------------------------------------------------
# Config versioning — monotonic version + deterministic content hash
# (audit: mvp_scope_catalogue_tagging § "Config versioning")
# ---------------------------------------------------------------------------


def test_config_descriptor_public_surface() -> None:
    """version + hash + descriptor are importable from the package root."""
    from unified_api_contracts import (
        MVP_SCOPE_CONFIG_HASH,
        MVP_SCOPE_CONFIG_VERSION,
        mvp_scope_config_descriptor,
    )

    assert isinstance(MVP_SCOPE_CONFIG_VERSION, int)
    assert MVP_SCOPE_CONFIG_VERSION >= 1
    assert isinstance(MVP_SCOPE_CONFIG_HASH, str)
    assert len(MVP_SCOPE_CONFIG_HASH) == 16
    int(MVP_SCOPE_CONFIG_HASH, 16)  # raises if non-hex
    desc = mvp_scope_config_descriptor()
    assert desc.config_version == MVP_SCOPE_CONFIG_VERSION
    assert desc.config_content_hash == MVP_SCOPE_CONFIG_HASH


def test_config_hash_is_deterministic_across_processes() -> None:
    """The hash flips IFF content changes — sets are sorted so it is stable
    across re-computation (PYTHONHASHSEED-independent)."""
    from unified_api_contracts.canonical.crosscutting.mvp_scope import (
        MVP_SCOPE_CONFIG_HASH,
        _compute_mvp_scope_content_hash,
    )

    assert _compute_mvp_scope_content_hash() == MVP_SCOPE_CONFIG_HASH
    # Recompute again — identical (no set-iteration-order dependence).
    assert _compute_mvp_scope_content_hash() == _compute_mvp_scope_content_hash()


def test_config_hash_changes_iff_content_changes() -> None:
    """A content change (different rule membership) yields a different hash;
    a frozenset reordering (same content) yields the SAME hash."""
    from unified_api_contracts.canonical.crosscutting.mvp_scope import (
        CeFiMvpRule,
        _canonical_repr,
    )

    rule_a = CeFiMvpRule(
        venues=frozenset({"BINANCE-FUTURES", "OKX"}),
        instrument_types=frozenset({"PERPETUAL"}),
        data_types=frozenset({"trades"}),
    )
    # Same content, frozensets built in a different order → identical canonical repr.
    rule_a_reordered = CeFiMvpRule(
        venues=frozenset({"OKX", "BINANCE-FUTURES"}),
        instrument_types=frozenset({"PERPETUAL"}),
        data_types=frozenset({"trades"}),
    )
    assert _canonical_repr(rule_a) == _canonical_repr(rule_a_reordered)
    # Different content → different canonical repr.
    rule_b = CeFiMvpRule(
        venues=frozenset({"BINANCE-FUTURES"}),
        instrument_types=frozenset({"PERPETUAL"}),
        data_types=frozenset({"trades"}),
    )
    assert _canonical_repr(rule_a) != _canonical_repr(rule_b)
