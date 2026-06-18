"""Total-reasonable-universe SSOT — the could-exist universe, distinct from MVP.

This module is the UAC SSOT for the **two distinct expected-universe concepts**
the data pipeline reasons about (operator follow-up 2026-06-18,
``instruments_mtds_subset_consistency_remediation_2026_06_17`` § B2). They are
NOT the same thing and were previously only one of them was codified:

Hierarchy (largest → smallest)::

    ALL instrument types  ⊇  TOTAL-REASONABLE universe (could-exist)  ⊇  MVP scope

* **TOTAL-REASONABLE universe** (this module) — the full *could-exist* set: every
  instrument that could reasonably have data on a given date, i.e. every
  catalogue-listed instrument x in-coverage date x expected data_type, gated by
  genesis / venue-launch dates. This is the denominator the data-status "100%"
  metric and ``enumerate_expected_universe.py`` (the v2 ``expected_unattempted``
  seeding) reason against. It was *implicit* (= the full lifecycle catalogue
  roll-up) but never NAMED or given an explicit axis taxonomy until now.
* **MVP scope** — a strict, rules-derived SUBSET of the total universe (the cells
  the May-23 archetypes actually need). Codified separately in
  :mod:`unified_api_contracts.canonical.crosscutting.mvp_scope`
  (:func:`~unified_api_contracts.is_mvp`). MVP ⊆ TOTAL by construction.

Why two concepts, not one:
    The backfill config + the data-status denominator must distinguish "what we
    SHOULD eventually have" (TOTAL — drives could-exist + backfill sizing) from
    "what the MVP archetypes need NOW" (MVP — drives the May-23 readiness gate).
    Conflating them either over-counts MVP readiness (using the TOTAL
    denominator) or under-sizes the backfill (using the MVP denominator).

Selection axes (the dimensions that define total-universe membership)
---------------------------------------------------------------------
The total-reasonable universe is selected along these axes (operator 2026-06-18):

* ``base_currency``  — CeFi spot/perp base assets (the 44-base
  ``CEFI_BASE_ASSET_UNIVERSE`` is the *MVP* subset; TOTAL = every base the venue
  lists).
* ``venue``          — every venue in ``VENUES_BY_ASSET_GROUP[ag]``.
* ``data_type``      — every data_type in ``DATA_TYPES_BY_ASSET_GROUP[ag]``.
* ``defi_pool_volume`` — DeFi pools above a liquidity/volume threshold (a pool
  with negligible volume is not "reasonable" to expect data for).
* ``fixtures``       — sports fixtures per canonical league x season (the sports
  could-exist atom).
* ``combinations``   — the cross-product of the above per asset_group (e.g.
  venue x instrument_type x data_type x date).

Membership provenance (HARDCODED-GENESIS vs DOWNLOAD-DERIVED)
------------------------------------------------------------
Each axis bound is sourced one of two ways — codified here as the
:class:`UniverseProvenance` taxonomy (operator 2026-06-18):

* :attr:`UniverseProvenance.HARDCODED_GENESIS` — a static, hand-maintained bound
  that does NOT come from a download: chain genesis dates
  (``CHAIN_GENESIS_DATES``), venue launch dates (``CEFI_VENUE_LAUNCH_DATES`` /
  ``PREDICTION_VENUE_LAUNCH_DATES`` / ``DEFI_VENUE_LAUNCH_DATES``), the CBOE VIX
  static index, and the curated seed lists
  (``cefi_instrument_universe`` / ``tradfi_instrument_universe`` /
  ``defi_prediction_instrument_seeds``). These are the LOWER bound — they say
  "data could not possibly exist before this date / outside this seed set".
* :attr:`UniverseProvenance.DOWNLOAD_DERIVED` — a bound discovered by actually
  fetching reference data: the lifecycle catalogue
  (``build_instrument_catalogue.py`` roll-up of the daily
  ``instrument_availability/by_date`` snapshots →
  ``available_from`` / ``available_to`` per instrument). This is the AUTHORITATIVE
  per-instrument lifecycle window — but it is only as complete as the fetch config
  that produced it (a venue/date never fetched is absent from the catalogue, so a
  download-derived universe is only TRUE-total once the backfill has run for the
  full could-exist set; that is the gating relationship B0 → B1 → B2).

The two compose: an instrument is in the total-reasonable universe on date ``d``
iff it is in the DOWNLOAD_DERIVED catalogue (``available_from ≤ d ≤ available_to``)
AND ``d`` is on/after every applicable HARDCODED_GENESIS bound (chain genesis +
venue launch). The catalogue is the SSOT for *which* instruments; the genesis /
launch registries are the SSOT for the *earliest reasonable date*.

Grain (everything-or-nothing per axis tuple, mirrors MVP)::

    (asset_group, venue, instrument_type, data_type[, base_ccy])
    sports:      + league
    prediction:  + market_group

No manifest column is written — membership is evaluated on-the-fly by consumers
(``enumerate_expected_universe.py``, the deployment-api data-status denominator)
via :func:`is_total_universe` and :func:`universe_membership`, exactly like
:func:`~unified_api_contracts.is_mvp`.

SSOT: ``plans/active/instruments_mtds_subset_consistency_remediation_2026_06_17.md`` § B2
(+ ``path_to_100pct_backfill_mtds_is_2026_06_17.md`` for the backfill that fills it).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from unified_api_contracts.canonical.crosscutting.config_versioning import (
    ConfigDescriptor,
    compute_config_content_hash,
)
from unified_api_contracts.canonical.crosscutting.mvp_scope import is_mvp

# ---------------------------------------------------------------------------
# Provenance taxonomy — how a universe bound is sourced (operator 2026-06-18).
# ---------------------------------------------------------------------------


class UniverseProvenance(StrEnum):
    """How a total-universe selection bound is sourced.

    HARDCODED_GENESIS bounds are static, hand-maintained, and a LOWER bound
    ("no data possible before this"). DOWNLOAD_DERIVED bounds come from actually
    fetching reference data (the lifecycle catalogue) and are the authoritative
    per-instrument lifecycle window — but only as complete as the fetch config
    that produced them.
    """

    HARDCODED_GENESIS = "hardcoded_genesis"
    DOWNLOAD_DERIVED = "download_derived"


class UniverseTier(StrEnum):
    """Where a catalogue cell sits in the universe hierarchy.

    NOT_IN_UNIVERSE  — outside the total-reasonable universe (e.g. a venue not in
        ``VENUES_BY_ASSET_GROUP`` or a date before the genesis/launch bound).
    TOTAL_ONLY       — in the total-reasonable could-exist universe but NOT in the
        MVP subset (backfill it for completeness, not for the May-23 gate).
    MVP              — in the MVP subset (and therefore in TOTAL too).
    """

    NOT_IN_UNIVERSE = "not_in_universe"
    TOTAL_ONLY = "total_only"
    MVP = "mvp"


# ---------------------------------------------------------------------------
# Selection-axis descriptors — the codified taxonomy of the axes that define
# total-universe membership, with each axis's SSOT pointer + provenance.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UniverseAxis:
    """One selection axis of the total-reasonable universe.

    Attributes:
        name: Axis identifier (``base_currency`` / ``venue`` / ``data_type`` /
            ``defi_pool_volume`` / ``fixtures`` / ``combinations``).
        provenance: How this axis's bound is sourced
            (:class:`UniverseProvenance`).
        ssot_ref: Dotted reference to the registry/module that is the SSOT for
            this axis's membership (for audit + cross-checking; NOT imported here
            to keep the predicate import-light).
        description: One-line human description.
    """

    name: str
    provenance: UniverseProvenance
    ssot_ref: str
    description: str


#: The codified selection-axis taxonomy. Per-asset_group axis lists describe
#: WHICH axes bound the could-exist universe for that AG and WHERE each axis's
#: membership SSOT lives. Consumers that build the could-exist denominator
#: (``enumerate_expected_universe.py``) cross-join exactly these axes.
TOTAL_UNIVERSE_AXES: Final[dict[str, tuple[UniverseAxis, ...]]] = {
    "cefi": (
        UniverseAxis(
            "base_currency",
            UniverseProvenance.DOWNLOAD_DERIVED,
            "instruments-service catalogue (build_instrument_catalogue) base_asset column",
            "Every base asset the venue lists (MVP subset = CEFI_BASE_ASSET_UNIVERSE).",
        ),
        UniverseAxis(
            "venue",
            UniverseProvenance.HARDCODED_GENESIS,
            "unified_api_contracts.registry.market_data_categories.VENUES_BY_ASSET_GROUP['cefi']",
            "Every CeFi venue; earliest date bounded by CEFI_VENUE_LAUNCH_DATES.",
        ),
        UniverseAxis(
            "data_type",
            UniverseProvenance.HARDCODED_GENESIS,
            "DATA_TYPES_BY_ASSET_GROUP['cefi']",
            "Every expected CeFi data_type (trades/book_snapshot_5/derivative_ticker/…).",
        ),
        UniverseAxis(
            "combinations",
            UniverseProvenance.DOWNLOAD_DERIVED,
            "catalogue x date x data_type cross-join (enumerate_v2)",
            "venue x instrument_type x base x data_type x in-coverage date.",
        ),
    ),
    "defi": (
        UniverseAxis(
            "venue",
            UniverseProvenance.HARDCODED_GENESIS,
            "VENUES_BY_ASSET_GROUP['defi'] + DEFI_VENUE_LAUNCH_DATES + CHAIN_GENESIS_DATES",
            "Every PROTOCOL-CHAIN venue; bounded by chain genesis AND protocol launch.",
        ),
        UniverseAxis(
            "defi_pool_volume",
            UniverseProvenance.DOWNLOAD_DERIVED,
            "instruments-service defi catalogue (pool liquidity/volume threshold)",
            "DEX pools above the liquidity/volume threshold (negligible pools excluded).",
        ),
        UniverseAxis(
            "data_type",
            UniverseProvenance.HARDCODED_GENESIS,
            "DATA_TYPES_BY_ASSET_GROUP['defi']",
            "dex_pool_state/dex_pool_swaps/lst_rates/lending_indices/perp_funding/oracle_prices.",
        ),
        UniverseAxis(
            "combinations",
            UniverseProvenance.DOWNLOAD_DERIVED,
            "catalogue x date x data_type cross-join (enumerate_v2)",
            "protocol-chain x instrument_type x data_type x post-launch date.",
        ),
    ),
    "tradfi": (
        UniverseAxis(
            "venue",
            UniverseProvenance.HARDCODED_GENESIS,
            "VENUES_BY_ASSET_GROUP['tradfi']",
            "CME/NASDAQ/NYSE/CBOE/ICE/FX.",
        ),
        UniverseAxis(
            "data_type",
            UniverseProvenance.HARDCODED_GENESIS,
            "DATA_TYPES_BY_ASSET_GROUP['tradfi']",
            "trades/ohlcv/options_chain/tbbo; CBOE VIX index is the static-genesis exception.",
        ),
        UniverseAxis(
            "combinations",
            UniverseProvenance.DOWNLOAD_DERIVED,
            "catalogue x date x data_type cross-join (Databento/Massive-listed instruments)",
            "venue x instrument_type x underlier x data_type x trading-day.",
        ),
    ),
    "sports": (
        UniverseAxis(
            "fixtures",
            UniverseProvenance.DOWNLOAD_DERIVED,
            "instruments-service sports catalogue (per-league fixture roll-up)",
            "Every fixture per canonical league x season in source coverage.",
        ),
        UniverseAxis(
            "data_type",
            UniverseProvenance.HARDCODED_GENESIS,
            "SPORTS_DATA_TYPE_TO_SOURCE",
            "Per-provider sports data_types (odds/fixtures/stats/…).",
        ),
    ),
    "prediction": (
        UniverseAxis(
            "venue",
            UniverseProvenance.HARDCODED_GENESIS,
            "VENUES_BY_ASSET_GROUP['prediction'] + PREDICTION_VENUE_LAUNCH_DATES",
            "POLYMARKET/KALSHI; bounded by venue launch.",
        ),
        UniverseAxis(
            "combinations",
            UniverseProvenance.DOWNLOAD_DERIVED,
            "prediction catalogue (per-market / per-cqg roll-up)",
            "Every canonical market/question-group x post-launch date.",
        ),
    ),
}
"""Per-asset_group total-universe selection-axis taxonomy.

The SSOT for WHICH axes bound the could-exist universe per AG + WHERE each axis's
membership lives + how it is sourced (HARDCODED_GENESIS vs DOWNLOAD_DERIVED).
``enumerate_expected_universe.py`` builds its could-exist denominator from
exactly these axes (the catalogue carries the DOWNLOAD_DERIVED axes; the genesis/
launch registries carry the HARDCODED_GENESIS lower bounds).
"""


# ---------------------------------------------------------------------------
# Config versioning — mirror mvp_scope (so a coverage delta attributes to a
# universe-DEFINITION change vs a DATA change).
# ---------------------------------------------------------------------------

TOTAL_UNIVERSE_CONFIG_VERSION: Final[int] = 1
"""Monotonic version of the total-universe axis taxonomy. Bump on any content change.

v1 (2026-06-18): initial codification — names the total-reasonable-universe
concept distinct from MVP, the selection-axis taxonomy (TOTAL_UNIVERSE_AXES), and
the HARDCODED_GENESIS vs DOWNLOAD_DERIVED provenance taxonomy. SSOT for
instruments_mtds_subset_consistency_remediation § B2.
"""


def _compute_total_universe_content_hash() -> str:
    """SHA-256 (16-hex prefix) of the canonical axis taxonomy + version."""
    serialisable = [
        (
            ag,
            tuple((a.name, str(a.provenance), a.ssot_ref, a.description) for a in axes),
        )
        for ag, axes in sorted(TOTAL_UNIVERSE_AXES.items())
    ]
    return compute_config_content_hash(TOTAL_UNIVERSE_CONFIG_VERSION, serialisable)


TOTAL_UNIVERSE_CONFIG_HASH: Final[str] = _compute_total_universe_content_hash()
"""Content hash of the axis taxonomy — flips IFF the taxonomy content changes."""


def total_universe_config_descriptor() -> ConfigDescriptor:
    """Return the total-universe ``(version, content-hash)`` descriptor."""
    return ConfigDescriptor(TOTAL_UNIVERSE_CONFIG_VERSION, TOTAL_UNIVERSE_CONFIG_HASH)


# ---------------------------------------------------------------------------
# Public predicates
# ---------------------------------------------------------------------------


def is_total_universe(asset_group: str, venue: str, instrument_type: str) -> bool:
    """Return ``True`` iff ``(asset_group, venue, instrument_type)`` is a member of
    the total-reasonable (could-exist) universe BY STRUCTURE.

    This is the *structural* membership check — "is this AG a real asset_group
    with a declared axis taxonomy". The *temporal + per-instrument* could-exist
    decision (is THIS instrument alive on THIS date) is the catalogue's
    ``available_from``/``available_to`` window ANDed with the genesis/launch
    lower bound — that lives in ``enumerate_expected_universe.py`` (which reads
    the catalogue), NOT here, because UAC must not depend on a service's runtime
    catalogue read.

    A catalogue cell that reaches a consumer (it came from the lifecycle
    catalogue, gated by genesis/launch in the enumerator) IS in the total
    universe by definition — so for the AGs that declare an axis taxonomy this
    returns ``True``. The predicate exists so consumers can (a) assert the AG is
    universe-bearing and (b) compose ``universe_membership`` cleanly.

    Args:
        asset_group: Lowercase asset-group key.
        venue: Canonical venue identifier (unused in the structural check today;
            accepted so the signature mirrors ``is_mvp`` for call-site symmetry
            and so a future per-venue exclusion list can slot in here).
        instrument_type: Canonical instrument type string (same — reserved for a
            future structural exclusion).

    Returns:
        ``True`` for any of the five declared asset_groups; ``False`` otherwise.
    """
    return asset_group in TOTAL_UNIVERSE_AXES


def universe_membership(
    asset_group: str,
    venue: str,
    instrument_type: str,
    data_type: str | None = None,
    *,
    base_ccy: str | None = None,
    league: str | None = None,
    market_group: str | None = None,
    source: str | None = None,
) -> UniverseTier:
    """Classify a catalogue cell into the universe hierarchy.

    Returns the most specific tier the cell belongs to:

    * :attr:`UniverseTier.MVP` — the cell is in the MVP subset
      (:func:`~unified_api_contracts.is_mvp` returns ``True``). MVP ⊆ TOTAL, so
      this is also in the total universe.
    * :attr:`UniverseTier.TOTAL_ONLY` — in the total-reasonable universe but NOT
      MVP (backfill for completeness, not for the May-23 gate).
    * :attr:`UniverseTier.NOT_IN_UNIVERSE` — outside the total universe (unknown
      asset_group).

    The MVP check forwards every axis to :func:`is_mvp` (the MVP SSOT owns the
    fine-grained per-axis rule); TOTAL membership is the structural check. This
    is the single call-site for "which tier is this cell" so the data-status
    denominator + the backfill config agree on the hierarchy.
    """
    if is_mvp(
        asset_group,
        venue,
        instrument_type,
        data_type,
        base_ccy=base_ccy,
        league=league,
        market_group=market_group,
        source=source,
    ):
        return UniverseTier.MVP
    if is_total_universe(asset_group, venue, instrument_type):
        return UniverseTier.TOTAL_ONLY
    return UniverseTier.NOT_IN_UNIVERSE
