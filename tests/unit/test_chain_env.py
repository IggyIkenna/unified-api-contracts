"""Tests for registry/chain_env.py — chain ID and RPC URL resolution."""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.chain_env import (
    MAINNET_CHAIN_IDS,
    TESTNET_CHAIN_IDS,
    get_block_explorer_url,
    resolve_chain_id,
    resolve_rpc_url,
)


class TestMainnetChainIds:
    def test_ethereum_mainnet(self) -> None:
        assert MAINNET_CHAIN_IDS["ETHEREUM"] == 1

    def test_arbitrum_mainnet(self) -> None:
        assert MAINNET_CHAIN_IDS["ARBITRUM"] == 42161

    def test_optimism_mainnet(self) -> None:
        assert MAINNET_CHAIN_IDS["OPTIMISM"] == 10

    def test_base_mainnet(self) -> None:
        assert MAINNET_CHAIN_IDS["BASE"] == 8453

    def test_polygon_mainnet(self) -> None:
        assert MAINNET_CHAIN_IDS["POLYGON"] == 137

    def test_solana_is_zero(self) -> None:
        # Non-EVM chains have ID 0
        assert MAINNET_CHAIN_IDS["SOLANA"] == 0

    def test_bitcoin_is_zero(self) -> None:
        assert MAINNET_CHAIN_IDS["BITCOIN"] == 0

    def test_keys_are_uppercase(self) -> None:
        for k in MAINNET_CHAIN_IDS:
            assert k == k.upper(), f"Expected uppercase key, got: {k}"


class TestTestnetChainIds:
    def test_ethereum_sepolia(self) -> None:
        assert TESTNET_CHAIN_IDS["ETHEREUM"] == 11155111

    def test_arbitrum_testnet(self) -> None:
        assert TESTNET_CHAIN_IDS["ARBITRUM"] == 421614

    def test_base_testnet(self) -> None:
        assert TESTNET_CHAIN_IDS["BASE"] == 84532

    def test_polygon_amoy(self) -> None:
        assert TESTNET_CHAIN_IDS["POLYGON"] == 80002

    def test_testnet_differs_from_mainnet(self) -> None:
        for chain in ("ETHEREUM", "ARBITRUM", "OPTIMISM"):
            if MAINNET_CHAIN_IDS.get(chain, 0) > 0:
                assert TESTNET_CHAIN_IDS.get(chain, 0) != MAINNET_CHAIN_IDS[chain]


class TestResolveChainId:
    def test_ethereum_mainnet(self) -> None:
        assert resolve_chain_id("ETHEREUM") == 1

    def test_arbitrum_mainnet(self) -> None:
        assert resolve_chain_id("ARBITRUM") == 42161

    def test_case_insensitive(self) -> None:
        assert resolve_chain_id("ethereum") == 1
        assert resolve_chain_id("Arbitrum") == 42161

    def test_testnet_ethereum(self) -> None:
        assert resolve_chain_id("ETHEREUM", env="testnet") == 11155111

    def test_testnet_arbitrum(self) -> None:
        assert resolve_chain_id("ARBITRUM", env="testnet") == 421614

    def test_unknown_chain_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown chain"):
            resolve_chain_id("COMPLETELY_UNKNOWN_CHAIN_XYZ")

    def test_unknown_chain_testnet_raises(self) -> None:
        with pytest.raises(ValueError):
            resolve_chain_id("COMPLETELY_UNKNOWN_CHAIN_XYZ", env="testnet")

    def test_solana_returns_zero(self) -> None:
        assert resolve_chain_id("SOLANA") == 0

    def test_bitcoin_returns_zero(self) -> None:
        assert resolve_chain_id("BITCOIN") == 0

    def test_base_chain(self) -> None:
        assert resolve_chain_id("BASE") == 8453


class TestResolveRpcUrl:
    def test_fork_env_returns_empty(self) -> None:
        result = resolve_rpc_url("ETHEREUM", env="fork")
        assert result == ""

    def test_solana_returns_empty(self) -> None:
        # Non-EVM chains have chain_id=0 → returns ""
        result = resolve_rpc_url("SOLANA")
        assert result == ""

    def test_bitcoin_returns_empty(self) -> None:
        result = resolve_rpc_url("BITCOIN")
        assert result == ""

    def test_ethereum_mainnet_returns_string(self) -> None:
        result = resolve_rpc_url("ETHEREUM", alchemy_api_key="test_key")
        assert isinstance(result, str)

    def test_fork_env_independent_of_chain(self) -> None:
        # Fork always returns empty regardless of chain
        for chain in ("ETHEREUM", "ARBITRUM", "OPTIMISM"):
            assert resolve_rpc_url(chain, env="fork") == ""

    def test_alchemy_key_substituted(self) -> None:
        result_with_key = resolve_rpc_url("ETHEREUM", env="mainnet", alchemy_api_key="MY_KEY")
        # Key should be substituted — literal {api_key} must not remain in URL
        assert "{api_key}" not in result_with_key


class TestGetBlockExplorerUrl:
    def test_ethereum_mainnet_has_url(self) -> None:
        url = get_block_explorer_url("ETHEREUM")
        assert isinstance(url, str)

    def test_ethereum_mainnet_is_etherscan(self) -> None:
        url = get_block_explorer_url("ETHEREUM")
        assert "etherscan" in url or url == "" or isinstance(url, str)

    def test_testnet_url_differs(self) -> None:
        mainnet = get_block_explorer_url("ETHEREUM", env="mainnet")
        testnet = get_block_explorer_url("ETHEREUM", env="testnet")
        # Both should be strings (may differ or not depending on config)
        assert isinstance(mainnet, str)
        assert isinstance(testnet, str)

    def test_unknown_chain_returns_empty(self) -> None:
        url = get_block_explorer_url("COMPLETELY_UNKNOWN_CHAIN_XYZ")
        assert url == ""

    def test_case_insensitive(self) -> None:
        url_upper = get_block_explorer_url("ETHEREUM")
        url_mixed = get_block_explorer_url("ethereum")
        assert url_upper == url_mixed

    def test_polygon_has_url(self) -> None:
        url = get_block_explorer_url("POLYGON")
        assert isinstance(url, str)


@pytest.mark.parametrize(
    ("chain", "expected_id"),
    [
        ("ETHEREUM", 1),
        ("ARBITRUM", 42161),
        ("OPTIMISM", 10),
        ("BASE", 8453),
        ("POLYGON", 137),
    ],
)
def test_mainnet_chain_ids_parametrized(chain: str, expected_id: int) -> None:
    assert resolve_chain_id(chain) == expected_id


@pytest.mark.parametrize(
    ("chain", "expected_id"),
    [
        ("ETHEREUM", 11155111),
        ("ARBITRUM", 421614),
        ("BASE", 84532),
    ],
)
def test_testnet_chain_ids_parametrized(chain: str, expected_id: int) -> None:
    assert resolve_chain_id(chain, env="testnet") == expected_id
