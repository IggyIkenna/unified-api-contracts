"""Asset-group capability ontology — fill / margin / settlement / liquidation models.

Per audit P1.2 + external-agent feedback #7 (workspace audit 2026-05-01): the
existing :mod:`unified_api_contracts.internal.architecture_v2.archetype_capability`
registry maps **archetype -> (asset_group, instrument_type) cells** with
SUPPORTED / PARTIAL / BLOCKED status. What was missing was the **per-asset_group
ontology**: which instrument types live in this group, which venues serve it,
what's the fill model, what's the margin model, what's the liquidation params,
what's the settlement model.

This module fills that gap. Together with the existing archetype-capability
registry, services have a single answer to "what's the margin model for a CeFi
perp position?" or "what's the settlement model for a sports market?".

NO duplication of the archetype matrix — that lives in
:mod:`unified_api_contracts.internal.architecture_v2.archetype_capability`. This
module is the layer **above** it: per-asset_group ontology that the matrix builds
on.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from unified_api_contracts.registry.taxonomy import (
    InstrumentTypeFamily,
    MarketAssetGroup,
)


@dataclass(frozen=True)
class FillModel:
    """How execution fills are simulated in batch and produced in live.

    The ``fill_source`` discriminator on :class:`FillEvent` records which path
    actually produced a given fill, but the **assumptions** (slippage,
    commission, latency, liquidity) live here so they're consistent batch=live.
    """

    name: str
    typical_slippage_bps: int
    typical_latency_ms: int
    commission_bps: int
    """Fees in bps. CeFi spot ~10 bps; DeFi swap ~30 bps; sports ~200-500 bps."""
    has_funding: bool = False
    has_liquidations: bool = False
    has_event_settlement: bool = False
    """True for sports / prediction markets where a discrete event settles all positions."""
    description: str = ""


@dataclass(frozen=True)
class SettlementModel:
    """How positions ultimately resolve cash flows."""

    name: str
    horizon: str  # 'immediate' | 't+1' | 't+2' | 'event_driven'
    cash_currency: str  # USD | USDT | USDC | ETH | GBP, etc.
    description: str = ""


@dataclass(frozen=True)
class AssetGroupOntology:
    """Per-asset-group capability ontology."""

    asset_group: MarketAssetGroup
    instrument_types: frozenset[InstrumentTypeFamily]
    venues: frozenset[str]
    """Venue slugs (lowercase, dash-delimited). E.g. 'binance', 'aave-v3-ethereum'."""
    fill_model: FillModel
    settlement_model: SettlementModel
    margin_model_name: str
    """Name of the :class:`MarginModel` enum value that applies (see
    :mod:`unified_api_contracts.internal.risk`). Use string here to avoid
    circular import."""
    state_model: str
    """One of: 'wallet_protocol_position' (DeFi) | 'venue_account' (CeFi/TradFi) |
    'event_market_holding' (sports/prediction)."""
    has_liquidations: bool = False
    has_funding: bool = False


# ── Fill models per asset group ─────────────────────────────────────────────

_CEFI_FILL = FillModel(
    name="cefi_perp_continuous",
    typical_slippage_bps=2,
    typical_latency_ms=80,
    commission_bps=5,
    has_funding=True,
    has_liquidations=True,
    description="Continuous order book; tight spreads on majors; funding every 8h.",
)

_DEFI_FILL = FillModel(
    name="defi_onchain",
    typical_slippage_bps=30,
    typical_latency_ms=12_000,
    commission_bps=30,
    has_funding=False,
    has_liquidations=True,
    description="DEX swap or lending interaction; gas + slippage; on-chain finality.",
)

_TRADFI_FILL = FillModel(
    name="tradfi_continuous",
    typical_slippage_bps=1,
    typical_latency_ms=50,
    commission_bps=2,
    has_funding=False,
    has_liquidations=True,
    description="Regulated venue; deep liquidity; SPAN margin; daily settlement.",
)

_SPORTS_FILL = FillModel(
    name="sports_event_settled",
    typical_slippage_bps=500,
    typical_latency_ms=300,
    commission_bps=200,
    has_funding=False,
    has_liquidations=False,
    has_event_settlement=True,
    description="Bet placement; settles on event outcome; bookmaker margin baked in.",
)

_PREDICTION_FILL = FillModel(
    name="prediction_event_settled",
    typical_slippage_bps=200,
    typical_latency_ms=2_000,
    commission_bps=200,
    has_funding=False,
    has_liquidations=False,
    has_event_settlement=True,
    description="Polymarket / Kalshi share trading; settles to $1 / $0 at resolution.",
)


# ── Settlement models per asset group ───────────────────────────────────────

_CEFI_SETTLEMENT = SettlementModel(
    name="cefi_immediate_funding",
    horizon="immediate",
    cash_currency="USDT",
    description="Spot/margin = immediate; perps accrue funding every 8h.",
)

_DEFI_SETTLEMENT = SettlementModel(
    name="defi_onchain_immediate",
    horizon="immediate",
    cash_currency="USDC",
    description="Tx confirmation = settlement. Lending interest accrues per block.",
)

_TRADFI_SETTLEMENT = SettlementModel(
    name="tradfi_t_plus_1",
    horizon="t+1",
    cash_currency="USD",
    description="Equities T+1; futures daily mark-to-market + final on expiry.",
)

_SPORTS_SETTLEMENT = SettlementModel(
    name="sports_event_outcome",
    horizon="event_driven",
    cash_currency="GBP",
    description="Stake locked at placement; settles on event outcome (win/loss/void).",
)

_PREDICTION_SETTLEMENT = SettlementModel(
    name="prediction_resolution",
    horizon="event_driven",
    cash_currency="USDC",
    description="Shares trade until resolution; YES = $1, NO = $0 at outcome.",
)


# ── Asset-group ontology registry ───────────────────────────────────────────

ASSET_GROUP_ONTOLOGY: Final[dict[MarketAssetGroup, AssetGroupOntology]] = {
    MarketAssetGroup.CEFI: AssetGroupOntology(
        asset_group=MarketAssetGroup.CEFI,
        instrument_types=frozenset(
            {
                InstrumentTypeFamily.SPOT,
                InstrumentTypeFamily.PERP,
                InstrumentTypeFamily.FUTURE,
                InstrumentTypeFamily.OPTION,
            }
        ),
        venues=frozenset(
            {
                "binance",
                "binance-futures",
                "bybit",
                "okx",
                "deribit",
                "coinbase",
                "kraken",
                "hyperliquid",
            }
        ),
        fill_model=_CEFI_FILL,
        settlement_model=_CEFI_SETTLEMENT,
        margin_model_name="BINANCE_CROSS",
        state_model="venue_account",
        has_liquidations=True,
        has_funding=True,
    ),
    MarketAssetGroup.DEFI: AssetGroupOntology(
        asset_group=MarketAssetGroup.DEFI,
        instrument_types=frozenset(
            {
                InstrumentTypeFamily.SPOT,
                InstrumentTypeFamily.LENDING_POSITION,
                InstrumentTypeFamily.BORROW_POSITION,
                InstrumentTypeFamily.LP_POSITION,
                InstrumentTypeFamily.STAKED_POSITION,
            }
        ),
        venues=frozenset(
            {
                "aave-v3-ethereum",
                "compound-v3-ethereum",
                "morpho-blue-ethereum",
                "uniswap-v3-ethereum",
                "balancer-v2-ethereum",
                "curve-ethereum",
                "lido-ethereum",
                "rocketpool-ethereum",
                "eigenlayer-ethereum",
            }
        ),
        fill_model=_DEFI_FILL,
        settlement_model=_DEFI_SETTLEMENT,
        margin_model_name="AAVE_V3",
        state_model="wallet_protocol_position",
        has_liquidations=True,
        has_funding=False,
    ),
    MarketAssetGroup.TRADFI: AssetGroupOntology(
        asset_group=MarketAssetGroup.TRADFI,
        instrument_types=frozenset(
            {
                InstrumentTypeFamily.SPOT,
                InstrumentTypeFamily.FUTURE,
                InstrumentTypeFamily.OPTION,
            }
        ),
        venues=frozenset(
            {
                "cme",
                "cboe",
                "nyse",
                "nasdaq",
                "ice",
                "lme",
            }
        ),
        fill_model=_TRADFI_FILL,
        settlement_model=_TRADFI_SETTLEMENT,
        margin_model_name="FUTURES_SPAN",
        state_model="venue_account",
        has_liquidations=True,
        has_funding=False,
    ),
    MarketAssetGroup.SPORTS: AssetGroupOntology(
        asset_group=MarketAssetGroup.SPORTS,
        instrument_types=frozenset({InstrumentTypeFamily.SPORTS_MARKET}),
        venues=frozenset(
            {
                "betfair",
                "smarkets",
                "matchbook",
            }
        ),
        fill_model=_SPORTS_FILL,
        settlement_model=_SPORTS_SETTLEMENT,
        margin_model_name="EXPOSURE_CAP",
        state_model="event_market_holding",
        has_liquidations=False,
        has_funding=False,
    ),
    MarketAssetGroup.PREDICTION: AssetGroupOntology(
        asset_group=MarketAssetGroup.PREDICTION,
        instrument_types=frozenset({InstrumentTypeFamily.PREDICTION_MARKET}),
        venues=frozenset(
            {
                "polymarket",
                "kalshi",
            }
        ),
        fill_model=_PREDICTION_FILL,
        settlement_model=_PREDICTION_SETTLEMENT,
        margin_model_name="EXPOSURE_CAP",
        state_model="event_market_holding",
        has_liquidations=False,
        has_funding=False,
    ),
}


def get_asset_group_ontology(asset_group: MarketAssetGroup) -> AssetGroupOntology:
    """Lookup helper. Always succeeds for valid asset groups."""
    return ASSET_GROUP_ONTOLOGY[asset_group]


def venues_for(asset_group: MarketAssetGroup) -> frozenset[str]:
    """Per-asset-group venue list (replaces hardcoded venue lists in services)."""
    return ASSET_GROUP_ONTOLOGY[asset_group].venues


def has_liquidations(asset_group: MarketAssetGroup) -> bool:
    """True if the asset group has hard liquidation thresholds (CeFi/DeFi/TradFi)."""
    return ASSET_GROUP_ONTOLOGY[asset_group].has_liquidations


# ── Per-asset-group hardcoded venue lists (P3.4 — moved from strategy-service)
#
# strategy-service/config.py:577-582 used to inline these. They now live here
# as the single source of truth for risk subscriptions.

AAVE_COLLATERAL_PATTERNS: Final[tuple[str, ...]] = ("AAVE_V3-ETHEREUM:A_TOKEN:*",)

CEX_MARGIN_VENUES: Final[tuple[str, ...]] = (
    "BINANCE:PERPETUAL:*",
    "BINANCE-FUTURES:PERPETUAL:*",
    "BYBIT:PERPETUAL:*",
    "OKX:PERPETUAL:*",
)
