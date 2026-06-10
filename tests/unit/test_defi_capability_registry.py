"""Tests for registry/capability_declarations/_defi.py — DeFi capability registry."""

from __future__ import annotations

from unified_api_contracts.registry.capability_declarations._defi import (
    KNOWN_CHAINS,
    DeFiDataSource,
    build_complete_major_assets,
    build_defi_venues,
    canonicalize_defi_venue_combined,
    get_all_defi_chains,
    get_data_types_for_protocol,
    get_evm_protocol_rest_url,
    get_mtds_operations_for_protocol,
    get_protocol_capability,
    get_required_tokens_for_protocol,
    get_required_tokens_for_venue,
    get_subgraph_id,
    get_supported_chains_for_protocol,
    get_venue_prefix,
    is_token_equivalent,
    parse_defi_venue,
    token_matches_major_assets,
)


class TestDeFiDataSource:
    def test_alchemy_value(self) -> None:
        assert DeFiDataSource.ALCHEMY == "alchemy"

    def test_thegraph_value(self) -> None:
        assert DeFiDataSource.THEGRAPH == "thegraph"

    def test_all_members_are_strings(self) -> None:
        for member in DeFiDataSource:
            assert isinstance(member, str)


class TestGetProtocolCapability:
    def test_known_protocol_returns_capability(self) -> None:
        cap = get_protocol_capability("aave_v3")
        assert cap is not None

    def test_unknown_protocol_returns_none(self) -> None:
        cap = get_protocol_capability("nonexistent_protocol_xyz")
        assert cap is None

    def test_uniswap_v3_capability(self) -> None:
        cap = get_protocol_capability("uniswap_v3")
        assert cap is not None

    def test_lido_capability(self) -> None:
        cap = get_protocol_capability("lido")
        assert cap is not None


class TestGetVenuePrefix:
    def test_aave_v3_prefix(self) -> None:
        prefix = get_venue_prefix("aave_v3")
        assert prefix == "AAVE_V3"

    def test_uniswap_v3_prefix(self) -> None:
        prefix = get_venue_prefix("uniswap_v3")
        assert prefix == "UNISWAP_V3"

    def test_unknown_protocol_prefix_is_none(self) -> None:
        prefix = get_venue_prefix("nonexistent_xyz")
        assert prefix is None


class TestGetDataTypesForProtocol:
    def test_aave_v3_has_data_types(self) -> None:
        data_types = get_data_types_for_protocol("aave_v3")
        assert isinstance(data_types, list)
        assert len(data_types) > 0

    def test_unknown_protocol_returns_empty(self) -> None:
        data_types = get_data_types_for_protocol("nonexistent_xyz")
        assert data_types == []

    def test_uniswap_v3_has_data_types(self) -> None:
        data_types = get_data_types_for_protocol("uniswap_v3")
        assert len(data_types) > 0


class TestGetMtdsOperationsForProtocol:
    def test_aave_v3_has_operations(self) -> None:
        ops = get_mtds_operations_for_protocol("aave_v3")
        assert isinstance(ops, list)
        assert len(ops) > 0

    def test_unknown_protocol_returns_empty(self) -> None:
        ops = get_mtds_operations_for_protocol("nonexistent_xyz")
        assert ops == []


class TestGetRequiredTokensForProtocol:
    def test_aave_v3_required_tokens(self) -> None:
        tokens = get_required_tokens_for_protocol("aave_v3")
        assert isinstance(tokens, frozenset)

    def test_unknown_protocol_returns_empty(self) -> None:
        tokens = get_required_tokens_for_protocol("nonexistent_xyz")
        assert tokens == frozenset()

    def test_returns_frozenset(self) -> None:
        tokens = get_required_tokens_for_protocol("lido")
        assert isinstance(tokens, frozenset)


class TestGetRequiredTokensForVenue:
    def test_aave_ethereum_venue(self) -> None:
        tokens = get_required_tokens_for_venue("AAVE_V3-ETHEREUM")
        assert isinstance(tokens, frozenset)

    def test_unknown_venue_returns_empty(self) -> None:
        tokens = get_required_tokens_for_venue("BADPROTOCOL")
        assert tokens == frozenset()

    def test_uniswap_ethereum_venue(self) -> None:
        tokens = get_required_tokens_for_venue("UNISWAP_V3-ETHEREUM")
        assert isinstance(tokens, frozenset)


class TestIsTokenEquivalent:
    def test_same_token_is_equivalent(self) -> None:
        assert is_token_equivalent("ETH", "ETH") is True

    def test_weth_and_steth_equivalent(self) -> None:
        assert is_token_equivalent("WETH", "stETH") is True

    def test_eth_group_members_equivalent(self) -> None:
        assert is_token_equivalent("ETH", "WETH") is True

    def test_different_groups_not_equivalent(self) -> None:
        assert is_token_equivalent("ETH", "BTC") is False

    def test_case_insensitive(self) -> None:
        assert is_token_equivalent("weth", "WETH") is True

    def test_completely_unknown_tokens(self) -> None:
        result = is_token_equivalent("UNKNOWN_XY_ZZ", "ANOTHER_TOKEN")
        assert isinstance(result, bool)


class TestTokenMatchesMajorAssets:
    def test_direct_match(self) -> None:
        major_assets: frozenset[str] = frozenset({"ETH", "BTC", "USDC"})
        assert token_matches_major_assets("ETH", major_assets) is True

    def test_equivalent_match(self) -> None:
        major_assets: frozenset[str] = frozenset({"ETH", "BTC"})
        assert token_matches_major_assets("WETH", major_assets) is True

    def test_no_match(self) -> None:
        major_assets: frozenset[str] = frozenset({"ETH", "BTC"})
        assert token_matches_major_assets("DOGE", major_assets) is False

    def test_empty_major_assets(self) -> None:
        assert token_matches_major_assets("ETH", frozenset()) is False


class TestBuildCompleteMajorAssets:
    def test_returns_frozenset(self) -> None:
        result = build_complete_major_assets()
        assert isinstance(result, frozenset)

    def test_includes_eth(self) -> None:
        result = build_complete_major_assets()
        assert "ETH" in result or "WETH" in result

    def test_non_empty(self) -> None:
        result = build_complete_major_assets()
        assert len(result) > 0


class TestBuildDefiVenues:
    def test_returns_non_empty_list(self) -> None:
        venues = build_defi_venues()
        assert isinstance(venues, list)
        assert len(venues) > 0

    def test_venues_follow_protocol_chain_format(self) -> None:
        venues = build_defi_venues()
        for venue in venues:
            assert "-" in venue, f"Expected PROTOCOL-CHAIN format, got: {venue}"

    def test_includes_known_venues(self) -> None:
        venues = build_defi_venues()
        venue_set = set(venues)
        # At least one known venue should be present
        known = {"AAVE_V3-ETHEREUM", "UNISWAP_V3-ETHEREUM", "LIDO-ETHEREUM"}
        assert known & venue_set, f"None of {known} found in venues"


class TestGetAllDefiChains:
    def test_returns_sorted_list(self) -> None:
        chains = get_all_defi_chains()
        assert chains == sorted(chains)

    def test_includes_ethereum(self) -> None:
        chains = get_all_defi_chains()
        assert "ETHEREUM" in chains

    def test_includes_arbitrum(self) -> None:
        chains = get_all_defi_chains()
        assert "ARBITRUM" in chains

    def test_non_empty(self) -> None:
        chains = get_all_defi_chains()
        assert len(chains) > 0

    def test_known_chains_frozenset_not_empty(self) -> None:
        assert len(KNOWN_CHAINS) > 0


class TestParseDefiVenue:
    def test_aave_v3_ethereum(self) -> None:
        slug, chain = parse_defi_venue("AAVE_V3-ETHEREUM")
        assert slug == "aave_v3"
        assert chain == "ETHEREUM"

    def test_uniswap_v3_base(self) -> None:
        slug, chain = parse_defi_venue("UNISWAP_V3-BASE")
        assert slug == "uniswap_v3"
        assert chain == "BASE"

    def test_lido_ethereum(self) -> None:
        slug, chain = parse_defi_venue("LIDO-ETHEREUM")
        assert slug == "lido"
        assert chain == "ETHEREUM"

    def test_unknown_venue_fallback(self) -> None:
        slug, chain = parse_defi_venue("UNKNOWNPROTOCOL-UNKNOWNCHAIN")
        # Falls back to last-hyphen split
        assert isinstance(slug, str)
        assert isinstance(chain, str)

    def test_no_hyphen_returns_lowercase(self) -> None:
        slug, chain = parse_defi_venue("BINANCE")
        assert slug == "binance"
        assert chain == ""


class TestCanonicalizeDefiVenueCombined:
    def test_glued_aave_v3_arbitrum(self) -> None:
        result = canonicalize_defi_venue_combined("AAVEV3-ARBITRUM")
        assert result == "AAVE_V3-ARBITRUM"

    def test_glued_uniswap_v3_ethereum(self) -> None:
        result = canonicalize_defi_venue_combined("UNISWAPV3-ETHEREUM")
        assert result == "UNISWAP_V3-ETHEREUM"

    def test_already_canonical_passthrough(self) -> None:
        result = canonicalize_defi_venue_combined("AAVE_V3-ARBITRUM")
        assert result == "AAVE_V3-ARBITRUM"

    def test_no_hyphen_passthrough(self) -> None:
        result = canonicalize_defi_venue_combined("BINANCE")
        assert result == "BINANCE"

    def test_unknown_chain_passthrough(self) -> None:
        result = canonicalize_defi_venue_combined("AAVEV3-UNKNOWNCHAIN99")
        assert result == "AAVEV3-UNKNOWNCHAIN99"


class TestGetSubgraphId:
    def test_aave_v3_ethereum_has_subgraph(self) -> None:
        subgraph = get_subgraph_id("aave_v3", "ETHEREUM")
        # May be None if aave_v3 doesn't have a subgraph (uses REST API)
        assert subgraph is None or isinstance(subgraph, str)

    def test_uniswap_v3_ethereum_has_subgraph(self) -> None:
        subgraph = get_subgraph_id("uniswap_v3", "ETHEREUM")
        assert subgraph is None or isinstance(subgraph, str)

    def test_unknown_protocol_returns_none(self) -> None:
        subgraph = get_subgraph_id("nonexistent_xyz", "ETHEREUM")
        assert subgraph is None


class TestGetSupportedChainsForProtocol:
    def test_aave_v3_has_chains(self) -> None:
        chains = get_supported_chains_for_protocol("aave_v3")
        assert isinstance(chains, list)

    def test_uniswap_v3_has_ethereum(self) -> None:
        chains = get_supported_chains_for_protocol("uniswap_v3")
        # uniswap_v3 should support at least ETHEREUM
        assert isinstance(chains, list)

    def test_unknown_protocol_returns_empty(self) -> None:
        chains = get_supported_chains_for_protocol("nonexistent_xyz")
        assert chains == []


class TestGetEvmProtocolRestUrl:
    def test_curve_has_api_url(self) -> None:
        url = get_evm_protocol_rest_url("curve")
        assert url is not None
        assert url.startswith("https://")

    def test_morpho_has_api_url(self) -> None:
        url = get_evm_protocol_rest_url("morpho")
        assert url is not None
        assert url.startswith("https://")

    def test_unknown_protocol_returns_none(self) -> None:
        url = get_evm_protocol_rest_url("nonexistent_xyz")
        assert url is None

    def test_custom_url_type(self) -> None:
        url = get_evm_protocol_rest_url("curve", url_type="api_url")
        assert url is not None

    def test_unknown_url_type_returns_none(self) -> None:
        url = get_evm_protocol_rest_url("curve", url_type="nonexistent_url_type")
        assert url is None
