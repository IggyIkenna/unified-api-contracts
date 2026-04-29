"""SSOT for cross-asset-group GCS bucket naming.

Before this module, every consumer hardcoded its own bucket templates:
``enumerate_strategy_instruments.py`` had a ``_CATEGORY_TO_INSTRUMENT_BUCKET``
dict, MDPS ``dependency_checker.py`` had inline templates, sports had a
domain-local ``sports_bucket_name``. This module consolidates the wire-format
templates so every consumer reads the same source.

Wire-format SSOT (matches deployed Terraform at
``deployment-service/terraform/gcp/main.tf``):

- Instruments-store buckets: ``instruments-store-{asset_group_lower}-{project_id}``
  (TRADFI has no instruments bucket today — universe registry is in UAC).
- Market-tick-data buckets: ``market-data-tick-{asset_group_lower}-{project_id}``.
- Test-mode buckets: ``-test-{project_id}`` suffix instead of ``-{project_id}``.
- Strategy catalogue bucket (single, cross-asset): ``strategy-store-cefi-{project_id}``.

Sports retains its dedicated facade (``sports_bucket_name``) for back-compat;
this module is what new code should use.
"""

from __future__ import annotations

from enum import StrEnum

# ---------------------------------------------------------------------------
# Asset group + bucket kind enums
# ---------------------------------------------------------------------------
# Dict keys stay lowercase per workspace SSOT (.cursorrules → asset-group
# vocabulary § "two intentional exceptions"). The Python enum values match.


class AssetGroup(StrEnum):
    """Canonical asset_group values. Lowercase matches GCS path segments."""

    CEFI = "cefi"
    DEFI = "defi"
    TRADFI = "tradfi"
    SPORTS = "sports"
    PREDICTION = "prediction"


class BucketKind(StrEnum):
    """Which GCS bucket family a consumer needs."""

    INSTRUMENTS = "instruments"
    """Instrument-availability + reference data
    (``instruments-store-{ag}-{pid}``)."""

    MARKET_DATA = "market_data"
    """Tick / book / trade snapshots
    (``market-data-tick-{ag}-{pid}``)."""


# ---------------------------------------------------------------------------
# Bucket templates — keyed by (asset_group, kind)
# ---------------------------------------------------------------------------
# Value is None for tuples that have no bucket today (TRADFI instruments —
# universe declared in UAC registry, not in a GCS parquet).

BUCKET_TEMPLATES_BY_ASSET_GROUP_KIND: dict[tuple[AssetGroup, BucketKind], str | None] = {
    # CeFi
    (AssetGroup.CEFI, BucketKind.INSTRUMENTS): "instruments-store-cefi-{project_id}",
    (AssetGroup.CEFI, BucketKind.MARKET_DATA): "market-data-tick-cefi-{project_id}",
    # DeFi
    (AssetGroup.DEFI, BucketKind.INSTRUMENTS): "instruments-store-defi-{project_id}",
    (AssetGroup.DEFI, BucketKind.MARKET_DATA): "market-data-tick-defi-{project_id}",
    # TradFi — no instruments bucket today; universe is in UAC registry
    (AssetGroup.TRADFI, BucketKind.INSTRUMENTS): None,
    (AssetGroup.TRADFI, BucketKind.MARKET_DATA): "market-data-tick-tradfi-{project_id}",
    # Sports — single-bucket-many-leagues
    (AssetGroup.SPORTS, BucketKind.INSTRUMENTS): "instruments-store-sports-{project_id}",
    (AssetGroup.SPORTS, BucketKind.MARKET_DATA): "market-data-tick-sports-{project_id}",
    # Prediction
    (AssetGroup.PREDICTION, BucketKind.INSTRUMENTS): "instruments-store-prediction-{project_id}",
    (AssetGroup.PREDICTION, BucketKind.MARKET_DATA): "market-data-tick-prediction-{project_id}",
}


# Catalogue artefacts (envelope, instrument-catalogue, shard-dynamics) all live
# in this single bucket regardless of asset_group. Sub-prefixes inside the
# bucket carve up by artefact family (catalogue/strategy/, catalogue/instrument/, …).
STRATEGY_STORE_BUCKET_TEMPLATE = "strategy-store-cefi-{project_id}"


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------


def bucket_template(
    asset_group: AssetGroup | str,
    *,
    kind: BucketKind | str = BucketKind.INSTRUMENTS,
    test_mode: bool = False,
) -> str | None:
    """Return the bucket-name template with ``{project_id}`` placeholder still
    in place.

    Use this when the caller resolves the project_id later (e.g. MDPS
    ``dependency_checker.py`` framework formats templates at lookup time).
    For immediate resolution, prefer :func:`bucket_name`.
    """
    ag = AssetGroup(asset_group) if not isinstance(asset_group, AssetGroup) else asset_group
    bk = BucketKind(kind) if not isinstance(kind, BucketKind) else kind
    template = BUCKET_TEMPLATES_BY_ASSET_GROUP_KIND.get((ag, bk))
    if template is None:
        return None
    if test_mode:
        template = template.replace("-{project_id}", "-test-{project_id}")
    return template


def bucket_name(
    asset_group: AssetGroup | str,
    project_id: str,
    *,
    kind: BucketKind | str = BucketKind.INSTRUMENTS,
    test_mode: bool = False,
) -> str | None:
    """Resolve a bucket name for ``(asset_group, kind)``.

    Args:
        asset_group: Asset group enum or lowercase string token
            (``cefi`` / ``defi`` / ``tradfi`` / ``sports`` / ``prediction``).
        project_id: GCP project id.
        kind: Which bucket family. ``INSTRUMENTS`` for reference / availability
            parquets; ``MARKET_DATA`` for tick / book / trade snapshots.
        test_mode: If True, swap ``-{project_id}`` for ``-test-{project_id}``
            (matches Terraform test buckets at deployment-service main.tf).

    Returns:
        Bucket name. Returns ``None`` for tuples that have no bucket today
        (currently only TRADFI instruments — universe is in UAC registry).
    """
    template = bucket_template(asset_group, kind=kind, test_mode=test_mode)
    if template is None:
        return None
    return template.format(project_id=project_id)


def strategy_store_bucket(project_id: str) -> str:
    """Catalogue-artefact bucket. Single bucket regardless of asset_group."""
    return STRATEGY_STORE_BUCKET_TEMPLATE.format(project_id=project_id)


# Sports parity import — sports has had its own facade since the phantom-row
# audit. New code should prefer ``bucket_name(AssetGroup.SPORTS, project_id)``,
# but importing ``sports_bucket_name`` from this module is the equivalent.
def sports_bucket_name(project_id: str) -> str:
    """Sports parity wrapper. Equivalent to
    ``bucket_name(AssetGroup.SPORTS, project_id)``."""
    return f"instruments-store-sports-{project_id}"


__all__ = [
    "BUCKET_TEMPLATES_BY_ASSET_GROUP_KIND",
    "STRATEGY_STORE_BUCKET_TEMPLATE",
    "AssetGroup",
    "BucketKind",
    "bucket_name",
    "bucket_template",
    "sports_bucket_name",
    "strategy_store_bucket",
]
