"""Unit tests for
:mod:`unified_api_contracts.canonical.crosscutting.execution_fidelity`.

Covers item 001 of
``plans/active/execution_fidelity_tiers_uac_governed_2026_06_28.md``:
``execution_fidelity(asset_group, venue, instrument_type, mode)`` — returns
the maximum :class:`ExecutionFidelityTier` for the cell, source-governed
by MVP_SCOPE data_types.

The three plan-gated cases (CeFi-with-ticks vs TradFi-1m vs candle-only)
are each tested explicitly; the rest of the tests cover the override
resolution path (COINBASE per-venue, DERIBIT OPTION per-instrument_type)
and the rejected asset_groups.
"""

from __future__ import annotations

import pytest

from unified_api_contracts import (
    ExecutionFidelityTier,
    execution_fidelity,
)


class TestPublicSurface:
    def test_importable_from_package_root(self) -> None:
        import unified_api_contracts

        assert hasattr(unified_api_contracts, "execution_fidelity")
        assert hasattr(unified_api_contracts, "ExecutionFidelityTier")
        assert hasattr(unified_api_contracts, "ExecutionMode")
        assert "execution_fidelity" in unified_api_contracts.__all__
        assert "ExecutionFidelityTier" in unified_api_contracts.__all__
        assert "ExecutionMode" in unified_api_contracts.__all__

    def test_tier_enum_members(self) -> None:
        assert {t.value for t in ExecutionFidelityTier} == {
            "L2_TICK",
            "CANDLE_BOOK_COLS",
            "OHLC_BAR",
        }


# ---------------------------------------------------------------------------
# Plan-gated cases (the three cells explicitly named in the gate)
# ---------------------------------------------------------------------------


class TestPlanGatedCases:
    """The plan acceptance gate names three cells; each gets its own test
    so a regression on any one is immediately visible."""

    def test_cefi_with_ticks_resolves_l2_tick(self) -> None:
        """CeFi-with-ticks (Binance perp): flat data_types include
        ``book_snapshot_5`` → L2 book walk."""
        assert execution_fidelity("cefi", "BINANCE-FUTURES", "PERPETUAL", "batch") == ExecutionFidelityTier.L2_TICK

    def test_tradfi_1m_resolves_ohlc_bar(self) -> None:
        """TradFi 1m: CME FUTURE MVP data_types = ``{ohlcv_1m}`` only →
        plain OHLC bar fill (the e2e 1m determinism spine)."""
        assert execution_fidelity("tradfi", "CME", "FUTURE", "batch") == ExecutionFidelityTier.OHLC_BAR

    def test_candle_only_with_book_cols_resolves_candle_book_cols(self) -> None:
        """Candle-only instrument with book columns: a DeFi POOL cell has
        ``dex_pool_state + dex_pool_swaps`` in scope; the Plan-1 candle
        carries pool-reserve columns → CANDLE_BOOK_COLS matcher."""
        assert (
            execution_fidelity("defi", "UNISWAP_V3-ETHEREUM", "POOL", "batch") == ExecutionFidelityTier.CANDLE_BOOK_COLS
        )


# ---------------------------------------------------------------------------
# Per-venue override path — COINBASE trades-only
# ---------------------------------------------------------------------------


class TestCoinbaseTradesOnlyOverride:
    """The CeFi rule's ``venue_data_types`` override strips
    ``book_snapshot_5`` from COINBASE — so even on a cell that would
    otherwise carry book ticks, the resolution must land on OHLC_BAR
    (no book → no L2 walk; the matcher uses bar-fill)."""

    def test_coinbase_spot_resolves_ohlc_bar(self) -> None:
        assert execution_fidelity("cefi", "COINBASE-SPOT", "SPOT_PAIR", "batch") == ExecutionFidelityTier.OHLC_BAR

    def test_coinbase_futures_resolves_ohlc_bar(self) -> None:
        assert execution_fidelity("cefi", "COINBASE-FUTURES", "PERPETUAL", "batch") == ExecutionFidelityTier.OHLC_BAR


# ---------------------------------------------------------------------------
# Per-instrument_type override path — Deribit OPTION → options_chain only
# ---------------------------------------------------------------------------


class TestDeribitOptionOverride:
    """The CeFi rule's ``instrument_type_data_types`` override drops
    OPTION to ``{options_chain}`` only — no trades + no book ticks. The
    matching engine has no L2 walk over options_chain marks → OHLC_BAR."""

    def test_deribit_option_resolves_ohlc_bar(self) -> None:
        assert execution_fidelity("cefi", "DERIBIT", "OPTION", "batch") == ExecutionFidelityTier.OHLC_BAR

    def test_deribit_perpetual_still_resolves_l2_tick(self) -> None:
        """The OPTION override does NOT cascade to DERIBIT PERPETUAL —
        the perp / future legs at Deribit keep ``book_snapshot_5``."""
        assert execution_fidelity("cefi", "DERIBIT", "PERPETUAL", "batch") == ExecutionFidelityTier.L2_TICK


# ---------------------------------------------------------------------------
# Per-AG breadth — make sure each AG resolves on a representative cell
# ---------------------------------------------------------------------------


class TestPerAgBreadth:
    @pytest.mark.parametrize(
        ("venue", "instrument_type"),
        [
            ("BINANCE-SPOT", "SPOT_PAIR"),
            ("BINANCE-FUTURES", "PERPETUAL"),
            ("BYBIT", "PERPETUAL"),
            ("OKX-SWAP", "PERPETUAL"),
            ("HYPERLIQUID", "PERPETUAL"),
        ],
    )
    def test_cefi_standard_venues_resolve_l2_tick(self, venue: str, instrument_type: str) -> None:
        """Every standard CeFi venue (no per-venue override) keeps the flat
        data_types set, which includes ``book_snapshot_5`` → L2_TICK."""
        assert execution_fidelity("cefi", venue, instrument_type, "batch") == ExecutionFidelityTier.L2_TICK

    @pytest.mark.parametrize(
        ("venue", "instrument_type"),
        [
            ("UNISWAP_V3-ETHEREUM", "POOL"),
            ("CURVE-ETHEREUM", "POOL"),
            # ORCA-SOLANA / RAYDIUM-SOLANA are POOL, not DEX_POOL — verified
            # 2026-07-09 against live adapter code (orca.py / raydium.py both
            # build `instrument_type=InstrumentType.POOL`); DEX_POOL was
            # aspirational-only in the pre-v13 DeFiMvpRule comment (no adapter
            # ever emitted it) and was dropped from the v13 "everything we
            # capture" instrument_types set. `_AMM_INSTRUMENT_TYPES` in
            # execution_fidelity.py still accepts DEX_POOL too (harmless
            # forward-compat), but POOL is the real, MVP-declared value.
            ("ORCA-SOLANA", "POOL"),
            ("RAYDIUM-SOLANA", "POOL"),
        ],
    )
    def test_defi_amm_pools_resolve_candle_book_cols(self, venue: str, instrument_type: str) -> None:
        """DeFi AMM POOL cells carry pool state + swaps → the candle's
        pool-reserve columns drive the matcher → CANDLE_BOOK_COLS."""
        assert execution_fidelity("defi", venue, instrument_type, "batch") == ExecutionFidelityTier.CANDLE_BOOK_COLS

    @pytest.mark.parametrize(
        ("venue", "instrument_type"),
        [
            ("LIDO-ETHEREUM", "LST"),
            ("AAVE_V3-ETHEREUM", "LENDING"),
            ("COMPOUND_V3-ETHEREUM", "LENDING"),
        ],
    )
    def test_defi_reference_rate_cells_resolve_ohlc_bar(self, venue: str, instrument_type: str) -> None:
        """LST / LENDING are reference-rate cells (``lst_rates`` /
        ``lending_indices``) — no AMM book; the matcher falls back to
        bar-fill on the rate time-series."""
        assert execution_fidelity("defi", venue, instrument_type, "batch") == ExecutionFidelityTier.OHLC_BAR

    @pytest.mark.parametrize(
        ("venue", "instrument_type"),
        [
            ("CME", "FUTURE"),
            ("CME", "OPTION"),
            ("NASDAQ", "EQUITY"),
            ("NYSE", "ETF"),
            ("KRX", "EQUITY"),
        ],
    )
    def test_tradfi_cells_resolve_ohlc_bar(self, venue: str, instrument_type: str) -> None:
        """TradFi MVP is ``ohlcv_1m`` only across the CME futures complex
        AND the equity-basis carve-out cells — every TradFi cell is
        OHLC_BAR."""
        assert execution_fidelity("tradfi", venue, instrument_type, "batch") == ExecutionFidelityTier.OHLC_BAR


# ---------------------------------------------------------------------------
# Mode parameter
# ---------------------------------------------------------------------------


class TestModeParameter:
    """Today both modes resolve to the same tier (per-cell data_types are
    identical live vs. batch). The test pins that invariant so a future
    per-mode divergence is a deliberate, visible change."""

    @pytest.mark.parametrize(
        ("asset_group", "venue", "instrument_type"),
        [
            ("cefi", "BINANCE-FUTURES", "PERPETUAL"),
            ("cefi", "COINBASE-SPOT", "SPOT_PAIR"),
            ("tradfi", "CME", "FUTURE"),
            ("defi", "UNISWAP_V3-ETHEREUM", "POOL"),
        ],
    )
    def test_live_equals_batch_for_today_mvp(self, asset_group: str, venue: str, instrument_type: str) -> None:
        assert execution_fidelity(asset_group, venue, instrument_type, "live") == execution_fidelity(
            asset_group, venue, instrument_type, "batch"
        )


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestErrorPaths:
    @pytest.mark.parametrize("asset_group", ["sports", "prediction"])
    def test_non_executable_asset_groups_raise(self, asset_group: str) -> None:
        """sports has no execution model; prediction's CLOB execution is
        out of scope for item 001 — both raise loudly so a caller cannot
        silently fall through to OHLC_BAR for a non-executable cell."""
        with pytest.raises(ValueError, match="not in the executable-instrument scope"):
            execution_fidelity(asset_group, "ANY", "ANY", "batch")

    def test_unknown_asset_group_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown asset_group"):
            execution_fidelity("not-a-group", "ANY", "ANY", "batch")

    def test_phase_2_stub_asset_group_raises(self) -> None:
        """``features`` / ``strategy`` / ``models`` are declared in MVP_SCOPE
        as stubs (no executable rule) — must raise so the matching engine
        cannot accidentally route a stub AG to a real tier."""
        with pytest.raises(ValueError, match="no executable-instrument rule"):
            execution_fidelity("features", "ANY", "ANY", "batch")

    def test_cell_not_in_mvp_raises(self) -> None:
        """A venue not declared in the cefi rule (e.g. MEXC) raises rather
        than silently degrading — the execution path should not route to a
        venue that is not even in the capture universe."""
        with pytest.raises(ValueError, match="is not an MVP cell"):
            execution_fidelity("cefi", "MEXC", "PERPETUAL", "batch")

    def test_instrument_type_not_in_mvp_raises(self) -> None:
        """A venue/instrument_type that is in the AG vocabulary but not the
        rule's declared product (e.g. DeFi venue with EQUITY) raises."""
        with pytest.raises(ValueError, match="is not an MVP cell"):
            execution_fidelity("defi", "UNISWAP_V3-ETHEREUM", "EQUITY", "batch")


# ---------------------------------------------------------------------------
# Decision-table determinism
# ---------------------------------------------------------------------------


class TestDecisionTableDeterminism:
    """The tier is a function of (asset_group, venue, instrument_type, mode)
    alone — no global state. Same inputs → same output across calls."""

    @pytest.mark.parametrize(
        ("asset_group", "venue", "instrument_type", "expected"),
        [
            ("cefi", "BINANCE-FUTURES", "PERPETUAL", ExecutionFidelityTier.L2_TICK),
            ("cefi", "COINBASE-SPOT", "SPOT_PAIR", ExecutionFidelityTier.OHLC_BAR),
            ("cefi", "DERIBIT", "OPTION", ExecutionFidelityTier.OHLC_BAR),
            ("tradfi", "CME", "FUTURE", ExecutionFidelityTier.OHLC_BAR),
            ("defi", "UNISWAP_V3-ETHEREUM", "POOL", ExecutionFidelityTier.CANDLE_BOOK_COLS),
            ("defi", "LIDO-ETHEREUM", "LST", ExecutionFidelityTier.OHLC_BAR),
        ],
    )
    def test_decision_table_row(
        self,
        asset_group: str,
        venue: str,
        instrument_type: str,
        expected: ExecutionFidelityTier,
    ) -> None:
        first = execution_fidelity(asset_group, venue, instrument_type, "batch")
        second = execution_fidelity(asset_group, venue, instrument_type, "batch")
        assert first == expected
        assert first == second
