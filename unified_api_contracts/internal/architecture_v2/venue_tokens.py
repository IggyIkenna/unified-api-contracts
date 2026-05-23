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
        "bitstamp",
        "huobi",
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
    }
)

# DeFi perp protocols
_DEFI_PERP_TOKENS: frozenset[str] = frozenset(
    {
        "gmx",
        # Added 2026-04-19 after operator approval (Phase 7 NEEDS_REVIEW resolution).
        # Drift is Solana-native perps — required for SOL basis + staked-basis
        # strategies that hedge native SOL exposure on the same chain. Forcing
        # the hedge to an EVM perp venue (Hyperliquid) was economically worse
        # than the native path on every per-hedge cross-chain transfer.
        "drift",
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
    }
)

# Prediction markets
_PREDICTION_TOKENS: frozenset[str] = frozenset(
    {
        "polymarket",
        "kalshi",
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
