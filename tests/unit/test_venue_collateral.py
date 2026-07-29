"""Unit tests for ``unified_api_contracts.registry.venue_collateral`` matrix.

Covers Stream A 2026-05-08 LST acceptance flips for DERIBIT / BYBIT / OKX.
Source evidence: ``unified-trading-pm/codex/16-strategy-playbooks/defi/venue-collateral-2026-05-07.md``.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from unified_api_contracts.registry.venue_collateral import (
    PLACEHOLDER_HAIRCUTS_PENDING_GO_LIVE,
    VENUE_COLLATERAL_MATRIX,
    accepted_perp_collateral,
    get_accepted_collateral,
    get_collateral_haircut,
    venue_accepts_collateral,
)


@pytest.mark.parametrize(
    ("venue", "token", "expected_haircut"),
    [
        # Stream A 2026-05-08 flips — DERIBIT / BYBIT / OKX LST acceptance.
        ("DERIBIT", "stETH", Decimal("0.075")),
        ("BYBIT", "stETH", Decimal("0.10")),
        ("BYBIT", "wstETH", Decimal("0.10")),
        ("BYBIT", "USDe", Decimal("0.05")),
        ("BYBIT", "sUSDe", Decimal("0.07")),
        ("OKX", "wstETH", Decimal("0.10")),
        # Pre-existing acceptances retained.
        ("DERIBIT", "ETH", Decimal("0")),
        ("DERIBIT", "BTC", Decimal("0")),
        ("HYPERLIQUID", "USDC", Decimal("0")),
    ],
)
def test_accepted_collateral_haircut(venue: str, token: str, expected_haircut: Decimal) -> None:
    """Stream A 2026-05-08 + pre-existing rows must report exact cited haircuts."""
    assert venue_accepts_collateral(venue, token), f"{venue} {token} must be accepted"
    haircut = get_collateral_haircut(venue, token)
    assert haircut is not None, f"{venue} {token} accepted but no haircut"
    assert haircut == expected_haircut, f"{venue} {token} haircut {haircut} != expected {expected_haircut}"


@pytest.mark.parametrize(
    ("venue", "token"),
    [
        # OKX stETH NOT on discount-rate list (only wstETH per OKX docs).
        ("OKX", "stETH"),
        # DERIBIT only stETH on PM, not wstETH/weETH/rETH.
        ("DERIBIT", "wstETH"),
        ("DERIBIT", "weETH"),
        ("DERIBIT", "rETH"),
        # BYBIT weETH not accepted.
        ("BYBIT", "weETH"),
        # HYPERLIQUID — all LSTs explicitly rejected (USDC-only by design).
        ("HYPERLIQUID", "stETH"),
        ("HYPERLIQUID", "wstETH"),
        ("HYPERLIQUID", "rETH"),
        # BINANCE — Multi-Assets Mode excludes LSTs.
        ("BINANCE", "stETH"),
        ("BINANCE", "wstETH"),
        # ASTER — Multi-Asset Mode does not list any of these LSTs.
        ("ASTER", "stETH"),
        ("ASTER", "wstETH"),
        ("ASTER", "weETH"),
    ],
)
def test_lst_explicitly_rejected(venue: str, token: str) -> None:
    """LST rows that remain ``accepted=False`` must not flip silently."""
    assert not venue_accepts_collateral(venue, token), f"{venue} {token} must NOT be accepted"
    assert get_collateral_haircut(venue, token) is None, f"{venue} {token} rejected but haircut returned"


def test_deribit_perp_collateral_set() -> None:
    """``accepted_perp_collateral('DERIBIT')`` returns BTC + ETH + USDC + stETH post-Stream A flip."""
    perp_set = set(accepted_perp_collateral("DERIBIT"))
    assert "stETH" in perp_set, "DERIBIT stETH missing from perp collateral set after Stream A flip"
    assert {"BTC", "ETH", "USDC"}.issubset(perp_set), "DERIBIT base perp set regressed"


def test_bybit_perp_collateral_set_includes_lst_and_stable_lst() -> None:
    """``accepted_perp_collateral('BYBIT')`` includes stETH/wstETH/USDe/sUSDe post-Stream A flip."""
    perp_set = set(accepted_perp_collateral("BYBIT"))
    assert {"stETH", "wstETH", "USDe", "sUSDe"}.issubset(perp_set), (
        f"BYBIT post-Stream-A perp set missing UTA tokens; got {perp_set}"
    )
    assert {"USDT", "BTC"}.issubset(perp_set), "BYBIT base perp set regressed"


def test_okx_perp_collateral_set_includes_wsteth_only() -> None:
    """``accepted_perp_collateral('OKX')`` includes wstETH but NOT stETH (asymmetric flip)."""
    perp_set = set(accepted_perp_collateral("OKX"))
    assert "wstETH" in perp_set, "OKX wstETH missing from perp collateral set after Stream A flip"
    assert "stETH" not in perp_set, "OKX stETH leaked into perp collateral set (should remain rejected)"


def test_no_duplicate_venue_token_pairs() -> None:
    """Each ``(venue, token)`` pair appears at most once in the matrix."""
    seen: set[tuple[str, str]] = set()
    for entry in VENUE_COLLATERAL_MATRIX:
        key = (entry.venue, entry.token)
        assert key not in seen, f"duplicate matrix entry for {key}"
        seen.add(key)


def test_get_accepted_collateral_deribit_includes_steth() -> None:
    """``get_accepted_collateral('DERIBIT')`` includes stETH post-Stream A flip."""
    accepted = get_accepted_collateral("DERIBIT")
    assert "stETH" in accepted, f"DERIBIT accepted set missing stETH; got {accepted}"


def test_accepted_rows_have_haircut_set() -> None:
    """Every ``accepted=True`` row must have a non-None haircut (correctness invariant)."""
    for entry in VENUE_COLLATERAL_MATRIX:
        if entry.accepted:
            assert entry.haircut_pct is not None, f"{entry.venue} {entry.token} accepted=True but haircut_pct is None"


def test_rejected_rows_have_no_haircut() -> None:
    """Every ``accepted=False`` row must have ``haircut_pct=None`` (no stale haircut)."""
    for entry in VENUE_COLLATERAL_MATRIX:
        if not entry.accepted:
            assert entry.haircut_pct is None, (
                f"{entry.venue} {entry.token} accepted=False but haircut_pct={entry.haircut_pct}"
            )


def test_f28_consolidation_canonical_clear_cut_values() -> None:
    """F28 (operator-approved 2026-06-15): UAC is the single canonical collateral-haircut SSOT.

    The execution-service ``_LST_REGISTRY`` duplicate is deleted; its resolver now
    consumes these accessors. Pin the operator-approved clear-cut rows so the
    consolidated truth cannot drift (haircuts are FRACTIONS, e.g. 0.075 = 7.5%).
    """
    # Deribit stETH — official current 7.5% (fraction 0.075).
    assert venue_accepts_collateral("DERIBIT", "stETH")
    assert get_collateral_haircut("DERIBIT", "stETH") == Decimal("0.075")
    # Clear-cut NOT-ACCEPTED rows.
    for venue, token in [
        ("HYPERLIQUID", "wstETH"),
        ("OKX", "stETH"),
        ("BINANCE", "stETH"),
        ("DERIBIT", "wstETH"),
    ]:
        assert not venue_accepts_collateral(venue, token), f"{venue} {token} must NOT be accepted (F28 clear-cut)"
        assert get_collateral_haircut(venue, token) is None
    # Clear-cut accepted-with-haircut rows.
    assert get_collateral_haircut("BYBIT", "wstETH") == Decimal("0.10")
    assert get_collateral_haircut("OKX", "wstETH") == Decimal("0.10")


def test_f28_haircuts_live_probed_2026_06_17() -> None:
    """F28 former-placeholder row is now LIVE-PROBED (operator-authorised 2026-06-17).

    Bybit stETH = 0.10 (Bybit UTA ``collateralRatio`` 0.9 via ``/v5/spot-margin-trade/data``).
    ``PLACEHOLDER_HAIRCUTS_PENDING_GO_LIVE`` is now empty. (The former Drift mSOL = 0.20 row was
    removed 2026-07-16 along with the rest of the DRIFT venue — operator ruling: all Solana perp
    DEXes dropped except Jupiter, not integrated.)
    """
    assert venue_accepts_collateral("BYBIT", "stETH")
    assert get_collateral_haircut("BYBIT", "stETH") == Decimal("0.10")
    assert not PLACEHOLDER_HAIRCUTS_PENDING_GO_LIVE  # empty: no haircut remains a placeholder


def test_aster_multi_asset_mode_live_verified_2026_07_29() -> None:
    """ASTER re-verified LIVE 2026-07-29 against ``fapi.asterdex.com`` /exchangeInfo + docs.asterdex.com.

    Confirmed our integration is the "Aster Perps" Multi-Asset Mode product (not "AstherusEX" — whose
    docs exclude USDC entirely, while /exchangeInfo's marginAvailable list includes it). USDC/USDT
    haircut corrected from the prior 0%/1% placeholder to the real Multi-Asset Mode ratio (99.99% ->
    0.01% haircut); BTC/ETH added as accepted (95% ratio -> 5% haircut), previously untracked.
    Source: plans/active/issues/aster_margining_registry_live_docs_drift_2026_07_28.md.
    """
    for token in ("USDC", "USDT"):
        assert venue_accepts_collateral("ASTER", token)
        assert get_collateral_haircut("ASTER", token) == Decimal("0.0001"), token
    for token in ("BTC", "ETH"):
        assert venue_accepts_collateral("ASTER", token)
        assert get_collateral_haircut("ASTER", token) == Decimal("0.05"), token
    perp_set = set(accepted_perp_collateral("ASTER"))
    assert {"USDC", "USDT", "BTC", "ETH"}.issubset(perp_set), f"ASTER perp set regressed; got {perp_set}"


def test_f27_venue_lookup_is_case_insensitive() -> None:
    """F27 (2026-06-15): venue lookups are case-insensitive — lowercase slot-config
    venue ids (``'deribit'``) must resolve against the UPPERCASE matrix keys
    (``'DERIBIT'``), else carry-staked-basis silently no-emits.
    """
    assert accepted_perp_collateral("deribit") == accepted_perp_collateral("DERIBIT")
    assert len(accepted_perp_collateral("deribit")) > 0
    assert venue_accepts_collateral("deribit", "stETH") is True
    assert get_collateral_haircut("deribit", "stETH") == Decimal("0.075")
