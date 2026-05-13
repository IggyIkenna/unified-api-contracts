"""Multi-chain DeFi reserve params dispatch tests — P0 chain-routing fix + multi-chain expansion.

Verifies the P0 silent-correctness fix from
defi_recursive_borrow_archetypes_2026_05_10.md:
- get_reserve_params(asset, chain=...) dispatches to the correct per-chain dict
- get_emode_category(asset, chain=...) dispatches per-chain
- get_emode_params(collateral, debt, chain=...) dispatches per-chain
- get_compound_reserve_params(asset, chain=..., market=...) dispatches per-chain x market
- UnknownChainError raised for unknown chains (NOT silently returning None)
- Backwards compat: existing callers with no chain arg default to ETHEREUM
- Cross-chain CBETH semantics: ETH+BASE have it, ARBITRUM does NOT
- ReserveParams frozen dataclass (immutability)
- Every primary chain has at least USDC + WETH
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from unified_api_contracts.registry.defi_reserve_params import (
    AAVE_V3_ARBITRUM_RESERVES,
    AAVE_V3_BASE_RESERVES,
    AAVE_V3_ETHEREUM_RESERVES,
    COMPOUND_V3_ARBITRUM_USDC_RESERVES,
    COMPOUND_V3_ARBITRUM_USDCE_RESERVES,
    COMPOUND_V3_BASE_USDC_RESERVES,
    COMPOUND_V3_ETHEREUM_RESERVES,
    UnknownChainError,
    get_compound_reserve_params,
    get_emode_category,
    get_emode_params,
    get_reserve_params,
)

# ---------------------------------------------------------------------------
# 1. get_reserve_params per-chain dispatch
# ---------------------------------------------------------------------------


def test_get_reserve_params_ethereum_usdc() -> None:
    """ETHEREUM USDC dispatch returns Ethereum-specific params."""
    params = get_reserve_params("USDC", chain="ETHEREUM")
    assert params is not None
    assert params is AAVE_V3_ETHEREUM_RESERVES["USDC"]
    # Ethereum USDC LTV is 0.80 (different from Arbitrum 0.75)
    assert params.max_ltv == Decimal("0.80")


def test_get_reserve_params_arbitrum_usdc() -> None:
    """ARBITRUM USDC dispatch returns Arbitrum-specific params (NOT Ethereum)."""
    arb_params = get_reserve_params("USDC", chain="ARBITRUM")
    eth_params = get_reserve_params("USDC", chain="ETHEREUM")
    assert arb_params is not None
    assert arb_params is AAVE_V3_ARBITRUM_RESERVES["USDC"]
    # Critical: Arbitrum params must differ from Ethereum params
    assert arb_params is not eth_params


def test_get_reserve_params_base_usdc() -> None:
    """BASE USDC dispatch returns Base-specific params."""
    params = get_reserve_params("USDC", chain="BASE")
    assert params is not None
    assert params is AAVE_V3_BASE_RESERVES["USDC"]


def test_get_reserve_params_ethereum_weth() -> None:
    """ETHEREUM WETH returns correct params."""
    params = get_reserve_params("WETH", chain="ETHEREUM")
    assert params is not None
    assert params.max_ltv == Decimal("0.825")


def test_get_reserve_params_arbitrum_weth() -> None:
    """ARBITRUM WETH returns Arbitrum-specific params."""
    params = get_reserve_params("WETH", chain="ARBITRUM")
    assert params is not None
    assert params is AAVE_V3_ARBITRUM_RESERVES["WETH"]


def test_get_reserve_params_base_weth() -> None:
    """BASE WETH returns Base-specific params."""
    params = get_reserve_params("WETH", chain="BASE")
    assert params is not None
    assert params is AAVE_V3_BASE_RESERVES["WETH"]


# ---------------------------------------------------------------------------
# 2. UnknownChainError raised for unknown chains
# ---------------------------------------------------------------------------


def test_get_reserve_params_unknown_chain_raises_unknown_chain_error() -> None:
    """get_reserve_params with unknown chain raises UnknownChainError."""
    with pytest.raises(UnknownChainError, match="GNOSIS"):
        get_reserve_params("USDC", chain="GNOSIS")


def test_get_emode_category_unknown_chain_raises_unknown_chain_error() -> None:
    """get_emode_category with unknown chain raises UnknownChainError."""
    with pytest.raises(UnknownChainError, match="SOLANA"):
        get_emode_category("WETH", chain="SOLANA")


def test_get_emode_params_unknown_chain_raises_unknown_chain_error() -> None:
    """get_emode_params with unknown chain raises UnknownChainError."""
    with pytest.raises(UnknownChainError, match="FANTOM"):
        get_emode_params("WSTETH", "WETH", chain="FANTOM")


def test_get_compound_reserve_params_unknown_chain_raises_unknown_chain_error() -> None:
    """get_compound_reserve_params with unknown chain raises UnknownChainError."""
    with pytest.raises(UnknownChainError, match="POLYGON"):
        get_compound_reserve_params("WETH", chain="POLYGON", market="USDC")


# ---------------------------------------------------------------------------
# 3. get_reserve_params for unknown asset on known chain returns None
# ---------------------------------------------------------------------------


def test_get_reserve_params_unknown_asset_on_known_chain_returns_none() -> None:
    """Unknown asset on a known chain returns None (not error)."""
    assert get_reserve_params("FAKECOIN", chain="ARBITRUM") is None


def test_get_reserve_params_cbeth_not_on_arbitrum() -> None:
    """CBETH is NOT on Arbitrum — returns None."""
    assert get_reserve_params("CBETH", chain="ARBITRUM") is None


def test_get_reserve_params_cbeth_on_base() -> None:
    """CBETH IS on Base — returns non-None params."""
    params = get_reserve_params("CBETH", chain="BASE")
    assert params is not None
    assert params is AAVE_V3_BASE_RESERVES["CBETH"]


def test_get_reserve_params_cbeth_on_ethereum() -> None:
    """CBETH IS on Ethereum — returns non-None params."""
    params = get_reserve_params("CBETH", chain="ETHEREUM")
    assert params is not None
    assert params is AAVE_V3_ETHEREUM_RESERVES["CBETH"]


# ---------------------------------------------------------------------------
# 4. Backwards compat — default chain="ETHEREUM"
# ---------------------------------------------------------------------------


def test_get_reserve_params_no_chain_arg_defaults_to_ethereum() -> None:
    """Existing callers with no chain arg receive Ethereum params (backwards compat)."""
    no_chain = get_reserve_params("WETH")
    explicit_eth = get_reserve_params("WETH", chain="ETHEREUM")
    assert no_chain is explicit_eth


def test_get_emode_category_no_chain_arg_defaults_to_ethereum() -> None:
    """get_emode_category with no chain defaults to ETHEREUM."""
    no_chain = get_emode_category("WSTETH")
    explicit_eth = get_emode_category("WSTETH", chain="ETHEREUM")
    assert no_chain is explicit_eth


# ---------------------------------------------------------------------------
# 5. E-Mode chain dispatch
# ---------------------------------------------------------------------------


def test_get_emode_category_cbeth_on_ethereum_is_eth_correlated() -> None:
    """CBETH on Ethereum is in ETH_CORRELATED E-Mode."""
    cat = get_emode_category("CBETH", chain="ETHEREUM")
    assert cat is not None
    assert cat.label == "ETH_CORRELATED"


def test_get_emode_category_cbeth_not_on_arbitrum() -> None:
    """CBETH is NOT on Arbitrum — E-Mode category returns None."""
    assert get_emode_category("CBETH", chain="ARBITRUM") is None


def test_get_emode_category_cbeth_on_base_is_eth_correlated() -> None:
    """CBETH on Base is in ETH_CORRELATED E-Mode."""
    cat = get_emode_category("CBETH", chain="BASE")
    assert cat is not None
    assert cat.label == "ETH_CORRELATED"


def test_get_emode_params_wsteth_weth_arbitrum_returns_eth_correlated() -> None:
    """wstETH/WETH pair on Arbitrum resolves to ETH_CORRELATED E-Mode."""
    emode = get_emode_params("WSTETH", "WETH", chain="ARBITRUM")
    assert emode is not None
    assert emode.label == "ETH_CORRELATED"
    # Arbitrum E-Mode LTV should be 0.93 (same as Ethereum per design)
    assert emode.max_ltv == Decimal("0.93")


def test_get_emode_params_cross_category_returns_none() -> None:
    """WEETH (ETH-correlated) + USDC (stablecoin) have no shared E-Mode category."""
    assert get_emode_params("WEETH", "USDC", chain="ETHEREUM") is None


# ---------------------------------------------------------------------------
# 6. Compound V3 multi-chain + multi-market dispatch
# ---------------------------------------------------------------------------


def test_get_compound_reserve_params_ethereum_usdc_weth() -> None:
    """Compound V3 Ethereum USDC market WETH lookup returns correct params."""
    params = get_compound_reserve_params("WETH", chain="ETHEREUM", market="USDC")
    assert params is not None
    assert params is COMPOUND_V3_ETHEREUM_RESERVES["WETH"]


def test_get_compound_reserve_params_arbitrum_usdce_weth() -> None:
    """Compound V3 Arbitrum USDC.E market WETH lookup."""
    params = get_compound_reserve_params("WETH", chain="ARBITRUM", market="USDC.E")
    assert params is not None
    assert params is COMPOUND_V3_ARBITRUM_USDCE_RESERVES["WETH"]


def test_get_compound_reserve_params_arbitrum_usdc_weth() -> None:
    """Compound V3 Arbitrum USDC (native) market WETH lookup."""
    params = get_compound_reserve_params("WETH", chain="ARBITRUM", market="USDC")
    assert params is not None
    assert params is COMPOUND_V3_ARBITRUM_USDC_RESERVES["WETH"]


def test_get_compound_reserve_params_base_usdc_weth() -> None:
    """Compound V3 Base USDC market WETH lookup."""
    params = get_compound_reserve_params("WETH", chain="BASE", market="USDC")
    assert params is not None
    assert params is COMPOUND_V3_BASE_USDC_RESERVES["WETH"]


def test_get_compound_reserve_params_unknown_market_returns_none() -> None:
    """Unknown market on known chain returns None (not error)."""
    assert get_compound_reserve_params("WETH", chain="ARBITRUM", market="ETH") is None


def test_get_compound_reserve_params_no_args_defaults_ethereum_usdc() -> None:
    """Backwards compat: no chain/market args defaults to ETHEREUM/USDC."""
    params = get_compound_reserve_params("WETH")
    assert params is not None
    assert params is COMPOUND_V3_ETHEREUM_RESERVES["WETH"]


# ---------------------------------------------------------------------------
# 7. Every primary chain has USDC + WETH
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("chain", ["ETHEREUM", "ARBITRUM", "BASE"])
def test_primary_chain_has_usdc(chain: str) -> None:
    """Every primary Family-1-in-scope chain has USDC reserve."""
    params = get_reserve_params("USDC", chain=chain)
    assert params is not None, f"{chain} missing USDC reserve"


@pytest.mark.parametrize("chain", ["ETHEREUM", "ARBITRUM", "BASE"])
def test_primary_chain_has_weth(chain: str) -> None:
    """Every primary Family-1-in-scope chain has WETH reserve."""
    params = get_reserve_params("WETH", chain=chain)
    assert params is not None, f"{chain} missing WETH reserve"


# ---------------------------------------------------------------------------
# 8. Arbitrum reserve completeness — 11 reserves per spec
# ---------------------------------------------------------------------------


def test_arbitrum_reserves_has_arb() -> None:
    """Arbitrum reserves include ARB (Arbitrum governance token)."""
    params = get_reserve_params("ARB", chain="ARBITRUM")
    assert params is not None


def test_arbitrum_reserves_has_link() -> None:
    """Arbitrum reserves include LINK (Chainlink)."""
    params = get_reserve_params("LINK", chain="ARBITRUM")
    assert params is not None


def test_arbitrum_reserves_count() -> None:
    """Arbitrum reserves contain at least 11 assets per spec."""
    assert len(AAVE_V3_ARBITRUM_RESERVES) >= 11


# ---------------------------------------------------------------------------
# 9. Base reserve completeness — 7 reserves per spec
# ---------------------------------------------------------------------------


def test_base_reserves_has_weeth() -> None:
    """Base reserves include WEETH (ether.fi wrapped ETH, via native bridge)."""
    params = get_reserve_params("WEETH", chain="BASE")
    assert params is not None


def test_base_reserves_has_cbbtc() -> None:
    """Base reserves include CBBTC (Coinbase Wrapped Bitcoin)."""
    params = get_reserve_params("CBBTC", chain="BASE")
    assert params is not None


def test_base_reserves_count() -> None:
    """Base reserves contain at least 7 assets per spec."""
    assert len(AAVE_V3_BASE_RESERVES) >= 7


def test_base_reserves_no_usdt() -> None:
    """Base does NOT have USDT (no Tether deployment on Aave V3 Base)."""
    assert get_reserve_params("USDT", chain="BASE") is None


def test_base_reserves_no_dai() -> None:
    """Base does NOT have DAI (no DAI on Aave V3 Base per design)."""
    assert get_reserve_params("DAI", chain="BASE") is None


# ---------------------------------------------------------------------------
# 10. ReserveParams immutability (frozen dataclass)
# ---------------------------------------------------------------------------


def test_reserve_params_is_frozen() -> None:
    """ReserveParams is a frozen dataclass — attempts to mutate raise FrozenInstanceError."""
    params = get_reserve_params("WETH", chain="ETHEREUM")
    assert params is not None
    with pytest.raises((AttributeError, TypeError)):
        params.max_ltv = Decimal("0.99")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 11. Decimal financials — no float leakage
# ---------------------------------------------------------------------------


def test_reserve_params_ltv_is_decimal() -> None:
    """max_ltv is Decimal, not float."""
    params = get_reserve_params("WSTETH", chain="ETHEREUM")
    assert params is not None
    assert isinstance(params.max_ltv, Decimal)
    assert isinstance(params.liquidation_threshold, Decimal)
    assert isinstance(params.liquidation_bonus, Decimal)
    assert isinstance(params.reserve_factor, Decimal)
