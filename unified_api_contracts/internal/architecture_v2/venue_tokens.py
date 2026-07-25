"""Canonical slot-label venue tokens.

SSOT for the lowercase-alnum venue tokens used inside slot labels (the
`{venue_scope}` segment of the grammar). This is a separate concern from the
full venue registry: slot labels use the *family* name of a venue (e.g.
`binance` not `BINANCE-SPOT`, `uniswap` not `UNISWAP_V3-ETHEREUM`) so that one
strategy instance can span spot+perp+options on the same venue.

Callers (strategy-service slot_label parser, etc.) use `is_venue_token()` to
split `scope_tokens` into venue-scope vs instrument-scope at parse time.

LSE, TSX are deliberately excluded — they are not in the Unified Trading
System.
"""

from __future__ import annotations

# CeFi exchanges + pricing-only (crypto spot/perp/options)
_CEFI_TOKENS: frozenset[str] = frozenset(
    {
        "binance",
        "okx",
        "bybit",
        "hyperliquid",
        "deribit",
        "coinbase",
        "cboe",
        "bitget",
        "kucoin",
        "mexc",
        "upbit",
        "aster",
        # 2026-05-04 Phase 4d/e: CARRY_STAKED_BASIS + CARRY_BASIS_PERP
        # universe expansion to all Tardis-captured CeFi perp venues.
        # ``kraken`` / ``bitfinex`` are the slot-label tokens; the venue
        # registry uses the suffixed forms ``KRAKEN-FUTURES`` /
        # ``BITFINEX-FUTURES`` for collateral-matrix lookups.
        "kraken",
        "bitfinex",
    }
)

# TradFi (via IBKR meta-broker + CME/ICE direct)
_TRADFI_TOKENS: frozenset[str] = frozenset(
    {
        "ibkr",
        "cme",
        "ice",
        "nasdaq",
        "nyse",
        "cbot",
        "nymex",
        "comex",
        # 2026-07-13 uac_venue_registry_completion: FX was missing from this
        # set entirely (found while verifying split_scope_tokens doesn't raise
        # for it, per that plan's own success criterion) — FXAdapter (IBKR
        # IDEALPRO) is a real, already-routed venue, same family as the other
        # IBKR-routed entries above.
        "fx",
    }
)

# DeFi DEX families (venue-family names, chain-agnostic)
_DEFI_DEX_TOKENS: frozenset[str] = frozenset(
    {
        "uniswap",
        "uniswapv2",
        "uniswapv3",
        "uniswapv4",
        "curve",
        "balancer",
        "aerodrome",
        "sushiswap",
        "pancakeswap",
        "joe",
        "orca",
        "raydium",
        "velodrome",
        # 2026-06-15 Phase V venue build-out — versioned/aggregator DEX family
        # tokens that ``archetype_leg_spec_seeds.py`` already lists as
        # ``eligible_venue_ids`` (``_DEX_SWAP_VENUES`` / ``_SPOT_VENUES_STAKED``
        # / DEX_LP seeds) but whose alnum-folded slot tokens were absent here, so
        # the v2 slot-label parser rejected every cell routing a leg to them
        # (F47 ``DeadEndReason.UNBUILDABLE_SLOT`` in the verdict matrix). The
        # family base (``balancer``/``sushiswap``/``pancakeswap``/``joe``) exists
        # above; the parser requires the EXACT folded token, so the explicit
        # protocol-version + aggregator forms are added here.
        "balancerv2",
        "balancerv3",
        "sushiswapv3",
        "pancakeswapv3",
        "traderjoe",
        "jupiter",
        # 2026-07-24 containment-fix follow-up (defi_archetype_universe_no_curtailment_
        # mechanism_2026_07_23.md Side-decision 2): archetype_leg_spec_seeds.py's
        # ARBITRAGE_PRICE_DISPERSION venues now cite "aerodrome_v3"/"camelot_v3"/"phoenix"
        # (the DEX cross-venue spot-dispersion sub-family, catalog_trading.py's
        # _dex_dispersion_pairs) — same F47 unbuildable-slot gap this file's own Phase-V
        # comment above describes; the family base "aerodrome" already exists (added here
        # for the exact versioned fold), "camelot"/"phoenix" had no entry at all.
        "aerodromev3",
        "camelot",
        "camelotv3",
        "phoenix",
    }
)

# DeFi lending protocols
_DEFI_LENDING_TOKENS: frozenset[str] = frozenset(
    {
        "aave",
        "aavev3",
        "compound",
        "compoundv3",
        "morpho",
        "spark",
        "kamino",
        "marginfi",
        "fluid",
        "euler",
    }
)

# DeFi staking + yield-bearing-vault protocols. Includes ERC-4626 vault
# venues (Yearn, MakerDAO sDAI, Frax sFRAX) alongside the LST issuers
# (Lido, RocketPool, etc.) since slot labels use the same scope grammar
# for staked-yield primitives — the parser doesn't care whether the
# token is rebasing or share-price-tracked.
_DEFI_STAKING_TOKENS: frozenset[str] = frozenset(
    {
        "lido",
        "rocketpool",
        "jito",
        "marinade",
        "etherfi",
        "ethena",
        # ERC-4626 vault venues — DEFI_LP_VAULT seed slot family. Added
        # 2026-05-03 with defi_pipeline_extension_followups Phase 3.
        "yearn",
        "yearnv3",
        "maker",
        "frax",
        # 2026-06-15 Phase V — Sommelier ERC-4626 yield-vault venue. Listed in
        # ``archetype_leg_spec_seeds.py`` DEX_LP yield-vault seed
        # (``("yearn_v3", "morpho", "sommelier")``) as a leg-eligible venue;
        # folds to ``sommelier``. Same vault-primitive class as the existing
        # Yearn / Maker rows.
        "sommelier",
    }
)

# DeFi perp protocols
_DEFI_PERP_TOKENS: frozenset[str] = frozenset(
    {
        # "gmx" / "gmxv2" removed 2026-07-25 (unreliable historical funding
        # data — see
        # unified-trading-pm/plans/active/defi_gmx_venue_removal_2026_07_25.md).
        # "drift" (Solana-native perps) removed 2026-07-16 (operator ruling: all Solana perp DEXes
        # dropped except Jupiter, not integrated).
        # SSOT: unified-trading-pm/codex/04-architecture/solana-defi-coverage.md.
        # dYdX is a Cosmos-native perpetuals DEX (dYdX Chain L1). Required for
        # ML_DIRECTIONAL_CONTINUOUS DeFi perp slots in target_universe catalog.
        "dydx",
    }
)

# Sports — prime broker + direct exchanges
_SPORTS_TOKENS: frozenset[str] = frozenset(
    {
        "unity",
        "betfair",
        "matchbook",
        # 2026-06-15 Phase V — direct-exchange sports venue ids. The family
        # bases (``betfair``/``matchbook``) exist, but ``archetype_leg_spec_seeds.py``
        # event-leg seeds list the routing-specific venue ids
        # ``betfair_direct`` / ``smarkets_direct`` / ``matchbook_direct``
        # (the execution-service ``SportsExecutionRouter`` data-source targets),
        # which fold to ``betfairdirect`` / ``smarketsdirect`` / ``matchbookdirect``.
        # ``smarkets`` had no family base either — added so the direct id parses.
        "smarkets",
        "betfairdirect",
        "smarketsdirect",
        "matchbookdirect",
    }
)

# Prediction markets
_PREDICTION_TOKENS: frozenset[str] = frozenset(
    {
        "polymarket",
        "kalshi",
        # 2026-07-24 containment-fix follow-up (defi_archetype_universe_no_curtailment_
        # mechanism_2026_07_23.md Side-decision 2): CARRY_BASIS_PERP / CARRY_FUNDING_
        # DISPERSION's eligible_venue_ids now cite "kalshi_perp"/"polymarket_perp" — the
        # CFTC-regulated crypto-perp CLOB product (distinct from the bare "kalshi"/
        # "polymarket" event-market product; venue_adapter_keys.VENUE_TO_ADAPTER_KEY keys
        # them separately too). Family bases exist above; the parser needs the exact
        # folded token for the perp-product variant.
        "kalshiperp",
        "polymarketperp",
    }
)

# Data aggregators (used as data "venues" in slot labels where relevant)
_DATA_AGGREGATOR_TOKENS: frozenset[str] = frozenset(
    {
        "oddsapi",
        "footystats",
        "sfi",
        "apifootball",
        "databento",
        "tardis",
        "defillama",
        "thegraph",
        "alchemy",
    }
)

KNOWN_VENUE_TOKENS: frozenset[str] = (
    _CEFI_TOKENS
    | _TRADFI_TOKENS
    | _DEFI_DEX_TOKENS
    | _DEFI_LENDING_TOKENS
    | _DEFI_STAKING_TOKENS
    | _DEFI_PERP_TOKENS
    | _SPORTS_TOKENS
    | _PREDICTION_TOKENS
    | _DATA_AGGREGATOR_TOKENS
)


def is_venue_token(token: str) -> bool:
    """Return True iff `token` is a known canonical venue-scope token.

    Tokens are matched case-sensitively against the lowercase canonical form;
    callers are responsible for lowercasing before calling.
    """
    return token in KNOWN_VENUE_TOKENS


def split_scope_tokens(tokens: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split slot-label scope tokens into (venue_tokens, instrument_tokens).

    Grammar rule: venue tokens come first (one or more), optionally followed by
    instrument tokens. The boundary is the first non-venue token. When every
    token in `tokens` is a venue token, `instrument_tokens` is empty — this is
    legal for single-asset strategies where the instrument is implied by the
    slot's share_class (e.g., CARRY_STAKED_BASIS on ETH has share_class=ETH
    and no separate instrument token).

    Example: ("lido", "aave", "hyperliquid")
      -> venues=("lido", "aave", "hyperliquid"), instruments=()
         (instrument = share_class, resolved by caller)

    Example: ("hyperliquid", "btc") -> venues=("hyperliquid",), instruments=("btc",)

    Example: ("unity", "epl", "1x2")
      -> venues=("unity",), instruments=("epl", "1x2")

    Raises ValueError iff `tokens` is empty OR the first token is not a venue.
    """
    if not tokens:
        raise ValueError("cannot split empty scope tokens")

    boundary = 0
    for token in tokens:
        if not is_venue_token(token):
            break
        boundary += 1

    if boundary == 0:
        raise ValueError(
            f"scope tokens {tokens!r} start with a non-venue token — grammar requires at least one venue token first"
        )

    return tokens[:boundary], tokens[boundary:]


__all__ = [
    "KNOWN_VENUE_TOKENS",
    "is_venue_token",
    "split_scope_tokens",
]
