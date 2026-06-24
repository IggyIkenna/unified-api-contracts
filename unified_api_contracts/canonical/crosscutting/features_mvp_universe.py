"""Features MVP universe — per-feature-family universe resolver.

Separate from the MTDS capture universe (``is_in_mvp_capture_universe`` in
``mvp_scope.py``). The MTDS gate controls WHAT we capture (capture → GCS);
this module controls WHAT the features pipeline COMPUTES OVER — which is the
same for price/funding families but WIDER for families that span options or
dated-futures curves.

Design (operator 2026-06-23):
  - **Price/technical/funding features** (default family) → the same perp-gated
    ``CEFI_BASE_ASSET_UNIVERSE`` used by MTDS capture, expressed as a base-asset
    allowlist. These feature families need only perpetual OHLCV candle data.
  - **Roll / spread features** (futures term-structure) → WIDER: dated-futures
    curve instruments are included (instrument_type = FUTURE, with expiry).
    Because the base set for roll families is still ``CEFI_BASE_ASSET_UNIVERSE``
    (no extra bases needed — the dated contracts are just additional instruments
    on the SAME bases), the universe flag here is ``include_dated_futures=True``
    on the CeFi resolver.
  - **Volatility features** (realised vol, skew) → WIDER for options underlyings:
    the options universe (``CEFI_OPTIONS_UNDERLYINGS`` = BTC + ETH only, Deribit)
    is included. Other vol families (realised vol from OHLCV) still use the full
    perp universe.
  - **DeFi on-chain features** → the on-chain full token set (all tokens in
    ``CEFI_BASE_ASSET_UNIVERSE`` plus any chain-native extras). Managed per-chain
    in ``features_service.onchain`` — no extra filtering here (the onchain family
    already manages its own universe).

Usage::

    from unified_api_contracts.canonical.crosscutting.features_mvp_universe import (
        FeatureFamilyUniverseConfig,
        FEATURE_FAMILY_UNIVERSE_REGISTRY,
        resolve_universe_for_family,
    )

    config = resolve_universe_for_family("funding_oi")
    # config.base_asset_universe → frozenset of base assets
    # config.include_dated_futures → False (perp-only family)
    # config.include_options_underlyings → False
"""

from __future__ import annotations

from dataclasses import dataclass, field

from unified_api_contracts.registry.cefi_instrument_universe import (
    CEFI_BASE_ASSET_UNIVERSE,
    CEFI_OPTIONS_UNDERLYINGS,
)

# ---------------------------------------------------------------------------
# Universe config dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeatureFamilyUniverseConfig:
    """Universe configuration for a single feature family.

    Attributes:
        family: The feature group/family name (e.g. ``"technical_indicators"``).
        base_asset_universe: Frozenset of accepted base assets for this family.
            Instruments whose base asset is NOT in this set are excluded before
            feature computation. The default (price/funding families) is
            ``CEFI_BASE_ASSET_UNIVERSE`` — the same survivorship-bias-free set
            that MTDS capture uses.
        include_dated_futures: When ``True``, dated futures instruments
            (instrument_type = FUTURE with an expiry date) are INCLUDED for
            this family in addition to perpetuals. Default ``False`` (perp-only
            families such as price/technical/funding groups).
        include_options_underlyings: When ``True``, options instruments are
            included for bases in ``CEFI_OPTIONS_UNDERLYINGS`` (BTC + ETH only,
            sourced from Deribit). Default ``False``.
        notes: Human-readable rationale for any non-default settings.
    """

    family: str
    base_asset_universe: frozenset[str] = field(default_factory=lambda: CEFI_BASE_ASSET_UNIVERSE)
    include_dated_futures: bool = False
    include_options_underlyings: bool = False
    notes: str = ""


# ---------------------------------------------------------------------------
# Per-family registry
# ---------------------------------------------------------------------------
# Only families that DIFFER from the default need an explicit entry.
# The default (returned by ``resolve_universe_for_family`` for any unlisted
# family) is: base_asset_universe=CEFI_BASE_ASSET_UNIVERSE,
# include_dated_futures=False, include_options_underlyings=False.
#
# CEFI/DEFI feature families:
#   funding_oi     — perp funding rates + open interest → perp-only default
#   liquidations   — perp liquidation events → perp-only default
# Roll/spread (futures term-structure families):
#   futures_basis  — TradFi dated-futures basis; for CeFi roll the same flag
#                    applies, but this family is TradFi-only in the CLI parser
# Volatility options families (future Phase 2 work):
#   [no CeFi group name yet — placeholder below for the extension point]
#   The options-vol family will need include_options_underlyings=True.

FEATURE_FAMILY_UNIVERSE_REGISTRY: dict[str, FeatureFamilyUniverseConfig] = {
    # --- Default (perp-gated) price/technical/indicator families ---
    # (listed explicitly here for documentation clarity; all share the same config)
    "technical_indicators": FeatureFamilyUniverseConfig(
        family="technical_indicators",
        notes="Price/technical features — perp-universe default.",
    ),
    "moving_averages": FeatureFamilyUniverseConfig(
        family="moving_averages",
        notes="Price/MA features — perp-universe default.",
    ),
    "oscillators": FeatureFamilyUniverseConfig(
        family="oscillators",
        notes="Oscillator features — perp-universe default.",
    ),
    "momentum": FeatureFamilyUniverseConfig(
        family="momentum",
        notes="Momentum features — perp-universe default.",
    ),
    "volume_analysis": FeatureFamilyUniverseConfig(
        family="volume_analysis",
        notes="Volume-based features — perp-universe default.",
    ),
    "vwap": FeatureFamilyUniverseConfig(
        family="vwap",
        notes="VWAP features — perp-universe default.",
    ),
    "candlestick_patterns": FeatureFamilyUniverseConfig(
        family="candlestick_patterns",
        notes="Candlestick pattern features — perp-universe default.",
    ),
    "market_structure": FeatureFamilyUniverseConfig(
        family="market_structure",
        notes="Market structure features — perp-universe default.",
    ),
    "returns": FeatureFamilyUniverseConfig(
        family="returns",
        notes="Return features — perp-universe default.",
    ),
    "round_numbers": FeatureFamilyUniverseConfig(
        family="round_numbers",
        notes="Round-number features — perp-universe default.",
    ),
    "streaks": FeatureFamilyUniverseConfig(
        family="streaks",
        notes="Streak features — perp-universe default.",
    ),
    "microstructure": FeatureFamilyUniverseConfig(
        family="microstructure",
        notes="Microstructure features (order book + tick data) — perp-universe default.",
    ),
    "temporal": FeatureFamilyUniverseConfig(
        family="temporal",
        notes="Temporal/calendar features — perp-universe default.",
    ),
    "economic_events": FeatureFamilyUniverseConfig(
        family="economic_events",
        notes="Economic event impact features — perp-universe default.",
    ),
    "targets": FeatureFamilyUniverseConfig(
        family="targets",
        notes="ML training targets — perp-universe default.",
    ),
    "swing_outcome_targets": FeatureFamilyUniverseConfig(
        family="swing_outcome_targets",
        notes="Swing outcome ML targets — perp-universe default.",
    ),
    # --- CeFi/DeFi perpetual-specific families ---
    "funding_oi": FeatureFamilyUniverseConfig(
        family="funding_oi",
        notes=(
            "Perpetual funding rates + open interest. "
            "Perp-gated: only instruments in CEFI_BASE_ASSET_UNIVERSE with an active perp."
        ),
    ),
    "liquidations": FeatureFamilyUniverseConfig(
        family="liquidations",
        notes=(
            "Perpetual liquidation events. "
            "Perp-gated: only instruments in CEFI_BASE_ASSET_UNIVERSE with an active perp."
        ),
    ),
    # --- Volatility (realised from OHLCV) ---
    "volatility_realized": FeatureFamilyUniverseConfig(
        family="volatility_realized",
        notes=(
            "Realised volatility from OHLCV candles. "
            "Full perp-universe (CEFI_BASE_ASSET_UNIVERSE). "
            "Options-surface vol (skew, term-structure) is a SEPARATE family "
            "that will set include_options_underlyings=True when wired."
        ),
    ),
    # --- Roll / term-structure families → WIDER: include dated futures ---
    # futures_basis is TradFi-only in the CLI today; the CeFi roll equivalent
    # will use a separate group name when built. Wired here so the resolver
    # is ready for the CeFi dated-futures feature family (Phase 2).
    "futures_basis": FeatureFamilyUniverseConfig(
        family="futures_basis",
        include_dated_futures=True,
        notes=(
            "Futures basis / term-structure features (TradFi today; CeFi roll in Phase 2). "
            "Wider universe: includes dated-futures instruments in addition to perpetuals "
            "for roll-spread calculation. Base assets still gated to CEFI_BASE_ASSET_UNIVERSE."
        ),
    ),
    "volume_flow": FeatureFamilyUniverseConfig(
        family="volume_flow",
        notes="TradFi uptick/downtick volume flow — perp-universe default.",
    ),
    # Extension point: options-surface volatility family (Phase 2)
    # When wired, set include_options_underlyings=True and the resolver
    # will include BTC/ETH options instruments from CEFI_OPTIONS_UNDERLYINGS.
    # Example (not yet active — uncomment when the family name is known):
    # "volatility_options": FeatureFamilyUniverseConfig(
    #     family="volatility_options",
    #     include_options_underlyings=True,
    #     notes="Options-surface vol (skew/term-structure). Wider: BTC+ETH Deribit options.",
    # ),
}


def resolve_universe_for_family(family: str) -> FeatureFamilyUniverseConfig:
    """Return the universe config for ``family``.

    Falls back to the default (full perp-gated ``CEFI_BASE_ASSET_UNIVERSE``,
    no dated futures, no options) for any family not explicitly registered.
    This makes the registry additive — new feature families get the correct
    default without requiring an explicit entry.

    Args:
        family: Feature group/family name (e.g. ``"funding_oi"``).

    Returns:
        :class:`FeatureFamilyUniverseConfig` for the family.
    """
    return FEATURE_FAMILY_UNIVERSE_REGISTRY.get(
        family,
        FeatureFamilyUniverseConfig(
            family=family,
            notes=f"Auto-defaulted: '{family}' not in registry → full CEFI_BASE_ASSET_UNIVERSE.",
        ),
    )


def get_options_underlyings() -> frozenset[str]:
    """Return the options underlyings set (BTC + ETH for Deribit).

    Separate accessor so callers don't need to import ``cefi_instrument_universe``
    directly just to check whether a base has options data.
    """
    return CEFI_OPTIONS_UNDERLYINGS
