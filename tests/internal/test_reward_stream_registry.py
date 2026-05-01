"""Unit tests for ``RewardStreamRegistry`` — the joined lookup over
``LST_REWARD_STREAMS`` + ``REWARD_TOKEN_ECONOMICS`` that eliminates the
per-token ``"unknown"`` / ``CARRY_BASE`` fallbacks consumers used to hit.

Pins the contract that consumers rely on:
  - ``lookup_by_token_symbol`` returns full join including
    layer + issuer + lst_symbol + distributor_address + distributor_kind
    + token_address + decimals + is_pre_tge_points
  - Same token across multiple LSTs resolves deterministically (lex
    lst_symbol, prefer non-CARRY_BASE).
  - Missing tokens return ``None`` (never raise).
  - ``lookup_by_token_address`` is case-insensitive.
"""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.internal import (
    LSTRewardStream,
    RewardPnLLayer,
    RewardStreamRegistry,
    RewardTokenEconomics,
)


def _stream(
    *,
    lst_symbol: str,
    issuer: str,
    layer: RewardPnLLayer,
    reward_token_symbol: str,
    distributor_address: str | None = None,
    distributor_chain: str | None = None,
    distributor_kind: str = "merkle",
) -> LSTRewardStream:
    return LSTRewardStream(
        lst_symbol=lst_symbol,
        issuer=issuer,
        layer=layer,
        reward_token_symbol=reward_token_symbol,
        distributor_address=distributor_address,
        distributor_chain=distributor_chain,
        distributor_kind=distributor_kind,  # type: ignore[arg-type]
    )


def _econ(
    *,
    token_symbol: str,
    token_address: str,
    chain: str = "ETHEREUM",
    decimals: int = 18,
    is_pre_tge_points: bool = False,
) -> RewardTokenEconomics:
    return RewardTokenEconomics(
        token_symbol=token_symbol,
        token_address=token_address,
        chain=chain,
        decimals=decimals,
        is_pre_tge_points=is_pre_tge_points,
    )


# ──────────────────────────────────────────────────────────────────────
# UAC-shipped registry — proves no fallbacks needed for any of the 8
# real reward tokens we ship streams for.
# ──────────────────────────────────────────────────────────────────────


def test_default_registry_resolves_all_avs_continuous_tokens() -> None:
    r = RewardStreamRegistry.default()
    eigen = r.lookup_by_token_symbol("EIGEN")
    assert eigen is not None
    assert eigen.layer is RewardPnLLayer.CARRY_AVS_CONTINUOUS
    assert eigen.issuer == "eigenlayer"
    # claim_function distributor doesn't necessarily carry an address
    # (it's a contract method, not a Merkle distributor) — verify the kind
    # tag flows through.
    assert eigen.distributor_kind == "claim_function"
    assert eigen.token_address  # populated from REWARD_TOKEN_ECONOMICS


def test_default_registry_resolves_all_issuer_seasonal_tokens() -> None:
    r = RewardStreamRegistry.default()
    expected_issuer_seasonal = [
        ("ETHFI", "ether.fi", "weETH"),
        ("CARROT", "puffer", "pufETH"),
        ("ANKR", "ankr", "ankrETH"),
        ("JTO", "jito", "jitoSOL"),
        ("MNDE", "marinade", "mSOL"),
        ("SD", "stader", "ETHx"),
    ]
    for token, expected_issuer, expected_lst in expected_issuer_seasonal:
        meta = r.lookup_by_token_symbol(token)
        assert meta is not None, f"{token} should resolve"
        assert meta.layer is RewardPnLLayer.CARRY_ISSUER_SEASONAL, token
        assert meta.issuer == expected_issuer, token
        assert meta.lst_symbol == expected_lst, token


def test_pre_tge_points_token_flagged() -> None:
    """CARROT is registered as pre-TGE points — registry should reflect it."""
    r = RewardStreamRegistry.default()
    carrot = r.lookup_by_token_symbol("CARROT")
    assert carrot is not None
    assert carrot.is_pre_tge_points is True


def test_unregistered_token_returns_none() -> None:
    r = RewardStreamRegistry.default()
    assert r.lookup_by_token_symbol("DEFINITELY_NOT_A_TOKEN") is None


def test_unregistered_address_returns_none() -> None:
    r = RewardStreamRegistry.default()
    assert r.lookup_by_token_address("0xnotanaddress") is None


def test_default_registry_has_complete_token_address_index() -> None:
    """Every token with a non-empty token_address in REWARD_TOKEN_ECONOMICS
    should be reachable via lookup_by_token_address."""
    r = RewardStreamRegistry.default()
    for token_symbol in r.all_token_symbols:
        meta = r.lookup_by_token_symbol(token_symbol)
        assert meta is not None
        if not meta.token_address:
            continue
        addr_meta = r.lookup_by_token_address(meta.token_address)
        assert addr_meta is not None, f"{token_symbol} address index missing"
        assert addr_meta.token_symbol == token_symbol


# ──────────────────────────────────────────────────────────────────────
# Synthetic registry — proves the resolution rules under tight control.
# ──────────────────────────────────────────────────────────────────────


def test_same_token_across_lsts_picks_first_lex_lst() -> None:
    """EIGEN is paid by EigenLayer for both weETH and ankrETH —
    resolution should pick the lexicographically-first lst_symbol
    (ankrETH < weETH alphabetically)."""
    streams = {
        "weETH": [
            _stream(
                lst_symbol="weETH",
                issuer="eigenlayer",
                layer=RewardPnLLayer.CARRY_AVS_CONTINUOUS,
                reward_token_symbol="EIGEN",
                distributor_address="0xEL_DIST",
                distributor_chain="ETHEREUM",
            )
        ],
        "ankrETH": [
            _stream(
                lst_symbol="ankrETH",
                issuer="eigenlayer",
                layer=RewardPnLLayer.CARRY_AVS_CONTINUOUS,
                reward_token_symbol="EIGEN",
                distributor_address="0xEL_DIST",
                distributor_chain="ETHEREUM",
            )
        ],
    }
    r = RewardStreamRegistry.from_streams(streams)
    eigen = r.lookup_by_token_symbol("EIGEN")
    assert eigen is not None
    # Sorted iteration: ankrETH < weETH
    assert eigen.lst_symbol == "ankrETH"


def test_carry_base_loses_to_avs_or_seasonal_for_same_token() -> None:
    """Pathological edge case: same token registered as both CARRY_BASE
    (no distributor) and an AVS layer. Resolution must prefer the
    non-base stream so distributor metadata flows through."""
    streams = {
        "weETH": [
            _stream(
                lst_symbol="weETH",
                issuer="ether.fi",
                layer=RewardPnLLayer.CARRY_BASE,
                reward_token_symbol="EIGEN",
                distributor_kind="exchange_rate",
            ),
        ],
        "ankrETH": [
            _stream(
                lst_symbol="ankrETH",
                issuer="eigenlayer",
                layer=RewardPnLLayer.CARRY_AVS_CONTINUOUS,
                reward_token_symbol="EIGEN",
                distributor_address="0xEL",
                distributor_chain="ETHEREUM",
                distributor_kind="claim_function",
            ),
        ],
    }
    r = RewardStreamRegistry.from_streams(streams)
    eigen = r.lookup_by_token_symbol("EIGEN")
    assert eigen is not None
    assert eigen.layer is RewardPnLLayer.CARRY_AVS_CONTINUOUS
    assert eigen.distributor_kind == "claim_function"
    assert eigen.distributor_address == "0xEL"


def test_token_economics_join_propagates_decimals() -> None:
    streams = {
        "jitoSOL": [
            _stream(
                lst_symbol="jitoSOL",
                issuer="jito",
                layer=RewardPnLLayer.CARRY_ISSUER_SEASONAL,
                reward_token_symbol="JTO",
                distributor_address="SoJito",
                distributor_chain="SOLANA",
                distributor_kind="direct_transfer",
            )
        ]
    }
    economics = {
        "JTO": _econ(
            token_symbol="JTO",
            token_address="JtoMint",
            chain="SOLANA",
            decimals=9,
        )
    }
    r = RewardStreamRegistry.from_streams(streams, token_economics=economics)
    jto = r.lookup_by_token_symbol("JTO")
    assert jto is not None
    assert jto.decimals == 9
    assert jto.chain == "SOLANA"
    assert jto.token_address == "JtoMint"


def test_address_lookup_is_case_insensitive() -> None:
    streams = {
        "weETH": [
            _stream(
                lst_symbol="weETH",
                issuer="ether.fi",
                layer=RewardPnLLayer.CARRY_ISSUER_SEASONAL,
                reward_token_symbol="ETHFI",
                distributor_address="0xDIST",
                distributor_chain="ETHEREUM",
            )
        ]
    }
    economics = {
        "ETHFI": _econ(token_symbol="ETHFI", token_address="0xABCDef0123"),
    }
    r = RewardStreamRegistry.from_streams(streams, token_economics=economics)
    upper = r.lookup_by_token_address("0xABCDEF0123")
    lower = r.lookup_by_token_address("0xabcdef0123")
    assert upper is not None
    assert lower is not None
    assert upper.token_symbol == "ETHFI"
    assert lower.token_symbol == "ETHFI"


def test_token_without_economics_falls_back_safely() -> None:
    """Token registered as a stream but missing from REWARD_TOKEN_ECONOMICS:
    registry returns metadata with safe defaults instead of raising."""
    streams = {
        "weETH": [
            _stream(
                lst_symbol="weETH",
                issuer="ether.fi",
                layer=RewardPnLLayer.CARRY_ISSUER_SEASONAL,
                reward_token_symbol="UNKNOWN_TOKEN",
                distributor_address="0xD",
                distributor_chain="ETHEREUM",
            )
        ]
    }
    r = RewardStreamRegistry.from_streams(streams, token_economics={})
    meta = r.lookup_by_token_symbol("UNKNOWN_TOKEN")
    assert meta is not None
    assert meta.token_address == ""
    assert meta.decimals == 18
    assert meta.is_pre_tge_points is False
    # Stream-side metadata still populated
    assert meta.layer is RewardPnLLayer.CARRY_ISSUER_SEASONAL
    assert meta.issuer == "ether.fi"
    assert meta.distributor_address == "0xD"


def test_empty_registry_yields_empty_indexes() -> None:
    r = RewardStreamRegistry.from_streams({})
    assert r.all_token_symbols == ()
    assert r.all_token_addresses == ()
    assert r.lookup_by_token_symbol("ANY") is None


def test_decimal_field_round_trip() -> None:
    """``RewardTokenEconomics.decimals`` is an int, but we propagate as
    int through the indexes — Decimal values should not accidentally appear."""
    streams = {
        "weETH": [
            _stream(
                lst_symbol="weETH",
                issuer="ether.fi",
                layer=RewardPnLLayer.CARRY_ISSUER_SEASONAL,
                reward_token_symbol="ETHFI",
                distributor_address="0xD",
                distributor_chain="ETHEREUM",
            )
        ]
    }
    economics = {
        "ETHFI": _econ(token_symbol="ETHFI", token_address="0xeth", decimals=18),
    }
    r = RewardStreamRegistry.from_streams(streams, token_economics=economics)
    meta = r.lookup_by_token_symbol("ETHFI")
    assert meta is not None
    assert isinstance(meta.decimals, int)
    assert not isinstance(meta.decimals, Decimal)
