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


_DATED_FUT_RE: Final[re.Pattern[str]] = re.compile(
    r"^([A-Z0-9]{1,4})([FGHJKMNQUVXZ])(\d{1,2})$"
)
"""Match a dated futures symbol (``ESM6``, ``NQU24``, ``CLZ5``)."""

_CME_MONTH_MAP: Final[dict[str, int]] = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
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


FUTURES_CHAIN_BUCKETS: Final[frozenset[str]] = frozenset(
    {"front", "back", "spread"}
)
"""Expected cluster set for ``futures_chain`` bundles.

Most roots emit at least a front + back contract on any given day;
spread-only days are rare and treated as honest absence
(``record_empty`` by the adapter, not a cluster failure).
"""


__all__ = [
    "BUNDLED_DATA_TYPES",
    "ES_OPTIONS_CLUSTERS",
    "ES_OPTIONS_DEFAULT_MIN_ROWS_PER_CLUSTER",
    "FUTURES_CHAIN_BUCKETS",
    "extract_es_options_cluster",
    "futures_expiry_bucket",
    "get_active_es_options_clusters_for_date",
    "parse_futures_expiry",
]
