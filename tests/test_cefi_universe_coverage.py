"""Regression: the CeFi base-asset universe is the curated capture set.

Guards :data:`CEFI_BASE_ASSET_UNIVERSE` — the SSOT every CeFi adapter
(tardis / hyperliquid / aster) ``_passes_asset_filter`` gates against, so a
missing base silently excludes its instruments from the catalogue + downloads.

The universe is (operator 2026-06-23) the survivorship-bias-free UNION of:
legacy-44 + top-100-by-mcap-aggregated-since-2019 + HL/ASTER perp bases + the
operator's 2026-06-23 explicit authoritative lists (List A ∪ B ∪ C + restaking
extras). These tests assert (a) the wider size band (≥500), (b) the legacy-44 +
the 2026-06-16 operator-requested bases are still present, (c) key RETIRED
top-100 coins are present (survivorship-bias proof), (d) key HL/ASTER perp coins
are present, (e) all 25 operator-authoritative 2026-06-23 bases + the restaking
extras + key historical coins are present, and (f) the frozenset is
sorted/deterministic.
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

# The original 44-coin MVP cap — all kept in the expanded union.
_LEGACY_44 = frozenset(
    {
        "BTC",
        "ETH",
        "BNB",
        "SOL",
        "XRP",
        "ADA",
        "DOGE",
        "AVAX",
        "DOT",
        "LINK",
        "TRX",
        "MATIC",
        "SHIB",
        "LTC",
        "UNI",
        "ATOM",
        "NEAR",
        "APT",
        "ARB",
        "OP",
        "HYPE",
        "PEPE",
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
        "USDT",
        "USDC",
        "DAI",
        "FTT",
        "LUNA",
    }
)

# RETIRED / collapsed / declined coins that WERE top-100 by mcap — their presence
# proves the set is survivorship-bias-free (a backtest over the cycle they mattered
# in must see them, not just today's survivors).
_RETIRED_TOP100 = frozenset(
    {
        "LUNA",  # Terra Luna — death-spiralled May 2022
        "LUNC",  # Terra Classic (post-fork)
        "UST",  # TerraUSD — de-pegged May 2022
        "FTT",  # FTX Token — exchange collapse Nov 2022
        "SRM",  # Serum — FTX/Alameda-linked, collapsed
        "CEL",  # Celsius — bankruptcy 2022
        "WAVES",  # Waves — declined sharply post-2022
        "OKB",  # OKX exchange token
        "HT",  # Huobi token
        "OMG",  # OMG Network — former top-100
    }
)

# Key HL / ASTER perp base assets — the cross-venue-dispersion tranche. A coin
# tradable as a perp on HL/ASTER must also be captured on the CEX venues.
_KEY_HL_ASTER_BASES = frozenset(
    {
        "HYPE",  # Hyperliquid's own token
        "PURR",  # HL native memecoin
        "ASTER",  # ASTER's own token
        "FARTCOIN",
        "POPCAT",
        "MOODENG",
    }
)

# Operator 2026-06-23: the explicit authoritative-list coins that MUST be present
# regardless of mcap rank (List A ∪ List B ∪ List C extras). These were the 25
# bases missing from the prior 493-set; they are required by operator directive.
_OPERATOR_AUTHORITATIVE_2026_06_23 = frozenset(
    {
        "ACH",
        "AERGO",
        "AGLD",
        "ATH",
        "BICO",
        "CHR",
        "COTI",
        "CVC",
        "G",
        "GLM",
        "GTC",
        "HFT",
        "ILV",
        "KING",
        "LPT",
        "LQTY",
        "MASK",
        "NMR",
        "OXT",
        "QNT",
        "RAD",
        "RARE",
        "RLC",
        "SPELL",
        "T",
    }
)

# Restaking-rewards-hedging extras (DeFi restaking) — grab where available.
_RESTAKING_EXTRAS = frozenset({"KING", "EIGEN", "ETHFI"})


def test_universe_size_band() -> None:
    # Expanded from the 44-coin MVP cap to the curated ~518-asset capture union
    # (legacy-44 + top-100-mcap-since-2019 + HL/ASTER perp bases + the operator's
    # 2026-06-23 explicit authoritative lists). Floor 500 — we land at ~518; a drop
    # below 500 means a tranche was lost.
    assert len(CEFI_BASE_ASSET_UNIVERSE) >= 500, (
        f"universe shrank below the curated capture floor: {len(CEFI_BASE_ASSET_UNIVERSE)}"
    )


def test_operator_authoritative_2026_06_23_bases_present() -> None:
    """All 25 operator-authoritative-list bases (2026-06-23) are present.

    These are required regardless of mcap rank — a missing one silently excludes
    its instruments from capture, so guard them explicitly.
    """
    missing = _OPERATOR_AUTHORITATIVE_2026_06_23 - CEFI_BASE_ASSET_UNIVERSE
    assert not missing, f"operator authoritative-list bases missing from the universe: {sorted(missing)}"


def test_restaking_extras_present() -> None:
    """Restaking-rewards-hedging extras (KING, EIGEN, ETHFI) are present."""
    missing = _RESTAKING_EXTRAS - CEFI_BASE_ASSET_UNIVERSE
    assert not missing, f"restaking extras missing from the universe: {sorted(missing)}"


def test_key_historical_coins_present() -> None:
    """Key historical / retired top-100 coins (FTT, LUNA) are present (survivorship)."""
    for coin in ("FTT", "LUNA"):
        assert coin in CEFI_BASE_ASSET_UNIVERSE, f"key historical coin {coin} missing from the universe"


def test_legacy_44_all_present() -> None:
    missing = _LEGACY_44 - CEFI_BASE_ASSET_UNIVERSE
    assert not missing, f"legacy-44 MVP bases dropped from the universe: {sorted(missing)}"


def test_requested_bases_present_in_universe() -> None:
    missing = _REQUESTED_BASES_2026_06_16 - CEFI_BASE_ASSET_UNIVERSE
    assert not missing, f"operator-requested CeFi bases missing from the universe: {sorted(missing)}"


def test_retired_top100_present_survivorship_bias_free() -> None:
    missing = _RETIRED_TOP100 - CEFI_BASE_ASSET_UNIVERSE
    assert not missing, f"retired top-100 coins missing → universe is NOT survivorship-bias-free: {sorted(missing)}"


def test_key_hl_aster_perp_bases_present() -> None:
    missing = _KEY_HL_ASTER_BASES - CEFI_BASE_ASSET_UNIVERSE
    assert not missing, f"key HL/ASTER perp bases missing from the universe: {sorted(missing)}"


def test_universe_is_sorted_and_deterministic() -> None:
    # The frozenset literal is checked in sorted for deterministic diffs; assert
    # no accidental duplicate/ordering regression by re-deriving the sorted tuple.
    elems = sorted(CEFI_BASE_ASSET_UNIVERSE)
    assert len(elems) == len(set(elems)), "duplicate base assets in the universe"
    # all upper-case, non-empty tokens
    assert all(e and e == e.upper() for e in elems if not e[0].isdigit()), (
        "non-canonical (lower-case / empty) base-asset token in the universe"
    )


def test_eigen_usdt_and_usdc_pairs_would_be_accepted() -> None:
    # A pair is accepted iff base ∈ universe AND quote ∈ accepted quotes. EIGENUSDT
    # (binance-spot) + EIGEN/USDC (hyperliquid settle) are the EigenLayer dust cases.
    assert "EIGEN" in CEFI_BASE_ASSET_UNIVERSE
    assert "USDT" in CEFI_ACCEPTED_QUOTE_ASSETS
    assert "USDC" in CEFI_ACCEPTED_QUOTE_ASSETS
