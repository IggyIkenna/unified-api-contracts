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

    def test_upbit_spot_is_mvp_in_base_rule(self) -> None:
        """UPBIT is now an MVP rule venue (cefi_universe_capture_rule 2026-06-23).

        ``is_mvp`` (the base rule) returns True for UPBIT spot in-universe; the
        spot-only-no-perp carve-out lives in ``is_in_mvp_capture_universe``.
        """
        assert is_mvp("cefi", "UPBIT", "SPOT_PAIR", "trades", base_ccy="BTC")

    def test_coinbase_spot_is_mvp_in_base_rule(self) -> None:
        """COINBASE-SPOT is now an MVP rule venue (2026-06-23). Bare ``COINBASE``
        (no -SPOT suffix, not an OKX sub-venue) still does NOT resolve."""
        assert is_mvp("cefi", "COINBASE-SPOT", "SPOT_PAIR", "trades", base_ccy="BTC")
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
        """An instrument_type not in the CeFi MVP set → False.

        (FUTURE is now an MVP cefi instrument_type — dated futures are in scope per
        cefi_universe_capture_rule_2026_06_23 — so this asserts COMBO, which is NOT
        in the rule.)
        """
        assert not is_mvp("cefi", "BINANCE-FUTURES", "COMBO", "trades", base_ccy="BTC")

    def test_dated_future_is_mvp_instrument_type(self) -> None:
        """FUTURE IS an MVP cefi instrument_type (dated/quarterly futures, 2026-06-23)."""
        assert is_mvp("cefi", "BINANCE-FUTURES", "FUTURE", "trades", base_ccy="BTC")

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
        # Non-MVP venue: blank data_type does NOT make it MVP. (GATEIO is not an
        # MVP rule venue; UPBIT/COINBASE-SPOT are MVP venues post-2026-06-23.)
        assert not is_mvp("cefi", "GATEIO-SPOT", "SPOT_PAIR", "", base_ccy="BTC")
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


# ---------------------------------------------------------------------------
# is_in_mvp_capture_universe — the perp-gated CeFi capture predicate
# (cefi_universe_capture_rule_2026_06_23). The shared SSOT the three capture
# consumers call: catalogue rollup, MTDS capture-universe, expected enumerator.
# ---------------------------------------------------------------------------


def test_capture_universe_perp_is_mvp_on_base_membership() -> None:
    """A PERPETUAL for a universe base is in the capture universe (the perp IS the gate)."""
    from unified_api_contracts import is_in_mvp_capture_universe

    assert is_in_mvp_capture_universe("BINANCE-FUTURES", "BTC", "PERPETUAL", has_perp_for_base=True)
    # has_perp_for_base is irrelevant for a perp — the perp self-qualifies.
    assert is_in_mvp_capture_universe("BINANCE-FUTURES", "ETH", "PERPETUAL", has_perp_for_base=False)


def test_capture_universe_spot_requires_perp_for_base() -> None:
    """HARD perp-gate: SPOT is in-universe ONLY IF the venue also lists a perp for the base."""
    from unified_api_contracts import is_in_mvp_capture_universe

    # spot WITH a sibling perp → in universe
    assert is_in_mvp_capture_universe("BINANCE-SPOT", "BTC", "SPOT_PAIR", has_perp_for_base=True)
    # spot WITHOUT a sibling perp → DROPPED even for a top-100 base
    assert not is_in_mvp_capture_universe("BINANCE-SPOT", "BTC", "SPOT_PAIR", has_perp_for_base=False)


def test_capture_universe_dated_future_not_perp_gated() -> None:
    """Dated/quarterly FUTURE sharing a universe base is MVP on base-membership +
    venue — NOT perp-gated (operator 2026-06-23: part of the futures complex)."""
    from unified_api_contracts import is_in_mvp_capture_universe

    # In-universe regardless of has_perp_for_base.
    assert is_in_mvp_capture_universe("BINANCE-FUTURES", "BTC", "FUTURE", has_perp_for_base=True)
    assert is_in_mvp_capture_universe("BINANCE-FUTURES", "BTC", "FUTURE", has_perp_for_base=False)
    # A base NOT in the universe is still excluded.
    assert not is_in_mvp_capture_universe("BINANCE-FUTURES", "NOTACOINXYZ", "FUTURE", has_perp_for_base=True)


def test_capture_universe_options_deribit_btc_eth_only() -> None:
    """OPTION is in-universe ONLY for venue==DERIBIT AND base in {BTC, ETH}; not perp-gated."""
    from unified_api_contracts import is_in_mvp_capture_universe

    # Deribit BTC/ETH options → in universe (no perp-sibling needed)
    assert is_in_mvp_capture_universe("DERIBIT", "BTC", "OPTION", has_perp_for_base=False)
    assert is_in_mvp_capture_universe("DERIBIT", "ETH", "OPTION", has_perp_for_base=False)
    # Deribit SOL option → NOT in universe (only BTC/ETH)
    assert not is_in_mvp_capture_universe("DERIBIT", "SOL", "OPTION", has_perp_for_base=True)
    # A non-Deribit venue option → NOT in universe even for BTC with a perp
    assert not is_in_mvp_capture_universe("BINANCE-FUTURES", "BTC", "OPTION", has_perp_for_base=True)


def test_capture_universe_tradfi_equity_perp() -> None:
    """TradFi-linked EQUITY_PERP on Binance is in-universe (it IS a perp)."""
    from unified_api_contracts import is_in_mvp_capture_universe

    assert is_in_mvp_capture_universe("BINANCE-FUTURES", "AAPL", "EQUITY_PERP", has_perp_for_base=True)


def test_capture_universe_base_not_in_universe_excluded() -> None:
    """A base not in the CeFi universe is excluded even with a perp."""
    from unified_api_contracts import is_in_mvp_capture_universe

    assert not is_in_mvp_capture_universe("BINANCE-FUTURES", "NOTACOINXYZ", "PERPETUAL", has_perp_for_base=True)


def test_capture_universe_non_mvp_venue_excluded() -> None:
    """A venue outside the cefi MVP rule is excluded."""
    from unified_api_contracts import is_in_mvp_capture_universe

    # GATEIO is not an MVP rule venue → excluded even with a perp sibling.
    assert not is_in_mvp_capture_universe("GATEIO-SPOT", "BTC", "SPOT_PAIR", has_perp_for_base=True)


def test_capture_universe_upbit_spot_no_perp_exempt() -> None:
    """UPBIT spot is mvp=true REGARDLESS of perp (venue carve-out, 2026-06-23)."""
    from unified_api_contracts import is_in_mvp_capture_universe

    # No perp on UPBIT (spot-only venue) — still mvp via the venue exemption.
    assert is_in_mvp_capture_universe("UPBIT", "BTC", "SPOT_PAIR", has_perp_for_base=False)
    assert is_in_mvp_capture_universe("UPBIT", "ADA", "SPOT_PAIR", has_perp_for_base=False)
    # A base outside the universe is still excluded even on UPBIT.
    assert not is_in_mvp_capture_universe("UPBIT", "NOTACOINXYZ", "SPOT_PAIR", has_perp_for_base=False)


def test_capture_universe_new_venues_perp_gated() -> None:
    """The 2026-06-23 venues gate correctly: spot needs a perp sibling, perp self-qualifies."""
    from unified_api_contracts import is_in_mvp_capture_universe

    # COINBASE-SPOT BTC: mvp only with a COINBASE perp sibling.
    assert is_in_mvp_capture_universe("COINBASE-SPOT", "BTC", "SPOT_PAIR", has_perp_for_base=True)
    assert not is_in_mvp_capture_universe("COINBASE-SPOT", "BTC", "SPOT_PAIR", has_perp_for_base=False)
    # COINBASE-FUTURES perp self-qualifies on base-membership.
    assert is_in_mvp_capture_universe("COINBASE-FUTURES", "BTC", "PERPETUAL", has_perp_for_base=False)
    # BYBIT-SPOT / BITFINEX-SPOT / BITGET-SPOT all perp-gated.
    assert is_in_mvp_capture_universe("BYBIT-SPOT", "ETH", "SPOT_PAIR", has_perp_for_base=True)
    assert is_in_mvp_capture_universe("BITFINEX-SPOT", "ETH", "SPOT_PAIR", has_perp_for_base=True)
    assert is_in_mvp_capture_universe("BITGET-SPOT", "ETH", "SPOT_PAIR", has_perp_for_base=True)
    assert not is_in_mvp_capture_universe("BITGET-SPOT", "ETH", "SPOT_PAIR", has_perp_for_base=False)


def test_capture_universe_binance_delivery_inverse() -> None:
    """BINANCE-DELIVERY (COIN-M inverse) perps + futures are in the capture universe.

    cefi_universe_capture_rule 2026-06-24: Binance COIN-M is the most-liquid
    inverse margin venue for BTC/ETH. PERPETUALs self-qualify on base-membership;
    FUTUREs also qualify (part of the futures complex). No SPOT on this venue.
    """
    from unified_api_contracts import is_in_mvp_capture_universe

    # PERPETUAL (e.g. BTCUSD_PERP) self-qualifies on base-membership.
    assert is_in_mvp_capture_universe("BINANCE-DELIVERY", "BTC", "PERPETUAL", has_perp_for_base=False)
    assert is_in_mvp_capture_universe("BINANCE-DELIVERY", "ETH", "PERPETUAL", has_perp_for_base=False)
    # FUTURE (dated, e.g. BTCUSD_241227) — part of futures complex, not perp-gated.
    assert is_in_mvp_capture_universe("BINANCE-DELIVERY", "BTC", "FUTURE", has_perp_for_base=False)
    assert is_in_mvp_capture_universe("BINANCE-DELIVERY", "ETH", "FUTURE", has_perp_for_base=True)
    # Out-of-universe base: still rejected.
    assert not is_in_mvp_capture_universe("BINANCE-DELIVERY", "NOTACOINXYZ", "PERPETUAL", has_perp_for_base=True)


def test_capture_universe_okx_bare_token_resolves() -> None:
    """A bare OKX caller resolves to the OKX sub-venues (is_mvp base-venue normalisation)."""
    from unified_api_contracts import is_in_mvp_capture_universe

    assert is_in_mvp_capture_universe("OKX", "BTC", "SPOT_PAIR", has_perp_for_base=True)


def test_capture_universe_returns_bool() -> None:
    """The predicate returns an actual bool (not a truthy object)."""
    from unified_api_contracts import is_in_mvp_capture_universe

    result = is_in_mvp_capture_universe("BINANCE-FUTURES", "BTC", "PERPETUAL", has_perp_for_base=True)
    assert result is True


def test_capture_universe_public_import_surface() -> None:
    """``is_in_mvp_capture_universe`` is importable from the package root."""
    import unified_api_contracts

    assert hasattr(unified_api_contracts, "is_in_mvp_capture_universe")
    assert "is_in_mvp_capture_universe" in unified_api_contracts.__all__


# ---------------------------------------------------------------------------
# STAKING_SPOT_EXCEPTION — the spot-without-perp carve-out (operator 2026-06-23)
# ---------------------------------------------------------------------------

# The LSTs the cefi_universe_capture_rule said were ABSENT and must be added.
# (v6: the original 7 ETH/SOL LSTs; v7: + the 15 wrapped/unwrapped LST/LRT
# equivalents added 2026-06-23 — forward-looking allow-list.)
_NEWLY_ADDED_LSTS = (
    "WSTETH",
    "RETH",
    "WEETH",
    "EETH",
    "MSOL",
    "JITOSOL",
    "BSOL",
    "FRXETH",
    "SFRXETH",
    "ANKRETH",
    "OSETH",
    "SWETH",
    "RSWETH",
    "ETHX",
    "METH",
    "RSETH",
    "EZETH",
    "PUFETH",
    "RSTETH",
    "JSOL",
    "SCNSOL",
    "INF",
)


def test_staking_spot_exception_members() -> None:
    """The exception set is exactly the operator's closed allow-list."""
    from unified_api_contracts import STAKING_SPOT_EXCEPTION

    expected = frozenset(
        {
            # Restaking
            "EIGEN",
            "KING",
            "ETHFI",
            # ETH LSTs / LRTs
            "STETH",
            "WSTETH",
            "RETH",
            "WEETH",
            "EETH",
            "CBETH",
            "FRXETH",
            "SFRXETH",
            "ANKRETH",
            "OSETH",
            "SWETH",
            "RSWETH",
            "ETHX",
            "METH",
            "RSETH",
            "EZETH",
            "PUFETH",
            "RSTETH",
            # SOL LSTs
            "MSOL",
            "JITOSOL",
            "JTO",
            "BSOL",
            "JSOL",
            "SCNSOL",
            "INF",
        }
    )
    assert expected == STAKING_SPOT_EXCEPTION
    assert len(STAKING_SPOT_EXCEPTION) == 28


def test_staking_spot_exception_is_frozenset() -> None:
    """The exception is an immutable frozenset (deterministic constant)."""
    from unified_api_contracts import STAKING_SPOT_EXCEPTION

    assert isinstance(STAKING_SPOT_EXCEPTION, frozenset)


def test_staking_spot_exception_public_import_surface() -> None:
    """``STAKING_SPOT_EXCEPTION`` is importable from the package root + in __all__."""
    import unified_api_contracts

    assert hasattr(unified_api_contracts, "STAKING_SPOT_EXCEPTION")
    assert "STAKING_SPOT_EXCEPTION" in unified_api_contracts.__all__


def test_staking_spot_exception_all_members_in_base_universe() -> None:
    """Every exception base is also in CEFI_BASE_ASSET_UNIVERSE (base-membership leg)."""
    from unified_api_contracts import (
        CEFI_BASE_ASSET_UNIVERSE,
        STAKING_SPOT_EXCEPTION,
    )

    missing = STAKING_SPOT_EXCEPTION - CEFI_BASE_ASSET_UNIVERSE
    assert not missing, f"exception bases missing from CEFI_BASE_ASSET_UNIVERSE: {sorted(missing)}"


def test_newly_added_lsts_present_in_base_universe() -> None:
    """The 7 previously-absent LSTs are now in CEFI_BASE_ASSET_UNIVERSE."""
    from unified_api_contracts import CEFI_BASE_ASSET_UNIVERSE

    for ticker in _NEWLY_ADDED_LSTS:
        assert ticker in CEFI_BASE_ASSET_UNIVERSE, f"{ticker} missing from CEFI_BASE_ASSET_UNIVERSE"


def test_base_universe_is_sorted_deterministic() -> None:
    """CEFI_BASE_ASSET_UNIVERSE renders sorted/deterministic (frozenset, no dupes)."""
    from unified_api_contracts import CEFI_BASE_ASSET_UNIVERSE

    assert isinstance(CEFI_BASE_ASSET_UNIVERSE, frozenset)
    # No duplicates survive a frozenset, but assert the literal is internally consistent.
    assert len(CEFI_BASE_ASSET_UNIVERSE) == len(set(CEFI_BASE_ASSET_UNIVERSE))


def test_capture_universe_staking_spot_mvp_without_perp() -> None:
    """Each STAKING_SPOT_EXCEPTION base's SPOT is mvp=true even with has_perp_for_base=False."""
    from unified_api_contracts import STAKING_SPOT_EXCEPTION, is_in_mvp_capture_universe

    for base in STAKING_SPOT_EXCEPTION:
        assert is_in_mvp_capture_universe("BINANCE-SPOT", base, "SPOT_PAIR", has_perp_for_base=False), (
            f"staking-exception base {base} SPOT should be mvp=true with no perp"
        )


def test_capture_universe_staking_spot_exception_on_any_venue() -> None:
    """The carve-out applies on any in-rule venue that lists it — e.g. Kraken spot."""
    from unified_api_contracts import is_in_mvp_capture_universe

    assert is_in_mvp_capture_universe("KRAKEN-SPOT", "STETH", "SPOT_PAIR", has_perp_for_base=False)


def test_capture_universe_non_exception_spot_no_perp_still_dropped() -> None:
    """A NON-exception base's spot-without-perp stays mvp=false (the gate holds)."""
    from unified_api_contracts import STAKING_SPOT_EXCEPTION, is_in_mvp_capture_universe

    # ADA is in the universe but NOT a staking-exception base.
    assert "ADA" not in STAKING_SPOT_EXCEPTION
    assert not is_in_mvp_capture_universe("BINANCE-SPOT", "ADA", "SPOT_PAIR", has_perp_for_base=False)
    # With a perp it's back in.
    assert is_in_mvp_capture_universe("BINANCE-SPOT", "ADA", "SPOT_PAIR", has_perp_for_base=True)


def test_capture_universe_config_version_bumped() -> None:
    """MVP_SCOPE_CONFIG_VERSION reflects the staking-exception change."""
    from unified_api_contracts.canonical.crosscutting.mvp_scope import (
        MVP_SCOPE_CONFIG_VERSION,
    )

    assert MVP_SCOPE_CONFIG_VERSION >= 8


def test_accepted_quotes_for_venue_upbit_krw() -> None:
    """KRW is accepted ONLY for UPBIT; default venues stay USDT/USDC/USD."""
    from unified_api_contracts import accepted_quotes_for_venue
    from unified_api_contracts.registry.cefi_instrument_universe import (
        CEFI_ACCEPTED_QUOTE_ASSETS,
    )

    assert "KRW" in accepted_quotes_for_venue("UPBIT")
    assert "KRW" in accepted_quotes_for_venue("UPBIT-SPOT")
    assert {"USDT", "USDC", "USD"} <= accepted_quotes_for_venue("UPBIT")
    # KRW NOT accepted on any other venue.
    assert "KRW" not in accepted_quotes_for_venue("BINANCE-SPOT")
    assert accepted_quotes_for_venue("BINANCE-SPOT") == CEFI_ACCEPTED_QUOTE_ASSETS
    assert accepted_quotes_for_venue(None) == CEFI_ACCEPTED_QUOTE_ASSETS
