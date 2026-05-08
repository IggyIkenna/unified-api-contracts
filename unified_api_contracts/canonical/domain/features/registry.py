"""SSOT for ``EXPECTED_FEATURE_GROUPS_BY_SERVICE`` and ``FEATURE_COVERAGE_START``.

These two registries are the **honest-coverage denominator** for the features
manifest. ``writegate_honest_coverage_endtoend_2026_05_06`` covers raw-data
shards (instruments / MTDS / MDPS); the features manifest needs its own
denominator because deployment-api ``data_status`` today infers what's
"expected" from what's been written — that infers a manifest from itself
and silently masks coverage holes.

Mirrors the SSOT pattern of ``unified_api_contracts.sports.SOURCE_COVERAGE_START``
+ ``DATA_TYPE_COVERAGE_START``: a lookup keyed by domain primitives that data-
status uses to clip the expected-dates window before counting captured / empty /
missing.

References:
- ``feature_dag_uac_ssot_and_features_coverage_2026_05_06.plan.md`` Phase 1A —
  ``EXPECTED_FEATURE_GROUPS_BY_SERVICE`` + ``FEATURE_COVERAGE_START``.
- ``features_repo_consolidation_2026_05_08.plan.md`` Phase 1A — the
  ``FeatureFamily`` enum + ``FEATURE_GROUP_TO_FAMILY`` registry below.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Final

# ---------------------------------------------------------------------------
# EXPECTED_FEATURE_GROUPS_BY_SERVICE — service -> [feature_group, ...]
# ---------------------------------------------------------------------------
#
# Source-of-truth for "service S is expected to produce these feature_groups".
# Sourced from each service's ``app/calculators/`` / ``calculators/`` directory
# listing as of 2026-05-07. data-status uses this as the denominator: every
# feature_group listed here is expected to have manifest rows; absence is
# coverage hole, not "not declared."
#
# Feature groups are listed in the same string form they appear as in the
# service's ``feature_builder_registry.py`` ``BuilderEntry.group_name`` —
# this is the same string the manifest writer uses for the ``feature_group``
# column. Drift here = data-status double-counts or under-counts.

EXPECTED_FEATURE_GROUPS_BY_SERVICE: Final[dict[str, list[str]]] = {
    "features-onchain-service": [
        # Phase 0 — base calculators (no inter-calculator deps)
        "aave_lending_rates",
        "aave_utilization",
        "aave_risk_params",
        "defillama_tvl",
        "fear_greed",
        "lst_staking_yields",
        "macro_sentiment",
        "eigen_rewards",
        "protocol_rewards",
        "flash_loan_availability",
        # Phase 1 — depends on base
        "aave_rate_impact",
        # Phase 2 — regime aggregator
        "onchain_regime",
    ],
    "features-delta-one-service": [
        # Phase 0 — Price-based (no inter-calculator deps)
        "technical_indicators",
        "moving_averages",
        "oscillators",
        "volatility_realized",
        "momentum",
        "volume_analysis",
        "vwap",
        "candlestick_patterns",
        "market_structure",
        "returns",
        "round_numbers",
        "streaks",
        "targets",
        "swing_outcome_targets",
        # Data-specific (no inter-calculator deps)
        "microstructure",
        "funding_oi",
        "liquidations",
        "futures_basis",
        "volume_flow",
        # Time-based (no deps)
        "temporal",
        "economic_events",
        # S/R level system (no deps)
        "supply_demand_zones",
        "fibonacci",
        "level_confluence",
        "market_structure_sequence",
        "sr_memory",
        # Enrichment (no deps on base calculators at registry level)
        "signal_confirmation",
        "statistical_anomaly",
        "order_flow_inference",
        "return_kurtosis",
        "polynomial_trendlines",
        # Phase 1 — ML enhancement (depends on base calculators)
        "risk_reward",
        "wedge_quality",
        # Phase 1 — Cross-calculator confluence
        "confluence",
    ],
    "features-sports-service": [
        # Sports calculators directory listing 2026-05-07. The
        # ``features-sports-service`` BuilderEntry vocabulary uses
        # ``required_inputs: list[str]`` of reference-entity names rather
        # than ``(source, data_type)`` pairs — full lift into
        # ``FEATURE_REQUIRED_INPUTS`` blocked behind a follow-up plan
        # (sports vocabulary alignment). For now this list is used by
        # ``data_status`` as the coverage denominator only.
        "advanced_stats",
        "bench_sub",
        "bucketed_features",
        "elo",
        "european_fatigue",
        "footystats_predictions",
        "formation",
        "goal_timing",
        "h2h",
        "halftime",
        "ht_features",
        "injury_impact",
        "league",
        "manager",
        "meta_features",
        "ml_predictions",
        "multisource_xg",
        "odds",
        "player_lineup",
        "poisson_xg",
        "promoted_team",
        "referee_features",
        "relative_context",
        "replacement_model",
        "season_context",
        "sfi_progressive",
        "squad_value",
        "steam_detector",
        "team_derived",
        "team_form",
        "team_goals",
        "team_xg",
        "transfer_window",
        "travel",
        "venue_context",
        "weather",
        "xg_decomposition",
    ],
    "features-volatility-service": [
        # Stub today; populate as volatility calculators land. Volatility
        # service produces IV-surface + realised-vol features for options
        # / perp basis trades — the ``features-volatility-service``
        # ``BuilderRegistry`` is currently a placeholder per audit
        # 2026-05-07.
    ],
    "features-cross-instrument-service": [
        # Cross-instrument feature service ships paired_price_dispersion
        # + cross-asset / index-vs-constituent features. The 20+
        # calculators in the dir today don't yet use a BuilderRegistry —
        # populate this list as they're rationalised under the same
        # vocabulary as features-delta-one.
    ],
}
"""service -> ordered list of feature_groups the service is expected to produce.

Used by:

* deployment-api ``_build_feature_group_breakdown`` (data-status) — denominator
  = ``len(EXPECTED_FEATURE_GROUPS_BY_SERVICE[service]) * dates_in_window``,
  ``found = captured + empty_confirmed``, ``missing = attempted_failed``.
* features-* phantom audit — probes every (service, feature_group) pair.

When adding a new feature_group to a service, register it here in the same
PR so data-status accounting stays honest.
"""


# ---------------------------------------------------------------------------
# FEATURE_COVERAGE_START — (service, feature_group) -> first-expected date
# ---------------------------------------------------------------------------
#
# Mirrors the ``SOURCE_COVERAGE_START`` shape in ``unified_api_contracts.sports``:
# the date BEFORE which a feature_group has no expected coverage. data-status
# uses ``_clip_dates_to_feature_coverage`` to drop pre-coverage dates from the
# denominator, so they don't render as "missing" coverage holes.
#
# Default for unregistered (service, feature_group) pairs: epoch (no clip).
# Register an entry here when the feature_group has a known later start date —
# typically because its upstream data source has a later
# ``SOURCE_COVERAGE_START``, or the calculator itself was added later than the
# upstream window.

FEATURE_COVERAGE_START: Final[dict[tuple[str, str], date]] = {
    # Onchain — bound by upstream data source coverage windows. These dates
    # mirror the underlying protocol-launch / source-launch dates already
    # encoded in ``CHAIN_GENESIS_DATES`` and ``PROTOCOL_LAUNCH_DATES``
    # (UAC) — register explicit floors here so the features manifest
    # denominator clips correctly without round-tripping through the raw
    # data registries.
    #
    # Aave V3 mainnet launch (March 2022). All Aave-derived feature
    # groups can't have data before this.
    ("features-onchain-service", "aave_lending_rates"): date(2022, 3, 16),
    ("features-onchain-service", "aave_utilization"): date(2022, 3, 16),
    ("features-onchain-service", "aave_risk_params"): date(2022, 3, 16),
    ("features-onchain-service", "aave_rate_impact"): date(2022, 3, 16),
    # Lido stETH launched Dec 2020; Etherfi mid-2023. The MIN of upstream
    # source starts wins for the multi-source aggregate.
    ("features-onchain-service", "lst_staking_yields"): date(2020, 12, 18),
    # EigenLayer mainnet launch (June 2023).
    ("features-onchain-service", "eigen_rewards"): date(2023, 6, 14),
    # Morpho v1 launch (June 2022).
    ("features-onchain-service", "flash_loan_availability"): date(2022, 6, 1),
    # Add deltas / sports / volatility entries as upstream coverage
    # windows are formalised — until then the default (epoch) means
    # data-status doesn't pre-clip, which renders genuine pre-coverage
    # dates as "missing" until populated. Tracked under the
    # data-status feature-coverage follow-up.
}
"""(service, feature_group) -> earliest date with expected coverage.

Default = epoch (no clip) for unregistered pairs. data-status's
``_clip_dates_to_feature_coverage(service, feature_group, start, end)``
intersects the requested window with this floor.
"""


def get_feature_coverage_start(service: str, feature_group: str) -> date | None:
    """Return the earliest expected-coverage date for ``(service, feature_group)``.

    Returns ``None`` when no explicit floor is registered, in which case
    callers should NOT clip (effectively epoch).
    """
    return FEATURE_COVERAGE_START.get((service, feature_group))


def is_known_feature_group(service: str, feature_group: str) -> bool:
    """True iff ``feature_group`` is declared for ``service`` in the registry."""
    return feature_group in EXPECTED_FEATURE_GROUPS_BY_SERVICE.get(service, [])


def list_services() -> list[str]:
    """Sorted list of services with feature-group declarations."""
    return sorted(EXPECTED_FEATURE_GROUPS_BY_SERVICE)


# ---------------------------------------------------------------------------
# FeatureFamily — closed-set enum of feature-service "families" (Phase 1A of
# ``features_repo_consolidation_2026_05_08``).
# ---------------------------------------------------------------------------
#
# The features-repo consolidation introduces ``feature_family`` as an additive
# sibling-or-prefix axis of ``feature_group`` in the v5 manifest schema. Every
# feature_group produced by a ``features-{family}-service`` calculator is
# tagged with its owning family at write time so the manifest can be sliced /
# rolled-up by family in deployment-UI without grepping the calculator name.
#
# This enum is the closed set — adding a new feature family is a deliberate
# UAC change, not a string-typo waiting to happen. The 8 values mirror the 8
# ``features-{family}-service`` repos enumerated in the consolidation plan.
#
# Plan: ``features_repo_consolidation_2026_05_08.plan.md`` Phase 1A.


class FeatureFamily(StrEnum):
    """Closed set of feature-service families.

    Each value corresponds to one ``features-{family}-service`` repo. The
    string value is the canonical lower_snake form used as the manifest
    column value and as the family key in ``FEATURE_GROUP_TO_FAMILY``.
    """

    CALENDAR = "calendar"
    COMMODITY = "commodity"
    CROSS_INSTRUMENT = "cross_instrument"
    DELTA_ONE = "delta_one"
    MULTI_TIMEFRAME = "multi_timeframe"
    ONCHAIN = "onchain"
    SPORTS = "sports"
    VOLATILITY = "volatility"


class FeatureGroupFamilyCollisionError(ValueError):
    """Raised when ``_build_feature_group_to_family`` finds the same
    ``feature_group`` declared by two services that map to different
    ``FeatureFamily`` values.

    This is a hard programming error — the plan's invariant is that every
    feature_group maps to exactly ONE feature_family. If a legitimate use
    case for cross-family feature_groups emerges, the plan + this enforcement
    must change deliberately, not by silently picking one side.
    """


# Service-name → FeatureFamily mapping. Mechanical: every
# ``features-{family}-service`` maps to the matching ``FeatureFamily`` value.
# Kept as a private constant — callers should reach for ``FEATURE_GROUP_TO_FAMILY``
# / ``get_feature_family`` instead of this dict directly.
_SERVICE_TO_FAMILY: Final[dict[str, FeatureFamily]] = {
    "features-calendar-service": FeatureFamily.CALENDAR,
    "features-commodity-service": FeatureFamily.COMMODITY,
    "features-cross-instrument-service": FeatureFamily.CROSS_INSTRUMENT,
    "features-delta-one-service": FeatureFamily.DELTA_ONE,
    "features-multi-timeframe-service": FeatureFamily.MULTI_TIMEFRAME,
    "features-onchain-service": FeatureFamily.ONCHAIN,
    "features-sports-service": FeatureFamily.SPORTS,
    "features-volatility-service": FeatureFamily.VOLATILITY,
}


def _build_feature_group_to_family() -> dict[str, FeatureFamily]:
    """Invert ``EXPECTED_FEATURE_GROUPS_BY_SERVICE`` into a
    ``feature_group -> FeatureFamily`` lookup at module-load time.

    Raises ``FeatureGroupFamilyCollisionError`` if the same feature_group is
    declared by two services that map to different families — a hard
    programming error.

    Services declared in ``EXPECTED_FEATURE_GROUPS_BY_SERVICE`` but absent
    in ``_SERVICE_TO_FAMILY`` raise ``KeyError`` loudly at module load time
    — that's the correct failure mode (a new service repo without a
    registered family would silently lose feature_family stamping).
    """
    result: dict[str, FeatureFamily] = {}
    for service, groups in EXPECTED_FEATURE_GROUPS_BY_SERVICE.items():
        family = _SERVICE_TO_FAMILY[service]
        for group in groups:
            existing = result.get(group)
            if existing is not None and existing != family:
                raise FeatureGroupFamilyCollisionError(
                    f"feature_group {group!r} is declared by two services "
                    f"that map to different feature_family values: "
                    f"{existing.value!r} vs {family.value!r}. The plan's "
                    "invariant is one-family-per-feature_group; resolve by "
                    "renaming the duplicate or revising _SERVICE_TO_FAMILY."
                )
            result[group] = family
    return result


FEATURE_GROUP_TO_FAMILY: Final[dict[str, FeatureFamily]] = _build_feature_group_to_family()
"""``feature_group -> FeatureFamily`` lookup.

Built once at module-load by inverting ``EXPECTED_FEATURE_GROUPS_BY_SERVICE``
through ``_SERVICE_TO_FAMILY``. ``ManifestWriter`` callers use
``get_feature_family(feature_group)`` to look up the family before stamping
the manifest column.

Plan: ``features_repo_consolidation_2026_05_08.plan.md`` Phase 1A.
"""


def get_feature_family(feature_group: str) -> FeatureFamily | None:
    """Return the ``FeatureFamily`` for ``feature_group``, or ``None`` if
    the feature_group is not registered in ``EXPECTED_FEATURE_GROUPS_BY_SERVICE``.

    Returning ``None`` (rather than raising) lets non-features writers
    (MTDS / MDPS) reach this helper without forcing a try/except — they
    simply don't stamp ``feature_family`` on their rows. Features-CLI
    writers should treat ``None`` as a contract violation and fail loudly.
    """
    return FEATURE_GROUP_TO_FAMILY.get(feature_group)


def is_known_feature_family(family: str) -> bool:
    """True iff ``family`` matches a member of :class:`FeatureFamily`.

    Useful for validating manifest-row values read back from disk before
    they're returned through the deployment-api ``feature_family=`` filter.
    """
    return family in {member.value for member in FeatureFamily}


__all__ = [
    "EXPECTED_FEATURE_GROUPS_BY_SERVICE",
    "FEATURE_COVERAGE_START",
    "FEATURE_GROUP_TO_FAMILY",
    "FeatureFamily",
    "FeatureGroupFamilyCollisionError",
    "get_feature_coverage_start",
    "get_feature_family",
    "is_known_feature_family",
    "is_known_feature_group",
    "list_services",
]
