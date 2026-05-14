"""Tests for multi-chain DeFi reserve params dispatch (P1B — 2026-05-15).

Verifies that:
- Each per-chain Aave V3 reserve dict has >= 3 reserves (sanity check
  against accidental empty additions).
- ``get_reserve_params(asset, chain=...)`` resolves to the right dict.
- Spark + Radiant explicit-protocol helpers route correctly.
- The legacy default (``chain="ETHEREUM"``) still hits the Aave V3
  Ethereum dict (backwards compatibility).
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.defi_reserve_params import (
    AAVE_V3_ARBITRUM_RESERVES,
    AAVE_V3_AVALANCHE_RESERVES,
    AAVE_V3_BASE_RESERVES,
    AAVE_V3_BSC_RESERVES,
    AAVE_V3_ETHEREUM_RESERVES,
    AAVE_V3_LINEA_RESERVES,
    AAVE_V3_OPTIMISM_RESERVES,
    AAVE_V3_POLYGON_RESERVES,
    AAVE_V3_SCROLL_RESERVES,
    AAVE_V3_ZKSYNC_RESERVES,
    RADIANT_ARBITRUM_RESERVES,
    RADIANT_BSC_RESERVES,
    SPARK_ETHEREUM_RESERVES,
    UnknownChainError,
    get_aave_reserve_params,
    get_radiant_reserve_params,
    get_reserve_params,
    get_spark_reserve_params,
)

# Each per-chain Aave V3 dict + minimum count it must satisfy.
_AAVE_V3_CHAIN_DICTS_MIN_COUNT: list[tuple[str, dict[str, object], int]] = [
    ("ARBITRUM", AAVE_V3_ARBITRUM_RESERVES, 3),
    ("OPTIMISM", AAVE_V3_OPTIMISM_RESERVES, 3),
    ("BASE", AAVE_V3_BASE_RESERVES, 3),
    ("AVALANCHE", AAVE_V3_AVALANCHE_RESERVES, 3),
    ("POLYGON", AAVE_V3_POLYGON_RESERVES, 3),
    ("BSC", AAVE_V3_BSC_RESERVES, 3),
    ("LINEA", AAVE_V3_LINEA_RESERVES, 3),
    ("SCROLL", AAVE_V3_SCROLL_RESERVES, 3),
    ("ZKSYNC", AAVE_V3_ZKSYNC_RESERVES, 3),
]


@pytest.mark.parametrize(("chain_name", "chain_dict", "min_count"), _AAVE_V3_CHAIN_DICTS_MIN_COUNT)
def test_aave_v3_chain_dict_has_min_reserves(chain_name: str, chain_dict: dict[str, object], min_count: int) -> None:
    """Each per-chain Aave V3 reserve dict must carry at least the documented floor."""
    assert len(chain_dict) >= min_count, (
        f"AAVE_V3_{chain_name}_RESERVES has {len(chain_dict)} reserves, expected >= {min_count}"
    )


def test_spark_ethereum_has_min_reserves() -> None:
    """Spark Ethereum reserve dict must carry at least 3 reserves."""
    assert len(SPARK_ETHEREUM_RESERVES) >= 3


def test_radiant_arbitrum_has_min_reserves() -> None:
    """Radiant Arbitrum reserve dict must carry at least 3 reserves."""
    assert len(RADIANT_ARBITRUM_RESERVES) >= 3


def test_radiant_bsc_has_min_reserves() -> None:
    """Radiant BSC reserve dict must carry at least 3 reserves."""
    assert len(RADIANT_BSC_RESERVES) >= 3


def test_get_reserve_params_defaults_to_ethereum() -> None:
    """Default ``chain`` argument must still resolve to Aave V3 Ethereum."""
    eth_usdc = get_reserve_params("USDC")
    assert eth_usdc is not None
    assert eth_usdc is AAVE_V3_ETHEREUM_RESERVES["USDC"]


def test_get_reserve_params_arbitrum_usdc() -> None:
    """Chain dispatch resolves Arbitrum USDC."""
    arb_usdc = get_reserve_params(asset="USDC", chain="ARBITRUM")
    assert arb_usdc is not None
    assert arb_usdc is AAVE_V3_ARBITRUM_RESERVES["USDC"]


def test_get_reserve_params_unknown_chain_raises() -> None:
    """Unknown chain name raises UnknownChainError (not silently returns None)."""
    with pytest.raises(UnknownChainError, match="GNOSIS"):
        get_reserve_params(asset="USDC", chain="GNOSIS")


def test_get_aave_reserve_params_explicit_chain() -> None:
    """Explicit-chain helper mirrors get_reserve_params."""
    op_weth = get_aave_reserve_params("WETH", chain="OPTIMISM")
    assert op_weth is not None
    assert op_weth is AAVE_V3_OPTIMISM_RESERVES["WETH"]


def test_get_spark_reserve_params_dai() -> None:
    """Spark Ethereum DAI lookup is non-None."""
    dai = get_spark_reserve_params("DAI")
    assert dai is not None
    assert dai is SPARK_ETHEREUM_RESERVES["DAI"]


def test_get_spark_reserve_params_unknown_asset_returns_none() -> None:
    """Unknown asset returns None."""
    assert get_spark_reserve_params("DOGECOIN") is None


def test_get_radiant_reserve_params_arbitrum_usdc() -> None:
    """Radiant Arbitrum USDC lookup is non-None."""
    rad_usdc = get_radiant_reserve_params("USDC", chain="ARBITRUM")
    assert rad_usdc is not None
    assert rad_usdc is RADIANT_ARBITRUM_RESERVES["USDC"]


def test_get_radiant_reserve_params_bsc_wbnb() -> None:
    """Radiant BSC WBNB lookup is non-None."""
    rad_wbnb = get_radiant_reserve_params("WBNB", chain="BSC")
    assert rad_wbnb is not None
    assert rad_wbnb is RADIANT_BSC_RESERVES["WBNB"]


def test_get_radiant_reserve_params_unknown_chain_returns_none() -> None:
    """Unknown Radiant chain returns None (not deployed)."""
    assert get_radiant_reserve_params("USDC", chain="ETHEREUM") is None
