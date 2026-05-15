"""Tests for ExecutionTarget, ExecutionTrigger enums and decompose() helper.

Covers pvl-p17a: migration from deprecated TestingStage to canonical 3-tuple.
"""

from __future__ import annotations

from unified_api_contracts.internal import (
    ExecutionTarget,
    ExecutionTrigger,
    OperationalMode,
    TestingStage,
    decompose,
)


class TestExecutionTargetEnum:
    def test_all_values_exist(self) -> None:
        assert ExecutionTarget.MAINNET == "mainnet"
        assert ExecutionTarget.TESTNET == "testnet"
        assert ExecutionTarget.FORK == "fork"
        assert ExecutionTarget.SIMULATION == "simulation"

    def test_str_roundtrip(self) -> None:
        for member in ExecutionTarget:
            assert ExecutionTarget(member.value) == member


class TestExecutionTriggerEnum:
    def test_all_values_exist(self) -> None:
        assert ExecutionTrigger.AUTOMATED == "automated"
        assert ExecutionTrigger.MANUAL_OPERATOR == "manual_operator"

    def test_str_roundtrip(self) -> None:
        for member in ExecutionTrigger:
            assert ExecutionTrigger(member.value) == member


class TestDecompose:
    def test_mock_maps_to_backtest_simulation(self) -> None:
        mode, target, trigger = decompose(TestingStage.MOCK)
        assert mode == OperationalMode.BACKTEST
        assert target == ExecutionTarget.SIMULATION
        assert trigger == ExecutionTrigger.AUTOMATED

    def test_historical_maps_to_backtest_simulation(self) -> None:
        mode, target, trigger = decompose(TestingStage.HISTORICAL)
        assert mode == OperationalMode.BACKTEST
        assert target == ExecutionTarget.SIMULATION
        assert trigger == ExecutionTrigger.AUTOMATED

    def test_live_mock_maps_to_paper_simulation(self) -> None:
        mode, target, trigger = decompose(TestingStage.LIVE_MOCK)
        assert mode == OperationalMode.PAPER
        assert target == ExecutionTarget.SIMULATION
        assert trigger == ExecutionTrigger.AUTOMATED

    def test_live_testnet_maps_to_paper_testnet(self) -> None:
        mode, target, trigger = decompose(TestingStage.LIVE_TESTNET)
        assert mode == OperationalMode.PAPER
        assert target == ExecutionTarget.TESTNET
        assert trigger == ExecutionTrigger.AUTOMATED

    def test_staging_maps_to_paper_fork(self) -> None:
        mode, target, trigger = decompose(TestingStage.STAGING)
        assert mode == OperationalMode.PAPER
        assert target == ExecutionTarget.FORK
        assert trigger == ExecutionTrigger.AUTOMATED

    def test_live_real_maps_to_live_mainnet(self) -> None:
        mode, target, trigger = decompose(TestingStage.LIVE_REAL)
        assert mode == OperationalMode.LIVE
        assert target == ExecutionTarget.MAINNET
        assert trigger == ExecutionTrigger.AUTOMATED

    def test_all_stages_covered(self) -> None:
        for stage in TestingStage:
            result = decompose(stage)
            assert len(result) == 3
            assert isinstance(result[0], OperationalMode)
            assert isinstance(result[1], ExecutionTarget)
            assert isinstance(result[2], ExecutionTrigger)
