"""Full combinatoric envelope of the strategy catalogue.

Unlike ``enumerate_catalogue.py`` (which prints the 99 curated representative
instances from ``STRATEGY_REGISTRY``), this script multiplies out each
archetype's capability claim into the full sensible product across venues,
chains (DeFi), timeframes, and style variants.

Dimensions treated as combinatoric multipliers:
- Venue (and venue-pairs for arbitrage archetypes)
- Chain (DeFi venues only)
- Timeframe (per archetype family policy)
- MM style (passive / inventory-skew / queue-microstructure — ML-lean is its own archetype)
- Vol style (split VOL_TRADING_OPTIONS into 9 distinct archetypes)

NOT combinatoric:
- Share class — crypto = selectable {BTC | ETH | USDT}, non-crypto = USD.
  Multi-SC access is an upgrade tier, not catalogue rows.
- Portfolio composition — portfolio strategies have a bounded sample of
  canonical configs + a bespoke row.

Bespoke-capable archetypes also emit a single ``{ARCHETYPE}_CUSTOM`` row
with ∞ instances (per-client bespoke construction).

VOL split, MM split, PORTFOLIO family, and bespoke rows are currently mocked
in this script — they are not yet in the UAC capability manifest. See the
active DART UI plan for the Phase 9 amendment that lifts these into UAC.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

# ---------------------------------------------------------------------------
# Manifest loading — read JSON directly, bypass UAC package __init__ (which is
# currently breaking on unrelated ProfileYaml validation from a parallel agent).
# ---------------------------------------------------------------------------

_MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "unified_api_contracts"
    / "internal"
    / "architecture_v2"
    / "archetype_capability_manifest.json"
)

# DeFi chain mapping, inlined from _defi.py so this script stays decoupled.
_DEFI_VENUE_CHAINS: dict[str, list[str]] = {
    "aave_v3": ["ethereum", "arbitrum", "optimism", "polygon", "avalanche", "base", "linea", "bsc"],
    "compound_v3": ["ethereum", "arbitrum", "optimism", "polygon", "base"],
    "morpho": ["ethereum", "base"],
    "uniswap_v3": ["ethereum", "arbitrum", "optimism", "polygon", "base", "bsc"],
    "pancakeswap_v3": ["bsc", "ethereum", "arbitrum", "base"],
    "balancer": ["ethereum", "arbitrum", "optimism", "polygon", "base"],
    "curve": ["ethereum", "arbitrum", "optimism", "polygon", "base"],
    "maverick": ["ethereum", "base", "bsc"],
    "sushiswap": ["ethereum", "arbitrum", "polygon", "base"],
    "pancakeswap": ["bsc", "ethereum", "arbitrum", "base"],
    "gmx": ["arbitrum", "avalanche"],
    "spark": ["ethereum"],
    "lido": ["ethereum"],
    "etherfi": ["ethereum"],
    "ethena": ["ethereum"],
    "eigenlayer": ["ethereum"],
    "hyperliquid": ["hyperliquid"],
    "aster": ["aster"],
    "drift": ["solana"],
    "kamino": ["solana"],
    "raydium": ["solana"],
    "orca": ["solana"],
    "jito": ["solana"],
    # LP vault wrappers
    "gamma": ["ethereum", "arbitrum", "optimism", "polygon", "base"],
    "arrakis": ["ethereum", "arbitrum", "optimism", "polygon", "base"],
    "steer": ["arbitrum", "polygon", "base", "bsc"],
}


def get_supported_chains_for_protocol(protocol: str) -> list[str]:
    return _DEFI_VENUE_CHAINS.get(protocol, [])


# ---------------------------------------------------------------------------
# Per-category venue universe (primary-category axis, 2026-04-24)
# ---------------------------------------------------------------------------
# Realistic venue lists per category, wider than the conservative manifest
# venue_ids. The envelope uses these in preference to cell.venue_ids so the
# catalogue reflects the accessible universe, not just currently-integrated
# venues.

_CEFI_SPOT_PERP_VENUES = [
    "binance", "okx", "bybit", "hyperliquid", "deribit",
    "coinbase", "kraken", "bitget", "gate", "kucoin",
]
_CEFI_OPTION_VENUES = ["deribit", "okx", "bybit", "binance", "bit_com"]
_DEFI_DEX_SPOT = ["uniswap_v3", "pancakeswap_v3", "balancer", "curve", "sushiswap", "maverick"]
_DEFI_PERP = ["hyperliquid", "gmx", "drift", "dydx_v4", "aster"]
_DEFI_LENDING = ["aave_v3", "compound_v3", "morpho", "spark"]
_DEFI_STAKING = ["lido", "etherfi", "ethena", "jito", "kamino"]
_DEFI_LP_CONC = ["uniswap_v3", "pancakeswap_v3"]
_DEFI_LP_POOL = ["balancer", "curve", "maverick"]
_DEFI_LP_VAULT = ["gamma", "arrakis", "steer"]
_TRADFI_CASH_FUT = [
    "ibkr", "cme", "ice", "saxo", "lmax", "eurex", "nyse", "nasdaq",
]
_TRADFI_OPTION = ["cboe", "cme", "eurex"]
_SPORTS_VENUES = [
    "unity", "betfair_direct", "smarkets_direct", "sporttrade",
    "sportradar", "fanduel", "draftkings",
]
_PREDICTION_VENUES = ["polymarket", "kalshi", "unity"]


def _category_venues(category: str, instrument: str, archetype_id: str) -> list[str]:
    """Return the accessible-universe venue list for a (category, instrument) pair.

    Falls back to empty list if the combination is nonsensical — callers should
    then use the manifest-declared venue_ids or skip the cell.
    """
    if category == "CEFI":
        if instrument == "option":
            return list(_CEFI_OPTION_VENUES)
        if instrument in ("spot", "perp", "dated_future"):
            return list(_CEFI_SPOT_PERP_VENUES)
    if category == "DEFI":
        if instrument == "spot":
            return list(_DEFI_DEX_SPOT)
        if instrument == "perp":
            return list(_DEFI_PERP)
        if instrument == "lending":
            return list(_DEFI_LENDING)
        if instrument == "staking":
            return list(_DEFI_STAKING)
        if instrument == "lp":
            if archetype_id == "DEFI_LP_CONCENTRATED":
                return list(_DEFI_LP_CONC)
            if archetype_id == "DEFI_LP_POOL":
                return list(_DEFI_LP_POOL)
            if archetype_id == "DEFI_LP_VAULT":
                return list(_DEFI_LP_VAULT)
            return list(_DEFI_DEX_SPOT)  # generic LP fallback
    if category == "TRADFI":
        if instrument == "option":
            return list(_TRADFI_OPTION)
        if instrument in ("spot", "dated_future"):
            return list(_TRADFI_CASH_FUT)
    if category == "SPORTS":
        return list(_SPORTS_VENUES)
    if category == "PREDICTION":
        return list(_PREDICTION_VENUES)
    return []


# ---------------------------------------------------------------------------
# Category × archetype capability rules — what you cannot do on which venue
# ---------------------------------------------------------------------------
# Defense-in-depth over the manifest: explicitly forbids combinations that
# make no sense (VOL options on sports, DeFi LP on TradFi, etc.). If the
# manifest has a cell the rules forbid, that cell is skipped.

_ARCHETYPE_ALLOWED_CATEGORIES: dict[str, set[str]] = {
    # Carry / yield — no funding or lending on sports/prediction
    "CARRY_BASIS_PERP": {"CEFI", "DEFI"},
    "CARRY_BASIS_DATED": {"CEFI", "TRADFI"},
    "CARRY_STAKED_BASIS": {"DEFI"},
    "CARRY_RECURSIVE_STAKED": {"DEFI"},
    "YIELD_ROTATION_LENDING": {"DEFI"},
    "YIELD_STAKING_SIMPLE": {"DEFI"},
    # Liquidation capture — on-venue only
    "LIQUIDATION_CAPTURE": {"CEFI", "DEFI"},
    # Arbitrage runs everywhere
    "ARBITRAGE_PRICE_DISPERSION": {"CEFI", "DEFI", "TRADFI", "SPORTS", "PREDICTION"},
    # Stat-arb — no coherent pair microstructure on sports/prediction
    "STAT_ARB_PAIRS_FIXED": {"CEFI", "DEFI", "TRADFI"},
    "STAT_ARB_CROSS_SECTIONAL": {"CEFI", "DEFI", "TRADFI"},
    # ML directional split by continuous vs event-settled
    "ML_DIRECTIONAL_CONTINUOUS": {"CEFI", "DEFI", "TRADFI"},
    "ML_DIRECTIONAL_EVENT_SETTLED": {"SPORTS", "PREDICTION"},
    "RULES_DIRECTIONAL_CONTINUOUS": {"CEFI", "DEFI", "TRADFI"},
    "RULES_DIRECTIONAL_EVENT_SETTLED": {"SPORTS", "PREDICTION"},
    # Event-driven — macro/news on financial, binary events on sports/prediction
    "EVENT_DRIVEN": {"CEFI", "TRADFI", "SPORTS", "PREDICTION"},
    # VOL archetypes — options venues only
    "VOL_ARB_RV_IV": {"CEFI", "TRADFI"},
    "VOL_SPREAD_STRUCTURES": {"CEFI", "TRADFI"},
    "VOL_CARRY": {"CEFI"},
    "VOL_OVERLAY_COVERED_CALLS": {"CEFI", "TRADFI"},
    "VOL_OVERLAY_PROTECTIVE_PUT": {"CEFI", "TRADFI"},
    "VOL_STRADDLE": {"CEFI", "TRADFI"},
    "VOL_SYNTHETIC_DELTA": {"CEFI"},
    "VOL_MARKET_MAKING": {"CEFI", "TRADFI"},
    "VOL_ML_LEAN": {"CEFI"},
    # 0DTE + term-structure
    "VOL_0DTE_GAMMA_SCALPING": {"CEFI", "TRADFI"},
    "VOL_0DTE_PIN_RISK": {"CEFI", "TRADFI"},
    "VOL_TERM_STRUCTURE_ARB": {"CEFI", "TRADFI"},
    "VOL_TERM_STRUCTURE_SLOPE": {"CEFI", "TRADFI"},
    "VOL_DISPERSION": {"CEFI", "TRADFI"},
    "VOL_VARIANCE_SWAP": {"CEFI", "TRADFI"},
    "VOL_LEAPS_CONVEXITY": {"CEFI", "TRADFI"},
    "VOL_CROSS_ASSET_SPREAD": {"CEFI", "TRADFI"},
    "VOL_RATIO_SPREAD": {"CEFI", "TRADFI"},
    # MEV — DeFi-only structural edges from blockchain mechanics
    "ARBITRAGE_MEV_SANDWICH": {"DEFI"},
    "ARBITRAGE_MEV_JIT_LIQUIDITY": {"DEFI"},
    "ARBITRAGE_MEV_BACKRUN": {"DEFI"},
    "ARBITRAGE_MEV_LIQUIDATION_BUNDLE": {"DEFI"},
    # Cross-domain event arb (PREDICTION + SPORTS), prediction MM
    "ARBITRAGE_CROSS_DOMAIN_EVENT": {"CROSS_CATEGORY"},
    "MARKET_MAKING_PREDICTION": {"PREDICTION"},
    # MM
    "MARKET_MAKING_PASSIVE_SPREAD": {"CEFI", "DEFI"},
    "MARKET_MAKING_INVENTORY_SKEW": {"CEFI", "DEFI"},
    "MARKET_MAKING_ML_LEAN": {"CEFI", "DEFI"},
    "MARKET_MAKING_QUEUE_MICROSTRUCTURE": {"CEFI"},  # no queue on AMMs
    "DEFI_LP_CONCENTRATED": {"DEFI"},
    "DEFI_LP_POOL": {"DEFI"},
    "DEFI_LP_VAULT": {"DEFI"},
    # Portfolio — cross-category
    "PORTFOLIO_MULTI_STRATEGY": {"CROSS_CATEGORY"},
    "PORTFOLIO_RISK_PARITY": {"CROSS_CATEGORY"},
    "PORTFOLIO_FACTOR_ALLOCATION": {"CROSS_CATEGORY"},
    "PORTFOLIO_TACTICAL_OVERLAY": {"CROSS_CATEGORY"},
}


def _category_allowed(archetype_id: str, category: str) -> bool:
    allowed = _ARCHETYPE_ALLOWED_CATEGORIES.get(archetype_id)
    if allowed is None:
        return True  # no rule = permit (conservative on unknowns)
    return category in allowed


# ---------------------------------------------------------------------------
# Timeframe policy per archetype family prefix
# ---------------------------------------------------------------------------

_TIMEFRAMES_BY_PREFIX: list[tuple[str, list[str]]] = [
    ("ML_DIRECTIONAL", ["5m", "1h", "1d"]),
    ("RULES_DIRECTIONAL", ["5m", "1h", "1d"]),
    ("ARBITRAGE", ["tick", "1m", "5m"]),
    ("STAT_ARB", ["5m", "1h"]),
    ("CARRY_BASIS", ["4h", "1d"]),
    ("CARRY_STAKED", ["1d"]),
    ("CARRY_RECURSIVE", ["1d"]),
    ("YIELD_ROTATION", ["1d", "1w"]),
    ("YIELD_STAKING", ["1d", "1w"]),
    ("LIQUIDATION_CAPTURE", ["tick", "1m"]),
    ("MARKET_MAKING", ["tick", "1m"]),
    ("DEFI_LP", ["1h", "1d"]),
    ("EVENT_DRIVEN", ["event"]),
    ("VOL_ARB", ["1h", "1d"]),
    ("VOL_SPREAD", ["1d"]),
    ("VOL_CARRY", ["1d"]),
    ("VOL_OVERLAY", ["1d"]),
    ("VOL_STRADDLE", ["1h", "1d"]),
    ("VOL_SYNTHETIC", ["1d"]),
    ("VOL_MARKET_MAKING", ["tick", "1m"]),
    ("VOL_ML_LEAN", ["1h", "1d"]),
    ("VOL_TRADING", ["1h", "1d"]),  # fallback for manifest VOL_TRADING_OPTIONS
    ("PORTFOLIO", ["1d"]),
]


def _timeframes_for(archetype_id: str) -> list[str]:
    for prefix, tfs in _TIMEFRAMES_BY_PREFIX:
        if archetype_id.startswith(prefix):
            return tfs
    return ["1d"]


# ---------------------------------------------------------------------------
# Venue-combo policy
# ---------------------------------------------------------------------------

_CROSS_VENUE_ARCHETYPES: set[str] = {
    "ARBITRAGE_PRICE_DISPERSION",
    "STAT_ARB_PAIRS_FIXED",
    "STAT_ARB_CROSS_SECTIONAL",
    "YIELD_ROTATION_LENDING",
}

_SAME_VENUE_BASIS: set[str] = {
    "CARRY_BASIS_PERP",
    "CARRY_BASIS_DATED",
}


# ---------------------------------------------------------------------------
# Bespoke-capable archetypes — emit a ``{id}_CUSTOM`` row with ∞ instances
# ---------------------------------------------------------------------------

_BESPOKE_CAPABLE: set[str] = {
    # Stat-arb: infinite pair / factor / residualisation designs
    "STAT_ARB_PAIRS_FIXED",
    "STAT_ARB_CROSS_SECTIONAL",
    # Rules: infinite custom logic
    "RULES_DIRECTIONAL_CONTINUOUS",
    "RULES_DIRECTIONAL_EVENT_SETTLED",
    # Event-driven: what event?
    "EVENT_DRIVEN",
    # ML: custom features/labels/models
    "ML_DIRECTIONAL_CONTINUOUS",
    "ML_DIRECTIONAL_EVENT_SETTLED",
    # Arbitrage: custom execution/routing
    "ARBITRAGE_PRICE_DISPERSION",
    # Market making: custom spread/inventory rules (applies to each MM archetype)
    "MARKET_MAKING_PASSIVE_SPREAD",
    "MARKET_MAKING_INVENTORY_SKEW",
    "MARKET_MAKING_ML_LEAN",
    "MARKET_MAKING_QUEUE_MICROSTRUCTURE",
    "DEFI_LP_CONCENTRATED",
    "DEFI_LP_POOL",
    "DEFI_LP_VAULT",
    # All Vol archetypes
    "VOL_ARB_RV_IV",
    "VOL_SPREAD_STRUCTURES",
    "VOL_CARRY",
    "VOL_OVERLAY_COVERED_CALLS",
    "VOL_OVERLAY_PROTECTIVE_PUT",
    "VOL_STRADDLE",
    "VOL_SYNTHETIC_DELTA",
    "VOL_MARKET_MAKING",
    "VOL_ML_LEAN",
    "VOL_0DTE_GAMMA_SCALPING",
    "VOL_0DTE_PIN_RISK",
    "VOL_TERM_STRUCTURE_ARB",
    "VOL_TERM_STRUCTURE_SLOPE",
    "VOL_DISPERSION",
    "VOL_VARIANCE_SWAP",
    "VOL_LEAPS_CONVEXITY",
    "VOL_CROSS_ASSET_SPREAD",
    "VOL_RATIO_SPREAD",
    # MEV (DeFi-only structural arb)
    "ARBITRAGE_MEV_SANDWICH",
    "ARBITRAGE_MEV_JIT_LIQUIDITY",
    "ARBITRAGE_MEV_BACKRUN",
    "ARBITRAGE_MEV_LIQUIDATION_BUNDLE",
    # Cross-domain event arb + prediction MM
    "ARBITRAGE_CROSS_DOMAIN_EVENT",
    "MARKET_MAKING_PREDICTION",
    # Portfolio construction
    "PORTFOLIO_MULTI_STRATEGY",
    "PORTFOLIO_RISK_PARITY",
    "PORTFOLIO_FACTOR_ALLOCATION",
    "PORTFOLIO_TACTICAL_OVERLAY",
}


# ---------------------------------------------------------------------------
# VOL split — replaces manifest's single VOL_TRADING_OPTIONS archetype
# ---------------------------------------------------------------------------

_OPTION_CEFI_VENUES = ["deribit", "okx", "bybit"]
_OPTION_TRADFI_VENUES = ["cboe", "cme"]


def _vol_cell(category: str, instrument: str, venues: list[str]) -> dict:
    return {
        "category": category,
        "instrument_type": instrument,
        "status": "SUPPORTED",
        "venue_ids": venues,
    }


# Tenor axis for option strategies — 0DTE (same-day) is materially distinct
# from short-dated and dated options. Different gamma profile, hedging cadence,
# pin-risk dynamics. Most VOL archetypes apply across a subset of tenors.
_TENOR_BUCKETS_BY_ARCHETYPE: dict[str, list[str]] = {
    "VOL_ARB_RV_IV": ["weekly", "monthly", "quarterly"],
    "VOL_SPREAD_STRUCTURES": ["weekly", "monthly", "quarterly"],
    "VOL_CARRY": ["0dte", "weekly", "monthly"],
    "VOL_OVERLAY_COVERED_CALLS": ["weekly", "monthly", "quarterly"],
    "VOL_OVERLAY_PROTECTIVE_PUT": ["monthly", "quarterly", "leaps"],
    "VOL_STRADDLE": ["0dte", "weekly", "monthly"],
    "VOL_SYNTHETIC_DELTA": ["weekly", "monthly", "quarterly"],
    "VOL_MARKET_MAKING": ["0dte", "weekly", "monthly", "quarterly"],
    "VOL_ML_LEAN": ["0dte", "weekly", "monthly"],
    # 0DTE-specific archetypes — only same-day expiry by definition
    "VOL_0DTE_GAMMA_SCALPING": ["0dte"],
    "VOL_0DTE_PIN_RISK": ["0dte"],
    # Term-structure archetypes — cross-tenor by definition; one row per category
    "VOL_TERM_STRUCTURE_ARB": ["multi-tenor"],
    "VOL_TERM_STRUCTURE_SLOPE": ["multi-tenor"],
    "VOL_DISPERSION": ["weekly", "monthly", "quarterly"],
    "VOL_VARIANCE_SWAP": ["monthly", "quarterly"],
    "VOL_LEAPS_CONVEXITY": ["leaps"],
    "VOL_CROSS_ASSET_SPREAD": ["weekly", "monthly", "quarterly"],
    "VOL_RATIO_SPREAD": ["weekly", "monthly", "quarterly"],
}


def _tenors_for(archetype_id: str) -> list[str]:
    return _TENOR_BUCKETS_BY_ARCHETYPE.get(archetype_id, ["weekly"])


_VOL_SPLIT: list[dict] = [
    {
        "archetype_id": "VOL_ARB_RV_IV",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    {
        "archetype_id": "VOL_SPREAD_STRUCTURES",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    {
        "archetype_id": "VOL_CARRY",
        "family": "VOL_TRADING",
        "cells": [_vol_cell("CEFI", "option", _OPTION_CEFI_VENUES)],
    },
    {
        "archetype_id": "VOL_OVERLAY_COVERED_CALLS",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    {
        "archetype_id": "VOL_OVERLAY_PROTECTIVE_PUT",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    {
        "archetype_id": "VOL_STRADDLE",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    {
        "archetype_id": "VOL_SYNTHETIC_DELTA",
        "family": "VOL_TRADING",
        "cells": [_vol_cell("CEFI", "option", _OPTION_CEFI_VENUES)],
    },
    {
        "archetype_id": "VOL_MARKET_MAKING",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    {
        "archetype_id": "VOL_ML_LEAN",
        "family": "VOL_TRADING",
        "cells": [_vol_cell("CEFI", "option", _OPTION_CEFI_VENUES)],
    },
    # 0DTE-specific archetypes (added 2026-04-25)
    # 0DTE has its own dynamics — gamma flip, pin risk, end-of-day settlement.
    # Sakuma et al. differential ML for 0DTE under stoch-vol+jumps maps to
    # VOL_0DTE_GAMMA_SCALPING (CEFI/TRADFI) as the strategy-side wrapper;
    # the pricing/Greeks engine itself is feature/library infrastructure.
    {
        "archetype_id": "VOL_0DTE_GAMMA_SCALPING",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    {
        "archetype_id": "VOL_0DTE_PIN_RISK",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    # Term-structure archetypes — explicit curve trading (added 2026-04-25)
    {
        "archetype_id": "VOL_TERM_STRUCTURE_ARB",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    {
        "archetype_id": "VOL_TERM_STRUCTURE_SLOPE",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    {
        "archetype_id": "VOL_DISPERSION",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    # Variance swap trading — direct (where listed) or replicated via option strip
    # (Carr-Madan 2001). Listed variance products on Eurex / OTC; replicated on
    # CEFI option venues via deep-OTM strip portfolios.
    {
        "archetype_id": "VOL_VARIANCE_SWAP",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    # LEAPS convexity — long-dated convex payoff structures (6m+). Delta-1 via
    # LEAPS calls (cheaper synthetic exposure with positive convexity), portfolio
    # insurance ladders (rolling LEAPS puts), long-vega buys for regime shifts.
    {
        "archetype_id": "VOL_LEAPS_CONVEXITY",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    # Cross-asset vol relative-value — BTC vol vs ETH vol, SPX vol vs Treasury
    # vol, gold vol vs equity vol. Distinct from VOL_DISPERSION (index vs
    # components on a single underlying); this trades vol *between* assets.
    {
        "archetype_id": "VOL_CROSS_ASSET_SPREAD",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
    # Ratio-spread structures — 1×2, 2×3, broken-wing flies. Signal-driven
    # strike selection (delta-anchored). Variants: premium-flat (zero net
    # premium → no loss if no move, profit on big breakout, body-loss zone
    # accepted), premium-credit (collect premium for body view), premium-debit
    # (pay for upside convexity).
    {
        "archetype_id": "VOL_RATIO_SPREAD",
        "family": "VOL_TRADING",
        "cells": [
            _vol_cell("CEFI", "option", _OPTION_CEFI_VENUES),
            _vol_cell("TRADFI", "option", _OPTION_TRADFI_VENUES),
        ],
    },
]


# ---------------------------------------------------------------------------
# MEV split — DeFi-only structural edges from blockchain mechanics.
# Sits under ARBITRAGE_STRUCTURAL family because the edge is mechanical,
# not predictive. Daian et al "Flash Boys 2.0" (2019), Qin et al sandwich
# analysis (2021), Wan-Adams JIT liquidity (2022).
# ---------------------------------------------------------------------------

# MEV operates across DEX venues; chain expansion handles the chain dimension.
# Use the wider DEX list rather than just LP-specific ones.
_MEV_DEX_VENUES = ["uniswap_v3", "pancakeswap_v3", "balancer", "curve", "sushiswap", "maverick"]
_MEV_LENDING_VENUES = ["aave_v3", "compound_v3", "morpho", "spark"]


def _mev_cell(category: str, instrument: str, venues: list[str]) -> dict:
    return {
        "category": category,
        "instrument_type": instrument,
        "status": "SUPPORTED",
        "venue_ids": venues,
    }


_MEV_SPLIT: list[dict] = [
    {
        "archetype_id": "ARBITRAGE_MEV_SANDWICH",
        "family": "ARBITRAGE_STRUCTURAL",
        "cells": [_mev_cell("DEFI", "spot", _MEV_DEX_VENUES)],
    },
    {
        "archetype_id": "ARBITRAGE_MEV_JIT_LIQUIDITY",
        "family": "ARBITRAGE_STRUCTURAL",
        "cells": [_mev_cell("DEFI", "lp", ["uniswap_v3", "pancakeswap_v3"])],
    },
    {
        "archetype_id": "ARBITRAGE_MEV_BACKRUN",
        "family": "ARBITRAGE_STRUCTURAL",
        "cells": [_mev_cell("DEFI", "spot", _MEV_DEX_VENUES)],
    },
    {
        "archetype_id": "ARBITRAGE_MEV_LIQUIDATION_BUNDLE",
        "family": "ARBITRAGE_STRUCTURAL",
        "cells": [_mev_cell("DEFI", "lending", _MEV_LENDING_VENUES)],
    },
]


# ---------------------------------------------------------------------------
# Cross-domain event arb — same real-world event listed across SPORTS and
# PREDICTION (e.g. Polymarket football market vs Betfair football market on
# the same match). Lives in CROSS_CATEGORY because no single primary category
# describes it. Venue list is the cross-product of (sports books × prediction
# markets) — each pair is an arb leg target.
# ---------------------------------------------------------------------------

def _cross_domain_pairs() -> list[str]:
    pairs: list[str] = []
    for s in _SPORTS_VENUES:
        for p in _PREDICTION_VENUES:
            if s == p:
                continue  # same venue listed in both universes — not a cross-domain pair
            pairs.append(f"{s}↔{p}")
    return pairs


_CROSS_DOMAIN_SPLIT: list[dict] = [
    {
        "archetype_id": "ARBITRAGE_CROSS_DOMAIN_EVENT",
        "family": "ARBITRAGE_STRUCTURAL",
        "cells": [
            {
                "category": "CROSS_CATEGORY",
                "instrument_type": "event_settled",
                "status": "SUPPORTED",
                "venue_ids": _cross_domain_pairs(),
                "note": "Same real-world event listed in both SPORTS and PREDICTION; arb the price difference.",
            },
        ],
    },
    # Prediction-market MM — 2-sided quoting on Polymarket / Kalshi.
    # Different mechanics from CEFI/DEFI MM: binary outcomes, time-to-resolution
    # decay, low-volume long-tail markets where MM is the main liquidity source.
    {
        "archetype_id": "MARKET_MAKING_PREDICTION",
        "family": "MARKET_MAKING",
        "cells": [
            {
                "category": "PREDICTION",
                "instrument_type": "event_settled",
                "status": "SUPPORTED",
                "venue_ids": list(_PREDICTION_VENUES),
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# MM split — replaces manifest's single MARKET_MAKING archetype
# ---------------------------------------------------------------------------

_MM_CEFI_VENUES = ["binance", "okx", "bybit", "hyperliquid", "deribit", "coinbase", "kraken"]


def _mm_cell(category: str, instrument: str, venues: list[str]) -> dict:
    return {
        "category": category,
        "instrument_type": instrument,
        "status": "SUPPORTED",
        "venue_ids": venues,
    }


_MM_SPLIT: list[dict] = [
    {
        "archetype_id": "MARKET_MAKING_PASSIVE_SPREAD",
        "family": "MARKET_MAKING",
        "cells": [
            _mm_cell("CEFI", "spot", _MM_CEFI_VENUES),
            _mm_cell("CEFI", "perp", _MM_CEFI_VENUES),
        ],
    },
    {
        "archetype_id": "MARKET_MAKING_INVENTORY_SKEW",
        "family": "MARKET_MAKING",
        "cells": [
            _mm_cell("CEFI", "spot", _MM_CEFI_VENUES),
            _mm_cell("CEFI", "perp", _MM_CEFI_VENUES),
        ],
    },
    {
        "archetype_id": "MARKET_MAKING_ML_LEAN",
        "family": "MARKET_MAKING",
        "cells": [
            _mm_cell("CEFI", "spot", _MM_CEFI_VENUES),
            _mm_cell("CEFI", "perp", _MM_CEFI_VENUES),
        ],
    },
    {
        "archetype_id": "MARKET_MAKING_QUEUE_MICROSTRUCTURE",
        "family": "MARKET_MAKING",
        "cells": [
            _mm_cell("CEFI", "spot", _MM_CEFI_VENUES),
            _mm_cell("CEFI", "perp", _MM_CEFI_VENUES),
        ],
    },
    {
        "archetype_id": "DEFI_LP_CONCENTRATED",
        "family": "MARKET_MAKING",
        "cells": [_mm_cell("DEFI", "lp", ["uniswap_v3", "pancakeswap_v3"])],
    },
    {
        "archetype_id": "DEFI_LP_POOL",
        "family": "MARKET_MAKING",
        "cells": [_mm_cell("DEFI", "lp", ["balancer", "curve", "maverick"])],
    },
    {
        "archetype_id": "DEFI_LP_VAULT",
        "family": "MARKET_MAKING",
        "cells": [_mm_cell("DEFI", "lp", ["gamma", "arrakis", "steer"])],
    },
]


# ---------------------------------------------------------------------------
# PORTFOLIO family — new, not in manifest. Counts are canonical sample configs.
# ---------------------------------------------------------------------------

_PORTFOLIO_ARCHETYPES: list[tuple[str, int, str]] = [
    ("PORTFOLIO_MULTI_STRATEGY", 3, "Conservative / Balanced / Aggressive sleeve mixes"),
    ("PORTFOLIO_RISK_PARITY", 2, "Crypto-only / Multi-asset parity"),
    ("PORTFOLIO_FACTOR_ALLOCATION", 2, "Momentum+Carry / Momentum+Value+Carry"),
    ("PORTFOLIO_TACTICAL_OVERLAY", 2, "Regime-switch / Signal-weighted allocation"),
]


# ---------------------------------------------------------------------------
# Share-class note
# ---------------------------------------------------------------------------

_CRYPTO_CATEGORIES = {"CEFI", "DEFI"}


# ---------------------------------------------------------------------------
# Expansion helpers
# ---------------------------------------------------------------------------

def _expand_defi_venues(venue_ids: list[str]) -> list[str]:
    expanded: list[str] = []
    for v in venue_ids:
        chains = get_supported_chains_for_protocol(v)
        if not chains:
            expanded.append(v)
        else:
            for c in chains:
                expanded.append(f"{v}@{c}")
    return expanded


def _cell_instances(
    archetype_id: str,
    category: str,
    instrument: str,
    manifest_venues: list[str],
) -> tuple[int, int, int, list[str]]:
    """Return (instance_count, combos, tf_count, expanded_venues).

    Uses the per-category venue universe (``_category_venues``) in preference
    to the manifest's ``venue_ids``. Falls back to manifest if the universe
    function returns empty (combination not modelled).
    """
    universe = _category_venues(category, instrument, archetype_id)
    venues = universe if universe else list(manifest_venues)

    if category == "DEFI":
        expanded = _expand_defi_venues(venues)
    else:
        expanded = list(venues)

    tfs = _timeframes_for(archetype_id)

    if archetype_id in _CROSS_VENUE_ARCHETYPES and len(expanded) >= 2:
        combos = len(list(combinations(expanded, 2)))
    elif archetype_id in _SAME_VENUE_BASIS:
        combos = len(expanded)
    else:
        combos = len(expanded)

    # VOL archetypes additionally multiply by option-tenor bucket count
    # (0DTE / weekly / monthly / quarterly / leaps / multi-tenor).
    tenor_mult = 1
    if archetype_id.startswith("VOL_"):
        tenor_mult = len(_tenors_for(archetype_id))

    return combos * len(tfs) * tenor_mult, combos, len(tfs) * tenor_mult, expanded


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    lines: list[str] = []

    lines.append("# Strategy Catalogue — Full Combinatoric Envelope")
    lines.append("")
    lines.append("**Primary axis**: Category (CEFI / DEFI / TRADFI / SPORTS / PREDICTION / CROSS).")
    lines.append("Users select a primary category first; family → archetype → instance follow.")
    lines.append("")
    lines.append("Generated by multiplying, per archetype:")
    lines.append("- **Venue universe per (category, instrument)** — accessible venues, not just currently-integrated ones")
    lines.append("- **Chains** (DeFi venues expanded via protocol→chain mapping)")
    lines.append("- **Timeframes** (per-archetype-family policy)")
    lines.append("- **MM style axis** (4 styles per CEX venue — passive / inventory-skew / queue-microstructure; ML-lean is its own archetype)")
    lines.append("- **Vol style axis** (18 archetypes — RV/IV arb, spread structures, carry, covered calls, protective put, straddle, synthetic delta, MM, ML lean, 0DTE gamma scalping, 0DTE pin risk, term-structure arb, term-structure slope, dispersion, variance swap, LEAPS convexity, cross-asset vol spread, ratio spread)")
    lines.append("- **Vol tenor axis** (0DTE / weekly / monthly / quarterly / LEAPS / multi-tenor — per-archetype allowed set)")
    lines.append("- **MEV archetypes** (4 DeFi-only: sandwich, JIT liquidity, backrun, liquidation bundle — Daian/Qin/Wan literature)")
    lines.append("- **Cross-domain event arb** (`ARBITRAGE_CROSS_DOMAIN_EVENT` — same real-world event listed across SPORTS bookies + PREDICTION markets; e.g. Polymarket football vs Betfair football)")
    lines.append("- **Prediction-market MM** (`MARKET_MAKING_PREDICTION` — distinct mechanics from CEFI/DEFI MM: binary outcomes, time-to-resolution decay)")
    lines.append("- **Category × archetype capability rules** — forbid nonsensical combinations (VOL options on sports, DeFi LP on TradFi, carry on sports, etc.)")
    lines.append("")
    lines.append("**Share class is NOT multiplied.** Each crypto instance is selectable among")
    lines.append("{BTC | ETH | USDT}; non-crypto = USD base. Multi-share-class access is sold")
    lines.append("as a tier upgrade, not catalogue rows.")
    lines.append("")
    lines.append("**Config version is NOT multiplied.** Every instance today runs on `v1`")
    lines.append("(baseline config). As parameter groups evolve, new versions (v2, v3, …)")
    lines.append("emerge; client org subscriptions lock in a specific version. Version-governance")
    lines.append("is the lock-down mechanism for an otherwise infinite config space.")
    lines.append("")
    lines.append("**Bespoke rows**: Every bespoke-capable archetype emits a `{archetype}_CUSTOM`")
    lines.append("entry with ∞ instances (per-client construction). Bespoke-capable set includes")
    lines.append("STAT_ARB, RULES_DIRECTIONAL, EVENT_DRIVEN, ML_DIRECTIONAL, ARBITRAGE, every MM")
    lines.append("archetype, every VOL archetype, and every PORTFOLIO archetype.")
    lines.append("")
    lines.append("**Mocked in this script** (not yet in UAC manifest — see Phase 9 of DART UI plan):")
    lines.append("VOL family split, MM style split, DEFI_LP sub-archetypes, PORTFOLIO family,")
    lines.append("per-category venue universe, category × archetype capability rules.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Load manifest
    with _MANIFEST_PATH.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    archetypes_by_family: dict[str, list[dict]] = defaultdict(list)

    # Manifest archetypes — skip ones replaced by more granular splits below.
    _REPLACED = {
        "VOL_TRADING_OPTIONS",
        "MARKET_MAKING",
        "MARKET_MAKING_CONTINUOUS",      # absorbed into passive/skew/ml-lean/queue
        "MARKET_MAKING_EVENT_SETTLED",   # absorbed into passive on event venues
    }
    for entry in manifest["archetypes"]:
        if entry["archetype_id"] in _REPLACED:
            continue
        archetypes_by_family[entry["family"]].append(entry)

    # Inject splits
    for entry in _VOL_SPLIT:
        archetypes_by_family[entry["family"]].append(entry)
    for entry in _MM_SPLIT:
        archetypes_by_family[entry["family"]].append(entry)
    for entry in _MEV_SPLIT:
        archetypes_by_family[entry["family"]].append(entry)
    for entry in _CROSS_DOMAIN_SPLIT:
        archetypes_by_family[entry["family"]].append(entry)

    # PORTFOLIO family — build synthetic entries so the same rendering code works
    portfolio_entries: list[dict] = []
    for arch_id, count, note in _PORTFOLIO_ARCHETYPES:
        portfolio_entries.append(
            {
                "archetype_id": arch_id,
                "family": "PORTFOLIO",
                "cells": [
                    {
                        "category": "CROSS_CATEGORY",
                        "instrument_type": "sleeve_mix",
                        "status": "SUPPORTED",
                        "venue_ids": [f"canonical-{i+1}" for i in range(count)],
                        "note": note,
                    }
                ],
            }
        )
    archetypes_by_family["PORTFOLIO"] = portfolio_entries

    # ----------------------------------------------------------------------- #
    # Re-group: primary_category -> family -> archetype -> cell.
    # Each archetype can appear in multiple category sections (one per cell).
    # Bespoke rows attach to the primary category a bespoke variant applies to
    # — we emit one per category cell so users see the bespoke option in context.
    # ----------------------------------------------------------------------- #

    _CATEGORY_ORDER = ["CEFI", "DEFI", "TRADFI", "SPORTS", "PREDICTION", "CROSS_CATEGORY"]

    # Build: category -> family -> list of (archetype_id, cell)
    per_category: dict[str, dict[str, list[tuple[str, str, dict]]]] = {
        c: defaultdict(list) for c in _CATEGORY_ORDER
    }

    for family, entries in archetypes_by_family.items():
        for entry in entries:
            archetype_id = entry["archetype_id"]
            for cell in entry["cells"]:
                status = cell["status"]
                if status not in ("SUPPORTED", "PARTIAL"):
                    continue
                category = cell["category"]
                if not _category_allowed(archetype_id, category):
                    continue
                if category not in per_category:
                    per_category[category] = defaultdict(list)
                per_category[category][family].append((archetype_id, family, cell))

    category_totals: dict[str, int] = defaultdict(int)
    category_bespoke: dict[str, int] = defaultdict(int)
    archetype_totals: dict[str, int] = defaultdict(int)
    grand_total = 0
    grand_bespoke = 0

    for category in _CATEGORY_ORDER:
        if category not in per_category or not per_category[category]:
            continue

        lines.append(f"## Primary Category: {category}")
        lines.append("")
        if category == "CROSS_CATEGORY":
            lines.append(
                "Portfolio archetypes span categories — they allocate across category-tagged sleeves."
            )
            lines.append("")

        for family in sorted(per_category[category].keys()):
            lines.append(f"### Family: {family}")
            lines.append("")

            # Group by archetype_id for clean subsections
            archetypes_in_family: dict[str, list[dict]] = defaultdict(list)
            for archetype_id, _fam, cell in per_category[category][family]:
                archetypes_in_family[archetype_id].append(cell)

            for archetype_id in sorted(archetypes_in_family.keys()):
                cells = archetypes_in_family[archetype_id]
                tfs = _timeframes_for(archetype_id)
                venue_policy = (
                    "C(v,2) pairs"
                    if archetype_id in _CROSS_VENUE_ARCHETYPES
                    else "singles"
                )
                lines.append(
                    f"#### {archetype_id}  —  timeframes: {tfs}  —  venue combos: {venue_policy}"
                )
                lines.append("")

                if family == "PORTFOLIO":
                    for cell in cells:
                        note = cell.get("note", "")
                        n = len(cell["venue_ids"])
                        lines.append(f"- **{n}** canonical configs — {note}")
                        archetype_totals[archetype_id] += n
                        category_totals[category] += n
                        grand_total += n
                else:
                    lines.append(
                        "| Instrument | Status | Venues (expanded) | Combos × TFs | Instances |"
                    )
                    lines.append("|---|---|---|---:|---:|")
                    for cell in cells:
                        instrument = cell["instrument_type"]
                        venues = list(cell.get("venue_ids", []))
                        count, combos, tf_count, expanded = _cell_instances(
                            archetype_id, category, instrument, venues
                        )
                        if count == 0:
                            continue
                        venue_preview = ", ".join(expanded[:4])
                        if len(expanded) > 4:
                            venue_preview += f", … ({len(expanded)} total)"
                        lines.append(
                            f"| {instrument} | {cell['status']} | {venue_preview} | "
                            f"{combos} × {tf_count} | **{count}** |"
                        )
                        archetype_totals[archetype_id] += count
                        category_totals[category] += count
                        grand_total += count

                # Bespoke row (once per category × archetype combination)
                if archetype_id in _BESPOKE_CAPABLE:
                    lines.append("")
                    lines.append(
                        f"- **`{archetype_id}_CUSTOM`** in **{category}** — bespoke, **∞** "
                        "per-client configurations (custom logic / features / pairs / event rules)."
                    )
                    category_bespoke[category] += 1
                    grand_bespoke += 1

                lines.append("")

        lines.append(
            f"**Category subtotal ({category})**: {category_totals[category]} instances "
            f"+ {category_bespoke[category]} bespoke archetype-rows"
        )
        lines.append("")
        lines.append("---")
        lines.append("")

    # ----------------------------------------------------------------------- #
    # Grand totals
    # ----------------------------------------------------------------------- #

    lines.append("## Grand total")
    lines.append("")
    lines.append(
        f"**{grand_total} single-share-class instances** + **{grand_bespoke} bespoke-capable "
        "archetypes** (each representing ∞ per-client configurations)."
    )
    lines.append("")
    lines.append("Multi-share-class (crypto only) multiplies crypto instances by up to 3")
    lines.append("({BTC, ETH, USDT}) — not counted as additional rows; sold as a tier upgrade.")
    lines.append("")
    lines.append("### Category breakdown")
    lines.append("")
    lines.append("| Category | Instances | Bespoke archetype-rows |")
    lines.append("|---|---:|---:|")
    for category in _CATEGORY_ORDER:
        if category_totals[category] == 0 and category_bespoke[category] == 0:
            continue
        lines.append(
            f"| {category} | {category_totals[category]} | {category_bespoke[category]} |"
        )

    output = "\n".join(lines)
    if _upload_target is None:
        print(output)
    else:
        _upload_to_gcs(output, _upload_target)


# ---------------------------------------------------------------------------
# GCS upload
# ---------------------------------------------------------------------------

# Canonical SSOT location for the catalogue envelope. Lives in the cefi
# central-region strategy bucket because no generic workspace bucket exists;
# the path makes it clear the file is the unified-catalogue snapshot, not
# CEFI-specific.
GCS_BUCKET = "strategy-store-cefi-central-element-323112"
GCS_OBJECT_PATH = "catalogue/envelope.md"


def _upload_to_gcs(content: str, target: str) -> None:
    """Upload to GCS. content_type derived from object_path extension."""
    from unified_trading_library.cloud_interface import upload_to_storage

    bucket_name, _, object_path = target.partition("/")
    if not object_path:
        print(f"Bad GCS target: {target!r}", file=sys.stderr)
        sys.exit(2)

    if object_path.endswith(".json"):
        content_type = "application/json; charset=utf-8"
    else:
        content_type = "text/markdown; charset=utf-8"

    upload_to_storage(
        bucket=bucket_name,
        path=object_path,
        data=content.encode("utf-8"),
        content_type=content_type,
    )

    https_url = f"https://console.cloud.google.com/storage/browser/_details/{bucket_name}/{object_path}"
    print(f"Uploaded {len(content):,} bytes to gs://{bucket_name}/{object_path}", file=sys.stderr)
    print(f"Console: {https_url}", file=sys.stderr)


_upload_target: str | None = None


# ---------------------------------------------------------------------------
# Structured JSON build (parallel to markdown rendering in main())
# ---------------------------------------------------------------------------

GCS_OBJECT_PATH_JSON = "catalogue/envelope.json"


def build_envelope_json() -> dict:
    """Build the structured JSON envelope, parallel to the markdown render.

    Schema:
      {
        "schema_version": "0.1.0",
        "categories": {
          "CEFI": {
             "instances_count": int,
             "bespoke_count": int,
             "families": {
                "VOL_TRADING": {
                   "archetypes": {
                      "VOL_0DTE_GAMMA_SCALPING": {
                         "tenors": [...],
                         "timeframes": [...],
                         "venue_combo_policy": "single_venue|cross_venue_pairs|same_venue_basis",
                         "bespoke_capable": bool,
                         "cells": [
                            {"instrument_type": "option", "status": "SUPPORTED",
                             "venue_count": 5, "venue_combos": 5, "tf_count": 1,
                             "instances": 5, "venues": [...]}
                         ]
                      }
                   }
                }
             }
          }
        },
        "totals": {"instances": int, "bespoke_archetype_rows": int}
      }
    """
    with _MANIFEST_PATH.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    archetypes_by_family: dict[str, list[dict]] = defaultdict(list)
    _REPLACED = {
        "VOL_TRADING_OPTIONS",
        "MARKET_MAKING",
        "MARKET_MAKING_CONTINUOUS",
        "MARKET_MAKING_EVENT_SETTLED",
    }
    for entry in manifest["archetypes"]:
        if entry["archetype_id"] in _REPLACED:
            continue
        archetypes_by_family[entry["family"]].append(entry)
    for entry in _VOL_SPLIT:
        archetypes_by_family[entry["family"]].append(entry)
    for entry in _MM_SPLIT:
        archetypes_by_family[entry["family"]].append(entry)
    for entry in _MEV_SPLIT:
        archetypes_by_family[entry["family"]].append(entry)
    for entry in _CROSS_DOMAIN_SPLIT:
        archetypes_by_family[entry["family"]].append(entry)

    portfolio_entries: list[dict] = []
    for arch_id, count, note in _PORTFOLIO_ARCHETYPES:
        portfolio_entries.append(
            {
                "archetype_id": arch_id,
                "family": "PORTFOLIO",
                "cells": [
                    {
                        "category": "CROSS_CATEGORY",
                        "instrument_type": "sleeve_mix",
                        "status": "SUPPORTED",
                        "venue_ids": [f"canonical-{i+1}" for i in range(count)],
                        "note": note,
                    }
                ],
            }
        )
    archetypes_by_family["PORTFOLIO"] = portfolio_entries

    _CATEGORY_ORDER = ["CEFI", "DEFI", "TRADFI", "SPORTS", "PREDICTION", "CROSS_CATEGORY"]
    out: dict = {
        "schema_version": "0.1.0",
        "categories": {},
        "totals": {"instances": 0, "bespoke_archetype_rows": 0},
    }

    grand_instances = 0
    grand_bespoke = 0

    for category in _CATEGORY_ORDER:
        cat_payload: dict = {"instances_count": 0, "bespoke_count": 0, "families": {}}
        cat_instances = 0
        cat_bespoke = 0

        for family, entries in archetypes_by_family.items():
            fam_payload: dict[str, dict] = {}
            for entry in entries:
                archetype_id = entry["archetype_id"]
                cells_in_cat: list[dict] = []
                arch_instances = 0

                for cell in entry["cells"]:
                    if cell.get("status") not in ("SUPPORTED", "PARTIAL"):
                        continue
                    cell_cat = cell["category"]
                    if cell_cat != category:
                        continue
                    if not _category_allowed(archetype_id, cell_cat):
                        continue
                    instrument = cell["instrument_type"]
                    venues = list(cell.get("venue_ids", []))
                    count, combos, tf_count, expanded = _cell_instances(
                        archetype_id, cell_cat, instrument, venues
                    )
                    if count == 0:
                        continue
                    cells_in_cat.append({
                        "instrument_type": instrument,
                        "status": cell["status"],
                        "venue_count": len(expanded),
                        "venue_combos": combos,
                        "tf_count": tf_count,
                        "instances": count,
                        "venues": expanded,
                        "note": cell.get("note"),
                    })
                    arch_instances += count

                if not cells_in_cat:
                    continue
                bespoke = archetype_id in _BESPOKE_CAPABLE
                if bespoke:
                    cat_bespoke += 1
                    grand_bespoke += 1
                fam_payload[archetype_id] = {
                    "tenors": _TENOR_BUCKETS_BY_ARCHETYPE.get(archetype_id),
                    "timeframes": _timeframes_for(archetype_id),
                    "venue_combo_policy": (
                        "cross_venue_pairs"
                        if archetype_id in _CROSS_VENUE_ARCHETYPES
                        else "same_venue_basis"
                        if archetype_id in _SAME_VENUE_BASIS
                        else "single_venue"
                    ),
                    "bespoke_capable": bespoke,
                    "instances_total": arch_instances,
                    "cells": cells_in_cat,
                }
                cat_instances += arch_instances

            if fam_payload:
                cat_payload["families"][family] = {"archetypes": fam_payload}

        if cat_instances > 0 or cat_bespoke > 0:
            cat_payload["instances_count"] = cat_instances
            cat_payload["bespoke_count"] = cat_bespoke
            out["categories"][category] = cat_payload
            grand_instances += cat_instances

    out["totals"]["instances"] = grand_instances
    out["totals"]["bespoke_archetype_rows"] = grand_bespoke
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--upload",
        action="store_true",
        help=(
            f"Upload BOTH markdown to gs://{GCS_BUCKET}/{GCS_OBJECT_PATH} and "
            f"JSON to gs://{GCS_BUCKET}/{GCS_OBJECT_PATH_JSON}."
        ),
    )
    parser.add_argument(
        "--format",
        choices=["md", "json"],
        default="md",
        help="Output format when not uploading. md (default) or json.",
    )
    parser.add_argument(
        "--gcs-target",
        type=str,
        default=None,
        help="Override GCS markdown target as '<bucket>/<path>'. Implies --upload.",
    )
    args = parser.parse_args()

    if args.gcs_target:
        _upload_target = args.gcs_target
    elif args.upload:
        _upload_target = f"{GCS_BUCKET}/{GCS_OBJECT_PATH}"

    if args.format == "json" and not args.upload:
        # JSON-only stdout mode (no upload)
        print(json.dumps(build_envelope_json(), indent=2, sort_keys=True))
    else:
        main()
        # Also upload JSON when --upload is set
        if args.upload:
            json_payload = json.dumps(build_envelope_json(), indent=2, sort_keys=True)
            _upload_to_gcs(json_payload, f"{GCS_BUCKET}/{GCS_OBJECT_PATH_JSON}")
