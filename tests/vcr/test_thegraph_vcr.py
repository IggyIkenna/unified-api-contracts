"""Replay VCR cassette for thegraph — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

from unified_api_contracts.unified_api_contracts_external.thegraph.schemas import (
    SubgraphPool,
    TheGraphResponse,
)

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent
    / "unified_api_contracts"
    / "unified_api_contracts_external"
    / "thegraph"
    / "mocks"
)

_POOLS_QUERY = (
    "{ pools(first: 2, orderBy: totalValueLockedUSD, orderDirection: desc)"
    " { id token0 { id symbol decimals } token1 { id symbol decimals }"
    " reserve0 reserve1 reserveUSD token0Price token1Price } }"
)


def test_thegraph_pools_query_cassette() -> None:
    """Replay VCR cassette for thegraph Uniswap V2 pools query — no live network."""
    cassette_path = CASSETTE_DIR / "pools_query.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post(
            "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2",
            json={"query": _POOLS_QUERY},
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data


def test_thegraph_response_schema_valid() -> None:
    """TheGraphResponse schema validates pools query response from cassette."""
    cassette_path = CASSETTE_DIR / "pools_query.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post(
            "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2",
            json={"query": _POOLS_QUERY},
        )
        data = response.json()
        validated = TheGraphResponse.model_validate(data)
        assert validated.data is not None
        assert "pools" in validated.data
        assert validated.errors is None


def test_thegraph_pool_fields_present() -> None:
    """Pool entries have id, token0, token1, and reserve fields."""
    cassette_path = CASSETTE_DIR / "pools_query.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post(
            "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2",
            json={"query": _POOLS_QUERY},
        )
        data = response.json()
        pools = data["data"]["pools"]
        assert isinstance(pools, list) and len(pools) > 0
        pool = pools[0]
        for field in ("id", "token0", "token1", "reserve0", "reserve1"):
            assert field in pool, f"Missing pool field: {field}"
        validated = SubgraphPool.model_validate(pool)
        assert validated.id is not None


def test_thegraph_token_structure() -> None:
    """Token entries have id, symbol, and decimals fields."""
    cassette_path = CASSETTE_DIR / "pools_query.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post(
            "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2",
            json={"query": _POOLS_QUERY},
        )
        data = response.json()
        pool = data["data"]["pools"][0]
        token0 = pool["token0"]
        assert "id" in token0 and "symbol" in token0 and "decimals" in token0
        assert token0["symbol"] in ("WETH", "USDT", "USDC", "WBTC", "DAI")
