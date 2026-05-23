"""Prediction-market taxonomy enums + rule-based classifier.

SSOT for the 6-dimension canonical sharding of prediction-market tick
data across venues (Polymarket today; Kalshi + Betfair + PredictIt in
the future):

    day / category=prediction / venue / chain / asset_group /
    underlying / market_type / resolution_period / data_type=trades /
    {condition_id}.parquet

Motivation
----------

Historical Polymarket tick data lived under
``instrument_type={BNB|BTC|ETH|...|OTHER}`` — a 14-bucket sharding where
``OTHER`` trapped 4986 / 4999 daily markets, making cross-venue
comparison, per-category P&L, and resolution-period-aware backtesting
impossible.

This module delivers the taxonomy that Polymarket (and future venues)
normalise into at ingest time:

*   :class:`PredictionShardCategory` — 13 normalized market categories
    (CRYPTO_PRICE, EQUITY_INDEX, COMMODITY, FX, MACRO, POLITICS_US,
    POLITICS_INTL, SPORTS_FOOTBALL, SPORTS_OTHER, CULTURE, TECH,
    WEATHER, MISC).
*   :class:`PredictionShardMarketType` — 5 market structures (BINARY,
    SCALAR, CATEGORICAL, RANKED, RANGE_BRACKET).
*   :class:`PredictionShardResolutionPeriod` — 8 resolution horizons
    (INTRADAY, HOURLY, DAILY, WEEKLY, MONTHLY, QUARTERLY, YEARLY,
    EVENT).
*   :func:`classify_polymarket_market` — rule-first classifier
    returning ``(category, underlying, market_type, resolution_period)``
    with deterministic slug-pattern matching and keyword fallbacks.

The ``Shard`` prefix distinguishes these from the legacy
``PredictionMarketCategory`` enum in
``canonical.domain.prediction.prediction_mapping`` (which uses a
coarser 7-value taxonomy and is already re-exported at the top-level
UAC facade).

The classifier is 95%+ deterministic on real Polymarket slug patterns
(``bnb-up-or-down-april-15``, ``trump-impeached-2025``,
``oscars-best-picture-2026``, ``kamala-pick-vp``). ``MISC`` catches
genuinely uncategorisable markets; target is <50/day.

This taxonomy is intentionally cross-venue: Kalshi, Betfair prediction
books, PredictIt all produce rows that resolve into the same
(category, underlying, market_type, resolution_period) tuple so that
downstream strategies operate on venue-agnostic shards.
"""

from __future__ import annotations

import hashlib
import re
from enum import StrEnum

__all__ = [
    "KEYWORD_TO_CATEGORY",
    "OUTCOME_TO_MARKET_TYPE",
    "SLUG_PREFIX_MAP",
    "PredictionShardCategory",
    "PredictionShardMarketType",
    "PredictionShardResolutionPeriod",
    "classify_polymarket_market",
]


class PredictionShardCategory(StrEnum):
    """Normalized prediction-market categories (cross-venue)."""

    CRYPTO_PRICE = "CRYPTO_PRICE"
    EQUITY_INDEX = "EQUITY_INDEX"
    COMMODITY = "COMMODITY"
    FX = "FX"
    MACRO = "MACRO"
    POLITICS_US = "POLITICS_US"
    POLITICS_INTL = "POLITICS_INTL"
    SPORTS_FOOTBALL = "SPORTS_FOOTBALL"
    SPORTS_OTHER = "SPORTS_OTHER"
    CULTURE = "CULTURE"
    TECH = "TECH"
    WEATHER = "WEATHER"
    MISC = "MISC"


class PredictionShardMarketType(StrEnum):
    """Prediction-market structure."""

    BINARY = "binary"
    SCALAR = "scalar"
    CATEGORICAL = "categorical"
    RANKED = "ranked"
    RANGE_BRACKET = "range_bracket"


class PredictionShardResolutionPeriod(StrEnum):
    """Resolution horizon."""

    INTRADAY = "intraday"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    EVENT = "event"


# ---------------------------------------------------------------------------
# Reference tables
# ---------------------------------------------------------------------------

# Slug prefix → (category, underlying).
# Ordered-dict semantics via Python 3.7+; most specific keys appear first so
# the linear scan finds them before short crypto-ticker prefixes match.
SLUG_PREFIX_MAP: dict[str, tuple[PredictionShardCategory, str]] = {
    # --- Crypto prices ---
    "bitcoin-": (PredictionShardCategory.CRYPTO_PRICE, "BTC"),
    "btc-": (PredictionShardCategory.CRYPTO_PRICE, "BTC"),
    "ethereum-": (PredictionShardCategory.CRYPTO_PRICE, "ETH"),
    "eth-": (PredictionShardCategory.CRYPTO_PRICE, "ETH"),
    "solana-": (PredictionShardCategory.CRYPTO_PRICE, "SOL"),
    "sol-": (PredictionShardCategory.CRYPTO_PRICE, "SOL"),
    "xrp-": (PredictionShardCategory.CRYPTO_PRICE, "XRP"),
    "ripple-": (PredictionShardCategory.CRYPTO_PRICE, "XRP"),
    "dogecoin-": (PredictionShardCategory.CRYPTO_PRICE, "DOGE"),
    "doge-": (PredictionShardCategory.CRYPTO_PRICE, "DOGE"),
    "bnb-": (PredictionShardCategory.CRYPTO_PRICE, "BNB"),
    "hype-": (PredictionShardCategory.CRYPTO_PRICE, "HYPE"),
    "hyperliquid-": (PredictionShardCategory.CRYPTO_PRICE, "HYPE"),
    "sui-": (PredictionShardCategory.CRYPTO_PRICE, "SUI"),
    "ada-": (PredictionShardCategory.CRYPTO_PRICE, "ADA"),
    "cardano-": (PredictionShardCategory.CRYPTO_PRICE, "ADA"),
    "ltc-": (PredictionShardCategory.CRYPTO_PRICE, "LTC"),
    "litecoin-": (PredictionShardCategory.CRYPTO_PRICE, "LTC"),
    "avax-": (PredictionShardCategory.CRYPTO_PRICE, "AVAX"),
    "avalanche-": (PredictionShardCategory.CRYPTO_PRICE, "AVAX"),
    "link-": (PredictionShardCategory.CRYPTO_PRICE, "LINK"),
    "chainlink-": (PredictionShardCategory.CRYPTO_PRICE, "LINK"),
    # --- Equity indices ---
    "spx-": (PredictionShardCategory.EQUITY_INDEX, "SPX"),
    "sp500-": (PredictionShardCategory.EQUITY_INDEX, "SPX"),
    "s-and-p-500-": (PredictionShardCategory.EQUITY_INDEX, "SPX"),
    "ndx-": (PredictionShardCategory.EQUITY_INDEX, "NDX"),
    "nasdaq-": (PredictionShardCategory.EQUITY_INDEX, "NDX"),
    "djia-": (PredictionShardCategory.EQUITY_INDEX, "DJIA"),
    "dow-": (PredictionShardCategory.EQUITY_INDEX, "DJIA"),
    "rut-": (PredictionShardCategory.EQUITY_INDEX, "RUT"),
    "russell-2000-": (PredictionShardCategory.EQUITY_INDEX, "RUT"),
    "russell-": (PredictionShardCategory.EQUITY_INDEX, "RUT"),
    # --- Commodities ---
    "gold-": (PredictionShardCategory.COMMODITY, "GOLD"),
    "silver-": (PredictionShardCategory.COMMODITY, "SILVER"),
    "crude-oil-": (PredictionShardCategory.COMMODITY, "CRUDE_OIL"),
    "oil-": (PredictionShardCategory.COMMODITY, "CRUDE_OIL"),
    "wti-": (PredictionShardCategory.COMMODITY, "CRUDE_OIL"),
    "brent-": (PredictionShardCategory.COMMODITY, "CRUDE_OIL"),
    "nat-gas-": (PredictionShardCategory.COMMODITY, "NAT_GAS"),
    "natural-gas-": (PredictionShardCategory.COMMODITY, "NAT_GAS"),
    # --- FX ---
    "usd-eur-": (PredictionShardCategory.FX, "EURUSD"),
    "eur-usd-": (PredictionShardCategory.FX, "EURUSD"),
    "usd-jpy-": (PredictionShardCategory.FX, "USDJPY"),
    "usd-gbp-": (PredictionShardCategory.FX, "GBPUSD"),
    "gbp-usd-": (PredictionShardCategory.FX, "GBPUSD"),
    # --- Macro ---
    "fed-rate-": (PredictionShardCategory.MACRO, "FED_FUNDS"),
    "fed-": (PredictionShardCategory.MACRO, "FED_FUNDS"),
    "fomc-": (PredictionShardCategory.MACRO, "FED_FUNDS"),
    "cpi-": (PredictionShardCategory.MACRO, "CPI"),
    "inflation-": (PredictionShardCategory.MACRO, "CPI"),
    "gdp-": (PredictionShardCategory.MACRO, "GDP"),
    "unemployment-": (PredictionShardCategory.MACRO, "UNEMPLOYMENT"),
    "nonfarm-": (PredictionShardCategory.MACRO, "NONFARM_PAYROLLS"),
    "nfp-": (PredictionShardCategory.MACRO, "NONFARM_PAYROLLS"),
    "treasury-": (PredictionShardCategory.MACRO, "TREASURY_YIELDS"),
    "10-year-yield-": (PredictionShardCategory.MACRO, "TREASURY_YIELDS"),
    # --- US Politics ---
    "trump-": (PredictionShardCategory.POLITICS_US, "TRUMP"),
    "biden-": (PredictionShardCategory.POLITICS_US, "BIDEN"),
    "kamala-": (PredictionShardCategory.POLITICS_US, "KAMALA_HARRIS"),
    "harris-": (PredictionShardCategory.POLITICS_US, "KAMALA_HARRIS"),
    "vance-": (PredictionShardCategory.POLITICS_US, "JD_VANCE"),
    "desantis-": (PredictionShardCategory.POLITICS_US, "DESANTIS"),
    "newsom-": (PredictionShardCategory.POLITICS_US, "NEWSOM"),
    "aoc-": (PredictionShardCategory.POLITICS_US, "AOC"),
    "us-election-": (PredictionShardCategory.POLITICS_US, "US_ELECTION"),
    "us-president-": (PredictionShardCategory.POLITICS_US, "US_ELECTION"),
    "presidential-": (PredictionShardCategory.POLITICS_US, "US_ELECTION"),
    "gop-": (PredictionShardCategory.POLITICS_US, "GOP_PRIMARY"),
    "republican-": (PredictionShardCategory.POLITICS_US, "GOP_PRIMARY"),
    "democratic-": (PredictionShardCategory.POLITICS_US, "DEM_PRIMARY"),
    "senate-": (PredictionShardCategory.POLITICS_US, "US_SENATE"),
    "house-": (PredictionShardCategory.POLITICS_US, "US_HOUSE"),
    "impeachment-": (PredictionShardCategory.POLITICS_US, "IMPEACHMENT"),
    "scotus-": (PredictionShardCategory.POLITICS_US, "SCOTUS"),
    "supreme-court-": (PredictionShardCategory.POLITICS_US, "SCOTUS"),
    # --- International Politics ---
    "uk-election-": (PredictionShardCategory.POLITICS_INTL, "UK_ELECTION"),
    "uk-pm-": (PredictionShardCategory.POLITICS_INTL, "UK_PM"),
    "starmer-": (PredictionShardCategory.POLITICS_INTL, "STARMER"),
    "sunak-": (PredictionShardCategory.POLITICS_INTL, "SUNAK"),
    "france-": (PredictionShardCategory.POLITICS_INTL, "FRANCE"),
    "macron-": (PredictionShardCategory.POLITICS_INTL, "MACRON"),
    "germany-": (PredictionShardCategory.POLITICS_INTL, "GERMANY"),
    "merz-": (PredictionShardCategory.POLITICS_INTL, "MERZ"),
    "india-election-": (PredictionShardCategory.POLITICS_INTL, "INDIA_ELECTION"),
    "modi-": (PredictionShardCategory.POLITICS_INTL, "MODI"),
    "putin-": (PredictionShardCategory.POLITICS_INTL, "PUTIN"),
    "zelensky-": (PredictionShardCategory.POLITICS_INTL, "ZELENSKY"),
    "duterte-": (PredictionShardCategory.POLITICS_INTL, "DUTERTE"),
    "israel-": (PredictionShardCategory.POLITICS_INTL, "ISRAEL"),
    "hamas-": (PredictionShardCategory.POLITICS_INTL, "ISRAEL"),
    "ukraine-": (PredictionShardCategory.POLITICS_INTL, "UKRAINE"),
    "russia-": (PredictionShardCategory.POLITICS_INTL, "RUSSIA"),
    "china-": (PredictionShardCategory.POLITICS_INTL, "CHINA"),
    "taiwan-": (PredictionShardCategory.POLITICS_INTL, "TAIWAN"),
    "iran-": (PredictionShardCategory.POLITICS_INTL, "IRAN"),
    "north-korea-": (PredictionShardCategory.POLITICS_INTL, "NORTH_KOREA"),
    "venezuela-": (PredictionShardCategory.POLITICS_INTL, "VENEZUELA"),
    "argentina-": (PredictionShardCategory.POLITICS_INTL, "ARGENTINA"),
    "brazil-": (PredictionShardCategory.POLITICS_INTL, "BRAZIL"),
    "mexico-": (PredictionShardCategory.POLITICS_INTL, "MEXICO"),
    "canada-": (PredictionShardCategory.POLITICS_INTL, "CANADA"),
    "trudeau-": (PredictionShardCategory.POLITICS_INTL, "CANADA"),
    "milei-": (PredictionShardCategory.POLITICS_INTL, "ARGENTINA"),
    # --- Macro / sentiment extension ---
    "fear-greed-": (PredictionShardCategory.MACRO, "FEAR_GREED"),
    "fear-and-greed-": (PredictionShardCategory.MACRO, "FEAR_GREED"),
    "fear-": (PredictionShardCategory.MACRO, "FEAR_GREED"),
    "greed-": (PredictionShardCategory.MACRO, "FEAR_GREED"),
    "ppi-": (PredictionShardCategory.MACRO, "PPI"),
    "pce-": (PredictionShardCategory.MACRO, "PCE"),
    "jobless-": (PredictionShardCategory.MACRO, "UNEMPLOYMENT"),
    "recession-": (PredictionShardCategory.MACRO, "RECESSION"),
    # --- Sports: Football (EPL, Champions League, World Cup, NFL) ---
    "epl-": (PredictionShardCategory.SPORTS_FOOTBALL, "EPL"),
    "premier-league-": (PredictionShardCategory.SPORTS_FOOTBALL, "EPL"),
    "uefa-": (PredictionShardCategory.SPORTS_FOOTBALL, "UEFA"),
    "champions-league-": (PredictionShardCategory.SPORTS_FOOTBALL, "CHAMPIONS_LEAGUE"),
    "world-cup-": (PredictionShardCategory.SPORTS_FOOTBALL, "WORLD_CUP"),
    "la-liga-": (PredictionShardCategory.SPORTS_FOOTBALL, "LA_LIGA"),
    "laliga-": (PredictionShardCategory.SPORTS_FOOTBALL, "LA_LIGA"),
    "serie-a-": (PredictionShardCategory.SPORTS_FOOTBALL, "SERIE_A"),
    "bundesliga-": (PredictionShardCategory.SPORTS_FOOTBALL, "BUNDESLIGA"),
    "nfl-": (PredictionShardCategory.SPORTS_FOOTBALL, "NFL"),
    "super-bowl-": (PredictionShardCategory.SPORTS_FOOTBALL, "NFL"),
    # --- Sports: Other ---
    "nba-": (PredictionShardCategory.SPORTS_OTHER, "NBA"),
    "mlb-": (PredictionShardCategory.SPORTS_OTHER, "MLB"),
    "nhl-": (PredictionShardCategory.SPORTS_OTHER, "NHL"),
    "f1-": (PredictionShardCategory.SPORTS_OTHER, "F1"),
    "formula-1-": (PredictionShardCategory.SPORTS_OTHER, "F1"),
    "tennis-": (PredictionShardCategory.SPORTS_OTHER, "TENNIS"),
    "wimbledon-": (PredictionShardCategory.SPORTS_OTHER, "TENNIS"),
    "us-open-tennis-": (PredictionShardCategory.SPORTS_OTHER, "TENNIS"),
    "atp-": (PredictionShardCategory.SPORTS_OTHER, "TENNIS"),
    "wta-": (PredictionShardCategory.SPORTS_OTHER, "TENNIS"),
    "golf-": (PredictionShardCategory.SPORTS_OTHER, "GOLF"),
    "pga-": (PredictionShardCategory.SPORTS_OTHER, "GOLF"),
    "masters-tournament-": (PredictionShardCategory.SPORTS_OTHER, "GOLF"),
    "ufc-": (PredictionShardCategory.SPORTS_OTHER, "UFC"),
    "mma-": (PredictionShardCategory.SPORTS_OTHER, "UFC"),
    "boxing-": (PredictionShardCategory.SPORTS_OTHER, "BOXING"),
    "olympics-": (PredictionShardCategory.SPORTS_OTHER, "OLYMPICS"),
    # --- Culture ---
    "oscars-": (PredictionShardCategory.CULTURE, "OSCARS"),
    "oscar-": (PredictionShardCategory.CULTURE, "OSCARS"),
    "academy-awards-": (PredictionShardCategory.CULTURE, "OSCARS"),
    "grammys-": (PredictionShardCategory.CULTURE, "GRAMMYS"),
    "grammy-": (PredictionShardCategory.CULTURE, "GRAMMYS"),
    "emmys-": (PredictionShardCategory.CULTURE, "EMMYS"),
    "emmy-": (PredictionShardCategory.CULTURE, "EMMYS"),
    "mtv-": (PredictionShardCategory.CULTURE, "MTV"),
    "billboard-": (PredictionShardCategory.CULTURE, "BILLBOARD"),
    "taylor-swift-": (PredictionShardCategory.CULTURE, "TAYLOR_SWIFT"),
    "eurovision-": (PredictionShardCategory.CULTURE, "EUROVISION"),
    "kanye-": (PredictionShardCategory.CULTURE, "KANYE"),
    "elon-": (PredictionShardCategory.TECH, "ELON_MUSK"),
    "musk-": (PredictionShardCategory.TECH, "ELON_MUSK"),
    # --- Tech ---
    "nvda-": (PredictionShardCategory.TECH, "NVDA"),
    "nvidia-": (PredictionShardCategory.TECH, "NVDA"),
    "tsla-": (PredictionShardCategory.TECH, "TSLA"),
    "tesla-": (PredictionShardCategory.TECH, "TSLA"),
    "aapl-": (PredictionShardCategory.TECH, "AAPL"),
    "apple-": (PredictionShardCategory.TECH, "AAPL"),
    "openai-": (PredictionShardCategory.TECH, "OPENAI"),
    "gpt-": (PredictionShardCategory.TECH, "OPENAI"),
    "chatgpt-": (PredictionShardCategory.TECH, "OPENAI"),
    "gemini-": (PredictionShardCategory.TECH, "GOOGLE"),
    "claude-": (PredictionShardCategory.TECH, "ANTHROPIC"),
    "anthropic-": (PredictionShardCategory.TECH, "ANTHROPIC"),
    "ai-benchmark-": (PredictionShardCategory.TECH, "AI_BENCHMARK"),
    "sora-": (PredictionShardCategory.TECH, "OPENAI"),
    # --- Weather ---
    "hurricane-": (PredictionShardCategory.WEATHER, "HURRICANE"),
    "typhoon-": (PredictionShardCategory.WEATHER, "TYPHOON"),
    "el-nino-": (PredictionShardCategory.WEATHER, "EL_NINO"),
    "la-nina-": (PredictionShardCategory.WEATHER, "LA_NINA"),
    "temperature-record-": (PredictionShardCategory.WEATHER, "TEMP_RECORD"),
    "temperature-": (PredictionShardCategory.WEATHER, "TEMPERATURE"),
    "weather-": (PredictionShardCategory.WEATHER, "WEATHER"),
    "heat-wave-": (PredictionShardCategory.WEATHER, "HEAT_WAVE"),
    "epstein-": (PredictionShardCategory.POLITICS_US, "EPSTEIN"),
    "wildfire-": (PredictionShardCategory.WEATHER, "WILDFIRE"),
    "snowfall-": (PredictionShardCategory.WEATHER, "SNOWFALL"),
}


# Keyword → category (lower-cased substring match). Only used if slug
# prefix matching fails.
KEYWORD_TO_CATEGORY: dict[str, tuple[PredictionShardCategory, str]] = {
    "bitcoin": (PredictionShardCategory.CRYPTO_PRICE, "BTC"),
    "ethereum": (PredictionShardCategory.CRYPTO_PRICE, "ETH"),
    "solana": (PredictionShardCategory.CRYPTO_PRICE, "SOL"),
    "dogecoin": (PredictionShardCategory.CRYPTO_PRICE, "DOGE"),
    "s&p 500": (PredictionShardCategory.EQUITY_INDEX, "SPX"),
    "nasdaq": (PredictionShardCategory.EQUITY_INDEX, "NDX"),
    "dow jones": (PredictionShardCategory.EQUITY_INDEX, "DJIA"),
    "crude oil": (PredictionShardCategory.COMMODITY, "CRUDE_OIL"),
    "gold price": (PredictionShardCategory.COMMODITY, "GOLD"),
    "silver price": (PredictionShardCategory.COMMODITY, "SILVER"),
    "fed rate": (PredictionShardCategory.MACRO, "FED_FUNDS"),
    "interest rate": (PredictionShardCategory.MACRO, "FED_FUNDS"),
    "trump": (PredictionShardCategory.POLITICS_US, "TRUMP"),
    "biden": (PredictionShardCategory.POLITICS_US, "BIDEN"),
    "kamala": (PredictionShardCategory.POLITICS_US, "KAMALA_HARRIS"),
    "putin": (PredictionShardCategory.POLITICS_INTL, "PUTIN"),
    "macron": (PredictionShardCategory.POLITICS_INTL, "MACRON"),
    "premier league": (PredictionShardCategory.SPORTS_FOOTBALL, "EPL"),
    "world cup": (PredictionShardCategory.SPORTS_FOOTBALL, "WORLD_CUP"),
    "super bowl": (PredictionShardCategory.SPORTS_FOOTBALL, "NFL"),
    "nba": (PredictionShardCategory.SPORTS_OTHER, "NBA"),
    "oscars": (PredictionShardCategory.CULTURE, "OSCARS"),
    "academy award": (PredictionShardCategory.CULTURE, "OSCARS"),
    "nvidia": (PredictionShardCategory.TECH, "NVDA"),
    "openai": (PredictionShardCategory.TECH, "OPENAI"),
    "hurricane": (PredictionShardCategory.WEATHER, "HURRICANE"),
}


# Outcome pattern → market type (applied after category resolved).
OUTCOME_TO_MARKET_TYPE: dict[str, PredictionShardMarketType] = {
    "yes": PredictionShardMarketType.BINARY,
    "no": PredictionShardMarketType.BINARY,
    "up": PredictionShardMarketType.BINARY,
    "down": PredictionShardMarketType.BINARY,
}


# Slug tokens that indicate a scalar/range-bracket market.
_RANGE_BRACKET_TOKENS: frozenset[str] = frozenset(
    {
        "up-or-down",
        "above-or-below",
        "greater-than",
        "less-than",
        "reach-",
        "hit-",
        "between-",
    }
)


# Date-token patterns (YYYY-MM-DD, april-15, q1-2026, etc.) used for
# resolution-period inference. Deliberately broad — classifier only uses
# them to pick a period once the category is known.
_WEEKLY_TOKENS: frozenset[str] = frozenset({"week", "weekly"})
_MONTHLY_TOKENS: frozenset[str] = frozenset(
    {
        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
        "january",
        "february",
        "march",
        "april",
        # 2026-05-06 bug fix (predictions plan Phase 1A): "may" was missing
        # from the full-name set even though the 3-letter form was present.
        # Resolution-period inference for "may-15" slugs was already working
        # via the abbreviated set; the full-name addition fixes the rare case
        # of a slug like "btc-up-or-down-may-2026" using the long form.
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    }
)
_QUARTERLY_TOKENS: frozenset[str] = frozenset({"q1", "q2", "q3", "q4"})


_SLUG_TOKEN_RE: re.Pattern[str] = re.compile(r"[a-z0-9]+")


# ---------------------------------------------------------------------------
# Classifier stability hash
# ---------------------------------------------------------------------------
# Bumped manually whenever the classifier's behaviour changes in a way that
# can re-classify existing markets. Manifest rows record the hash that was
# active when the row was written so a reclassification pass can be triggered
# only for rows whose stored hash differs from the current
# ``CLASSIFIER_STABILITY_HASH`` — see
# `unified-trading-pm/plans/active/predictions_canonical_question_group_polymarket_migration_2026_05_06.md`
# Phase 0 audit-7 (classifier stability hash design).
#
# Increment ``CLASSIFIER_VERSION`` in tandem with any rule-table edit.
# ``CLASSIFIER_STABILITY_HASH`` is computed at module load from the canonical
# byte representation of the version + every rule table the classifier reads,
# so adding a new entry to ``SLUG_PREFIX_MAP`` (or any other table) flips the
# hash automatically — no manual sync required.

CLASSIFIER_VERSION = "2026-05-23.2"


def _compute_classifier_stability_hash() -> str:
    """Compute SHA-256 of the classifier's rule-tables + version constant.

    Hash inputs (in deterministic order):
      1. ``CLASSIFIER_VERSION``
      2. ``SLUG_PREFIX_MAP`` — sorted ``(slug_prefix, category, underlying)`` tuples
      3. ``KEYWORD_TO_CATEGORY`` — sorted ``(keyword, category, underlying)`` tuples
      4. ``OUTCOME_TO_MARKET_TYPE`` — sorted ``(outcome, market_type)`` tuples
      5. ``_RANGE_BRACKET_TOKENS`` — sorted token list
      6. ``_WEEKLY_TOKENS`` — sorted token list
      7. ``_MONTHLY_TOKENS`` — sorted token list
      8. ``_QUARTERLY_TOKENS`` — sorted token list

    Returns the first 16 hex characters of the SHA-256 digest (64-bit prefix
    is sufficient for collision detection across this small input space and
    keeps manifest rows compact). Manifest readers compare prefix-only.
    """
    hasher = hashlib.sha256()
    hasher.update(CLASSIFIER_VERSION.encode("utf-8"))
    hasher.update(b"\x00")

    # SLUG_PREFIX_MAP — sorted by key for deterministic hashing
    for prefix in sorted(SLUG_PREFIX_MAP):
        cat, und = SLUG_PREFIX_MAP[prefix]
        hasher.update(f"{prefix}|{cat.value}|{und}".encode())
        hasher.update(b"\x00")

    hasher.update(b"---KEYWORD_TO_CATEGORY---\x00")
    for keyword in sorted(KEYWORD_TO_CATEGORY):
        cat, und = KEYWORD_TO_CATEGORY[keyword]
        hasher.update(f"{keyword}|{cat.value}|{und}".encode())
        hasher.update(b"\x00")

    hasher.update(b"---OUTCOME_TO_MARKET_TYPE---\x00")
    for outcome in sorted(OUTCOME_TO_MARKET_TYPE):
        mt = OUTCOME_TO_MARKET_TYPE[outcome]
        hasher.update(f"{outcome}|{mt.value}".encode())
        hasher.update(b"\x00")

    for tokens_label, tokens_set in (
        ("_RANGE_BRACKET_TOKENS", _RANGE_BRACKET_TOKENS),
        ("_WEEKLY_TOKENS", _WEEKLY_TOKENS),
        ("_MONTHLY_TOKENS", _MONTHLY_TOKENS),
        ("_QUARTERLY_TOKENS", _QUARTERLY_TOKENS),
    ):
        hasher.update(f"---{tokens_label}---".encode())
        hasher.update(b"\x00")
        for tok in sorted(tokens_set):
            hasher.update(tok.encode("utf-8"))
            hasher.update(b"\x00")

    return hasher.hexdigest()[:16]


CLASSIFIER_STABILITY_HASH: str = _compute_classifier_stability_hash()


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def _classify_from_slug_prefix(
    slug: str,
) -> tuple[PredictionShardCategory, str] | None:
    """Return the first (category, underlying) whose slug prefix matches."""
    for prefix, mapping in SLUG_PREFIX_MAP.items():
        if slug.startswith(prefix):
            return mapping
    return None


def _classify_from_slug_token(
    slug: str,
) -> tuple[PredictionShardCategory, str] | None:
    """Return first (category, underlying) whose prefix appears as a ``-`` token.

    Polymarket slugs often embed the identifier mid-token
    (``will-nvda-announce-jan-15``, ``can-trump-win-iowa``,
    ``will-the-price-of-bitcoin-be-above-90k``). We tokenise on ``-``
    and look up each token + ``-`` against the prefix map, so
    ``nvda`` in ``will-nvda-announce-jan-15`` matches the ``nvda-``
    prefix entry. Tokens of length ≤ 2 are skipped to avoid false
    hits. Also retries each token with the trailing possessive ``s``
    stripped so ``trumps-approval-rating`` matches ``trump-``.
    """
    for token in slug.split("-"):
        if len(token) <= 2:
            continue
        probe = f"{token}-"
        hit = SLUG_PREFIX_MAP.get(probe)
        if hit is not None:
            return hit
        # Possessive / plural fallback — Polymarket slugs drop the
        # apostrophe (``trumps-approval-rating``, ``bidens-approval``).
        if token.endswith("s") and len(token) > 3:
            stripped = token[:-1]
            probe2 = f"{stripped}-"
            hit2 = SLUG_PREFIX_MAP.get(probe2)
            if hit2 is not None:
                return hit2
    return None


def _classify_from_keywords(
    text: str,
) -> tuple[PredictionShardCategory, str] | None:
    lower = text.lower()
    for keyword, mapping in KEYWORD_TO_CATEGORY.items():
        if keyword in lower:
            return mapping
    return None


def _infer_market_type(slug: str, outcome: str) -> PredictionShardMarketType:
    slug_lower = slug.lower()
    outcome_lower = outcome.lower().strip()
    if any(tok in slug_lower for tok in _RANGE_BRACKET_TOKENS):
        return PredictionShardMarketType.RANGE_BRACKET
    if "bracket" in slug_lower or "range" in slug_lower:
        return PredictionShardMarketType.RANGE_BRACKET
    if outcome_lower in OUTCOME_TO_MARKET_TYPE:
        return OUTCOME_TO_MARKET_TYPE[outcome_lower]
    # Slugs like ``most-xxx-2026``, ``top-3``, ``finish-top-10`` → ranked.
    if "most-" in slug_lower or "top-" in slug_lower or "finish-top" in slug_lower:
        return PredictionShardMarketType.RANKED
    # Slugs with winner/runner-up/pick-*/mvp/nominee/best-* → categorical
    # (one-of-many).
    if any(
        tok in slug_lower
        for tok in (
            "winner",
            "who-will-win",
            "pick-",
            "nominee",
            "best-",
            "mvp",
            "champion",
            "drivers-champion",
            "final",
        )
    ):
        return PredictionShardMarketType.CATEGORICAL
    return PredictionShardMarketType.BINARY


def _infer_resolution_period(
    slug: str,
    title: str,
    category: PredictionShardCategory,
) -> PredictionShardResolutionPeriod:
    slug_lower = slug.lower()
    title_lower = title.lower()
    combined = f"{slug_lower} {title_lower}"
    tokens = set(_SLUG_TOKEN_RE.findall(slug_lower))
    # ``up-or-down-hour-*`` and ``up-or-down-minute-*`` → intraday.
    if "hour" in combined or "hourly" in combined:
        return PredictionShardResolutionPeriod.HOURLY
    if "minute" in combined or "intraday" in combined:
        return PredictionShardResolutionPeriod.INTRADAY
    # Direct tokens.
    if tokens & _WEEKLY_TOKENS:
        return PredictionShardResolutionPeriod.WEEKLY
    if tokens & _QUARTERLY_TOKENS:
        return PredictionShardResolutionPeriod.QUARTERLY
    if "daily" in tokens or "day" in tokens:
        return PredictionShardResolutionPeriod.DAILY
    # ``-2026`` / ``-2027`` year marker (Polymarket year-markets) → yearly.
    if re.search(r"-20\d{2}\b", slug_lower) or re.search(r"\b20\d{2}\b", title_lower):
        # But only if it's not a month-specific slug.
        if tokens & _MONTHLY_TOKENS:
            return PredictionShardResolutionPeriod.MONTHLY
        # Sports + Weather categories with a year still resolve per-fixture/storm.
        if category in (
            PredictionShardCategory.SPORTS_FOOTBALL,
            PredictionShardCategory.SPORTS_OTHER,
            PredictionShardCategory.WEATHER,
        ):
            return PredictionShardResolutionPeriod.EVENT
        return PredictionShardResolutionPeriod.YEARLY
    # Sports fixture-style markets — resolve per-event.
    if category in (
        PredictionShardCategory.SPORTS_FOOTBALL,
        PredictionShardCategory.SPORTS_OTHER,
    ):
        return PredictionShardResolutionPeriod.EVENT
    # Weather events resolve per-storm.
    if category is PredictionShardCategory.WEATHER:
        return PredictionShardResolutionPeriod.EVENT
    # Month tokens alone → monthly.
    if tokens & _MONTHLY_TOKENS:
        return PredictionShardResolutionPeriod.MONTHLY
    # Default — event-based.
    return PredictionShardResolutionPeriod.EVENT


def classify_polymarket_market(
    title: str,
    slug: str,
    event_slug: str,
    outcome: str,
) -> tuple[PredictionShardCategory, str, PredictionShardMarketType, PredictionShardResolutionPeriod]:
    """Classify a Polymarket market into the 4-tuple canonical taxonomy.

    Rule-first: slug prefix match handles ~95% of real Polymarket slugs
    (``bnb-up-or-down-april-15``, ``trump-impeached-2025``,
    ``oscars-best-picture-2026``, ``kamala-pick-vp``). Falls back to
    keyword search against ``title`` then ``event_slug``. ``MISC``
    catches everything else.

    Parameters
    ----------
    title:
        Human-readable question (``"Will BNB be up or down on April 15?"``).
    slug:
        Primary slug (``"bnb-up-or-down-april-15"``).
    event_slug:
        Parent event slug — often broader than the market slug
        (``"bnb-price-daily"``). Falls back if ``slug`` is empty.
    outcome:
        Specific outcome row (``"Up"``, ``"Yes"``, candidate name, etc.).

    Returns
    -------
    (category, underlying, market_type, resolution_period)
    """
    slug_norm = (slug or "").lower().strip()
    event_slug_norm = (event_slug or "").lower().strip()
    title_norm = (title or "").strip()
    outcome_norm = (outcome or "").strip()

    # 1) Slug prefix (primary).
    cat_und = _classify_from_slug_prefix(slug_norm)
    # 2) Event-slug prefix (fallback for empty/generic market slugs).
    if cat_und is None and event_slug_norm:
        cat_und = _classify_from_slug_prefix(event_slug_norm)
    # 3) Slug token-anywhere (catches ``will-nvda-announce-jan-15`` etc).
    if cat_und is None and slug_norm:
        cat_und = _classify_from_slug_token(slug_norm)
    # 4) Event-slug token-anywhere.
    if cat_und is None and event_slug_norm:
        cat_und = _classify_from_slug_token(event_slug_norm)
    # 5) Title keyword.
    if cat_und is None and title_norm:
        cat_und = _classify_from_keywords(title_norm)
    # 6) Event-slug keyword.
    if cat_und is None and event_slug_norm:
        cat_und = _classify_from_keywords(event_slug_norm)

    if cat_und is None:
        category = PredictionShardCategory.MISC
        underlying = "UNKNOWN"
    else:
        category, underlying = cat_und

    market_type = _infer_market_type(slug_norm or event_slug_norm, outcome_norm)
    resolution_period = _infer_resolution_period(slug_norm or event_slug_norm, title_norm, category)

    return category, underlying, market_type, resolution_period
