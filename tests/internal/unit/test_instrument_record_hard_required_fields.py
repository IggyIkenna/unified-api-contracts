"""Tests for InstrumentRecord model_validator per-asset-group hard-required fields.

Covers:
- CeFi SPOT_PAIR / PERPETUAL: base_asset + quote_asset non-empty
- DeFi on-chain types: pool_address OR base_asset_contract_address non-empty
- DeFi on-chain: base_asset_decimals non-null for all DEFI_ONCHAIN types (Phase A)
- DeFi POOL: quote_asset_decimals non-null (Phase A)
- EVENT_CONTRACT: expiry non-null
- FUTURE: expiry non-null (tradfi_master Q1 gate 2026-05-13)
- OPTION: expiry non-null (tradfi_master Q2 gate 2026-05-13)

Per hard_schema_enforcement_2026_05_08 Phase 1 +
hard_schema_phase1_field_flip_migration_2026_05_19 Phase A.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from unified_api_contracts.internal.reference.instrument import InstrumentRecord, InstrumentType

_FUTURE_EXPIRY = datetime(2026, 12, 19, 21, 0, 0, tzinfo=UTC)
_DUMMY_ADDR = "0xBcca60bB61934080951369a648Fb03DF4F96263C"


# ---------------------------------------------------------------------------
# CeFi SPOT_PAIR + PERPETUAL rules
# ---------------------------------------------------------------------------


class TestCeFiPairRules:
    def test_spot_pair_requires_base_asset(self) -> None:
        with pytest.raises(ValueError, match="base_asset"):
            InstrumentRecord(
                instrument_key="BINANCE:SPOT_PAIR:USDC",
                venue="BINANCE",
                instrument_type=InstrumentType.SPOT_PAIR,
                base_asset="",
                quote_asset="USDT",
            )

    def test_spot_pair_requires_quote_asset(self) -> None:
        with pytest.raises(ValueError, match="quote_asset"):
            InstrumentRecord(
                instrument_key="BINANCE:SPOT_PAIR:BTC",
                venue="BINANCE",
                instrument_type=InstrumentType.SPOT_PAIR,
                base_asset="BTC",
                quote_asset="",
            )

    def test_spot_pair_with_both_passes(self) -> None:
        rec = InstrumentRecord(
            instrument_key="BINANCE:SPOT_PAIR:BTCUSDT",
            venue="BINANCE",
            instrument_type=InstrumentType.SPOT_PAIR,
            base_asset="BTC",
            quote_asset="USDT",
        )
        assert rec.base_asset == "BTC"

    def test_perpetual_requires_base_asset(self) -> None:
        with pytest.raises(ValueError, match="base_asset"):
            InstrumentRecord(
                instrument_key="BINANCE:PERPETUAL:ETHUSDT",
                venue="BINANCE",
                instrument_type=InstrumentType.PERPETUAL,
                base_asset="",
                quote_asset="USDT",
            )

    def test_perpetual_with_both_passes(self) -> None:
        rec = InstrumentRecord(
            instrument_key="BINANCE:PERPETUAL:ETHUSDT",
            venue="BINANCE",
            instrument_type=InstrumentType.PERPETUAL,
            base_asset="ETH",
            quote_asset="USDT",
        )
        assert rec.quote_asset == "USDT"


# ---------------------------------------------------------------------------
# DeFi on-chain rules
# ---------------------------------------------------------------------------


class TestDeFiOnchainRules:
    def test_pool_without_identifier_fails(self) -> None:
        with pytest.raises(ValueError, match="on-chain identifier"):
            InstrumentRecord(
                instrument_key="UNISWAPV3-ETHEREUM:POOL:WETH-USDC",
                venue="UNISWAPV3-ETHEREUM",
                instrument_type=InstrumentType.POOL,
            )

    def test_pool_with_pool_address_passes(self) -> None:
        rec = InstrumentRecord(
            instrument_key="UNISWAPV3-ETHEREUM:POOL:WETH-USDC",
            venue="UNISWAPV3-ETHEREUM",
            instrument_type=InstrumentType.POOL,
            pool_address=_DUMMY_ADDR,
            base_asset_decimals=18,
            quote_asset_decimals=6,
        )
        assert rec.pool_address == _DUMMY_ADDR

    def test_lending_with_base_contract_address_passes(self) -> None:
        rec = InstrumentRecord(
            instrument_key="AAVEV3-ETHEREUM:LENDING:USDC",
            venue="AAVEV3-ETHEREUM",
            instrument_type=InstrumentType.LENDING,
            base_asset_contract_address=_DUMMY_ADDR,
            base_asset_decimals=6,
        )
        assert rec.base_asset_contract_address == _DUMMY_ADDR


# ---------------------------------------------------------------------------
# DeFi decimals rules (Phase A — hard_schema_phase1_field_flip_migration_2026_05_19)
# ---------------------------------------------------------------------------


class TestDeFiDecimalsRules:
    """Rule 6: base_asset_decimals non-null for all DEFI_ONCHAIN types.
    Rule 7: quote_asset_decimals non-null for POOL type only.
    """

    def test_pool_without_base_decimals_fails(self) -> None:
        with pytest.raises(ValueError, match="base_asset_decimals"):
            InstrumentRecord(
                instrument_key="UNISWAPV3-ETHEREUM:POOL:WETH-USDC",
                venue="UNISWAPV3-ETHEREUM",
                instrument_type=InstrumentType.POOL,
                pool_address=_DUMMY_ADDR,
                base_asset_decimals=None,
                quote_asset_decimals=6,
            )

    def test_lending_without_base_decimals_fails(self) -> None:
        with pytest.raises(ValueError, match="base_asset_decimals"):
            InstrumentRecord(
                instrument_key="AAVEV3-ETHEREUM:LENDING:USDC",
                venue="AAVEV3-ETHEREUM",
                instrument_type=InstrumentType.LENDING,
                base_asset_contract_address=_DUMMY_ADDR,
                base_asset_decimals=None,
            )

    def test_lst_without_base_decimals_fails(self) -> None:
        with pytest.raises(ValueError, match="base_asset_decimals"):
            InstrumentRecord(
                instrument_key="LIDO-ETHEREUM:LST:STETH",
                venue="LIDO-ETHEREUM",
                instrument_type=InstrumentType.LST,
                base_asset_contract_address=_DUMMY_ADDR,
                base_asset_decimals=None,
            )

    def test_pool_without_quote_decimals_fails(self) -> None:
        with pytest.raises(ValueError, match="quote_asset_decimals"):
            InstrumentRecord(
                instrument_key="UNISWAPV3-ETHEREUM:POOL:WETH-USDC",
                venue="UNISWAPV3-ETHEREUM",
                instrument_type=InstrumentType.POOL,
                pool_address=_DUMMY_ADDR,
                base_asset_decimals=18,
                quote_asset_decimals=None,
            )

    def test_pool_with_both_decimals_passes(self) -> None:
        rec = InstrumentRecord(
            instrument_key="UNISWAPV3-ETHEREUM:POOL:WETH-USDC",
            venue="UNISWAPV3-ETHEREUM",
            instrument_type=InstrumentType.POOL,
            pool_address=_DUMMY_ADDR,
            base_asset_decimals=18,
            quote_asset_decimals=6,
        )
        assert rec.base_asset_decimals == 18
        assert rec.quote_asset_decimals == 6

    def test_lending_without_quote_decimals_passes(self) -> None:
        """LENDING is single-asset — quote_asset_decimals legitimately None."""
        rec = InstrumentRecord(
            instrument_key="AAVEV3-ETHEREUM:LENDING:USDC",
            venue="AAVEV3-ETHEREUM",
            instrument_type=InstrumentType.LENDING,
            base_asset_contract_address=_DUMMY_ADDR,
            base_asset_decimals=6,
            quote_asset_decimals=None,
        )
        assert rec.base_asset_decimals == 6
        assert rec.quote_asset_decimals is None

    def test_staking_without_quote_decimals_passes(self) -> None:
        """STAKING is single-asset — quote_asset_decimals legitimately None."""
        rec = InstrumentRecord(
            instrument_key="LIDO-ETHEREUM:STAKING:ETH",
            venue="LIDO-ETHEREUM",
            instrument_type=InstrumentType.STAKING,
            base_asset_contract_address=_DUMMY_ADDR,
            base_asset_decimals=18,
            quote_asset_decimals=None,
        )
        assert rec.base_asset_decimals == 18

    def test_spot_asset_without_quote_decimals_passes(self) -> None:
        """SPOT_ASSET is single-asset — quote_asset_decimals legitimately None."""
        rec = InstrumentRecord(
            instrument_key="SOLANA:SPOT_ASSET:SOL",
            venue="SOLANA",
            instrument_type=InstrumentType.SPOT_ASSET,
            base_asset_contract_address=_DUMMY_ADDR,
            base_asset_decimals=9,
            quote_asset_decimals=None,
        )
        assert rec.base_asset_decimals == 9

    def test_error_message_cites_phase_a_plan(self) -> None:
        with pytest.raises(ValueError, match="hard_schema_phase1_field_flip_migration_2026_05_19"):
            InstrumentRecord(
                instrument_key="UNISWAPV3-ETHEREUM:POOL:WETH-USDC",
                venue="UNISWAPV3-ETHEREUM",
                instrument_type=InstrumentType.POOL,
                pool_address=_DUMMY_ADDR,
                base_asset_decimals=None,
            )


# ---------------------------------------------------------------------------
# EVENT_CONTRACT rule
# ---------------------------------------------------------------------------


class TestEventContractRule:
    def test_event_contract_requires_expiry(self) -> None:
        with pytest.raises(ValueError, match="expiry"):
            InstrumentRecord(
                instrument_key="POLYMARKET:EVENT_CONTRACT:US-ELECTION-2026",
                venue="POLYMARKET",
                instrument_type=InstrumentType.EVENT_CONTRACT,
                expiry=None,
            )

    def test_event_contract_with_expiry_passes(self) -> None:
        rec = InstrumentRecord(
            instrument_key="POLYMARKET:EVENT_CONTRACT:US-ELECTION-2026",
            venue="POLYMARKET",
            instrument_type=InstrumentType.EVENT_CONTRACT,
            expiry=_FUTURE_EXPIRY,
        )
        assert rec.expiry == _FUTURE_EXPIRY


# ---------------------------------------------------------------------------
# FUTURE rule (tradfi_master Q1 gate 2026-05-13)
# ---------------------------------------------------------------------------


class TestFutureRule:
    def test_future_requires_expiry(self) -> None:
        with pytest.raises(ValueError, match="expiry"):
            InstrumentRecord(
                instrument_key="CME:FUTURE:ESH26",
                venue="CME",
                instrument_type=InstrumentType.FUTURE,
                base_asset="ES",
                expiry=None,
            )

    def test_future_with_expiry_passes(self) -> None:
        rec = InstrumentRecord(
            instrument_key="CME:FUTURE:ESH26",
            venue="CME",
            instrument_type=InstrumentType.FUTURE,
            base_asset="ES",
            expiry=_FUTURE_EXPIRY,
        )
        assert rec.expiry == _FUTURE_EXPIRY

    def test_future_error_message_mentions_plan(self) -> None:
        with pytest.raises(ValueError, match="hard_schema_enforcement_2026_05_08"):
            InstrumentRecord(
                instrument_key="CME:FUTURE:NQH26",
                venue="CME",
                instrument_type=InstrumentType.FUTURE,
                base_asset="NQ",
                expiry=None,
            )


# ---------------------------------------------------------------------------
# OPTION rule (tradfi_master Q2 gate 2026-05-13)
# ---------------------------------------------------------------------------


class TestOptionRule:
    def test_option_requires_expiry(self) -> None:
        with pytest.raises(ValueError, match="expiry"):
            InstrumentRecord(
                instrument_key="DERIBIT:OPTION:BTC-25DEC26-100000-C",
                venue="DERIBIT",
                instrument_type=InstrumentType.OPTION,
                base_asset="BTC",
                expiry=None,
            )

    def test_option_with_expiry_passes(self) -> None:
        rec = InstrumentRecord(
            instrument_key="DERIBIT:OPTION:BTC-25DEC26-100000-C",
            venue="DERIBIT",
            instrument_type=InstrumentType.OPTION,
            base_asset="BTC",
            expiry=_FUTURE_EXPIRY,
        )
        assert rec.expiry == _FUTURE_EXPIRY

    def test_option_error_message_mentions_plan(self) -> None:
        with pytest.raises(ValueError, match="hard_schema_enforcement_2026_05_08"):
            InstrumentRecord(
                instrument_key="CME:OPTION:SPX-25DEC26-5000-C",
                venue="CME",
                instrument_type=InstrumentType.OPTION,
                base_asset="SPX",
                expiry=None,
            )
