"""Operator-expected coverage policy (SSOT).

Phase 1 of the unified-data-status work — declares the subset of
(asset_group, venue, data_type) tuples we *intend* to keep filled.
Sister registry to :mod:`processed_data_dependencies`; together they
power the four-state data-status view in deployment-ui:

    captured       — manifest row has ``capture_status='captured'``.
    missing        — in-policy, raw shard captured (or this IS raw),
                     but the expected shard is absent. Actionable.
    blocked_on_raw — processed shard absent because the underlying raw
                     shard is absent. Fix raw first; this is derived.
    out_of_scope   — venue x data_type not in EXPECTED_COVERAGE for the
                     active asset_group. Excluded from the denominator;
                     rendered gray (or hidden) in the UI.

Distinction from :data:`VENUE_DATA_TYPE_CAPABILITIES`:

    capability — what a venue *could* emit (declared in
                 ``market_data_categories.py``). Used by adapters to
                 know what calls are valid.
    expected   — what we *plan* to fill (this file). Used by the data-
                 status denominator and by gap-fill launchers to know
                 what to chase.

Operator overrides via UI filter chips overlay on top of this policy
at request time — narrowing the denominator further but never
expanding it.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# CeFi — full Tardis sharded backfill coverage (9 venues x 6 data types).
# All venues capable of every data_type are expected to fill it. Deribit gets
# the full options/futures chain bulk; HYPERLIQUID/ASTER are perp-only.
# ---------------------------------------------------------------------------
_CEFI: dict[str, list[str]] = {
    "BINANCE-SPOT": ["trades", "book_snapshot_5"],
    "BINANCE-FUTURES": [
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "liquidations",
        "futures_chain",
    ],
    "BYBIT": [
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "liquidations",
        "futures_chain",
    ],
    "OKX": ["trades", "book_snapshot_5", "derivative_ticker", "liquidations"],
    "DERIBIT": [
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "liquidations",
        "options_chain",
        "futures_chain",
    ],
    "UPBIT": ["trades", "book_snapshot_5"],
    "COINBASE": ["trades", "book_snapshot_5"],
    "HYPERLIQUID": [
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "liquidations",
    ],
    "ASTER": [
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "liquidations",
    ],
}

# ---------------------------------------------------------------------------
# TradFi — operator-confirmed scope (2026-04-28). CME / ICE futures get
# trades + ohlcv_1m + tbbo via Databento. CBOE provides VIX 15m. FX +
# YAHOO_FINANCE for daily rates / VIX rolling.
#
# DELIBERATELY OMITTED: NASDAQ, NYSE, BARCHART. They are declared in
# ``VENUE_DATA_TYPE_CAPABILITIES`` (capable of trades/ohlcv_1m/tbbo) but
# are NOT in scope today — the operator confirmed "what we have is
# enough for now"; OPRA / per-symbol US-equity tick is cost-prohibitive.
# An operator can opt them back in via the UI filter chips at any time
# without editing this policy.
# ---------------------------------------------------------------------------
_TRADFI: dict[str, list[str]] = {
    "CME": ["trades", "ohlcv_1m", "tbbo"],
    "ICE": ["trades", "ohlcv_1m", "tbbo"],
    "CBOE": ["ohlcv_15m"],
    # NASDAQ + NYSE equity venues added 2026-05-17 per OHLCV-only MVP scope
    # (operator direction 2026-05-15 — see
    # plans/active/tradfi_ohlcv_only_mvp_backfill_2026_05_15.md). Phase 7
    # backfill captured 33,672 NASDAQ + 122,494 NYSE ohlcv_1m rows from
    # 2023-04-15+ via Databento XNAS.ITCH + XNYS.PILLAR. Before this entry
    # the venues were silently out_of_scope in the data-status denominator.
    "NASDAQ": ["ohlcv_1m"],
    "NYSE": ["ohlcv_1m"],
    "FX": ["ohlcv_24h"],
    "YAHOO_FINANCE": ["ohlcv_15m", "ohlcv_24h"],
}

# ---------------------------------------------------------------------------
# DeFi — Phase 1 expansion (2026-04-24). Scope set declares the data types
# each protocol-chain composite is expected to fill. Pass-through types
# (lending_indices, perp_funding, oracle_prices, gas_fees, rewards, …) live
# alongside candle-built types (dex_swaps, dex_pools).
#
# Per protocol family:
#   DEXes   → dex_pools, dex_swaps
#   Lending → lending_indices, liquidation_events, position_data
#             (+ flash_loan_events on Aave V3 only)
#   LST     → lst_rates, staking_yields
#   Cross-chain   → bridge_events, token_transfers (selective)
#   Oracle / gas  → oracle_prices, gas_fees (chain-level)
# ---------------------------------------------------------------------------
_DEFI_DEX_PAIRS: list[str] = ["dex_pools", "dex_swaps"]
_DEFI_LENDING_PAIRS: list[str] = [
    "lending_indices",
    "liquidation_events",
    "position_data",
    "risk_params",
]
_DEFI_LENDING_AAVE_PAIRS: list[str] = [*_DEFI_LENDING_PAIRS, "flash_loan_events"]
_DEFI_LST_PAIRS: list[str] = ["lst_rates", "staking_yields"]

_DEFI: dict[str, list[str]] = {
    # --- DEX protocols ---
    "UNISWAPV2-ETHEREUM": list(_DEFI_DEX_PAIRS),
    "UNISWAPV3-ETHEREUM": list(_DEFI_DEX_PAIRS),
    "UNISWAPV3-ARBITRUM": list(_DEFI_DEX_PAIRS),
    "UNISWAPV3-BASE": list(_DEFI_DEX_PAIRS),
    "UNISWAPV3-OPTIMISM": list(_DEFI_DEX_PAIRS),
    "UNISWAPV3-POLYGON": list(_DEFI_DEX_PAIRS),
    "UNISWAPV4-ETHEREUM": list(_DEFI_DEX_PAIRS),
    "CURVE-ETHEREUM": list(_DEFI_DEX_PAIRS),
    "CURVE-AVALANCHE": list(_DEFI_DEX_PAIRS),
    "CURVE-OPTIMISM": list(_DEFI_DEX_PAIRS),
    "BALANCER-ETHEREUM": list(_DEFI_DEX_PAIRS),
    "BALANCER-ARBITRUM": list(_DEFI_DEX_PAIRS),
    "BALANCER-AVALANCHE": list(_DEFI_DEX_PAIRS),
    "BALANCER-BASE": list(_DEFI_DEX_PAIRS),
    "BALANCER-OPTIMISM": list(_DEFI_DEX_PAIRS),
    "BALANCER-POLYGON": list(_DEFI_DEX_PAIRS),
    # --- Lending protocols ---
    "AAVEV3-ETHEREUM": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-ARBITRUM": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-AVALANCHE": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-BASE": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-BSC": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-LINEA": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-OPTIMISM": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-POLYGON": list(_DEFI_LENDING_AAVE_PAIRS),
    "COMPOUNDV3-ETHEREUM": list(_DEFI_LENDING_PAIRS),
    "COMPOUNDV3-ARBITRUM": list(_DEFI_LENDING_PAIRS),
    "COMPOUNDV3-BASE": list(_DEFI_LENDING_PAIRS),
    "COMPOUNDV3-OPTIMISM": list(_DEFI_LENDING_PAIRS),
    "COMPOUNDV3-POLYGON": list(_DEFI_LENDING_PAIRS),
    "MORPHO-ETHEREUM": list(_DEFI_LENDING_PAIRS),
    "MORPHO-ARBITRUM": list(_DEFI_LENDING_PAIRS),
    "MORPHO-BASE": list(_DEFI_LENDING_PAIRS),
    "MORPHO-OPTIMISM": list(_DEFI_LENDING_PAIRS),
    "MORPHO-POLYGON": list(_DEFI_LENDING_PAIRS),
    "FLUID-ETHEREUM": list(_DEFI_LENDING_PAIRS),
    # --- LST / yield ---
    "LIDO-ETHEREUM": list(_DEFI_LST_PAIRS),
    "ETHERFI-ETHEREUM": [*_DEFI_LST_PAIRS, "eigenlayer_rewards"],
    "ETHENA-ETHEREUM": list(_DEFI_LST_PAIRS),
    "JITO-SOLANA": list(_DEFI_LST_PAIRS),
}

# ---------------------------------------------------------------------------
# Sports — ODDS_API is the raw odds source; per-bookmaker venues emit
# point-in-time odds_snapshot + odds_movement for cross-feed validation.
#
# DELIBERATELY OMITTED on capability rows: arbitrage_opportunity. It is a
# purely-derived MDPS output (cross-bookmaker disparity) — not emitted by
# any venue. Lives in :mod:`processed_data_dependencies` instead.
# ---------------------------------------------------------------------------
_SPORTS: dict[str, list[str]] = {
    "ODDS_API": ["odds"],
    "PINNACLE": ["odds_snapshot", "odds_movement"],
    "BETFAIR": ["odds_snapshot", "odds_movement"],
    "DRAFTKINGS": ["odds_snapshot", "odds_movement"],
    "FANDUEL": ["odds_snapshot", "odds_movement"],
    "BET365": ["odds_snapshot", "odds_movement"],
}

# ---------------------------------------------------------------------------
# Prediction — Polymarket + Kalshi CLOB trades. book_snapshot_5 was retired
# 2026-04-19 (neither adapter captures order book snapshots). Polymarket
# "other" categorisation already lives in instruments-service Polymarket
# adapter — surfaces in the UI via the instrument_type breakdown, no
# separate data_type needed here.
# ---------------------------------------------------------------------------
_PREDICTION: dict[str, list[str]] = {
    "POLYMARKET": ["trades"],
    "KALSHI": ["trades"],
}


EXPECTED_COVERAGE_BY_ASSET_GROUP: dict[str, dict[str, list[str]]] = {
    "cefi": _CEFI,
    "tradfi": _TRADFI,
    "defi": _DEFI,
    "sports": _SPORTS,
    "prediction": _PREDICTION,
}


def is_expected(asset_group: str, venue: str, data_type: str) -> bool:
    """Return ``True`` iff ``(asset_group, venue, data_type)`` is in scope.

    Used by deployment-api to decide whether a missing manifest shard
    counts against the denominator (in-scope) or is excluded as
    out-of-scope. UI filter chips narrow this further at request time.
    """
    ag_scope = EXPECTED_COVERAGE_BY_ASSET_GROUP.get(asset_group.lower(), {})
    return data_type in ag_scope.get(venue, [])


def get_expected_data_types_for_venue_in_scope(asset_group: str, venue: str) -> list[str]:
    """Return the in-scope data_types for ``(asset_group, venue)``.

    Empty list means the venue is entirely out-of-scope for the asset
    group's expected-coverage policy. Callers branch on truthiness:
    truthy → include venue in denominator; falsy → render as
    ``out_of_scope``.
    """
    ag_scope = EXPECTED_COVERAGE_BY_ASSET_GROUP.get(asset_group.lower(), {})
    return list(ag_scope.get(venue, []))


def get_expected_venues_in_scope(asset_group: str) -> list[str]:
    """Return the venues with at least one expected data_type in this asset group."""
    ag_scope = EXPECTED_COVERAGE_BY_ASSET_GROUP.get(asset_group.lower(), {})
    return [venue for venue, dts in ag_scope.items() if dts]


def get_expected_pairs(asset_group: str) -> list[tuple[str, str]]:
    """Flatten to ``(venue, data_type)`` tuples for the asset group."""
    ag_scope = EXPECTED_COVERAGE_BY_ASSET_GROUP.get(asset_group.lower(), {})
    return [(venue, dt) for venue, dts in ag_scope.items() for dt in dts]


__all__ = [
    "EXPECTED_COVERAGE_BY_ASSET_GROUP",
    "get_expected_data_types_for_venue_in_scope",
    "get_expected_pairs",
    "get_expected_venues_in_scope",
    "is_expected",
]
