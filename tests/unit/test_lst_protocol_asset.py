"""Tests for LST_TOKEN_TO_PROTOCOL_ASSET and helpers.

Phase 9 plan ``carry_tracer_phase_9_catalog_paired_dispersion_2026_05_06.md``
Phase 1.A — UAC SSOT lifted from tracer-local table.
"""

from __future__ import annotations

from unified_api_contracts.internal.domain.defi import (
    LST_TOKEN_TO_PROTOCOL_ASSET,
    protocol_asset_for_token,
    tokens_for_protocol_asset,
)


class TestLstTokenToProtocolAsset:
    """Coverage of the canonical LST mapping."""

    def test_table_has_all_canonical_lsts(self) -> None:
        """Every LST/LRT resolved by the carry tracer (2026-05-06) + restaking
        LRTs added 2026-05-12 per defi_catalogue Phase 1A must be present."""
        expected = {
            # ETH LSTs (carry-tracer baseline 2026-05-06)
            "stETH",
            "wstETH",
            "rETH",
            "cbETH",
            "weETH",
            "ankrETH",
            "mETH",
            "swETH",
            "ETHx",
            "osETH",
            "pufETH",
            "wBETH",
            # Yield-bearing stablecoins
            "sUSDe",
            "sDAI",
            # Solana LSTs
            "jitoSOL",
            "mSOL",
            "bSOL",
            "sanctumSOL",
            # Restaking LRTs (defi_catalogue Phase 1G + 1A; added 2026-05-12)
            "ezETH",
            "rsETH",
        }
        assert set(LST_TOKEN_TO_PROTOCOL_ASSET) == expected

    def test_eth_lsts_resolve_to_eth(self) -> None:
        eth_lsts = {
            "stETH",
            "wstETH",
            "rETH",
            "cbETH",
            "weETH",
            "ankrETH",
            "mETH",
            "swETH",
            "ETHx",
            "osETH",
            "pufETH",
            "wBETH",
        }
        for token in eth_lsts:
            _proto, asset = LST_TOKEN_TO_PROTOCOL_ASSET[token]
            assert asset == "ETH", f"{token} should map to ETH base"

    def test_sol_lsts_resolve_to_sol(self) -> None:
        for token in ("jitoSOL", "mSOL", "bSOL", "sanctumSOL"):
            _proto, asset = LST_TOKEN_TO_PROTOCOL_ASSET[token]
            assert asset == "SOL"

    def test_stablecoin_lsts(self) -> None:
        assert LST_TOKEN_TO_PROTOCOL_ASSET["sUSDe"] == ("ETHENA", "USDE")
        assert LST_TOKEN_TO_PROTOCOL_ASSET["sDAI"] == ("SPARK", "DAI")

    def test_wbeth_and_sanctumsol(self) -> None:
        """wBETH (Binance) + sanctumSOL (Sanctum Infinity) — added 2026-08-03 per
        lst_yields_writegate_permanently_blocked_2026_07_28.md's follow-up; both were
        genuine LSTs dropped by ``_drop_unmapped_tokens`` purely for being absent here."""
        assert LST_TOKEN_TO_PROTOCOL_ASSET["wBETH"] == ("BINANCE", "ETH")
        assert LST_TOKEN_TO_PROTOCOL_ASSET["sanctumSOL"] == ("SANCTUM", "SOL")

    def test_protocol_uppercase_no_version_suffix(self) -> None:
        """Protocol names must be upper-case, no version suffix.

        Catalog rows speak ``aave`` etc. lower-case + un-versioned; on-chain
        ``instrument_id`` carries ``AAVE_V3``. The LST table sits between —
        upper-case to match the parquet write side, no version because LSTs
        don't fork by protocol version.
        """
        for token, (protocol, _asset) in LST_TOKEN_TO_PROTOCOL_ASSET.items():
            assert protocol == protocol.upper(), f"{token}: protocol must be upper-case"
            for suffix in ("_V1", "_V2", "_V3"):
                assert not protocol.endswith(suffix), f"{token}: protocol must not end with {suffix}"


class TestTokensForProtocolAsset:
    """Helper that filters tokens by ``(protocol, asset)`` selector."""

    def test_lido_eth_returns_steth(self) -> None:
        assert tokens_for_protocol_asset("LIDO", "ETH") == {"stETH"}

    def test_jito_sol_returns_jitosol(self) -> None:
        assert tokens_for_protocol_asset("JITO", "SOL") == {"jitoSOL"}

    def test_empty_protocol_filters_by_asset_only(self) -> None:
        eth_tokens = tokens_for_protocol_asset("", "ETH")
        sol_tokens = tokens_for_protocol_asset("", "SOL")
        assert "stETH" in eth_tokens
        assert "weETH" in eth_tokens
        assert "jitoSOL" not in eth_tokens
        assert sol_tokens == {"jitoSOL", "mSOL", "bSOL", "sanctumSOL"}

    def test_empty_asset_filters_by_protocol_only(self) -> None:
        assert tokens_for_protocol_asset("ETHENA", "") == {"sUSDe"}

    def test_both_empty_returns_all(self) -> None:
        assert tokens_for_protocol_asset("", "") == set(LST_TOKEN_TO_PROTOCOL_ASSET)

    def test_case_insensitive(self) -> None:
        assert tokens_for_protocol_asset("lido", "eth") == {"stETH"}
        assert tokens_for_protocol_asset("LIDO", "Eth") == {"stETH"}

    def test_unknown_protocol_returns_empty(self) -> None:
        assert tokens_for_protocol_asset("UNKNOWN_PROTOCOL", "ETH") == set()


class TestProtocolAssetForToken:
    """Inverse helper used by features-onchain calculator-side stamping."""

    def test_known_token(self) -> None:
        assert protocol_asset_for_token("sUSDe") == ("ETHENA", "USDE")
        assert protocol_asset_for_token("wstETH") == ("LIDO_WRAPPED", "ETH")

    def test_unknown_token_returns_none(self) -> None:
        assert protocol_asset_for_token("NOT_AN_LST") is None
        assert protocol_asset_for_token("") is None

    def test_case_sensitive_token_lookup(self) -> None:
        """Token symbols are case-sensitive (matches on-chain ERC20 / SPL name).

        ``stETH`` is the canonical Lido staked ETH token; ``STETH`` /
        ``stEth`` aren't on-chain forms. Strict matching keeps callers
        honest about their input shape.
        """
        assert protocol_asset_for_token("stETH") == ("LIDO", "ETH")
        assert protocol_asset_for_token("steth") is None
        assert protocol_asset_for_token("STETH") is None
