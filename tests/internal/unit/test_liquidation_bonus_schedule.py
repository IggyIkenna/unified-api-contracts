"""Tests for G2.9 gap #4 — LiquidationBonusSchedule."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal.architecture_v2.liquidation_bonus_schedule import (
    CONSUMER_CALL_SITES,
    LIQUIDATION_BONUS_SCHEDULE,
    LiquidationBonusEntry,
    LiquidationBonusNotFoundError,
    LiquidationProtocol,
    _validate_registry_invariants,
    bonuses_for_protocol,
    liquidation_bonus_for,
)


class TestRegistryShape:
    def test_registry_not_empty(self) -> None:
        assert len(LIQUIDATION_BONUS_SCHEDULE) >= 8

    def test_all_keys_unique(self) -> None:
        keys = [(e.protocol, e.chain, e.collateral_token, e.debt_token) for e in LIQUIDATION_BONUS_SCHEDULE]
        assert len(keys) == len(set(keys))


class TestContent:
    def test_aave_v3_wbtc_ethereum(self) -> None:
        entry = liquidation_bonus_for(
            LiquidationProtocol.AAVE_V3,
            "ETHEREUM",
            "WBTC",
        )
        assert entry.liquidation_bonus_bps == 700
        assert entry.close_factor == 0.5

    def test_aave_v3_wbtc_arbitrum_differs_from_mainnet(self) -> None:
        mainnet = liquidation_bonus_for(
            LiquidationProtocol.AAVE_V3,
            "ETHEREUM",
            "WBTC",
        )
        arbitrum = liquidation_bonus_for(
            LiquidationProtocol.AAVE_V3,
            "ARBITRUM",
            "WBTC",
        )
        assert mainnet.liquidation_bonus_bps != arbitrum.liquidation_bonus_bps

    def test_compound_v3_close_factor_100pct(self) -> None:
        entry = liquidation_bonus_for(
            LiquidationProtocol.COMPOUND_V3,
            "ETHEREUM",
            "WETH",
            "USDC",
        )
        assert entry.close_factor == 1.0

    def test_kamino_on_solana(self) -> None:
        entry = liquidation_bonus_for(
            LiquidationProtocol.KAMINO,
            "SOLANA",
            "SOL",
        )
        assert entry.protocol is LiquidationProtocol.KAMINO

    def test_bonuses_for_aave_v3(self) -> None:
        entries = bonuses_for_protocol(LiquidationProtocol.AAVE_V3)
        chains = {e.chain for e in entries}
        assert "ETHEREUM" in chains
        assert "ARBITRUM" in chains


class TestDebtTokenMatching:
    def test_exact_debt_match_preferred(self) -> None:
        # Compound V3 WETH collateral has explicit USDC debt row.
        entry = liquidation_bonus_for(
            LiquidationProtocol.COMPOUND_V3,
            "ETHEREUM",
            "WETH",
            "USDC",
        )
        assert entry.debt_token == "USDC"

    def test_wildcard_fallback(self) -> None:
        # Aave WBTC row has debt_token=None (any debt).
        entry = liquidation_bonus_for(
            LiquidationProtocol.AAVE_V3,
            "ETHEREUM",
            "WBTC",
            "DAI",
        )
        assert entry.debt_token is None

    def test_missing_collateral_raises(self) -> None:
        with pytest.raises(LiquidationBonusNotFoundError):
            liquidation_bonus_for(
                LiquidationProtocol.AAVE_V3,
                "ETHEREUM",
                "MADE_UP_TOKEN",
            )

    def test_missing_protocol_chain_raises(self) -> None:
        with pytest.raises(LiquidationBonusNotFoundError):
            liquidation_bonus_for(
                LiquidationProtocol.KAMINO,
                "ETHEREUM",
                "SOL",
            )


class TestInvariants:
    def test_duplicate_key_rejected(self) -> None:
        bad = (
            LiquidationBonusEntry(
                protocol=LiquidationProtocol.AAVE_V3,
                chain="X",
                collateral_token="T",
                liquidation_bonus_bps=500,
                close_factor=0.5,
                source_url="https://example.com/1",
            ),
            LiquidationBonusEntry(
                protocol=LiquidationProtocol.AAVE_V3,
                chain="X",
                collateral_token="T",
                liquidation_bonus_bps=600,
                close_factor=0.5,
                source_url="https://example.com/2",
            ),
        )
        with pytest.raises(ValueError, match="duplicate"):
            _validate_registry_invariants(bad)

    def test_empty_source_url_rejected(self) -> None:
        bad = (
            LiquidationBonusEntry(
                protocol=LiquidationProtocol.AAVE_V3,
                chain="X",
                collateral_token="T",
                liquidation_bonus_bps=500,
                close_factor=0.5,
                source_url="",
            ),
        )
        with pytest.raises(ValueError, match="source_url"):
            _validate_registry_invariants(bad)

    def test_bonus_out_of_range_rejected_by_pydantic(self) -> None:
        with pytest.raises(ValidationError):
            LiquidationBonusEntry(
                protocol=LiquidationProtocol.AAVE_V3,
                chain="X",
                collateral_token="T",
                liquidation_bonus_bps=10_000,  # > 5000 cap
                close_factor=0.5,
                source_url="https://example.com",
            )

    def test_close_factor_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LiquidationBonusEntry(
                protocol=LiquidationProtocol.AAVE_V3,
                chain="X",
                collateral_token="T",
                liquidation_bonus_bps=500,
                close_factor=0.0,
                source_url="https://example.com",
            )


class TestConsumerReferences:
    def test_consumer_call_sites_non_empty(self) -> None:
        assert len(CONSUMER_CALL_SITES) >= 1
