"""Bundled-data_type cluster registries — split out of honest_coverage.py.

Pure-literal SSOT for the per-bundled-data_type cluster taxonomy (which
bookmakers / strikes / question-groups a bundled shard must cover to count as
``captured``). Re-exported by :mod:`honest_coverage` so the public import
surface is unchanged. Lives in its own module to keep honest_coverage.py under
the 900-line cap (mirrors the existing ``_honest_coverage_logic`` split).
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Bundled data_types — referenced by the ManifestWriter cluster-validation guard.
# ---------------------------------------------------------------------------


BUNDLED_DATA_TYPES: Final[frozenset[str]] = frozenset(
    {
        "options_chain",
        "futures_chain",
        "prediction_canonical_question_group",
        "sports_fixture_bundle",
        # Phase 3 of cme_polymarket_arb_2026_05_08: CME event-contract
        # shard atom (root, resolution_month, day) with cluster validation
        # on strike_threshold. Registered here so ManifestWriter enforces
        # cluster validation on record_captured calls for this data_type.
        "event_contract",
        # Per-fixture sports data_types — bundle = multiple bookmakers per fixture.
        # cluster_extractor: bookmaker. Registry: SPORTS_FIXTURE_CLUSTERS.
        "odds_snapshot",
        "odds_movement",
        "arbitrage_opportunity",
    }
)
"""Closed set of bundled data_types.

A "bundled" shard packs multiple cluster identities into a single
per-day parquet (e.g. all 11 ES.OPT clusters in one file, all bookmakers
for one fixture in one row group). Cluster validation at
``record_captured`` is mandatory for these types — silent partial
bundles are the failure mode this set guards against.

Adding a new bundled data_type means adding it here AND seeding its
cluster registry (per-root, per-fixture-tier, etc.) in this module or a
neighbouring module. No half-measures: the writer guard fires the
moment the data_type appears, regardless of whether the registry has
been populated.
"""


# ---------------------------------------------------------------------------
# DATA_TYPE_TO_CLUSTER_REGISTRY — bundled-data_type → registry-name mapping.
#
# Companion to :data:`BUNDLED_DATA_TYPES`. The UTL ``record_captured`` guard
# (``MissingClusterValidationError``) cites this registry name in the error
# message so adapters know exactly which UAC SSOT to look up. Kept as a
# string→string mapping rather than a string→object to avoid eagerly
# importing every registry module from honest_coverage import paths.
# ---------------------------------------------------------------------------


DATA_TYPE_TO_CLUSTER_REGISTRY: Final[dict[str, str]] = {
    "options_chain": "ES_OPTIONS_CLUSTERS",
    "futures_chain": "FUTURES_CHAIN_BUCKETS",
    "prediction_canonical_question_group": "PREDICTION_GROUPS",
    "sports_fixture_bundle": "SPORTS_FIXTURE_CLUSTERS",
    "event_contract": "EVENT_CONTRACT_ROOT_CLUSTERS",
    "odds_snapshot": "SPORTS_FIXTURE_CLUSTERS",
    "odds_movement": "SPORTS_FIXTURE_CLUSTERS",
    "arbitrage_opportunity": "SPORTS_FIXTURE_CLUSTERS",
}


# ---------------------------------------------------------------------------
# SPORTS_FIXTURE_CLUSTERS — tier-1 EU football seed (greenfield 2026-05-06).
#
# Per-(league_tier) → expected bookmaker set. Used as the cluster registry
# for ``sports_fixture_bundle`` data_types (ODDS_SNAPSHOT / ODDS_MOVEMENT /
# ARBITRAGE per the writegate plan). A bundle that covers fewer bookmakers
# than the league-tier expects flips to ``attempted_failed[ClusterCoverageError]``
# instead of silently passing as ``captured``.
#
# Tier-1 seed: top 5 European football leagues (EPL, LaLiga, Bundesliga,
# Serie A, Ligue 1). Tier-2 / tier-3 expansion is a follow-up plan slot —
# don't pre-build until a real consumer needs it.
# ---------------------------------------------------------------------------


SPORTS_FIXTURE_CLUSTERS: Final[dict[str, dict[str, int]]] = {
    "tier_1_eu_football": {
        # Bookmakers required for a tier-1 EU football fixture odds bundle to
        # count as ``captured``. Numbers are minimum row counts per bookmaker
        # per fixture per snapshot — tuneable per the data_status_multi_axis
        # plan's "feature_group → required_inputs" framework.
        "pinnacle": 1,
        "bet365": 1,
        "william_hill": 1,
        "bwin": 1,
        "betfair_exchange": 1,
    },
}
"""Per-league-tier expected bookmaker sets for sports_fixture_bundle shards.

Tier-1 EU football seed only (writegate plan Phase 1B). Tier-2 / tier-3
expansion deferred to a follow-up plan slot — don't pre-build without a
real consumer.
"""


# ---------------------------------------------------------------------------
# PREDICTION_GROUPS — empty placeholder slot (temporary state).
#
# Populated by ``predictions_canonical_question_group_polymarket_migration_2026_05_06``
# Phase 1A. The slot is reserved here so the UTL writer guard
# (``MissingClusterValidationError``) fires consistently for the
# ``prediction_canonical_question_group`` data_type even before predictions
# Phase 1A lands. Until that plan ships, no caller passes this data_type;
# the guard surface is correct-by-construction.
#
# Documented in the writegate plan's "Temporary states + their canonical
# follow-up plans" section.
# ---------------------------------------------------------------------------


PREDICTION_GROUPS: Final[dict[str, dict[str, int]]] = {
    # Cadenced range-bracket markets — count is min ticks per market_id
    # required for the bundle to count as ``captured``. HOURLY markets
    # tick fast through their 1-hour life (~1000 events typical);
    # DAILY markets tick over 24h (~10000 events typical). Lower bounds
    # are intentionally conservative — adapters that fall short flip
    # the bundle to ``attempted_failed[ClusterCoverageError]`` instead
    # of silently passing.
    #
    # Cluster keys are market_ids; the cluster_extractor lambda is
    # ``lambda row: row["market_id"]``. Per-day expected market_id set
    # is derived at runtime from the lifecycle table
    # (via ``unified_api_contracts.canonical.domain.predictions.lifecycle.expected_market_ids_for_canonical_group``);
    # the registry carries the per-market min row count only.
    "BTC_UP_DOWN_5MIN": {"_per_market_min_rows": 20},
    "BTC_UP_DOWN_15MIN": {"_per_market_min_rows": 20},
    "BTC_UP_DOWN_INTRADAY": {"_per_market_min_rows": 20},
    "BTC_UP_DOWN_HOURLY": {"_per_market_min_rows": 100},
    "BTC_UP_DOWN_DAILY": {"_per_market_min_rows": 1000},
    "ETH_UP_DOWN_5MIN": {"_per_market_min_rows": 20},
    "ETH_UP_DOWN_15MIN": {"_per_market_min_rows": 20},
    "ETH_UP_DOWN_INTRADAY": {"_per_market_min_rows": 20},
    "ETH_UP_DOWN_HOURLY": {"_per_market_min_rows": 100},
    "ETH_UP_DOWN_DAILY": {"_per_market_min_rows": 1000},
    "SPX_UP_DOWN_DAILY": {"_per_market_min_rows": 1000},
    # CME event-contract linked groups — predictions_master Phase 5.
    # Min-row floors set conservatively at 500 (daily market, ~30min resolution
    # window before CME 21:00 UTC settlement; Polymarket thinner than BTC/ETH).
    "NDX_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "RUT_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "DJIA_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "GOLD_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "CRUDE_OIL_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "NATGAS_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "EUR_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "FED_RATE_DECISION_PER_FOMC": {"_per_market_min_rows": 100},
    "CPI_PRINT_PER_MONTH": {"_per_market_min_rows": 100},
    # Alt-coin daily up-or-down — mirror BTC/ETH DAILY (decision 338).
    # Floor 500: alts thinner than BTC/ETH (1000) on Polymarket.
    "SOL_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "XRP_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "DOGE_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "BNB_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "ADA_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "AVAX_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "LINK_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "LTC_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "SUI_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    "HYPE_UP_DOWN_DAILY": {"_per_market_min_rows": 500},
    # Macro economic-release groups (decision 338). Floor 100 (matches
    # FED/CPI — release-cadence markets, thinner than crypto price tickers).
    "UNEMPLOYMENT_RATE_PER_MONTH": {"_per_market_min_rows": 100},
    "NONFARM_PAYROLLS_PER_MONTH": {"_per_market_min_rows": 100},
    "GDP_PRINT_PER_QUARTER": {"_per_market_min_rows": 100},
    "PPI_PRINT_PER_MONTH": {"_per_market_min_rows": 100},
    "PCE_PRINT_PER_MONTH": {"_per_market_min_rows": 100},
    "TREASURY_YIELD_PER_PRINT": {"_per_market_min_rows": 100},
    "CRYPTO_FEAR_GREED_INDEX": {"_per_market_min_rows": 100},
    # Weather daily highest-temperature (decision 338). Floor 20 — weather
    # markets are thin per market_id.
    "WEATHER_TEMP_DAILY": {"_per_market_min_rows": 20},
    # === decision 338 pass 2 (2026-06-16) — granular split ===
    # Crypto PRICE-RANGE ("between $X-$Y" / multistrike) — split from UP_DOWN.
    "BTC_PRICE_RANGE_DAILY": {"_per_market_min_rows": 500},
    "ETH_PRICE_RANGE_DAILY": {"_per_market_min_rows": 500},
    "SOL_PRICE_RANGE_DAILY": {"_per_market_min_rows": 500},
    "XRP_PRICE_RANGE_DAILY": {"_per_market_min_rows": 500},
    "DOGE_PRICE_RANGE_DAILY": {"_per_market_min_rows": 500},
    "BNB_PRICE_RANGE_DAILY": {"_per_market_min_rows": 500},
    "ADA_PRICE_RANGE_DAILY": {"_per_market_min_rows": 500},
    "AVAX_PRICE_RANGE_DAILY": {"_per_market_min_rows": 500},
    "LINK_PRICE_RANGE_DAILY": {"_per_market_min_rows": 500},
    "LTC_PRICE_RANGE_DAILY": {"_per_market_min_rows": 500},
    "SUI_PRICE_RANGE_DAILY": {"_per_market_min_rows": 500},
    "HYPE_PRICE_RANGE_DAILY": {"_per_market_min_rows": 500},
    # Political-figure split + tech-personality factories.
    "TRUMP_APPROVAL_RATING": {"_per_market_min_rows": 100},
    "TRUMP_STATEMENTS": {"_per_market_min_rows": 50},
    "TRUMP_EXEC_ORDER": {"_per_market_min_rows": 50},
    "ELON_TWEET_COUNT": {"_per_market_min_rows": 50},
    "ELON_STATEMENTS": {"_per_market_min_rows": 50},
    "ELON_NET_WORTH": {"_per_market_min_rows": 50},
    # Geopolitics conflict-by-date.
    "GEO_ISRAEL_IRAN": {"_per_market_min_rows": 50},
    "GEO_RUSSIA_UKRAINE": {"_per_market_min_rows": 50},
    "GEO_OTHER_BY_DATE": {"_per_market_min_rows": 50},
    # Culture + commodity price-level.
    "BOX_OFFICE_OPENING_WEEKEND": {"_per_market_min_rows": 50},
    "GOLD_PRICE_LEVEL": {"_per_market_min_rows": 50},
    "SILVER_PRICE_LEVEL": {"_per_market_min_rows": 50},
    "CRUDE_OIL_PRICE_LEVEL": {"_per_market_min_rows": 50},
    # === decision 338 pass 2 sports (league x market-type; thin per market) ===
    "SPORTS_MLB_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_MLB_SPREAD": {"_per_market_min_rows": 20},
    "SPORTS_MLB_TOTAL": {"_per_market_min_rows": 20},
    "SPORTS_MLB_NRFI": {"_per_market_min_rows": 20},
    "SPORTS_NFL_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_NFL_SPREAD": {"_per_market_min_rows": 20},
    "SPORTS_NFL_TOTAL": {"_per_market_min_rows": 20},
    "SPORTS_NBA_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_NBA_SPREAD": {"_per_market_min_rows": 20},
    "SPORTS_NBA_TOTAL": {"_per_market_min_rows": 20},
    "SPORTS_NHL_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_NHL_SPREAD": {"_per_market_min_rows": 20},
    "SPORTS_NHL_TOTAL": {"_per_market_min_rows": 20},
    "SPORTS_EPL_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_EPL_TOTAL": {"_per_market_min_rows": 20},
    "SPORTS_UEFA_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_UEFA_TOTAL": {"_per_market_min_rows": 20},
    "SPORTS_CHAMPIONS_LEAGUE_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_LA_LIGA_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_SERIE_A_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_BUNDESLIGA_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_WORLD_CUP_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_F1_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_F1_GP_WINNER": {"_per_market_min_rows": 20},
    "SPORTS_F1_CONSTRUCTOR": {"_per_market_min_rows": 20},
    "SPORTS_TENNIS_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_GOLF_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_UFC_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_BOXING_MATCH": {"_per_market_min_rows": 20},
    "SPORTS_OLYMPICS_MATCH": {"_per_market_min_rows": 20},
    # Explicit small residual for genuinely-uncategorised novelty markets.
    "MISC_NOVELTY": {"_per_market_min_rows": 1},
    "ELECTION_PRESIDENT_2028": {"_per_market_min_rows": 100},
    "OSCARS_BEST_PICTURE": {"_per_market_min_rows": 50},
    # OTHER catch-all: cluster validation is count > 0 (any market falls through).
    # _per_market_min_rows=1 — the gate passes when ≥1 row exists for any market_id
    # routed here. No per-day expected market_id set is derived from the lifecycle
    # table (unlike curated groups); the manifest records the capture for auditing.
    "OTHER": {"_per_market_min_rows": 1},
}
"""Per-canonical_question_group expected market_id sets.

Keyed by canonical_question_group name (string form of
:class:`unified_api_contracts.canonical.domain.predictions.canonical_groups.CanonicalQuestionGroup`).
Each group's inner dict carries a ``_per_market_min_rows`` floor — the
cluster gate at ``ManifestWriter.record_captured`` derives the per-day
expected market_id set from the lifecycle table at runtime and applies
this min-rows floor per market_id.

Populated by predictions plan
``predictions_canonical_question_group_polymarket_migration_2026_05_06.plan``
Phase 1A.
"""


# ---------------------------------------------------------------------------
# EVENT_CONTRACT_ROOT_CLUSTERS — CME binary event-contract shard atom.
#
# Shard atom: (asset_group=tradfi, venue=CME, data_type=EVENT_CONTRACT,
#   root, resolution_date, day). Each root (ECES/ECBTC/etc.) bundles
# multiple (resolution_date, strike_threshold) clusters in one per-day
# parquet. The expected cluster set is derived at runtime from the
# instruments-service catalog; this registry carries the per-cluster
# min-rows floor (1 row per (resolution_date, strike_threshold) pair is
# the minimum — each binary is a distinct YES/NO contract).
#
# 9 roots: ECES (SP500) · ECNQ (NASDAQ100) · ECRTY (RUSSELL2000) ·
#   ECYM (DOW) · ECGC (GOLD) · ECCL (CRUDE) · ECNG (NATGAS) ·
#   EC6E (EUR) · ECBTC (BTC).
# Databento coverage starts 2025-09-28 for all roots.
# SSOT: cme_polymarket_arb_2026_05_08.md Phase 3.
# ---------------------------------------------------------------------------


EVENT_CONTRACT_ROOT_CLUSTERS: Final[dict[str, dict[str, int]]] = {
    "ECES": {"_per_cluster_min_rows": 1},
    "ECNQ": {"_per_cluster_min_rows": 1},
    "ECRTY": {"_per_cluster_min_rows": 1},
    "ECYM": {"_per_cluster_min_rows": 1},
    "ECGC": {"_per_cluster_min_rows": 1},
    "ECCL": {"_per_cluster_min_rows": 1},
    "ECNG": {"_per_cluster_min_rows": 1},
    "EC6E": {"_per_cluster_min_rows": 1},
    "ECBTC": {"_per_cluster_min_rows": 1},
}
"""Per-root minimum-rows floor for CME EVENT_CONTRACT bundle shards.

Keyed by CME root symbol (ECES, ECNQ, etc.). The actual expected cluster
set (resolution_date x strike_threshold tuples) is derived at runtime
from the instruments-service catalog — this registry only supplies the
``_per_cluster_min_rows`` floor. A bundle missing any expected cluster
flips to ``attempted_failed[ClusterCoverageError]`` instead of silently
passing as ``captured``.

Registered in :data:`DATA_TYPE_TO_CLUSTER_REGISTRY` under key
``"EVENT_CONTRACT"`` and in :data:`BUNDLED_DATA_TYPES`.
Populated by cme_polymarket_arb_2026_05_08 Phase 3.
"""
