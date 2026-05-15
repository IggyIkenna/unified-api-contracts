"""Tests for PAPER_EXECUTION_TARGETS registry and get_paper_target helper."""

from __future__ import annotations

from unified_api_contracts.internal import PAPER_EXECUTION_TARGETS, get_paper_target
from unified_api_contracts.internal.modes import ExecutionTarget


class TestPaperExecutionTargets:
    def test_registry_not_empty(self) -> None:
        assert len(PAPER_EXECUTION_TARGETS) > 0

    def test_evm_chains_map_to_fork(self) -> None:
        for chain in ("ethereum", "arbitrum", "base", "optimism", "polygon"):
            assert PAPER_EXECUTION_TARGETS[chain] == ExecutionTarget.FORK

    def test_solana_maps_to_testnet(self) -> None:
        assert PAPER_EXECUTION_TARGETS["solana"] == ExecutionTarget.TESTNET

    def test_cefi_perp_venues_map_to_testnet(self) -> None:
        for venue in ("DERIBIT", "BINANCE", "BYBIT", "OKX", "HYPERLIQUID"):
            assert PAPER_EXECUTION_TARGETS[venue] == ExecutionTarget.TESTNET, f"{venue} should be TESTNET"

    def test_sports_venues_map_to_simulation(self) -> None:
        for venue in ("BETFAIR", "MATCHBOOK"):
            assert PAPER_EXECUTION_TARGETS[venue] == ExecutionTarget.SIMULATION, f"{venue} should be SIMULATION"

    def test_prediction_venues_map_to_simulation(self) -> None:
        for venue in ("POLYMARKET", "KALSHI"):
            assert PAPER_EXECUTION_TARGETS[venue] == ExecutionTarget.SIMULATION, f"{venue} should be SIMULATION"


class TestGetPaperTarget:
    def test_known_evm_chain(self) -> None:
        assert get_paper_target("ethereum") == ExecutionTarget.FORK

    def test_known_cefi_venue(self) -> None:
        assert get_paper_target("DERIBIT") == ExecutionTarget.TESTNET

    def test_unknown_key_returns_simulation(self) -> None:
        assert get_paper_target("UNKNOWN_VENUE_XYZ") == ExecutionTarget.SIMULATION

    def test_solana(self) -> None:
        assert get_paper_target("solana") == ExecutionTarget.TESTNET
