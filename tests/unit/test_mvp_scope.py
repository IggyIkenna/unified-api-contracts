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
from unified_api_contracts.canonical.crosscutting._mvp_scope_rules import (
    _mvp_defi_data_types,
)
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

    def test_deribit_btc_option_options_chain_is_mvp(self) -> None:
        """Deribit BTC OPTION options_chain → MVP (carve-out admits BTC + ETH).

        operator 2026-06-27 decision #2: the Deribit OPTION MVP data_type is
        ``options_chain`` ONLY (it carries marks + IVs); per-strike trades +
        book_snapshot_5 are EXCLUDED.
        """
        assert is_mvp("cefi", "DERIBIT", "OPTION", "options_chain", base_ccy="BTC")

    def test_deribit_eth_option_options_chain_is_mvp(self) -> None:
        """Deribit ETH OPTION options_chain → MVP (the options carve-out admits BTC + ETH)."""
        assert is_mvp("cefi", "DERIBIT", "OPTION", "options_chain", base_ccy="ETH")

    def test_deribit_option_trades_excluded(self) -> None:
        """Deribit OPTION trades → NOT MVP (decision #2 — per-strike tick excluded)."""
        assert not is_mvp("cefi", "DERIBIT", "OPTION", "trades", base_ccy="BTC")

    def test_deribit_option_book_snapshot_5_excluded(self) -> None:
        """Deribit OPTION book_snapshot_5 → NOT MVP (decision #2 — per-strike depth excluded)."""
        assert not is_mvp("cefi", "DERIBIT", "OPTION", "book_snapshot_5", base_ccy="BTC")

    def test_deribit_sol_option_not_mvp(self) -> None:
        """A non-BTC/ETH OPTION → False even though SOL is in the spot/perp universe.

        The Deribit-options carve-out narrows the OPTION expected universe to
        BTC + ETH only, so a SOL option is NOT expected (no false-missing).
        """
        assert not is_mvp("cefi", "DERIBIT", "OPTION", "options_chain", base_ccy="SOL")

    def test_dex_clob_perp_venues_are_cefi_mvp(self) -> None:
        """LIGHTER / EXTENDED perps are cefi MVP (decision #4). (PACIFICA
        (Solana) was a third venue here until removed 2026-07-16 — operator
        ruling: all Solana perp DEXes dropped except Jupiter, not
        integrated.)"""
        assert is_mvp("cefi", "LIGHTER-ZKSYNC", "PERPETUAL", "trades", base_ccy="BTC")
        assert is_mvp("cefi", "EXTENDED-STARKNET", "PERPETUAL", "trades", base_ccy="ETH")

    def test_binance_delivery_dropped_from_mvp(self) -> None:
        """BINANCE-DELIVERY (COIN-M) dropped from cefi MVP (decision #3)."""
        assert not is_mvp("cefi", "BINANCE-DELIVERY", "PERPETUAL", "trades", base_ccy="BTC")
        assert not is_mvp("cefi", "BINANCE-DELIVERY", "FUTURE", "trades", base_ccy="BTC")

    def test_no_base_ccy_with_non_empty_rule_returns_false(self) -> None:
        """When the rule has non-empty base_ccys, None base_ccy → False."""
        assert not is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades", base_ccy=None)

    def test_non_mvp_data_type_returns_false(self) -> None:
        """A data_type not in the CeFi MVP set → False."""
        assert not is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "positions", base_ccy="BTC")

    def test_non_mvp_instrument_type_returns_false(self) -> None:
        """An instrument_type not in the CeFi MVP set → False.

        (FUTURE is now an MVP cefi instrument_type — dated futures are in scope per
        cefi_universe_capture_rule_2026_06_23 — and COMBO joined too, v16, for
        DERIBIT-COMBO — so this asserts POOL, a DeFi-only instrument_type that is
        NOT in the CeFi rule.)
        """
        assert not is_mvp("cefi", "BINANCE-FUTURES", "POOL", "trades", base_ccy="BTC")

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

    def test_orca_solana_pool_dex_pool_swaps_is_mvp(self) -> None:
        """ORCA-SOLANA POOL dex_pool_swaps → MVP.

        POOL, not DEX_POOL — ``DEX_POOL`` was aspirational-only (v10-v12): no
        live adapter ever emitted it (``orca.py`` builds
        ``instrument_type=InstrumentType.POOL``, same as the EVM AMM
        adapters). Verified 2026-07-09 via a repo-wide grep of every
        ``adapters/defi/*.py`` file's real ``InstrumentType.*`` usage.
        """
        assert is_mvp("defi", "ORCA-SOLANA", "POOL", "dex_pool_swaps")

    def test_non_mvp_defi_venue_returns_false(self) -> None:
        """YEARN_V3-OPTIMISM is in ALL_DEFI_VENUES but NOT IS-producible (not in P) → False.

        MVP DeFi == P (``VENUES_BY_ASSET_GROUP["defi"]``, phase=="live"), not the
        broader declarative ``ALL_DEFI_VENUES`` registry. YEARN_V3-OPTIMISM has a
        real adapter CLASS (yearn.py) but ``_YEARN_VAULTS_BY_CHAIN`` has NO Optimism
        vault entries, so ``get_instruments()`` returns 0 rows and it is deliberately
        left out of ``_build_defi_venues()`` (phase="pipeline") — no phantom
        expected-but-never-captured cell. (Pre-2026-07-18 this test used
        YEARN_V3-ETHEREUM, which was onboarded to P in the v17 LST/vault wiring pass.)
        """
        assert not is_mvp("defi", "YEARN_V3-OPTIMISM", "POOL", "dex_pool_state")

    def test_non_mvp_defi_data_type_returns_false(self) -> None:
        """trades is a CeFi/prediction data_type, NOT a real DeFi data_type → False.

        (Pre-v13 this test used ``gas_fees`` — v13 broadened DeFi MVP's
        data_types to the FULL ``DATA_TYPES_BY_ASSET_GROUP["defi"]`` list
        (see ``TestDeFiMvpV13Broadening``), which now includes ``gas_fees``.
        ``trades`` is never a member of the defi data_types list at all, so
        it remains a valid "impossible" negative case.)
        """
        assert not is_mvp("defi", "UNISWAP_V3-ETHEREUM", "POOL", "trades")

    def test_non_mvp_defi_instrument_type_returns_false(self) -> None:
        """SPOT_ASSET is a DeFi InstrumentType enum member but NO adapter emits it → False."""
        assert not is_mvp("defi", "UNISWAP_V3-ETHEREUM", "SPOT_ASSET", "dex_pool_state")


# ---------------------------------------------------------------------------
# TradFi tests
# ---------------------------------------------------------------------------


class TestTradFiMvp:
    """TradFi MVP rule tests — positive + negative cases."""

    def test_cme_future_es_ohlcv_1m_is_mvp(self) -> None:
        """CME FUTURE ES ohlcv_1m → MVP (tradfi MVP grain is ohlcv_1m, decision #7)."""
        assert is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="ES")

    def test_cme_future_nq_ohlcv_1m_is_mvp(self) -> None:
        """CME FUTURE NQ ohlcv_1m → MVP."""
        assert is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="NQ")

    def test_cme_future_vx_ohlcv_1m_is_mvp(self) -> None:
        """CME FUTURE VX (VIX futures) ohlcv_1m → MVP."""
        assert is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="VX")

    def test_cme_option_es_ohlcv_1m_is_mvp(self) -> None:
        """CME OPTION ES ohlcv_1m → MVP (decision #7 — CME options MVP at ohlcv_1m)."""
        assert is_mvp("tradfi", "CME", "OPTION", "ohlcv_1m", base_ccy="ES")

    def test_cme_trades_excluded(self) -> None:
        """CME trades → NOT MVP (decision #7 — tradfi MVP is ohlcv_1m only)."""
        assert not is_mvp("tradfi", "CME", "FUTURE", "trades", base_ccy="ES")

    def test_cme_ohlcv_1s_excluded(self) -> None:
        """CME ohlcv_1s → NOT MVP (decision #7 — tradfi MVP is ohlcv_1m only, no 1s)."""
        assert not is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1s", base_ccy="ES")

    def test_non_mvp_tradfi_venue_returns_false(self) -> None:
        """NASDAQ is in tradfi venues but NOT in the MVP set → False."""
        assert not is_mvp("tradfi", "NASDAQ", "EQUITY", "ohlcv_1m")

    def test_non_mvp_tradfi_underlier_returns_false(self) -> None:
        """RTY (Russell 2000) underlier is NOT in the MVP set → False."""
        assert not is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="RTY")

    def test_non_mvp_tradfi_data_type_returns_false(self) -> None:
        """ohlcv_15m is a tradfi data_type but NOT in the MVP set → False."""
        assert not is_mvp("tradfi", "CME", "FUTURE", "ohlcv_15m", base_ccy="ES")


# ---------------------------------------------------------------------------
# v14 — TradFi MVP OPTION underlier narrowing (2026-07-14, operator ruling on
# tradfi_eu_not_draining_source_axis_drift_2026_06_24.md, verbatim: "We DO
# want tradfi options for S&P 500 — options and futures — but NO other
# options in tradfi MVP; just the single stocks, ETFs and futures already in
# MVP."). Before this change every OPTION cell inherited the full
# ``TradFiMvpRule.underliers`` set (ES/NQ/VX/GC/SI/PL/PA/NG/CL/HG) with no
# OPTION-specific narrowing — this class pins the new
# ``option_underliers`` = ``TRADFI_MVP_OPTION_UNDERLYING_ROOTS`` = {"ES"} gate.
# ---------------------------------------------------------------------------


class TestTradFiOptionUnderlierNarrowingV14:
    """v14: tradfi MVP OPTION scope narrows to the S&P 500 / ES complex ONLY."""

    def test_es_option_is_mvp(self) -> None:
        """CME OPTION on the ES root → MVP (the S&P 500 complex stays in scope)."""
        assert is_mvp("tradfi", "CME", "OPTION", "ohlcv_1m", base_ccy="ES")

    def test_gc_gold_option_not_mvp(self) -> None:
        """CME OPTION on GC (gold) → NOT MVP (narrowed out, even though the GC
        FUTURE itself stays MVP — see test_gc_future_still_mvp below)."""
        assert not is_mvp("tradfi", "CME", "OPTION", "ohlcv_1m", base_ccy="GC")

    def test_cl_crude_option_not_mvp(self) -> None:
        """CME OPTION on CL (crude) → NOT MVP (narrowed out)."""
        assert not is_mvp("tradfi", "CME", "OPTION", "ohlcv_1m", base_ccy="CL")

    def test_ng_natgas_option_not_mvp(self) -> None:
        """CME OPTION on NG (natgas) → NOT MVP (narrowed out)."""
        assert not is_mvp("tradfi", "CME", "OPTION", "ohlcv_1m", base_ccy="NG")

    def test_nq_option_not_mvp(self) -> None:
        """CME OPTION on NQ (Nasdaq 100) → NOT MVP — narrowed out even though NQ
        is itself an MVP underlier for FUTURE cells (the S&P 500 complex is the
        ONLY MVP options underlier per the 2026-07-14 ruling)."""
        assert not is_mvp("tradfi", "CME", "OPTION", "ohlcv_1m", base_ccy="NQ")

    def test_vx_option_not_mvp(self) -> None:
        """CME OPTION on VX (VIX futures) → NOT MVP (narrowed out)."""
        assert not is_mvp("tradfi", "CME", "OPTION", "ohlcv_1m", base_ccy="VX")

    def test_si_pl_pa_hg_options_not_mvp(self) -> None:
        """The remaining commodity-option underliers (SI/PL/PA/HG) → NOT MVP."""
        for root in ("SI", "PL", "PA", "HG"):
            assert not is_mvp("tradfi", "CME", "OPTION", "ohlcv_1m", base_ccy=root)

    def test_gc_future_still_mvp(self) -> None:
        """Regression: GC FUTURE (not OPTION) is UNCHANGED — still MVP.

        ``option_underliers`` gates OPTION cells only; the flat ``underliers``
        set still governs FUTURE cells exactly as before this change.
        """
        assert is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="GC")

    def test_nq_future_still_mvp(self) -> None:
        """Regression: NQ FUTURE is UNCHANGED — still MVP."""
        assert is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="NQ")

    def test_equity_basis_carve_out_still_mvp(self) -> None:
        """Regression: the cash equity/ETF basis carve-out is UNCHANGED — still
        MVP (single stocks/ETFs are untouched by the OPTION-only narrowing)."""
        assert is_mvp("tradfi", "NASDAQ", "EQUITY", "ohlcv_1m", base_ccy="NVDA")

    def test_option_underliers_field_exact_value(self) -> None:
        """``TradFiMvpRule.option_underliers`` == ``TRADFI_MVP_OPTION_UNDERLYING_ROOTS`` == {"ES"}."""
        from unified_api_contracts.canonical.crosscutting.mvp_scope import (
            TRADFI_MVP_OPTION_UNDERLYING_ROOTS,
        )

        rule = MVP_SCOPE["tradfi"]
        assert isinstance(rule, TradFiMvpRule)
        assert rule.option_underliers == TRADFI_MVP_OPTION_UNDERLYING_ROOTS
        assert frozenset({"ES"}) == TRADFI_MVP_OPTION_UNDERLYING_ROOTS

    def test_config_version_is_latest(self) -> None:
        """MVP_SCOPE_CONFIG_VERSION == 19 exactly (v19 = tradfi MVP-set expansion:
        CME BTC/ETH/MBT/MET futures + CBOE VIX futures + CBOE Treasury-yield INDEX
        tenors + FX KRW-USD; v18 = book_snapshot_5 added to
        PredictionMvpRule.data_types; v17 = 26 LST/restaking/vault DeFi venues
        onboarded to P → live → MVP; v16 = COMBO instrument_type for
        DERIBIT-COMBO)."""
        from unified_api_contracts.canonical.crosscutting.mvp_scope import MVP_SCOPE_CONFIG_VERSION

        assert MVP_SCOPE_CONFIG_VERSION == 19


# ---------------------------------------------------------------------------
# v19 — TradFi MVP-set expansion (operator directive 2026-07-21): four new
# instrument groups flipped into tradfi MVP. (1) CME BTC/ETH/MBT/MET FUTURES
# (via ``underliers``), (2) CBOE VIX (VX) futures, (3) the daily US
# Treasury-yield INDEX tenors, and (4) the FX KRW-USD spot pair (the latter
# three via the declarative ``extra_mvp_cells`` triples). The prior tradfi MVP
# set is UNCHANGED, and CME BTC/ETH OPTIONS stay OUT (``option_underliers``).
# ---------------------------------------------------------------------------


class TestTradFiMvpExpansionV19:
    """v19: CME BTC/ETH futures, CBOE VIX futures, CBOE Treasury INDEX, FX KRW."""

    def test_cme_future_btc_is_mvp(self) -> None:
        """CME FUTURE on BTC (Bitcoin) → MVP."""
        assert is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="BTC")

    def test_cme_future_eth_is_mvp(self) -> None:
        """CME FUTURE on ETH (Ether) → MVP."""
        assert is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="ETH")

    def test_cme_future_micro_btc_eth_is_mvp(self) -> None:
        """CME FUTURE on MBT/MET (micro Bitcoin/Ether) → MVP — the IS catalogue
        tags micro-future rows with base_asset=MBT/MET, so both micro roots must
        themselves be MVP underliers (not ES-style sub-codes)."""
        assert is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="MBT")
        assert is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="MET")

    def test_cme_option_btc_eth_not_mvp(self) -> None:
        """CME OPTION on BTC/ETH → NOT MVP (operator: "no CME option for BTC and
        ETH"). ``option_underliers``={"ES"} governs OPTION cells, so the new
        BTC/ETH/MBT/MET ``underliers`` additions do not reach options."""
        for root in ("BTC", "ETH", "MBT", "MET"):
            assert not is_mvp("tradfi", "CME", "OPTION", "ohlcv_1m", base_ccy=root)

    def test_cboe_vix_future_is_mvp(self) -> None:
        """CBOE FUTURE on VX (VIX futures) → MVP via the extra-cell carve-out.

        The IS catalogue writer emits venue=CBOE with base_asset=VX for these
        rows; "CBOE" is NOT in the flat ``venues`` set (it also carries ~33k
        SPX/VIX OPTION rows that must stay non-MVP), so this rides the exact
        (CBOE, FUTURE, VX) ``extra_mvp_cells`` triple.
        """
        assert is_mvp("tradfi", "CBOE", "FUTURE", "ohlcv_1m", base_ccy="VX")

    def test_cboe_option_not_swept_in(self) -> None:
        """Regression: adding CBOE VIX futures did NOT sweep in CBOE OPTIONs — a
        CBOE OPTION (e.g. an SPX option) is NOT MVP (would be if "CBOE" had been
        added to the flat ``venues`` set instead of a scoped extra cell)."""
        assert not is_mvp("tradfi", "CBOE", "OPTION", "ohlcv_1m", base_ccy="SPX")
        assert not is_mvp("tradfi", "CBOE", "SPOT_PAIR", "ohlcv_24h", base_ccy="SPX")

    def test_cboe_index_treasury_tenors_are_mvp(self) -> None:
        """CBOE INDEX on the 5 daily Treasury-yield tenors → MVP (Yahoo ohlcv_24h)."""
        for tenor in ("US2Y", "US5Y", "US10Y", "US30Y", "US3M"):
            assert is_mvp("tradfi", "CBOE", "INDEX", "ohlcv_24h", base_ccy=tenor)

    def test_cboe_index_vix_cash_not_mvp(self) -> None:
        """CBOE INDEX on VIX (the cash index) → NOT MVP — only the treasury-yield
        tenors are in scope, not the VIX cash INDEX rows."""
        assert not is_mvp("tradfi", "CBOE", "INDEX", "ohlcv_24h", base_ccy="VIX")

    def test_fx_krw_spot_is_mvp(self) -> None:
        """FX SPOT_PAIR on KRW (KRW-USD, kimchi-premium basis leg) → MVP."""
        assert is_mvp("tradfi", "FX", "SPOT_PAIR", "ohlcv_24h", base_ccy="KRW")

    def test_fx_other_majors_not_mvp(self) -> None:
        """Regression: the other FX majors stay non-MVP (only KRW is in scope)."""
        for base in ("EUR", "GBP", "JPY", "AUD", "CAD"):
            assert not is_mvp("tradfi", "FX", "SPOT_PAIR", "ohlcv_24h", base_ccy=base)

    def test_extra_mvp_cells_exact_membership(self) -> None:
        """``TradFiMvpRule.extra_mvp_cells`` == the exact 7-triple expansion set."""
        rule = MVP_SCOPE["tradfi"]
        assert isinstance(rule, TradFiMvpRule)
        assert rule.extra_mvp_cells == frozenset(
            {
                ("CBOE", "FUTURE", "VX"),
                ("CBOE", "INDEX", "US2Y"),
                ("CBOE", "INDEX", "US5Y"),
                ("CBOE", "INDEX", "US10Y"),
                ("CBOE", "INDEX", "US30Y"),
                ("CBOE", "INDEX", "US3M"),
                ("FX", "SPOT_PAIR", "KRW"),
            }
        )

    def test_cme_crypto_underliers_present(self) -> None:
        """The CME crypto futures roots are in ``TradFiMvpRule.underliers``."""
        rule = MVP_SCOPE["tradfi"]
        assert isinstance(rule, TradFiMvpRule)
        assert {"BTC", "ETH", "MBT", "MET"} <= rule.underliers

    def test_prior_tradfi_set_unchanged(self) -> None:
        """Regression: the pre-v19 tradfi MVP set is UNCHANGED (ES/NQ/VX futures +
        ES options + the equity-basis carve-out all still MVP)."""
        assert is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="ES")
        assert is_mvp("tradfi", "CME", "OPTION", "ohlcv_1m", base_ccy="ES")
        assert is_mvp("tradfi", "NASDAQ", "EQUITY", "ohlcv_1m", base_ccy="NVDA")


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
        result_esh26 = is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="ES")
        # ESM26 (June 2026 expiry) — same base_ccy
        result_esm26 = is_mvp("tradfi", "CME", "FUTURE", "ohlcv_1m", base_ccy="ES")
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

    def test_mls_odds_snapshot_is_mvp(self) -> None:
        """MLS (a football league in the 94) odds_snapshot → MVP (decision #1)."""
        assert is_mvp("sports", "ODDS_API", "FIXED_ODDS", "odds_snapshot", league="MLS")

    def test_eng_championship_is_mvp(self) -> None:
        """ENG_CHAMPIONSHIP (football) IS MVP — the 94-league universe is ALL football
        leagues, not just the top tier (decision #1 BUG FIX)."""
        assert is_mvp("sports", "ODDS_API", "FIXED_ODDS", "markets", league="ENG_CHAMPIONSHIP")

    def test_full_94_football_universe_is_mvp(self) -> None:
        """Every ``sport == "FOOTBALL"`` league (the 94) is MVP; non-football are not."""
        from unified_api_contracts.canonical.domain.sports.league_data import LEAGUE_REGISTRY

        football = [lg for lg in LEAGUE_REGISTRY.values() if lg.sport == "FOOTBALL"]
        non_football = [lg for lg in LEAGUE_REGISTRY.values() if lg.sport != "FOOTBALL"]
        assert len(football) == 96  # China+Russia added 2026-07-21 (operator ruling: in-universe)
        assert len(non_football) == 7
        for lg in football:
            assert is_mvp("sports", "ODDS_API", "FIXED_ODDS", "odds", league=lg.league_id)
        for lg in non_football:
            assert not is_mvp("sports", "ODDS_API", "FIXED_ODDS", "odds", league=lg.league_id)

    def test_nfl_nba_excluded(self) -> None:
        """NFL / NBA (non-football) are NOT MVP (decision #1 — exclude the 7 non-football)."""
        assert not is_mvp("sports", "ODDS_API", "FIXED_ODDS", "odds", league="NFL")
        assert not is_mvp("sports", "BETFAIR", "EXCHANGE_ODDS", "markets", league="NBA")

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

    def test_kalshi_is_mvp(self) -> None:
        """KALSHI is in the prediction MVP set (decision #5 — Kalshi↔Polymarket
        arb-overlap requires BOTH venues; the post-MVP TODO is resolved)."""
        assert is_mvp(
            "prediction",
            "KALSHI",
            "PREDICTION_MARKET",
            "trades",
            market_group="crypto",
        )

    def test_unknown_prediction_venue_returns_false(self) -> None:
        """A prediction venue outside the MVP set (POLYMARKET/KALSHI) → False."""
        assert not is_mvp(
            "prediction",
            "MANIFOLD",
            "PREDICTION_MARKET",
            "trades",
            market_group="crypto",
        )

    def test_prediction_book_snapshot_5_is_mvp(self) -> None:
        """book_snapshot_5 IS a prediction MVP data_type for BOTH venues.

        Reconcile (prediction_consolidated_closeout_2026_07_18.md P1, 2026-07-18):
        book_snapshot_5 was already in DATA_TYPES_BY_ASSET_GROUP["prediction"] +
        VENUE_DATA_TYPE_CAPABILITIES["POLYMARKET"/"KALSHI"] +
        expected_coverage._PREDICTION, and the depth data is genuinely captured
        (live A0 measured 399,713 book_snapshot_5 prediction rows) — but was
        ABSENT from PredictionMvpRule.data_types, so ``--mvp-only`` silently
        dropped the CLOB-depth shard. Added to the rule to align it with the
        other two registries + the captured data. (This flips the pre-2026-07-18
        ``test_non_mvp_prediction_data_type_returns_false`` — that assertion
        pinned the accidental omission, not a deliberate trades-only decision.)
        """
        assert is_mvp(
            "prediction",
            "POLYMARKET",
            "PREDICTION_MARKET",
            "book_snapshot_5",
            market_group="crypto",
        )
        # Both venues — the arb-overlap MVP requires the depth leg on each side.
        assert is_mvp(
            "prediction",
            "KALSHI",
            "PREDICTION_MARKET",
            "book_snapshot_5",
            market_group="crypto",
        )
        # Unbound market_group (the IS catalogue rollup passes none) still MVP.
        assert is_mvp("prediction", "POLYMARKET", "PREDICTION_MARKET", "book_snapshot_5")
        assert is_mvp("prediction", "KALSHI", "PREDICTION_MARKET", "book_snapshot_5")

    def test_prediction_mvp_data_types_exact_set(self) -> None:
        """PredictionMvpRule.data_types is exactly the reconciled 5-entry set."""
        rule = MVP_SCOPE["prediction"]
        assert isinstance(rule, PredictionMvpRule)
        assert rule.data_types == frozenset(
            {
                "trades",
                "book_snapshot_5",
                "prediction_canonical_question_group",
                "market_lifecycle",
                "MARKET_LIFECYCLE",
            }
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
# Rule-11 blast-radius guard: the prediction book_snapshot_5 reconcile
# (prediction_consolidated_closeout_2026_07_18.md P1) must NOT change any
# OTHER asset_group's MVP data_types set.
# ---------------------------------------------------------------------------


class TestPredictionReconcileCrossAgUnchanged:
    """Adding book_snapshot_5 to prediction MVP leaves cefi/tradfi/defi/sports untouched."""

    def test_cefi_flat_data_types_unchanged(self) -> None:
        """CeFi flat data_types is exactly the unchanged trades/book5/funding set."""
        rule = MVP_SCOPE["cefi"]
        assert isinstance(rule, CeFiMvpRule)
        assert rule.data_types == frozenset({"trades", "book_snapshot_5", "derivative_ticker", "funding_rate"})

    def test_tradfi_data_types_unchanged(self) -> None:
        """TradFi MVP data_types is exactly {ohlcv_1m} — no book_snapshot_5 leak."""
        rule = MVP_SCOPE["tradfi"]
        assert isinstance(rule, TradFiMvpRule)
        assert rule.data_types == frozenset({"ohlcv_1m"})
        assert not is_mvp("tradfi", "CME", "FUTURE", "book_snapshot_5", base_ccy="ES")

    def test_sports_data_types_unchanged(self) -> None:
        """Sports MVP data_types is the exact odds/markets set — no book_snapshot_5 leak."""
        rule = MVP_SCOPE["sports"]
        assert isinstance(rule, SportsMvpRule)
        assert rule.data_types == frozenset({"odds", "ODDS", "odds_snapshot", "markets", "outcomes", "settlements"})

    def test_defi_data_types_unchanged(self) -> None:
        """DeFi MVP data_types stays == the derived DATA_TYPES_BY_ASSET_GROUP['defi']."""
        rule = MVP_SCOPE["defi"]
        assert isinstance(rule, DeFiMvpRule)
        assert rule.data_types == _mvp_defi_data_types()


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
        """A defi venue not in the MVP config → False.

        IDLE-ARBITRUM: wired adapter class (idle.py) but ``_IDLE_VAULTS_BY_CHAIN``
        has no Arbitrum entries → 0 rows → phase="pipeline" → not in P → not MVP.
        (Pre-2026-07-18 this used CONVEX-ETHEREUM, onboarded to P in the v17 pass.)
        """
        assert not is_mvp("defi", "IDLE-ARBITRUM", "POOL", "dex_pool_state")

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

    def test_prediction_unbound_market_group_is_mvp(self) -> None:
        """Prediction with no market_group → MVP (any-market_group, decision #5).

        The IS catalogue rollup never passes ``market_group`` (instrument-grain),
        so a blank market_group must NOT block — POLYMARKET + KALSHI tag mvp=True.
        A NON-blank non-MVP market_group is still gated out.
        """
        assert is_mvp("prediction", "POLYMARKET", "PREDICTION_MARKET", "trades")
        assert is_mvp("prediction", "KALSHI", "PREDICTION_MARKET", "trades")
        assert is_mvp("prediction", "KALSHI", "PREDICTION_MARKET")
        # NON-blank non-MVP market_group still blocked ("financial" not in set).
        assert not is_mvp("prediction", "POLYMARKET", "PREDICTION_MARKET", "trades", market_group="financial")

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
    """A crypto-venue single-stock equity perp is typed PERPETUAL (operator
    2026-07-16, no distinct EQUITY_PERP type) and its equity base rides
    CEFI_EQUITY_PERP_BASE_UNIVERSE → in-universe (it IS a perp)."""
    from unified_api_contracts import is_in_mvp_capture_universe

    assert is_in_mvp_capture_universe("BINANCE-FUTURES", "AAPL", "PERPETUAL", has_perp_for_base=True)


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


def test_capture_universe_binance_delivery_dropped() -> None:
    """BINANCE-DELIVERY (COIN-M inverse) is DROPPED from the cefi MVP capture
    universe (operator 2026-06-27 decision #3 — COIN-M delivery is NOT MVP).

    The venue is no longer in the cefi MVP rule, so neither its perps nor its
    dated futures qualify, regardless of base or perp-gate. Other venues' dated
    futures stay MVP (the FUTURE instrument_type is unchanged for them).
    """
    from unified_api_contracts import is_in_mvp_capture_universe

    assert not is_in_mvp_capture_universe("BINANCE-DELIVERY", "BTC", "PERPETUAL", has_perp_for_base=False)
    assert not is_in_mvp_capture_universe("BINANCE-DELIVERY", "ETH", "PERPETUAL", has_perp_for_base=True)
    assert not is_in_mvp_capture_universe("BINANCE-DELIVERY", "BTC", "FUTURE", has_perp_for_base=False)
    # Other venues' dated futures stay MVP (decision #3 — only COIN-M dropped).
    assert is_in_mvp_capture_universe("BINANCE-FUTURES", "BTC", "FUTURE", has_perp_for_base=False)


def test_capture_universe_dex_clob_perps_in_universe() -> None:
    """LIGHTER / EXTENDED perps are in the cefi capture universe (decision #4).
    (PACIFICA (Solana) was a third venue here until removed 2026-07-16 —
    operator ruling: all Solana perp DEXes dropped except Jupiter, not
    integrated.)"""
    from unified_api_contracts import is_in_mvp_capture_universe

    assert is_in_mvp_capture_universe("LIGHTER-ZKSYNC", "BTC", "PERPETUAL", has_perp_for_base=False)
    assert is_in_mvp_capture_universe("EXTENDED-STARKNET", "ETH", "PERPETUAL", has_perp_for_base=False)


def test_capture_universe_deribit_option_in_universe() -> None:
    """Deribit BTC/ETH OPTION stays in the capture universe (instrument-grain,
    data_type-agnostic) even though only options_chain is the MVP data_type
    (decision #2 narrows the data_type, not the instrument's universe membership)."""
    from unified_api_contracts import is_in_mvp_capture_universe

    assert is_in_mvp_capture_universe("DERIBIT", "BTC", "OPTION", has_perp_for_base=False)
    assert is_in_mvp_capture_universe("DERIBIT", "ETH", "OPTION", has_perp_for_base=False)


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

    assert MVP_SCOPE_CONFIG_VERSION >= 10


# ---------------------------------------------------------------------------
# v11 — COINBASE venue_data_types override (operator 2026-06-28 decision A)
# ---------------------------------------------------------------------------
# COINBASE-SPOT + COINBASE-FUTURES: trades ONLY; book_snapshot_5 EXCLUDED.
# All other venues (Binance, Bybit, OKX, …) keep trades + book_snapshot_5.
# Deribit is UNCHANGED from v10: OPTION = options_chain-only;
# PERP/FUTURE = trades + book_snapshot_5 (still MVP).
# ---------------------------------------------------------------------------


class TestCoinbaseVenueOverrideV11:
    """v11 per-venue data_type override: COINBASE = trades only."""

    def test_coinbase_spot_trades_is_mvp(self) -> None:
        """COINBASE-SPOT SPOT_PAIR trades → MVP (unchanged, still in scope)."""
        assert is_mvp("cefi", "COINBASE-SPOT", "SPOT_PAIR", "trades", base_ccy="BTC")

    def test_coinbase_futures_trades_is_mvp(self) -> None:
        """COINBASE-FUTURES PERPETUAL trades → MVP."""
        assert is_mvp("cefi", "COINBASE-FUTURES", "PERPETUAL", "trades", base_ccy="BTC")

    def test_coinbase_spot_book_snapshot_5_not_mvp(self) -> None:
        """COINBASE-SPOT book_snapshot_5 → NOT MVP (decision A — book5 excluded)."""
        assert not is_mvp("cefi", "COINBASE-SPOT", "SPOT_PAIR", "book_snapshot_5", base_ccy="BTC")

    def test_coinbase_futures_book_snapshot_5_not_mvp(self) -> None:
        """COINBASE-FUTURES book_snapshot_5 → NOT MVP (decision A)."""
        assert not is_mvp("cefi", "COINBASE-FUTURES", "PERPETUAL", "book_snapshot_5", base_ccy="BTC")

    def test_coinbase_spot_book5_eth_not_mvp(self) -> None:
        """COINBASE-SPOT book_snapshot_5 ETH → NOT MVP (venue override applies to all bases)."""
        assert not is_mvp("cefi", "COINBASE-SPOT", "SPOT_PAIR", "book_snapshot_5", base_ccy="ETH")

    def test_binance_book_snapshot_5_still_mvp(self) -> None:
        """BINANCE-SPOT book_snapshot_5 → still MVP (override is Coinbase-only)."""
        assert is_mvp("cefi", "BINANCE-SPOT", "SPOT_PAIR", "book_snapshot_5", base_ccy="BTC")

    def test_bybit_book_snapshot_5_still_mvp(self) -> None:
        """BYBIT book_snapshot_5 → still MVP (override is Coinbase-only)."""
        assert is_mvp("cefi", "BYBIT", "PERPETUAL", "book_snapshot_5", base_ccy="ETH")

    def test_okx_swap_book_snapshot_5_still_mvp(self) -> None:
        """OKX-SWAP book_snapshot_5 → still MVP."""
        assert is_mvp("cefi", "OKX-SWAP", "PERPETUAL", "book_snapshot_5", base_ccy="BTC")

    def test_deribit_perp_trades_still_mvp(self) -> None:
        """Deribit PERPETUAL trades → still MVP (v10 behavior unchanged in v11)."""
        assert is_mvp("cefi", "DERIBIT", "PERPETUAL", "trades", base_ccy="BTC")

    def test_deribit_perp_book_snapshot_5_still_mvp(self) -> None:
        """Deribit PERPETUAL book_snapshot_5 → still MVP (v10 behavior unchanged — perp/future tick wanted)."""
        assert is_mvp("cefi", "DERIBIT", "PERPETUAL", "book_snapshot_5", base_ccy="BTC")

    def test_deribit_future_book_snapshot_5_still_mvp(self) -> None:
        """Deribit FUTURE book_snapshot_5 → still MVP (v10 behavior unchanged)."""
        assert is_mvp("cefi", "DERIBIT", "FUTURE", "book_snapshot_5", base_ccy="BTC")

    def test_deribit_option_options_chain_still_mvp(self) -> None:
        """Deribit OPTION options_chain → still MVP (v10 behavior unchanged)."""
        assert is_mvp("cefi", "DERIBIT", "OPTION", "options_chain", base_ccy="BTC")

    def test_deribit_option_book_snapshot_5_still_excluded(self) -> None:
        """Deribit OPTION book_snapshot_5 → NOT MVP (v10 instrument_type override unchanged)."""
        assert not is_mvp("cefi", "DERIBIT", "OPTION", "book_snapshot_5", base_ccy="BTC")

    def test_get_mvp_data_types_coinbase_spot(self) -> None:
        """get_mvp_data_types_for_cefi_venue returns trades-only for COINBASE-SPOT."""
        from unified_api_contracts import get_mvp_data_types_for_cefi_venue

        dt = get_mvp_data_types_for_cefi_venue("COINBASE-SPOT")
        assert dt == frozenset({"trades"})
        assert "book_snapshot_5" not in dt

    def test_get_mvp_data_types_coinbase_futures(self) -> None:
        """get_mvp_data_types_for_cefi_venue returns trades-only for COINBASE-FUTURES."""
        from unified_api_contracts import get_mvp_data_types_for_cefi_venue

        dt = get_mvp_data_types_for_cefi_venue("COINBASE-FUTURES")
        assert dt == frozenset({"trades"})

    def test_get_mvp_data_types_binance_includes_book5(self) -> None:
        """get_mvp_data_types_for_cefi_venue returns trades+book5 for BINANCE-FUTURES."""
        from unified_api_contracts import get_mvp_data_types_for_cefi_venue

        dt = get_mvp_data_types_for_cefi_venue("BINANCE-FUTURES")
        assert "trades" in dt
        assert "book_snapshot_5" in dt


# ---------------------------------------------------------------------------
# v12 — DERIBIT-COMBO MVP_SCOPE.venues membership (operator
# 2026-07-10, decision #6 — cefi_layer1_denominator_gaps_2026_07_03.md's
# BLOCKED-OPERATOR-DECISION). DERIBIT-COMBO was a declared cefi venue
# (VENUES_BY_ASSET_GROUP["cefi"]) with real captured data but absent from
# MVP_SCOPE["cefi"].venues, silently zeroing its Layer-1 EXPECTED
# regardless of the itype/capability gates. (Decision #6 also named bare
# "COINBASE" for the same treatment, but that was deliberately NOT added —
# see test_coinbase_spot_is_mvp_in_base_rule above / the active
# coinbase_bare_name_migration_2026_07_06.md plan.)
# ---------------------------------------------------------------------------


class TestDeribitComboMvpScopeV12:
    """v12: DERIBIT-COMBO added to MVP_SCOPE['cefi'].venues."""

    def test_deribit_combo_option_trades_is_mvp(self) -> None:
        """DERIBIT-COMBO OPTION trades -> MVP (its real capture surface)."""
        assert is_mvp("cefi", "DERIBIT-COMBO", "OPTION", "trades", base_ccy="BTC")

    def test_deribit_combo_option_book_snapshot_5_is_mvp(self) -> None:
        """DERIBIT-COMBO OPTION book_snapshot_5 -> MVP (its real capture surface)."""
        assert is_mvp("cefi", "DERIBIT-COMBO", "OPTION", "book_snapshot_5", base_ccy="BTC")

    def test_deribit_combo_does_not_inherit_options_chain_override(self) -> None:
        """DERIBIT-COMBO OPTION options_chain -> NOT MVP.

        Without the venue_data_types override, DERIBIT-COMBO would silently
        inherit the bare-DERIBIT instrument_type_data_types["OPTION"] ->
        {options_chain} rule -- a phantom cell DERIBIT-COMBO cannot actually
        produce (its real DataTypeCapability declarations are trades +
        book_snapshot_5, not options_chain).
        """
        assert not is_mvp("cefi", "DERIBIT-COMBO", "OPTION", "options_chain", base_ccy="BTC")

    def test_get_mvp_data_types_deribit_combo(self) -> None:
        """get_mvp_data_types_for_cefi_venue returns trades+book5 (not options_chain) for DERIBIT-COMBO."""
        from unified_api_contracts import get_mvp_data_types_for_cefi_venue

        dt = get_mvp_data_types_for_cefi_venue("DERIBIT-COMBO")
        assert dt == frozenset({"trades", "book_snapshot_5"})
        assert "options_chain" not in dt

    def test_deribit_bare_option_override_unaffected(self) -> None:
        """Bare DERIBIT's OPTION -> {options_chain} override is unchanged by the
        DERIBIT-COMBO override (the two venues are distinct dict keys)."""
        assert is_mvp("cefi", "DERIBIT", "OPTION", "options_chain", base_ccy="BTC")
        assert not is_mvp("cefi", "DERIBIT", "OPTION", "trades", base_ccy="BTC")


# ---------------------------------------------------------------------------
# v16 — "COMBO" added to CeFiMvpRule.instrument_types (operator decision on
# cefi_deribit_combo_and_okx_bare_venue_gaps_2026_07_12.md's
# BLOCKED-OPERATOR-DECISION item, option (a), 2026-07-16). The
# instruments-service catalogue tags DERIBIT-COMBO rows with instrument_type
# "COMBO" (distinct from "OPTION" — see _instrument_enums.py), so before this
# fix is_mvp() unconditionally returned False for every DERIBIT-COMBO
# catalogue row regardless of the venue already being MVP-declared (v12
# above).
# ---------------------------------------------------------------------------


class TestDeribitComboInstrumentTypeV16:
    """v16: "COMBO" instrument_type joins CeFiMvpRule.instrument_types."""

    def test_deribit_combo_combo_trades_is_mvp(self) -> None:
        """DERIBIT-COMBO COMBO trades -> MVP (the real catalogue-row itype)."""
        assert is_mvp("cefi", "DERIBIT-COMBO", "COMBO", "trades", base_ccy="BTC")

    def test_deribit_combo_combo_book_snapshot_5_is_mvp(self) -> None:
        """DERIBIT-COMBO COMBO book_snapshot_5 -> MVP (the real catalogue-row itype)."""
        assert is_mvp("cefi", "DERIBIT-COMBO", "COMBO", "book_snapshot_5", base_ccy="BTC")

    def test_deribit_combo_combo_eth_is_mvp(self) -> None:
        """DERIBIT-COMBO COMBO trades -> MVP for ETH too (not BTC-only)."""
        assert is_mvp("cefi", "DERIBIT-COMBO", "COMBO", "trades", base_ccy="ETH")

    def test_deribit_combo_combo_does_not_inherit_options_chain(self) -> None:
        """DERIBIT-COMBO COMBO options_chain -> NOT MVP.

        The venue_data_types override ({trades, book_snapshot_5}) is final for
        ALL instrument_types at DERIBIT-COMBO (per-instrument_type overrides
        never apply when a venue override is set) — so COMBO does not inherit
        any options_chain minting either, same guarantee v12 established for
        the OPTION itype.
        """
        assert not is_mvp("cefi", "DERIBIT-COMBO", "COMBO", "options_chain", base_ccy="BTC")

    def test_combo_instrument_type_scoped_to_deribit_combo_venue(self) -> None:
        """A COMBO itype on a venue that isn't in the CeFi MVP rule -> NOT MVP.

        "COMBO" only broadens the instrument_type axis; venue membership is a
        separate, still-enforced axis (axis 1 of is_mvp), so this does not
        open MVP scope for arbitrary venues.
        """
        assert not is_mvp("cefi", "FAKE_VENUE_XYZ", "COMBO", "trades", base_ccy="BTC")

    def test_config_version_is_at_least_v16(self) -> None:
        """MVP_SCOPE_CONFIG_VERSION >= 16 (the COMBO instrument_type addition)."""
        from unified_api_contracts.canonical.crosscutting.mvp_scope import MVP_SCOPE_CONFIG_VERSION

        assert MVP_SCOPE_CONFIG_VERSION >= 16


class TestCoinbaseVenueOverrideV11Continued:
    """Continuation of TestCoinbaseVenueOverrideV11 (split by the v12 class insert above)."""

    def test_get_mvp_data_types_non_mvp_venue_empty(self) -> None:
        """get_mvp_data_types_for_cefi_venue returns empty frozenset for non-MVP venue."""
        from unified_api_contracts import get_mvp_data_types_for_cefi_venue

        assert get_mvp_data_types_for_cefi_venue("FAKE_VENUE_XYZ") == frozenset()

    def test_config_version_is_at_least_v13(self) -> None:
        """MVP_SCOPE_CONFIG_VERSION >= 13 (the DeFi MVP "everything we capture" broadening this
        class exercises is still live; v14's exact pin lives in
        ``TestTradFiOptionUnderlierNarrowingV14``).
        """
        from unified_api_contracts.canonical.crosscutting.mvp_scope import MVP_SCOPE_CONFIG_VERSION

        assert MVP_SCOPE_CONFIG_VERSION >= 13

    def test_get_mvp_data_types_public_import_surface(self) -> None:
        """get_mvp_data_types_for_cefi_venue is importable from the package root."""
        import unified_api_contracts

        assert hasattr(unified_api_contracts, "get_mvp_data_types_for_cefi_venue")
        assert "get_mvp_data_types_for_cefi_venue" in unified_api_contracts.__all__


# ---------------------------------------------------------------------------
# v12 — DeFi MVP-exclusion (2026-06-29, Decision D)
# ---------------------------------------------------------------------------
# ROCKETPOOL-ETHEREUM removed from DeFiMvpRule.venues — NOT in IS-producible
# set P per instrument_universe_registry_consolidation_2026_06_29.md.
# All other DeFiMvpRule venues are confirmed in P.
# ---------------------------------------------------------------------------


class TestDeFiMvpExclusionV12:
    """v12 established MVP⊆P (a wired adapter CLASS alone does not make a venue MVP —
    it must be IS-producible / in ``_build_defi_venues()``). ROCKETPOOL-ETHEREUM was
    the original example; v17 (2026-07-18) wired rocket_pool.py into
    ``_build_defi_venues()`` (1 real rETH row) so ROCKETPOOL is now producible and
    therefore MVP. The MVP⊆P invariant itself is unchanged and is re-pinned below
    with a still-pipeline example (YEARN_V3-OPTIMISM: wired class, empty per-chain
    registry, 0 rows)."""

    def test_rocketpool_ethereum_now_defi_mvp(self) -> None:
        """ROCKETPOOL-ETHEREUM IS in DeFiMvpRule.venues post-v17 (now IS-producible);
        MVP⊆P still holds — YEARN_V3-OPTIMISM (wired class, empty registry) stays out."""
        from unified_api_contracts.canonical.crosscutting.mvp_scope import (
            DeFiMvpRule,
        )

        rule = MVP_SCOPE["defi"]
        assert isinstance(rule, DeFiMvpRule)
        assert "ROCKETPOOL-ETHEREUM" in rule.venues
        # MVP⊆P invariant: a wired-but-not-producible venue is still excluded.
        assert "YEARN_V3-OPTIMISM" not in rule.venues

    def test_is_mvp_rocketpool_ethereum_returns_true(self) -> None:
        """is_mvp(defi, ROCKETPOOL-ETHEREUM, ...) → True (onboarded to P in v17)."""
        assert is_mvp("defi", "ROCKETPOOL-ETHEREUM", "LST", "lst_rates")

    def test_lido_ethereum_still_defi_mvp(self) -> None:
        """LIDO-ETHEREUM remains in DeFiMvpRule (IS-producible, in P)."""
        assert is_mvp("defi", "LIDO-ETHEREUM", "LST", "lst_rates")

    def test_config_version_is_at_least_v12(self) -> None:
        """MVP_SCOPE_CONFIG_VERSION >= 12 (the DeFi MVP-exclusion this class pins is still live).

        Not pinned to exactly 12: v13 (DeFi MVP "everything we capture"
        broadening) bumped the global monotonic version further while
        preserving this class's ROCKETPOOL-ETHEREUM exclusion invariant
        unchanged (see ``TestDeFiMvpV13Broadening`` for the v13-exact pin).
        """
        from unified_api_contracts.canonical.crosscutting.mvp_scope import MVP_SCOPE_CONFIG_VERSION

        assert MVP_SCOPE_CONFIG_VERSION >= 12

    def test_defi_identity_with_mds_capture_mvp_v12(self) -> None:
        """defi: Cartesian-product identity still holds after ROCKETPOOL removal."""
        from unified_api_contracts import mdps_mvp_universe
        from unified_api_contracts.canonical.crosscutting.mvp_scope import DeFiMvpRule

        rule = MVP_SCOPE["defi"]
        assert isinstance(rule, DeFiMvpRule)
        expected = frozenset((v, it) for v in rule.venues for it in rule.instrument_types)
        assert mdps_mvp_universe("defi") == expected


# ---------------------------------------------------------------------------
# v13 — DeFi MVP "everything we capture" broadening (2026-07-09, operator
# ruling on defi_perp_funding_mvp_scope_contradiction_2026_06_29.md §E5).
# ---------------------------------------------------------------------------


class TestDeFiMvpV13Broadening:
    """v13: DeFi MVP == the full IS-producible capture universe (P), not a
    curated 11-venue subset. Same pass wired 2 real Solana lending adapters
    (MarginFi, Solend) into instruments-service and flipped their
    ``DEFI_VENUE_PHASE`` from "pipeline" to "live"."""

    def test_config_version_is_at_least_v13(self) -> None:
        """MVP_SCOPE_CONFIG_VERSION >= 13 (the v13 broadening pass is still live;
        v14's exact pin lives in ``TestTradFiOptionUnderlierNarrowingV14``)."""
        from unified_api_contracts.canonical.crosscutting.mvp_scope import MVP_SCOPE_CONFIG_VERSION

        assert MVP_SCOPE_CONFIG_VERSION >= 13

    def test_defi_venues_equal_is_producible_set(self) -> None:
        """DeFiMvpRule.venues == VENUES_BY_ASSET_GROUP["defi"] exactly (== P)."""
        from unified_api_contracts.canonical.crosscutting.mvp_scope import DeFiMvpRule
        from unified_api_contracts.registry.market_data_categories import (
            VENUES_BY_ASSET_GROUP,
        )

        rule = MVP_SCOPE["defi"]
        assert isinstance(rule, DeFiMvpRule)
        assert rule.venues == frozenset(VENUES_BY_ASSET_GROUP["defi"])
        # Broadened from the pre-v13 11-venue curated subset.
        assert len(rule.venues) >= 57

    def test_defi_data_types_equal_full_registry(self) -> None:
        """DeFiMvpRule.data_types == the FULL DATA_TYPES_BY_ASSET_GROUP["defi"] list."""
        from unified_api_contracts.canonical.crosscutting.mvp_scope import DeFiMvpRule
        from unified_api_contracts.registry.market_data_categories import (
            DATA_TYPES_BY_ASSET_GROUP,
        )

        rule = MVP_SCOPE["defi"]
        assert isinstance(rule, DeFiMvpRule)
        assert rule.data_types == frozenset(DATA_TYPES_BY_ASSET_GROUP["defi"])
        # gas_fees was explicitly excluded pre-v13 — now in scope.
        assert "gas_fees" in rule.data_types

    def test_marginfi_solana_a_token_is_mvp(self) -> None:
        """MARGINFI-SOLANA A_TOKEN lending_indices → MVP (new real adapter, 2026-07-09)."""
        assert is_mvp("defi", "MARGINFI-SOLANA", "A_TOKEN", "lending_indices")

    def test_marginfi_solana_debt_token_is_mvp(self) -> None:
        """MARGINFI-SOLANA DEBT_TOKEN lending_indices → MVP."""
        assert is_mvp("defi", "MARGINFI-SOLANA", "DEBT_TOKEN", "lending_indices")

    def test_solend_solana_a_token_is_mvp(self) -> None:
        """SOLEND-SOLANA A_TOKEN lending_indices → MVP (new real adapter, 2026-07-09)."""
        assert is_mvp("defi", "SOLEND-SOLANA", "A_TOKEN", "lending_indices")

    def test_solend_solana_debt_token_is_mvp(self) -> None:
        """SOLEND-SOLANA DEBT_TOKEN lending_indices → MVP."""
        assert is_mvp("defi", "SOLEND-SOLANA", "DEBT_TOKEN", "lending_indices")

    def test_previously_excluded_multichain_venue_now_mvp(self) -> None:
        """AAVE_V3-ARBITRUM was outside the pre-v13 curated (ETHEREUM-only) subset — now MVP."""
        assert is_mvp("defi", "AAVE_V3-ARBITRUM", "LENDING", "lending_indices")

    # test_drift_perpetual_perp_funding_now_mvp removed 2026-07-16 (operator
    # ruling: all Solana perp DEXes dropped except Jupiter, not integrated —
    # "no instruments no mvp nothing"). DRIFT (Solana)'s MVP_SCOPE entry no
    # longer exists; the venue itself is gone from the system. SSOT:
    # unified-trading-pm/codex/04-architecture/solana-defi-coverage.md.

    def test_mvp_venues_still_subset_of_producible_post_v17(self) -> None:
        """MVP venues are still ⊆ P post-v17. ROCKETPOOL-ETHEREUM was the pre-v17
        excluded example; it is now producible (rocket_pool.py wired into
        ``_build_defi_venues()``), so the invariant is re-pinned with a venue that
        remains pipeline: IDLE-ARBITRUM (wired class, empty per-chain registry)."""
        assert is_mvp("defi", "ROCKETPOOL-ETHEREUM", "LST", "lst_rates")
        assert not is_mvp("defi", "IDLE-ARBITRUM", "POOL", "dex_pool_state")

    def test_marginfi_solend_are_is_producible(self) -> None:
        """MARGINFI-SOLANA / SOLEND-SOLANA are phase="live" (IS-producible) post-wiring."""
        from unified_api_contracts.registry.defi_venues import DEFI_VENUE_PHASE

        assert DEFI_VENUE_PHASE["MARGINFI-SOLANA"] == "live"
        assert DEFI_VENUE_PHASE["SOLEND-SOLANA"] == "live"


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


# ---------------------------------------------------------------------------
# mdps_mvp_universe — MVP-for-MDPS == MVP-for-MDS (Concept 1).
# Identity gate: the (venue, instrument_type) set returned by the helper must
# equal the same set derived directly from MVP_SCOPE (cefi/defi) or the
# is_mvp predicate's reachable projection (tradfi, which composes the CME
# futures complex with the equity-basis carve-out).
# ---------------------------------------------------------------------------


class TestMdpsMvpUniverse:
    """``mdps_mvp_universe`` returns the (venue, instrument_type) cells MDPS
    processes — which by Concept 1 is identical to the MDS capture MVP for
    the asset_group, derived structurally from MVP_SCOPE."""

    def test_public_import_surface(self) -> None:
        """``mdps_mvp_universe`` is importable from the package root + listed in __all__."""
        import unified_api_contracts

        assert hasattr(unified_api_contracts, "mdps_mvp_universe")
        assert "mdps_mvp_universe" in unified_api_contracts.__all__

    def test_cefi_identity_with_mds_capture_mvp(self) -> None:
        """cefi: returned set equals the (venue, instrument_type) product
        declared in MVP_SCOPE['cefi'] — the SAME source MDS reads. This is
        the identity proof: no separate hand-maintained list."""
        from unified_api_contracts import MVP_SCOPE, mdps_mvp_universe
        from unified_api_contracts.canonical.crosscutting.mvp_scope import (
            CeFiMvpRule,
        )

        rule = MVP_SCOPE["cefi"]
        assert isinstance(rule, CeFiMvpRule)
        expected = frozenset((v, it) for v in rule.venues for it in rule.instrument_types)
        assert mdps_mvp_universe("cefi") == expected

    def test_defi_identity_with_mds_capture_mvp(self) -> None:
        """defi: same Cartesian-product identity."""
        from unified_api_contracts import MVP_SCOPE, mdps_mvp_universe
        from unified_api_contracts.canonical.crosscutting.mvp_scope import (
            DeFiMvpRule,
        )

        rule = MVP_SCOPE["defi"]
        assert isinstance(rule, DeFiMvpRule)
        expected = frozenset((v, it) for v in rule.venues for it in rule.instrument_types)
        assert mdps_mvp_universe("defi") == expected

    def test_tradfi_identity_includes_equity_basis_carve_out(self) -> None:
        """tradfi: CME futures complex + the equity-basis carve-out (NASDAQ/
        NYSE/ARCA/AMEX/BATS/KRX × {EQUITY, ETF}) that is_mvp's tradfi branch
        hardcodes. Identity here is with the reachable set of the predicate."""
        from unified_api_contracts import MVP_SCOPE, mdps_mvp_universe
        from unified_api_contracts.canonical.crosscutting.mvp_scope import (
            TradFiMvpRule,
        )

        rule = MVP_SCOPE["tradfi"]
        assert isinstance(rule, TradFiMvpRule)
        cme_cells = {(v, it) for v in rule.venues for it in rule.instrument_types}
        equity_cells = {(v, it) for v in ("NASDAQ", "NYSE", "ARCA", "AMEX", "BATS", "KRX") for it in ("EQUITY", "ETF")}
        expected = frozenset(cme_cells | equity_cells)
        assert mdps_mvp_universe("tradfi") == expected

    def test_cefi_contains_deribit_option_and_binance_perp(self) -> None:
        """Spot-check the cefi cells the predicate ALSO admits for at least
        one base — confirms the helper's set is the same reachable set MDS
        captures (not a stale subset)."""
        from unified_api_contracts import is_in_mvp_capture_universe, mdps_mvp_universe

        cells = mdps_mvp_universe("cefi")
        assert ("DERIBIT", "OPTION") in cells
        assert ("BINANCE-FUTURES", "PERPETUAL") in cells
        assert ("BINANCE-SPOT", "SPOT_PAIR") in cells
        assert ("COINBASE-FUTURES", "PERPETUAL") in cells
        # Each axis pair the helper returns is reachable via the capture
        # predicate for some base — the per-(venue, base) carve-outs apply
        # at the instrument grain, not at the axis-pair grain.
        assert is_in_mvp_capture_universe("DERIBIT", "BTC", "OPTION", has_perp_for_base=False)
        assert is_in_mvp_capture_universe("BINANCE-FUTURES", "BTC", "PERPETUAL", has_perp_for_base=True)

    def test_tradfi_contains_cme_and_equity_basis(self) -> None:
        """Spot-check tradfi cells — CME futures + NASDAQ equity carve-out."""
        from unified_api_contracts import mdps_mvp_universe

        cells = mdps_mvp_universe("tradfi")
        assert ("CME", "FUTURE") in cells
        assert ("CME", "OPTION") in cells
        assert ("NASDAQ", "EQUITY") in cells
        assert ("KRX", "EQUITY") in cells
        assert ("NYSE", "ETF") in cells

    def test_sports_raises_no_axis(self) -> None:
        """sports has no (venue, instrument_type) axis — raises ValueError."""
        import pytest

        from unified_api_contracts import mdps_mvp_universe

        with pytest.raises(ValueError, match="no .venue, instrument_type. axis"):
            mdps_mvp_universe("sports")

    def test_prediction_raises_no_axis(self) -> None:
        """prediction has no (venue, instrument_type) axis — raises ValueError."""
        import pytest

        from unified_api_contracts import mdps_mvp_universe

        with pytest.raises(ValueError, match="no .venue, instrument_type. axis"):
            mdps_mvp_universe("prediction")

    def test_unknown_asset_group_raises(self) -> None:
        """An asset_group not declared in MVP_SCOPE raises ValueError."""
        import pytest

        from unified_api_contracts import mdps_mvp_universe

        with pytest.raises(ValueError, match="unknown asset_group"):
            mdps_mvp_universe("not-an-asset-group")

    def test_phase2_stub_returns_empty(self) -> None:
        """Phase-2+ stubs (features/strategy/models) have no rule yet — empty set."""
        from unified_api_contracts import mdps_mvp_universe

        assert mdps_mvp_universe("features") == frozenset()
        assert mdps_mvp_universe("strategy") == frozenset()
        assert mdps_mvp_universe("models") == frozenset()

    def test_return_type_is_frozenset_of_tuples(self) -> None:
        """Return type is a frozenset of (venue, instrument_type) tuples — both strings."""
        from unified_api_contracts import mdps_mvp_universe

        result = mdps_mvp_universe("cefi")
        assert isinstance(result, frozenset)
        for cell in result:
            assert isinstance(cell, tuple)
            assert len(cell) == 2
            venue, itype = cell
            assert isinstance(venue, str) and venue == venue.upper().strip()
            assert isinstance(itype, str) and itype == itype.upper().strip()


# ---------------------------------------------------------------------------
# v15 — ``liquidations`` restored as a PERPETUAL-leg CeFi MVP data_type
# (2026-07-15, cefi_completion_program_2026_07_15.md workstream E). liquidations
# is captured on exactly 6 perp venues (732,751 captured PERPETUAL manifest rows);
# it is added to the PERPETUAL instrument_type_data_types override ONLY (NOT the
# flat set → no SPOT_PAIR over-claim; NOT FUTURE → dated-futures liq
# is negligible). The venue axis is gated by ``VENUE_DATA_TYPE_CAPABILITIES``.
# ---------------------------------------------------------------------------
class TestLiquidationsPerpetualMvpV15:
    """v15: ``liquidations`` is a PERPETUAL-leg CeFi MVP data_type."""

    # The 6 venues with a real captured liquidations feed.
    LIQ_FEED_VENUES = (
        "BINANCE-FUTURES",
        "OKX-SWAP",
        "BYBIT",
        "KRAKEN-FUTURES",
        "BITFINEX-FUTURES",
        "BITGET-FUTURES",
    )

    def test_perpetual_override_carries_liquidations(self) -> None:
        """The PERPETUAL override = flat tick set + liquidations (full replacement)."""
        rule = MVP_SCOPE["cefi"]
        assert isinstance(rule, CeFiMvpRule)
        perp = rule.instrument_type_data_types["PERPETUAL"]
        assert perp == frozenset({"trades", "book_snapshot_5", "derivative_ticker", "funding_rate", "liquidations"})

    def test_liquidations_not_in_flat_data_types(self) -> None:
        """liquidations is NOT in the flat data_types set (so SPOT_PAIR does
        NOT silently gain it)."""
        rule = MVP_SCOPE["cefi"]
        assert isinstance(rule, CeFiMvpRule)
        assert "liquidations" not in rule.data_types

    def test_liquidations_is_mvp_for_perpetual_on_feed_venues(self) -> None:
        """is_mvp True for a PERPETUAL liquidations cell on each of the 6 feed venues."""
        for venue in self.LIQ_FEED_VENUES:
            assert is_mvp("cefi", venue, "PERPETUAL", "liquidations", base_ccy="BTC"), venue

    def test_liquidations_not_mvp_for_future(self) -> None:
        """FUTURE cells do NOT carry liquidations (dated-futures liq negligible)."""
        for venue in ("BINANCE-FUTURES", "BYBIT", "KRAKEN-FUTURES"):
            assert not is_mvp("cefi", venue, "FUTURE", "liquidations", base_ccy="BTC"), venue

    def test_liquidations_not_mvp_for_spot(self) -> None:
        """SPOT_PAIR cells do NOT carry liquidations (validity excludes it too)."""
        for venue in ("BINANCE-SPOT", "COINBASE-SPOT", "UPBIT", "OKX-SPOT"):
            assert not is_mvp("cefi", venue, "SPOT_PAIR", "liquidations", base_ccy="BTC"), venue

    def test_liquidations_mvp_for_equity_perp_as_perpetual(self) -> None:
        """A crypto-venue single-stock equity perp is typed PERPETUAL (operator
        2026-07-16, no distinct EQUITY_PERP type) so it rides the PERPETUAL
        liquidations override on a feed venue — its equity base (META) is in
        CEFI_EQUITY_PERP_BASE_UNIVERSE ⊂ base_ccys."""
        assert is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "liquidations", base_ccy="META")

    def test_coinbase_futures_perpetual_stays_trades_only(self) -> None:
        """COINBASE-FUTURES venue_data_types={trades} override still wins for its
        PERPETUAL cells (no book5/derivative_ticker/liquidations over-seed)."""
        assert is_mvp("cefi", "COINBASE-FUTURES", "PERPETUAL", "trades", base_ccy="BTC")
        for dt in ("book_snapshot_5", "derivative_ticker", "liquidations"):
            assert not is_mvp("cefi", "COINBASE-FUTURES", "PERPETUAL", dt, base_ccy="BTC"), dt

    def test_itype_aware_helper_resolution(self) -> None:
        """get_mvp_data_types_for_cefi_venue_itype resolves the exact per-cell set."""
        from unified_api_contracts import get_mvp_data_types_for_cefi_venue_itype

        # PERPETUAL on a feed venue → includes liquidations.
        assert "liquidations" in get_mvp_data_types_for_cefi_venue_itype("BINANCE-FUTURES", "PERPETUAL")
        # FUTURE on the same venue → the flat set, NO liquidations.
        assert "liquidations" not in get_mvp_data_types_for_cefi_venue_itype("BINANCE-FUTURES", "FUTURE")
        # Per-venue override wins over the per-itype override for COINBASE-FUTURES.
        assert get_mvp_data_types_for_cefi_venue_itype("COINBASE-FUTURES", "PERPETUAL") == frozenset({"trades"})
        # Venue not in the MVP rule → empty frozenset.
        assert get_mvp_data_types_for_cefi_venue_itype("FAKE_VENUE_XYZ", "PERPETUAL") == frozenset()

    def test_venue_only_helper_unchanged_no_liquidations(self) -> None:
        """The venue-only (itype-agnostic) helper is byte-identical to pre-v15:
        it returns the flat set (NO liquidations) for a standard perp venue."""
        from unified_api_contracts import get_mvp_data_types_for_cefi_venue

        assert "liquidations" not in get_mvp_data_types_for_cefi_venue("BINANCE-FUTURES")

    def test_itype_aware_helper_exported_from_root(self) -> None:
        """get_mvp_data_types_for_cefi_venue_itype is importable from the package root."""
        import unified_api_contracts

        assert hasattr(unified_api_contracts, "get_mvp_data_types_for_cefi_venue_itype")
        assert "get_mvp_data_types_for_cefi_venue_itype" in unified_api_contracts.__all__
