"""Unit tests for the Citadel paper ⟷ batch ⟷ live determinism-spine contract.

Covers the Phase 0 schemas of
``plans/active/citadel_paper_batch_live_reconciliation_2026_06_19.md``:
 - RunManifest (the as-of snapshot pin) — frozen, extra-forbid, tuple fields
 - make_trade_key — determinism + UTC normalisation (the reconciliation match key)
 - TradeFillRecord — keyed per-trade fill
 - TradingMode / FillModel / ReconVerdictType / DeterminismBugClass — StrEnums
 - TradeDeviation / WeeklyReconReport — the recon report
 - PositionLedgerRow — the derived as-if-filled position view
 - the public import surface (root facade + internal)

SSOT: codex/09-strategy/operational/paper-batch-live-reconciliation.md
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts import PositionLedgerRow
from unified_api_contracts.canonical.crosscutting.ledger import AssetClass
from unified_api_contracts.internal import (
    DeterminismBugClass,
    FillModel,
    ReconVerdictType,
    RunManifest,
    TradeDeviation,
    TradeFillRecord,
    TradingMode,
    WeeklyReconReport,
    make_trade_key,
)

_W_START = datetime(2026, 6, 19, tzinfo=UTC)
_W_END = datetime(2026, 6, 26, tzinfo=UTC)


def _manifest(mode: TradingMode, fill_model: FillModel, run_id: str = "run-1") -> RunManifest:
    return RunManifest(
        run_id=run_id,
        window_start=_W_START,
        window_end=_W_END,
        mode=mode,
        client_id="SL",
        strategy_ids=("carry_funding_dispersion@binance",),
        code_shas={"strategy-service": "abc123", "unified-api-contracts": "def456"},
        market_data_days=("gs://md/day=2026-06-19", "gs://md/day=2026-06-20"),
        feature_group_versions={"perp_funding": 3},
        captured_tick_stream="gs://runs/run-1/ticks/",
        fill_model=fill_model,
        ledger_root="gs://runs/run-1/ledger/",
    )


# --------------------------------------------------------------------------- #
# RunManifest
# --------------------------------------------------------------------------- #
def test_run_manifest_instantiates() -> None:
    m = _manifest(TradingMode.PAPER, FillModel.BENCHMARK)
    assert m.mode is TradingMode.PAPER
    assert m.fill_model is FillModel.BENCHMARK
    assert m.parent_run_id is None
    assert m.feature_group_versions["perp_funding"] == 3


def test_run_manifest_is_frozen() -> None:
    m = _manifest(TradingMode.PAPER, FillModel.BENCHMARK)
    with pytest.raises(ValidationError):
        m.run_id = "mutated"  # type: ignore[misc]


def test_run_manifest_forbids_extra() -> None:
    with pytest.raises(ValidationError):
        RunManifest(
            run_id="x",
            window_start=_W_START,
            window_end=_W_END,
            mode=TradingMode.BATCH,
            client_id="SL",
            strategy_ids=(),
            code_shas={},
            market_data_days=(),
            feature_group_versions={},
            captured_tick_stream="gs://x",
            fill_model=FillModel.BENCHMARK,
            ledger_root="gs://x",
            not_a_field="boom",  # type: ignore[call-arg]
        )


def test_batch_rerun_back_references_paper() -> None:
    paper = _manifest(TradingMode.PAPER, FillModel.BENCHMARK, run_id="paper-19")
    batch = RunManifest(
        run_id="batch-of-paper-19",
        window_start=_W_START,
        window_end=_W_END,
        mode=TradingMode.BATCH,
        client_id="SL",
        strategy_ids=paper.strategy_ids,
        code_shas=paper.code_shas,
        market_data_days=paper.market_data_days,
        feature_group_versions=paper.feature_group_versions,
        captured_tick_stream=paper.captured_tick_stream,
        fill_model=FillModel.BENCHMARK,
        ledger_root="gs://runs/batch/ledger/",
        parent_run_id=paper.run_id,
    )
    # The determinism contract: a batch rerun shares code + inputs + fill model.
    assert batch.parent_run_id == paper.run_id
    assert batch.code_shas == paper.code_shas
    assert batch.captured_tick_stream == paper.captured_tick_stream
    assert batch.fill_model is paper.fill_model


# --------------------------------------------------------------------------- #
# make_trade_key
# --------------------------------------------------------------------------- #
def test_make_trade_key_is_deterministic() -> None:
    ts = datetime(2026, 6, 19, 12, 30, 0, 123456, tzinfo=UTC)
    a = make_trade_key("BINANCE:PERPETUAL:BTC-PERP", "instr-7", ts)
    b = make_trade_key("BINANCE:PERPETUAL:BTC-PERP", "instr-7", ts)
    assert a == b
    assert a == "BINANCE:PERPETUAL:BTC-PERP|instr-7|2026-06-19T12:30:00.123456+00:00"


def test_make_trade_key_naive_assumed_utc_equals_aware_utc() -> None:
    aware = datetime(2026, 6, 19, 12, 0, 0, tzinfo=UTC)
    naive = datetime(2026, 6, 19, 12, 0, 0)
    assert make_trade_key("V:T:S", "i", aware) == make_trade_key("V:T:S", "i", naive)


def test_make_trade_key_normalises_tz_offset() -> None:
    utc = datetime(2026, 6, 19, 12, 0, 0, tzinfo=UTC)
    plus2 = datetime(2026, 6, 19, 14, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    # Same instant in different zones → same key.
    assert make_trade_key("V:T:S", "i", utc) == make_trade_key("V:T:S", "i", plus2)


def test_make_trade_key_distinct_inputs_distinct_keys() -> None:
    ts = datetime(2026, 6, 19, 12, 0, 0, tzinfo=UTC)
    base = make_trade_key("V:T:S", "i", ts)
    assert make_trade_key("V:T:OTHER", "i", ts) != base
    assert make_trade_key("V:T:S", "j", ts) != base
    assert make_trade_key("V:T:S", "i", ts + timedelta(seconds=1)) != base


# --------------------------------------------------------------------------- #
# TradeFillRecord + enums
# --------------------------------------------------------------------------- #
def test_trade_fill_record_carries_key() -> None:
    ts = datetime(2026, 6, 19, 12, 0, 0, tzinfo=UTC)
    key = make_trade_key("BINANCE:PERPETUAL:ETH-PERP", "instr-1", ts)
    fill = TradeFillRecord(
        trade_key=key,
        instrument_key="BINANCE:PERPETUAL:ETH-PERP",
        strategy_instruction_id="instr-1",
        tick_timestamp=ts,
        venue="BINANCE",
        side="SELL",
        qty=Decimal("2.5"),
        fill_price=Decimal("3000.5"),
        fees_in_quote=Decimal("1.5"),
        fill_model=FillModel.BENCHMARK,
        correlation_id="corr-9",
    )
    assert fill.trade_key == key
    assert fill.client_order_id is None
    with pytest.raises(ValidationError):
        fill.qty = Decimal("3")  # type: ignore[misc]


@pytest.mark.parametrize(
    ("enum_cls", "n"),
    [(TradingMode, 3), (FillModel, 2), (ReconVerdictType, 3), (DeterminismBugClass, 4)],
)
def test_enums_are_strenums_of_expected_size(enum_cls: type, n: int) -> None:
    members = list(enum_cls)
    assert len(members) == n
    for m in members:
        assert isinstance(m.value, str)
        assert m.value == m.name or m.value.isupper()


def test_two_fill_realities_only() -> None:
    # The HARD RULE: exactly two fill realities — benchmark (batch+paper) + live.
    assert {m.value for m in FillModel} == {"BENCHMARK", "LIVE_VENUE"}


# --------------------------------------------------------------------------- #
# WeeklyReconReport
# --------------------------------------------------------------------------- #
def test_determinism_report_clean_is_deterministic() -> None:
    rep = WeeklyReconReport(
        verdict_type=ReconVerdictType.DETERMINISM,
        run_a_id="paper-19",
        run_b_id="batch-of-paper-19",
        window_start=_W_START,
        window_end=_W_END,
        total_trades_a=42,
        total_trades_b=42,
        matched=42,
        unmatched_a=0,
        unmatched_b=0,
        deviations=(),
        is_deterministic=True,
    )
    assert rep.is_deterministic
    assert rep.determinism_bug_class is DeterminismBugClass.NONE
    assert rep.unmatched_a == 0 and rep.unmatched_b == 0


def test_determinism_report_with_drift_names_bug_class() -> None:
    dev = TradeDeviation(
        trade_key="V:T:S|i|2026-06-19T12:00:00.000000+00:00",
        instrument_key="V:T:S",
        venue="V",
        side_match=True,
        qty_delta=Decimal("0"),
        fill_price_delta_bps=Decimal("12.5"),
        fees_delta=Decimal("0"),
        timing_delta_ms=0.0,
        present_in_a=True,
        present_in_b=True,
    )
    rep = WeeklyReconReport(
        verdict_type=ReconVerdictType.DETERMINISM,
        run_a_id="paper-19",
        run_b_id="batch-of-paper-19",
        window_start=_W_START,
        window_end=_W_END,
        total_trades_a=42,
        total_trades_b=42,
        matched=42,
        unmatched_a=0,
        unmatched_b=0,
        deviations=(dev,),
        is_deterministic=False,
        determinism_bug_class=DeterminismBugClass.FILL_MODEL_DRIFT,
        mean_fill_price_delta_bps=Decimal("12.5"),
        p99_fill_price_delta_bps=Decimal("12.5"),
    )
    assert not rep.is_deterministic
    assert rep.determinism_bug_class is DeterminismBugClass.FILL_MODEL_DRIFT
    assert rep.deviations[0].fill_price_delta_bps == Decimal("12.5")


def test_execution_verdict_carries_alpha_rollup() -> None:
    rep = WeeklyReconReport(
        verdict_type=ReconVerdictType.EXECUTION,
        run_a_id="live-19",
        run_b_id="paper-19",
        window_start=_W_START,
        window_end=_W_END,
        total_trades_a=40,
        total_trades_b=42,
        matched=40,
        unmatched_a=0,
        unmatched_b=2,
        deviations=(),
        is_deterministic=False,
        mean_fill_price_delta_bps=Decimal("3.2"),
        p99_fill_price_delta_bps=Decimal("18.0"),
    )
    assert rep.verdict_type is ReconVerdictType.EXECUTION
    assert rep.mean_fill_price_delta_bps == Decimal("3.2")


# --------------------------------------------------------------------------- #
# PositionLedgerRow
# --------------------------------------------------------------------------- #
def test_position_ledger_row_instantiates_and_defaults() -> None:
    row = PositionLedgerRow(
        as_of=_W_START,
        account_id="binance-SL",
        client_id="SL",
        venue="BINANCE",
        instrument_key="BINANCE:PERPETUAL:BTC-PERP",
        asset_canonical_id="BTC",
        asset_symbol="BTC",
        asset_class=AssetClass.PERP,
        share_class="BTC",
        net_qty=Decimal("1.5"),
        avg_cost=Decimal("60000"),
        mark_price=Decimal("61000"),
        quote_currency="USDT",
    )
    assert row.net_qty == Decimal("1.5")
    assert row.realized_pnl == Decimal("0")
    assert row.unrealized_pnl == Decimal("0")
    with pytest.raises(ValidationError):
        row.net_qty = Decimal("2")  # type: ignore[misc]


def test_position_ledger_row_forbids_extra() -> None:
    with pytest.raises(ValidationError):
        PositionLedgerRow(
            as_of=_W_START,
            account_id="a",
            client_id="SL",
            venue="BINANCE",
            instrument_key="k",
            asset_canonical_id="BTC",
            asset_symbol="BTC",
            asset_class=AssetClass.PERP,
            share_class="BTC",
            net_qty=Decimal("1"),
            bogus="x",  # type: ignore[call-arg]
        )


# --------------------------------------------------------------------------- #
# public import surface
# --------------------------------------------------------------------------- #
def test_public_import_surface() -> None:
    import unified_api_contracts as uac
    from unified_api_contracts import internal

    # PositionLedgerRow is a canonical/crosscutting type → exposed at the root facade.
    assert uac.PositionLedgerRow is PositionLedgerRow
    # The reconciliation contract types are internal → reached via .internal.
    assert internal.RunManifest is RunManifest
    for name in (
        "RunManifest",
        "TradeFillRecord",
        "WeeklyReconReport",
        "TradeDeviation",
        "TradingMode",
        "FillModel",
        "ReconVerdictType",
        "DeterminismBugClass",
        "make_trade_key",
    ):
        assert hasattr(internal, name), name
