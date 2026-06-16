"""Regression: the CeFi base-asset universe carries the operator-requested coins.

Guards against an accidental shrink of ``CEFI_BASE_ASSET_UNIVERSE`` dropping the
2026-06-16 additions (EigenLayer dust + the full requested CeFi coin list). The
universe is the SSOT every CeFi adapter (tardis/hyperliquid/aster) filters against,
so a missing base silently excludes its instruments from the catalogue + downloads.
"""

from __future__ import annotations

from unified_api_contracts.registry import (
    CEFI_ACCEPTED_QUOTE_ASSETS,
    CEFI_BASE_ASSET_UNIVERSE,
)

# Operator 2026-06-16: "add the rest" — EIGEN (EigenLayer rewards dust) + the
# previously-missing coins from the requested vs-USDT / vs-USDC list.
_REQUESTED_BASES_2026_06_16 = frozenset(
    {
        "EIGEN",
        "AAVE",
        "ALGO",
        "AXS",
        "CHZ",
        "COMP",
        "DASH",
        "ENJ",
        "EOS",
        "FIL",
        "GALA",
        "ICP",
        "MANA",
        "SAND",
        "THETA",
        "XLM",
        "ZEC",
    }
)


def test_requested_bases_present_in_universe() -> None:
    missing = _REQUESTED_BASES_2026_06_16 - CEFI_BASE_ASSET_UNIVERSE
    assert not missing, f"operator-requested CeFi bases missing from the universe: {sorted(missing)}"


def test_eigen_usdt_and_usdc_pairs_would_be_accepted() -> None:
    # A pair is accepted iff base ∈ universe AND quote ∈ accepted quotes. EIGENUSDT
    # (binance-spot) + EIGEN/USDC (hyperliquid settle) are the EigenLayer dust cases.
    assert "EIGEN" in CEFI_BASE_ASSET_UNIVERSE
    assert "USDT" in CEFI_ACCEPTED_QUOTE_ASSETS
    assert "USDC" in CEFI_ACCEPTED_QUOTE_ASSETS
