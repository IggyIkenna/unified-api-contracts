"""Canonical taxonomy SSOT — grep-discoverable term definitions.

Workspace CLAUDE.md already enforces ``asset_group`` as the venue axis with two
intentional exceptions (lowercase dict keys, ``category=`` GCS path segments).
This module makes that contract programmatically importable so consumers can
reference one ``MarketAssetGroup`` instead of restating the literal set.

Per audit follow-up P4.9 (workspace audit 2026-05-01): formalise the term
glossary so future agents stop drifting between ``asset_group`` / ``domain`` /
``category`` / ``pipeline_category`` for the same axis.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class MarketAssetGroup(StrEnum):
    """The five asset groups. Canonical venue axis."""

    CEFI = "CEFI"
    DEFI = "DEFI"
    TRADFI = "TRADFI"
    SPORTS = "SPORTS"
    PREDICTION = "PREDICTION"


class InstrumentTypeFamily(StrEnum):
    """Instrument-type families spanning all asset groups.

    Per-asset-group instrument-type lists live in
    :mod:`unified_api_contracts.registry.archetype_capability_matrix`.
    """

    SPOT = "spot"
    PERP = "perp"
    FUTURE = "future"
    OPTION = "option"
    LENDING_POSITION = "lending_position"
    BORROW_POSITION = "borrow_position"
    LP_POSITION = "lp_position"
    STAKED_POSITION = "staked_position"
    SPORTS_MARKET = "sports_market"
    PREDICTION_MARKET = "prediction_market"


class PipelineCategory(StrEnum):
    """Reconciliation pipeline grouping (used by batch-live-reconciliation-service).

    Distinct from ``MarketAssetGroup`` — pipelines are about WHAT we reconcile
    (data / ML / strategy / execution / pnl), not WHO the venue is.
    """

    DATA_PIPELINE = "data_pipeline"
    ML = "ml"
    STRATEGY = "strategy"
    EXECUTION = "execution"
    PNL = "pnl"
    AGENT_ANALYSIS = "agent_analysis"


# Lowercase form of MarketAssetGroup — the SSOT for dict keys and GCS path
# segments per workspace CLAUDE.md "Two intentional exceptions" rule.
ASSET_GROUP_KEY_LOWERCASE: Final[dict[MarketAssetGroup, str]] = {
    MarketAssetGroup.CEFI: "cefi",
    MarketAssetGroup.DEFI: "defi",
    MarketAssetGroup.TRADFI: "tradfi",
    MarketAssetGroup.SPORTS: "sports",
    MarketAssetGroup.PREDICTION: "prediction",
}


def asset_group_key(asset_group: MarketAssetGroup) -> str:
    """Lowercase dict-key / GCS-path-segment form of an asset group.

    Example: ``asset_group_key(MarketAssetGroup.DEFI) == "defi"``.
    """
    return ASSET_GROUP_KEY_LOWERCASE[asset_group]


# Banned synonyms — older codebases used these for the asset_group axis.
# Tooling can grep for these to flag drift back to non-canonical terms.
BANNED_ASSET_GROUP_SYNONYMS: Final[frozenset[str]] = frozenset(
    {
        "category",  # historical name; still allowed in GCS path segment ONLY
        "domain",
        "market_category",
        "venue_class",
    }
)
