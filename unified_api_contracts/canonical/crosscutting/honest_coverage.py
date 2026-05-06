"""Honest-coverage cluster registries for bundled-shard validation.

SSOT for the per-bundled-data_type cluster taxonomy referenced by the
writegate-honest-coverage end-to-end plan. Consumed by
``unified_trading_library.manifest_writer.ManifestWriter.record_captured``
when ``data_type ∈ BUNDLED_DATA_TYPES`` — cluster validation MANDATORY.

Two SSOTs live here today:

* :data:`BUNDLED_DATA_TYPES` — the closed set of data_types whose
  parquet shards bundle multiple cluster identities into a single
  per-day file. The writer guard at ``record_captured`` requires
  ``expected_root_clusters`` + ``cluster_extractor`` kwargs whenever
  the data_type is in this set; missing kwargs raise
  ``MissingClusterValidationError``.

* :func:`futures_expiry_bucket` — derives a coarse expiry bucket
  (``front`` / ``back`` / ``spread`` / ``unknown``) from a futures
  symbol shape. Used as the ``cluster_extractor`` for ``futures_chain``
  shards where the cluster identity is the expiry window, not the
  underlying root (rows already partition by underlying).

ES.OPT options-chain cluster taxonomy is **NOT** redefined here — its
SSOT is :data:`unified_api_contracts.registry.ES_OPTIONS_CLUSTERS` with
the per-symbol extractor :func:`unified_api_contracts.registry.extract_es_options_cluster`
and the per-day calendar fallback
:func:`unified_api_contracts.registry.get_active_es_options_clusters_for_date`.
This module re-exports those names from the registry for callers who
prefer the ``honest_coverage`` import surface.

This module is the [UAC] half of the layer split per
``shard_granularity_ssot_propagation_2026_05_06.HANDOVER.md``:

* [UAC] — what the clusters ARE (this module + registry).
* [UTL] — runtime guard (``MissingClusterValidationError``) and writer
  enforcement at ``record_captured``.
* [per-service] — adapters pass ``cluster_extractor`` recipes that map
  rows to cluster names.
"""

from __future__ import annotations

import datetime as _dt
import re
from typing import Final

from unified_api_contracts.registry import (
    ES_OPTIONS_CLUSTERS,
    ES_OPTIONS_DEFAULT_MIN_ROWS_PER_CLUSTER,
    extract_es_options_cluster,
    get_active_es_options_clusters_for_date,
)

# ---------------------------------------------------------------------------
# Bundled data_types — referenced by the ManifestWriter cluster-validation guard.
# ---------------------------------------------------------------------------


BUNDLED_DATA_TYPES: Final[frozenset[str]] = frozenset(
    {
        "options_chain",
        "futures_chain",
        "prediction_canonical_question_group",
        "sports_fixture_bundle",
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
# Futures expiry-bucket derivation.
#
# The ``futures_chain`` bundle row schema doesn't natively carry an
# expiry-bucket column — we derive it from the raw symbol so the
# cluster gate can fire meaningfully. Front/back is the analogue of
# ES.OPT's per-root cluster split for the futures bundle.
# ---------------------------------------------------------------------------


_DATED_FUT_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Z0-9]{1,4})([FGHJKMNQUVXZ])(\d{1,2})$")
"""Match a dated futures symbol (``ESM6``, ``NQU24``, ``CLZ5``)."""

_CME_MONTH_MAP: Final[dict[str, int]] = {
    "F": 1,
    "G": 2,
    "H": 3,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "U": 9,
    "V": 10,
    "X": 11,
    "Z": 12,
}


def _expand_two_digit_year(year_token: str) -> int:
    if len(year_token) == 1:
        return 2020 + int(year_token)
    return 2000 + int(year_token)


def parse_futures_expiry(symbol: str) -> _dt.date | None:
    """Parse the expiry date out of a dated futures symbol.

    Returns ``None`` for shapes the parser doesn't handle (combos,
    continuous codes, options, equities) — caller should fall through
    to other parsers (OSI option, ICE, etc.).

    Uses the third Friday of the contract month as the canonical listed
    expiry (CME convention). Callers needing FX-future-grade precision
    must use ``DatabentoClassification.expiry_date`` instead — this
    helper is for cluster bucketing, not order-routing.

    Args:
        symbol: Raw symbol string (e.g. ``"ESM6"``, ``"NQU24"``).

    Returns:
        Expiry ``date`` or ``None`` if unparseable.
    """
    match = _DATED_FUT_RE.match(symbol.strip().upper())
    if match is None:
        return None
    month = _CME_MONTH_MAP[match.group(2)]
    year = _expand_two_digit_year(match.group(3))
    first = _dt.date(year, month, 1)
    first_friday_day = 1 + (4 - first.weekday()) % 7
    return _dt.date(year, month, first_friday_day + 14)


def futures_expiry_bucket(
    symbol: str,
    as_of: _dt.date,
    *,
    front_window_days: int = 60,
) -> str:
    """Bucket a futures symbol's expiry into ``front`` / ``back`` / ``spread`` / ``unknown``.

    Used as the ``cluster_extractor`` for ``futures_chain`` bundle
    validation. Bucket semantics:

    * ``"front"`` — expiry within ``front_window_days`` of ``as_of``
      (default 60d). Most-active contract.
    * ``"back"`` — dated future beyond the front window.
    * ``"spread"`` — calendar spread / combo (symbol contains ``-``).
    * ``"unknown"`` — symbol doesn't parse as a dated future and isn't
      a recognised spread shape (continuous codes, equities, options).

    Args:
        symbol: Raw symbol string.
        as_of: Reference date for the front-vs-back classification
            (typically the partition date).
        front_window_days: Threshold in days for the front bucket.

    Returns:
        Bucket name as a string (one of :data:`FUTURES_CHAIN_BUCKETS`
        plus ``"unknown"``).
    """
    if not symbol:
        return "unknown"
    cleaned = symbol.strip().upper()
    if "-" in cleaned:
        return "spread"
    expiry = parse_futures_expiry(cleaned)
    if expiry is None:
        return "unknown"
    days_to_expiry = (expiry - as_of).days
    if 0 <= days_to_expiry <= front_window_days:
        return "front"
    return "back"


FUTURES_CHAIN_BUCKETS: Final[frozenset[str]] = frozenset({"front", "back", "spread"})
"""Expected cluster set for ``futures_chain`` bundles.

Most roots emit at least a front + back contract on any given day;
spread-only days are rare and treated as honest absence
(``record_empty`` by the adapter, not a cluster failure).
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
    "BTC_UP_DOWN_HOURLY": {"_per_market_min_rows": 100},
    "BTC_UP_DOWN_DAILY": {"_per_market_min_rows": 1000},
    "ETH_UP_DOWN_HOURLY": {"_per_market_min_rows": 100},
    "ETH_UP_DOWN_DAILY": {"_per_market_min_rows": 1000},
    "SPX_UP_DOWN_DAILY": {"_per_market_min_rows": 1000},
    "FED_RATE_DECISION_PER_FOMC": {"_per_market_min_rows": 100},
    "CPI_PRINT_PER_MONTH": {"_per_market_min_rows": 100},
    "ELECTION_PRESIDENT_2028": {"_per_market_min_rows": 100},
    "OSCARS_BEST_PICTURE": {"_per_market_min_rows": 50},
    # OTHER intentionally absent — markets that classify into OTHER
    # bypass the cluster gate (no expected market_id set), but the
    # manifest still records the capture for audit purposes.
}
"""Per-canonical_question_group expected market_id sets.

Keyed by canonical_question_group name (string form of
:class:`unified_api_contracts.canonical.domain.predictions.canonical_groups.CanonicalQuestionGroup`).
Each group's inner dict carries a ``_per_market_min_rows`` floor — the
cluster gate at ``ManifestWriter.record_captured`` derives the per-day
expected market_id set from the lifecycle table at runtime and applies
this min-rows floor per market_id.

Populated by predictions plan
``predictions_canonical_question_group_polymarket_migration_2026_05_06.plan.md``
Phase 1A.
"""


__all__ = [
    "BUNDLED_DATA_TYPES",
    "DATA_TYPE_TO_CLUSTER_REGISTRY",
    "ES_OPTIONS_CLUSTERS",
    "ES_OPTIONS_DEFAULT_MIN_ROWS_PER_CLUSTER",
    "FUTURES_CHAIN_BUCKETS",
    "PREDICTION_GROUPS",
    "SPORTS_FIXTURE_CLUSTERS",
    "extract_es_options_cluster",
    "futures_expiry_bucket",
    "get_active_es_options_clusters_for_date",
    "parse_futures_expiry",
]
