"""Dual-form DeFi pool identity converter tests (canonical ↔ glued-pair).

Plan: defi_instrument_catalogue_and_capture_pipeline_2026_06_23 (operator
Refinement 1 — keep BOTH forms per pool + a bidirectional converter as the SSOT).
"""

from __future__ import annotations

import pytest

from unified_api_contracts import (
    DefiPoolIdentity,
    build_pool_identity,
    glued_venue_prefix,
    parse_glued_pool_id,
    split_glued_venue_chain,
)


class TestGluedVenuePrefix:
    def test_preserves_version_underscore_and_uppercases_chain(self) -> None:
        assert glued_venue_prefix("UNISWAP_V3", "ARBITRUM") == "UNISWAP_V3-ARBITRUM"

    def test_idempotent_on_already_canonical_protocol(self) -> None:
        assert glued_venue_prefix("AERODROME_V3", "base") == "AERODROME_V3-BASE"

    def test_protocol_without_version_token(self) -> None:
        assert glued_venue_prefix("CURVE", "ETHEREUM") == "CURVE-ETHEREUM"

    def test_glued_venue_passed_as_venue_is_split(self) -> None:
        # Defensive: a caller that passes the LEGACY no-underscore glued venue with
        # empty chain -- self-heals to the with-underscore canonical form.
        assert glued_venue_prefix("UNISWAPV3-ARBITRUM", "") == "UNISWAP_V3-ARBITRUM"


class TestSplitGluedVenueChain:
    def test_inserts_version_underscore_and_uppercases_chain(self) -> None:
        assert split_glued_venue_chain("UNISWAPV3-ARBITRUM") == ("UNISWAP_V3", "ARBITRUM")

    def test_already_canonical_protocol_is_idempotent(self) -> None:
        assert split_glued_venue_chain("UNISWAP_V3-ETHEREUM") == ("UNISWAP_V3", "ETHEREUM")

    def test_bare_venue_no_chain(self) -> None:
        assert split_glued_venue_chain("PANCAKESWAPV3") == ("PANCAKESWAP_V3", "")

    def test_aerodrome(self) -> None:
        assert split_glued_venue_chain("AERODROMEV3-BASE") == ("AERODROME_V3", "BASE")


class TestBuildPoolIdentity:
    def test_canonical_id_is_lowercased_pool_address(self) -> None:
        pid = build_pool_identity(
            venue="UNISWAP_V3",
            chain="ARBITRUM",
            pool_address="0x88E6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
            base_asset="AAVE",
            quote_asset="USDC",
            fee=100,
        )
        assert pid.canonical_instrument_id == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
        assert pid.venue == "UNISWAP_V3"
        assert pid.chain == "ARBITRUM"

    def test_glued_pair_id_carries_pair_and_fee(self) -> None:
        pid = build_pool_identity(
            venue="UNISWAP_V3",
            chain="ARBITRUM",
            pool_address="0xf9188aff",
            base_asset="AAVE",
            quote_asset="USDC",
            fee=100,
        )
        assert pid.glued_pair_id == "UNISWAP_V3-ARBITRUM:POOL:AAVE-USDC:100"

    def test_glued_venue_input_is_split(self) -> None:
        pid = build_pool_identity(
            venue="UNISWAPV3-POLYGON",
            chain="",
            pool_address="0xABC",
            base_asset="COMP",
            quote_asset="USDC",
            fee="10000",
        )
        assert pid.venue == "UNISWAP_V3"
        assert pid.chain == "POLYGON"
        assert pid.glued_pair_id == "UNISWAP_V3-POLYGON:POOL:COMP-USDC:10000"

    def test_explicit_chain_wins_over_derived(self) -> None:
        pid = build_pool_identity(
            venue="UNISWAPV3-ETHEREUM",
            chain="ARBITRUM",
            pool_address="0xABC",
        )
        assert pid.chain == "ARBITRUM"

    def test_glued_pair_falls_back_to_address_when_pair_unknown(self) -> None:
        pid = build_pool_identity(venue="CURVE", chain="ETHEREUM", pool_address="0xDEADbeef")
        assert pid.glued_pair_id == "CURVE-ETHEREUM:POOL:0xdeadbeef"

    def test_none_fee_is_blank(self) -> None:
        pid = build_pool_identity(
            venue="UNISWAP_V3", chain="BASE", pool_address="0x1", base_asset="WETH", quote_asset="DAI", fee=None
        )
        assert pid.glued_pair_id == "UNISWAP_V3-BASE:POOL:WETH-DAI"


class TestParseGluedPoolId:
    def test_parses_pair_and_fee(self) -> None:
        pid = parse_glued_pool_id("UNISWAPV3-ARBITRUM:POOL:AAVE-USDC:100")
        assert pid is not None
        assert pid.venue == "UNISWAP_V3"
        assert pid.chain == "ARBITRUM"
        assert pid.base_asset == "AAVE"
        assert pid.quote_asset == "USDC"
        assert pid.fee == "100"
        # The address is NOT recoverable from the pair-form glued id.
        assert pid.pool_address == ""

    def test_recovers_address_from_address_as_symbol_form(self) -> None:
        pid = parse_glued_pool_id("UNISWAP_V3-ETH:POOL:0xF9188AFF")
        assert pid is not None
        assert pid.pool_address == "0xf9188aff"
        assert pid.canonical_instrument_id == "0xf9188aff"

    def test_returns_none_on_non_pool_string(self) -> None:
        assert parse_glued_pool_id("0x88e6a0c2") is None
        assert parse_glued_pool_id("BINANCE-SPOT:PERP:BTC") is None

    def test_no_fee_segment(self) -> None:
        pid = parse_glued_pool_id("AERODROMEV3-BASE:POOL:WETH-USDC")
        assert pid is not None
        assert pid.fee == ""
        assert pid.base_asset == "WETH"
        assert pid.quote_asset == "USDC"


class TestRoundTrip:
    @pytest.mark.parametrize(
        ("venue", "chain", "pool_address", "base", "quote", "fee"),
        [
            ("UNISWAP_V3", "ARBITRUM", "0x88e6a0c2", "AAVE", "USDC", "100"),
            ("PANCAKESWAP_V3", "BSC", "0xabc123", "CAKE", "BNB", "2500"),
            ("AERODROME_V3", "BASE", "0xdef456", "WETH", "USDC", "3000"),
        ],
    )
    def test_build_then_parse_pair_form_round_trips(
        self, venue: str, chain: str, pool_address: str, base: str, quote: str, fee: str
    ) -> None:
        built = build_pool_identity(
            venue=venue, chain=chain, pool_address=pool_address, base_asset=base, quote_asset=quote, fee=fee
        )
        reparsed = parse_glued_pool_id(built.glued_pair_id)
        assert reparsed is not None
        # venue/chain/pair/fee survive the round-trip (address is re-resolved by the caller from the store).
        assert reparsed.venue == venue
        assert reparsed.chain == chain
        assert reparsed.base_asset == base
        assert reparsed.quote_asset == quote
        assert reparsed.fee == fee

    def test_canonical_id_is_stable(self) -> None:
        pid = build_pool_identity(
            venue="UNISWAP_V3", chain="ETHEREUM", pool_address="0xABCDEF", base_asset="WETH", quote_asset="DAI"
        )
        # Reconstructing from venue+chain+address gives the identical canonical id.
        assert (
            pid.canonical_instrument_id
            == DefiPoolIdentity(venue="UNISWAP_V3", chain="ETHEREUM", pool_address="0xabcdef").canonical_instrument_id
        )
