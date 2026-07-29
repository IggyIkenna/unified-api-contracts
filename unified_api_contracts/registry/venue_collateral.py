"""Venue collateral acceptance matrix — which tokens each venue accepts as margin.

F28 haircuts LIVE-PROBED 2026-06-17 (the former operator-held placeholder is now real, operator-authorised):

- ``("BYBIT", "stETH")`` haircut **0.10** — Bybit public UTA collateral API ``GET /v5/spot-margin-trade/data``
  ``collateralRatio=0.9`` (base/non-VIP tier, the conservative tier) → ``1 - 0.9 = 0.10``. (Placeholder was correct.)

DRIFT (Solana) — including its on-chain spot-market collateral probe history: SOL/mSOL/JitoSOL haircuts — and
PACIFICA (Solana) collateral rows were REMOVED 2026-07-16 (operator ruling: all Solana perp DEXes dropped except
Jupiter, which is not integrated). SSOT: unified-trading-pm/codex/04-architecture/solana-defi-coverage.md.

ASTER re-verified LIVE 2026-07-29 (`plans/active/issues/aster_margining_registry_live_docs_drift_2026_07_28.md`):
confirmed our `fapi.asterdex.com` integration is the "Aster Perps" Multi-Asset Mode product (not "AstherusEX"), and
its documented collateral ratios were materially different from the prior placeholder rows — USDC/USDT haircut
corrected from 0%/1% to the real 0.01%, and BTC/ETH added as accepted (95% ratio) where they were previously
untracked (effectively treated as not-accepted).

:data:`PLACEHOLDER_HAIRCUTS_PENDING_GO_LIVE` is now empty — no haircut remains a placeholder. Re-probe on a venue
margin-policy change (Bybit tiers).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Literal

VenueKind = Literal["PERP_CEX", "PERP_DEX", "LENDING", "STAKING"]
"""How callers should think about this venue's collateral usage.

- ``PERP_CEX`` / ``PERP_DEX``: collateral funds a perpetual short / long.
- ``LENDING``: collateral underwrites a borrow (Aave, Compound, etc.).
- ``STAKING``: collateral is the principal being staked.

Used by callers like ``CARRY_STAKED_BASIS`` to filter to perp-margining venues
when deciding the leg sequence — see
``unified-trading-pm/plans/active/carry_staked_basis_structure_axis_2026_05_04.md``.
"""

_PERP_VENUE_KINDS: Final[frozenset[str]] = frozenset({"PERP_CEX", "PERP_DEX"})


@dataclass(frozen=True)
class CollateralAcceptance:
    """A single venue-token collateral acceptance entry."""

    venue: str
    token: str
    accepted: bool
    haircut_pct: Decimal | None
    margin_type: str
    notes: str
    venue_kind: VenueKind


VENUE_COLLATERAL_MATRIX: list[CollateralAcceptance] = [
    # HyperLiquid — USDC only
    CollateralAcceptance("HYPERLIQUID", "USDC", True, Decimal("0"), "CROSS", "Only accepted margin", "PERP_CEX"),
    CollateralAcceptance("HYPERLIQUID", "ETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("HYPERLIQUID", "weETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("HYPERLIQUID", "WETH", False, None, "", "Not accepted", "PERP_CEX"),
    # Aster — fapi.asterdex.com is the "Aster Perps" Multi-Asset Mode product
    # (confirmed 2026-07-29: live /fapi/v1/exchangeInfo's 39-asset marginAvailable
    # list — incl. USDC, SLISBNB, LISUSD, WBETH, STONE — matches
    # docs.asterdex.com's Multi-Asset Mode table across all 4 chains, NOT the
    # narrower "AstherusEX" orderbook product, whose docs explicitly exclude
    # USDC on both listed chains). Ratios below are Multi-Asset Mode's
    # documented collateral ratios (haircut = 1 - ratio).
    CollateralAcceptance("ASTER", "USDC", True, Decimal("0.0001"), "CROSS", "Multi-Asset Mode 99.99%", "PERP_CEX"),
    CollateralAcceptance("ASTER", "USDT", True, Decimal("0.0001"), "CROSS", "Multi-Asset Mode 99.99%", "PERP_CEX"),
    CollateralAcceptance("ASTER", "BTC", True, Decimal("0.05"), "CROSS", "Multi-Asset Mode 95%", "PERP_CEX"),
    CollateralAcceptance("ASTER", "ETH", True, Decimal("0.05"), "CROSS", "Multi-Asset Mode 95%", "PERP_CEX"),
    # Aave V3 (referencing defi_reserve_params.py LTV values)
    CollateralAcceptance("AAVE_V3-ETHEREUM", "WETH", True, Decimal("0.175"), "ISOLATED", "LTV 82.5%", "LENDING"),
    CollateralAcceptance("AAVE_V3-ETHEREUM", "weETH", True, Decimal("0.275"), "ISOLATED", "LTV 72.5%", "LENDING"),
    CollateralAcceptance("AAVE_V3-ETHEREUM", "wstETH", True, Decimal("0.205"), "ISOLATED", "LTV 79.5%", "LENDING"),
    CollateralAcceptance("AAVE_V3-ETHEREUM", "USDT", True, Decimal("0.23"), "ISOLATED", "LTV 77%", "LENDING"),
    CollateralAcceptance("AAVE_V3-ETHEREUM", "USDC", True, Decimal("0.23"), "ISOLATED", "LTV 77%", "LENDING"),
    CollateralAcceptance("AAVE_V3-ETHEREUM", "WBTC", True, Decimal("0.27"), "ISOLATED", "LTV 73%", "LENDING"),
    # Binance
    CollateralAcceptance("BINANCE", "USDT", True, Decimal("0"), "CROSS", "Linear futures", "PERP_CEX"),
    CollateralAcceptance("BINANCE", "BTC", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    CollateralAcceptance("BINANCE", "ETH", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    # OKX
    CollateralAcceptance("OKX", "USDT", True, Decimal("0"), "CROSS", "Linear", "PERP_CEX"),
    CollateralAcceptance("OKX", "BTC", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    CollateralAcceptance("OKX", "ETH", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    # Bybit
    CollateralAcceptance("BYBIT", "USDT", True, Decimal("0"), "CROSS", "Linear", "PERP_CEX"),
    CollateralAcceptance("BYBIT", "BTC", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    # Deribit
    CollateralAcceptance("DERIBIT", "BTC", True, Decimal("0"), "PORTFOLIO", "Portfolio margin", "PERP_CEX"),
    CollateralAcceptance("DERIBIT", "ETH", True, Decimal("0"), "PORTFOLIO", "Portfolio margin", "PERP_CEX"),
    CollateralAcceptance("DERIBIT", "USDC", True, Decimal("0.02"), "PORTFOLIO", "Slight haircut", "PERP_CEX"),
    # Lido / Etherfi staking venues — included so callers can discover the
    # staking principal asset (ETH) without needing a separate registry.
    # ``accepted=True`` for the native asset only; the staking contract is
    # not a perp-margining venue.
    CollateralAcceptance("LIDO", "ETH", True, Decimal("0"), "STAKE", "Native staking", "STAKING"),
    CollateralAcceptance("ETHERFI", "ETH", True, Decimal("0"), "STAKE", "Native staking", "STAKING"),
    # Tardis-captured CeFi perp venues — funding data lives in
    # ``gs://market-data-tick-cefi-{pid}/raw_tick_data/.../derivative_ticker/``
    # per ``VENUES_BY_ASSET_GROUP['cefi']``. All take USDT as primary
    # linear-perp margin (5 bps haircut applied to coin-margined where used).
    CollateralAcceptance("BINANCE-FUTURES", "USDT", True, Decimal("0"), "CROSS", "Linear-USDT perp margin", "PERP_CEX"),
    CollateralAcceptance("BINANCE-FUTURES", "BTC", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    CollateralAcceptance("BINANCE-FUTURES", "ETH", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    CollateralAcceptance("BYBIT-FUTURES", "USDT", True, Decimal("0"), "CROSS", "Linear", "PERP_CEX"),
    CollateralAcceptance("BYBIT-FUTURES", "BTC", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    CollateralAcceptance("OKX-FUTURES", "USDT", True, Decimal("0"), "CROSS", "Linear", "PERP_CEX"),
    CollateralAcceptance("OKX-FUTURES", "BTC", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    CollateralAcceptance("OKX-FUTURES", "ETH", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    CollateralAcceptance("KRAKEN-FUTURES", "USDT", True, Decimal("0"), "CROSS", "Linear", "PERP_CEX"),
    CollateralAcceptance(
        "KRAKEN-FUTURES", "USDC", True, Decimal("0.01"), "CROSS", "Linear (slight haircut)", "PERP_CEX"
    ),
    CollateralAcceptance("BITFINEX-FUTURES", "USDT", True, Decimal("0"), "CROSS", "Linear", "PERP_CEX"),
    CollateralAcceptance("BITGET-FUTURES", "USDT", True, Decimal("0"), "CROSS", "Linear", "PERP_CEX"),
    # DRIFT (Solana) + PACIFICA (Solana) + GMX (Arbitrum/Avalanche) collateral
    # rows removed 2026-07-16 / 2026-07-25 (operator ruling: all Solana perp
    # DEXes dropped except Jupiter, not integrated; GMX removed for unreliable
    # historical funding data — see
    # unified-trading-pm/plans/active/defi_gmx_venue_removal_2026_07_25.md).
    # SSOT: unified-trading-pm/codex/04-architecture/solana-defi-coverage.md.
    # ----- ETH LST acceptance gaps (explicit `accepted=False` so the catalog ----
    # generator's `accepted_perp_collateral(venue)` short-circuits cleanly and
    # the absence is documented, not silently absent. Positive rows wait on
    # Phase 7a operator audit (see plan
    # ``carry_staked_basis_structure_axis_2026_05_04`` Phase 7a).
    #
    # STALENESS_FLAG_2026_05_07 — the prior 2026-05-05 comment claimed "NO
    # production ETH-perp venue accepts an ETH LST as direct cross-margin
    # today". This is OUT OF DATE. Live venue re-verification 2026-05-07
    # (web docs, not yet API-probed) found:
    #   - DERIBIT stETH IS accepted at 7.5% haircut, X:PM/X:SM, offsets
    #     ETH-perp directly (effective 2026-01-13). Source:
    #     https://insights.deribit.com/exchange-updates/portfolio-margin-improvements-for-steth-and-cross-collateral-haircuts/
    #   - BYBIT stETH + METH UTA collateral since 2024-02; USDe since
    #     2024-12-19. Per Bybit margin-spec page.
    #   - OKX wstETH on multi-currency-margin / portfolio-margin
    #     discount-rate list. Per OKX cross-margin docs.
    # The DATA below is preserved as-is pending Stream A live-API probe in
    # plan ``defi_archetypes_canonicalisation_and_venue_matrix_2026_05_07``.
    # DO NOT trust ``accepted=False`` for {DERIBIT, BYBIT, OKX} x {stETH,
    # wstETH, METH, USDe} until that probe lands and the rows below flip.
    # Hyperliquid (L1) + Binance (Multi-Assets Mode currently
    # BTC/ETH/BNB/XRP/ADA/DOT/SOL/USDC/USDT only) + Aster (USDT/USDF/asBNB)
    # remain genuine ``accepted=False``.
    #
    # When Aevo / Lyra-V2 / dYdX / Hyperliquid ship LST-margin support, flip
    # the row to ``accepted=True`` with a haircut citation in ``notes``.
    CollateralAcceptance("HYPERLIQUID", "stETH", False, None, "", "Not accepted (USDC-only)", "PERP_CEX"),
    CollateralAcceptance("HYPERLIQUID", "wstETH", False, None, "", "Not accepted (USDC-only)", "PERP_CEX"),
    CollateralAcceptance("HYPERLIQUID", "rETH", False, None, "", "Not accepted (USDC-only)", "PERP_CEX"),
    CollateralAcceptance("HYPERLIQUID", "cbETH", False, None, "", "Not accepted (USDC-only)", "PERP_CEX"),
    CollateralAcceptance("HYPERLIQUID", "eETH", False, None, "", "Not accepted (USDC-only)", "PERP_CEX"),
    # DERIBIT — stETH accepted at 7.5% haircut on Portfolio Margin (X:PM/X:SM),
    # offsets ETH-perp directly. Effective 2026-01-13 per Deribit insights post
    # ``portfolio-margin-improvements-for-steth-and-cross-collateral-haircuts``.
    # Stream A flip 2026-05-08 (was ``accepted=False`` — stale 2026-05-05 entry).
    # See unified-trading-pm/codex/16-strategy-playbooks/defi/venue-collateral-2026-05-07.md.
    CollateralAcceptance(
        "DERIBIT",
        "stETH",
        True,
        Decimal("0.075"),
        "PORTFOLIO",
        "PM/SM only; offsets ETH-perp",
        "PERP_CEX",
    ),
    CollateralAcceptance("DERIBIT", "wstETH", False, None, "", "Not accepted (only stETH on PM)", "PERP_CEX"),
    CollateralAcceptance("DERIBIT", "weETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("DERIBIT", "rETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("BINANCE", "stETH", False, None, "", "Not accepted as futures margin", "PERP_CEX"),
    CollateralAcceptance("BINANCE", "wstETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("BINANCE", "weETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("BINANCE", "rETH", False, None, "", "Not accepted", "PERP_CEX"),
    # BYBIT — stETH + METH on UTA collateral (Unified Trading Account) since
    # 2024-02 per Bybit margin-spec page; USDe added 2024-12-19. Stream A flip 2026-05-08.
    # See unified-trading-pm/codex/16-strategy-playbooks/defi/venue-collateral-2026-05-07.md.
    # PROBED 2026-06-17: Bybit public UTA collateral API GET /v5/spot-margin-trade/data reports
    # collateralRatio=0.9 for STETH (base/non-VIP tier — the conservative tier) -> haircut 1-0.9 = 0.10.
    CollateralAcceptance(
        "BYBIT",
        "stETH",
        True,
        Decimal("0.10"),
        "PORTFOLIO",
        "UTA collateral since 2024-02 — haircut 0.10 (Bybit collateralRatio 0.9, probed 2026-06-17)",
        "PERP_CEX",
    ),
    CollateralAcceptance("BYBIT", "wstETH", True, Decimal("0.10"), "PORTFOLIO", "UTA collateral", "PERP_CEX"),
    CollateralAcceptance("BYBIT", "weETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance(
        "BYBIT", "USDe", True, Decimal("0.05"), "PORTFOLIO", "UTA collateral since 2024-12-19", "PERP_CEX"
    ),
    CollateralAcceptance(
        "BYBIT", "sUSDe", True, Decimal("0.07"), "PORTFOLIO", "UTA collateral; sUSDe staked", "PERP_CEX"
    ),
    # OKX — wstETH on multi-currency-margin / portfolio-margin discount-rate
    # list (per OKX cross-margin docs). Stream A flip 2026-05-08. stETH not
    # explicitly listed on discount-rate page; conservative ``False`` until
    # live-API probe confirms.
    # See unified-trading-pm/codex/16-strategy-playbooks/defi/venue-collateral-2026-05-07.md.
    CollateralAcceptance("OKX", "stETH", False, None, "", "Not on discount-rate list", "PERP_CEX"),
    CollateralAcceptance(
        "OKX",
        "wstETH",
        True,
        Decimal("0.10"),
        "PORTFOLIO",
        "Multi-currency-margin discount-rate list",
        "PERP_CEX",
    ),
    CollateralAcceptance("OKX", "weETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("ASTER", "stETH", False, None, "", "Not accepted (USDC/USDT-only)", "PERP_CEX"),
    CollateralAcceptance("ASTER", "wstETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("ASTER", "weETH", False, None, "", "Not accepted", "PERP_CEX"),
    # Tardis-captured futures venues: same gap (linear-USDT or coin-margined
    # only; no LST acceptance).
    CollateralAcceptance("BINANCE-FUTURES", "stETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("BINANCE-FUTURES", "wstETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("BINANCE-FUTURES", "weETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("BYBIT-FUTURES", "stETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("BYBIT-FUTURES", "wstETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("OKX-FUTURES", "stETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("OKX-FUTURES", "wstETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("KRAKEN-FUTURES", "stETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("KRAKEN-FUTURES", "wstETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("BITFINEX-FUTURES", "stETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("BITGET-FUTURES", "stETH", False, None, "", "Not accepted", "PERP_CEX"),
    # ----- SOL LST acceptance (DRIFT (Solana)/PACIFICA (Solana) rows removed
    # 2026-07-16 — operator ruling: all Solana perp DEXes dropped except
    # Jupiter, not integrated. Remaining venues below don't accept Solana
    # LSTs as cross-margin today). Ethereum-side venues don't carry SOL LSTs
    # at all — no row needed.
    CollateralAcceptance("HYPERLIQUID", "JitoSOL", False, None, "", "Not accepted (USDC-only)", "PERP_CEX"),
    CollateralAcceptance("HYPERLIQUID", "mSOL", False, None, "", "Not accepted (USDC-only)", "PERP_CEX"),
    CollateralAcceptance("BINANCE", "JitoSOL", False, None, "", "Not accepted as futures margin", "PERP_CEX"),
    CollateralAcceptance("BINANCE", "mSOL", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("BYBIT", "JitoSOL", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("OKX", "JitoSOL", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("ASTER", "JitoSOL", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("ASTER", "mSOL", False, None, "", "Not accepted", "PERP_CEX"),
]


PLACEHOLDER_HAIRCUTS_PENDING_GO_LIVE: Final[frozenset[tuple[str, str]]] = frozenset()
"""(venue, token) pairs whose haircut is still an un-probed placeholder. **EMPTY since 2026-06-17** — the former
F28 operator-held placeholder was live-probed + operator-authorised: ``("BYBIT","stETH")`` → 0.10 (Bybit UTA
``collateralRatio`` 0.9). (The former ``("DRIFT","mSOL")`` entry was removed 2026-07-16 along with the rest of the
DRIFT venue — operator ruling.) A go-live preflight asserts this set is empty (it is). Re-add a pair here ONLY if a
new venue-token ships with an un-probed stand-in haircut. SSOT:
``plans/active/engine_findings_remediation_2026_06_15.md`` (F28 live-API probe)."""


def venue_accepts_collateral(venue: str, token: str) -> bool:
    """Check if a venue accepts a given token as collateral.

    Venue lookup is CASE-INSENSITIVE (F27 fix 2026-06-15): callers pass the
    venue id in mixed case (slot-config/catalog use lowercase ``'deribit'``;
    the matrix keys UPPERCASE ``'DERIBIT'``) — a case mismatch previously made
    the accessor silently return the not-accepted answer, so carry-staked-basis
    never emitted. Normalised here so every caller is protected, not just one.
    """
    for entry in VENUE_COLLATERAL_MATRIX:
        if entry.venue.upper() == venue.upper() and entry.token == token:
            return entry.accepted
    return False


def get_collateral_haircut(venue: str, token: str) -> Decimal | None:
    """Get the haircut percentage for a token at a venue, or None if not accepted."""
    for entry in VENUE_COLLATERAL_MATRIX:
        if entry.venue.upper() == venue.upper() and entry.token == token and entry.accepted:
            return entry.haircut_pct
    return None


def get_accepted_collateral(venue: str) -> list[str]:
    """Get list of accepted collateral tokens for a venue."""
    return [e.token for e in VENUE_COLLATERAL_MATRIX if e.venue.upper() == venue.upper() and e.accepted]


def accepted_perp_collateral(venue: str) -> list[str]:
    """Get list of accepted collateral tokens at a perp-margining venue.

    Filters to ``venue_kind in {PERP_CEX, PERP_DEX}``. Used by carry/basis
    strategies that need to know which assets a perp short can post as margin
    — distinct from lending-protocol or staking-protocol acceptance.
    Returns ``[]`` if the venue is not perp-kind or has no accepted rows.
    """
    return [
        e.token
        for e in VENUE_COLLATERAL_MATRIX
        if e.venue.upper() == venue.upper() and e.accepted and e.venue_kind in _PERP_VENUE_KINDS
    ]
