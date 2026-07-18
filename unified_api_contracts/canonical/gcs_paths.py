"""SSOT for cross-asset-group GCS bucket naming.

Before this module, every consumer hardcoded its own bucket templates:
``enumerate_strategy_instruments.py`` had a ``_CATEGORY_TO_INSTRUMENT_BUCKET``
dict, MDPS ``dependency_checker.py`` had inline templates, sports had a
domain-local ``sports_bucket_name``. This module consolidates the wire-format
templates so every consumer reads the same source.

Wire-format SSOT (matches deployed Terraform at
``deployment-service/terraform/gcp/main.tf`` and
``deployment-service/configs/cloud-providers.yaml``):

- Instruments-store buckets:
    ``instruments-store-{asset_group_lower}-{env}-{project_id}``
  (TRADFI has no instruments bucket today — universe registry is in UAC).
- Market-tick-data buckets:
    ``market-data-tick-{asset_group_lower}-{env}-{project_id}``.
- ``env`` defaults to ``"prd"`` — the production short form matching
  ``DEPLOYMENT_ENV_SHORT=prd`` in cloud-providers.yaml. Set explicitly for
  dev/staging buckets.
- Test-mode buckets: insert ``test-`` before ``{project_id}``
  (``...-prd-test-{project_id}``).
- Strategy catalogue bucket (single, cross-asset):
    ``strategy-store-prd-{project_id}`` (unified bucket, no asset-group segment —
    cloud-providers.yaml kind ``strategy-store``; env-tiered to ``prd`` per
    strategy FOLD D fold_d_cutover_spec 2026-07-18; see
    plans/active/issues/strategy_store_split_brain_2026_07_13.md).

The canonical resolver (UTL ``resolve_bucket_name``) reads the live process env
for DEPLOYMENT_ENV_SHORT and GCP_PROJECT_ID; this facade is the UAC-layer helper
for consumers that already know the project_id at call time.

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
    (AssetGroup.CEFI, BucketKind.INSTRUMENTS): "instruments-store-cefi-{env}-{project_id}",
    (AssetGroup.CEFI, BucketKind.MARKET_DATA): "market-data-tick-cefi-{env}-{project_id}",
    # DeFi
    (AssetGroup.DEFI, BucketKind.INSTRUMENTS): "instruments-store-defi-{env}-{project_id}",
    (AssetGroup.DEFI, BucketKind.MARKET_DATA): "market-data-tick-defi-{env}-{project_id}",
    # TradFi — no instruments bucket today; universe is in UAC registry
    (AssetGroup.TRADFI, BucketKind.INSTRUMENTS): None,
    (AssetGroup.TRADFI, BucketKind.MARKET_DATA): "market-data-tick-tradfi-{env}-{project_id}",
    # Sports — single-bucket-many-leagues
    (AssetGroup.SPORTS, BucketKind.INSTRUMENTS): "instruments-store-sports-{env}-{project_id}",
    (AssetGroup.SPORTS, BucketKind.MARKET_DATA): "market-data-tick-sports-{env}-{project_id}",
    # Prediction
    # INSTRUMENTS: FIXED 2026-07-08 — was the unabbreviated "instruments-store-
    # prediction-{env}-{project_id}", a bucket that has never existed (confirmed live
    # against the production GCP project: the abbreviated "instruments-store-pred-"
    # form exists with real data — 33,122 blobs — while the unabbreviated
    # "instruments-store-prediction-" form 404s). This was a dormant landmine — no
    # consumer reaches this facade for PREDICTION+INSTRUMENTS today (instruments-
    # service's own catalogue/orchestrator code resolves the prediction instruments
    # bucket via the flat, already-correct
    # `resolve_bucket_name(kind="instruments-store-prediction")` key, which abbreviates
    # via cloud-providers.yaml) — but it is a live landmine for the next consumer that
    # reaches for this per-asset-group facade instead. See
    # unified-trading-pm/plans/active/issues/instrument_id_format_canonicalization_2026_07_08.md
    # finding 8 and instruments-service/docs/PREDICTION_INSTRUMENTS.md.
    (AssetGroup.PREDICTION, BucketKind.INSTRUMENTS): "instruments-store-pred-{env}-{project_id}",
    # MARKET_DATA: FLIPPED 2026-07-14 to the abbreviated `pred` token — the
    # migration to `market-data-tick-pred-prd-{pid}` completed (plan
    # prediction_manifest_canonicalisation_2026_06_01.md archived), and the legacy
    # long-form bucket `market-data-tick-prediction-{pid}` was deleted 2026-07-12
    # (confirmed 404 against production). `pred-prd` is now the sole, complete SSOT.
    # See unified-trading-pm/plans/active/issues/mdps_prediction_tick_bucket_uac_ssot_404_2026_07_14.md.
    (AssetGroup.PREDICTION, BucketKind.MARKET_DATA): "market-data-tick-pred-{env}-{project_id}",
}


# Catalogue artefacts (envelope, instrument-catalogue, shard-dynamics) all live
# in this single bucket regardless of asset_group. Sub-prefixes inside the
# bucket carve up by artefact family (catalogue/strategy/, catalogue/instrument/, …).
# Unified FLAT bucket (cloud-providers.yaml storage kind `strategy-store` — no
# `-cefi-`/`-tradfi-`/`-defi-` asset_group segment): per the operator-ratified
# 2026-05-20 (D6 Phase 4) decision the yaml is canonical and every live
# strategy-service writer resolves this name; this template previously drifted
# onto the stale per-AG `strategy-store-cefi-{project_id}` bucket — see
# plans/active/issues/strategy_store_split_brain_2026_07_13.md.
# strategy FOLD D (fold_d_cutover_spec, 2026-07-18): the bucket is now
# env-tiered `strategy-store-prd-{project_id}` (was un-tiered
# `strategy-store-{project_id}`). This facade hardcodes the `prd` tier — the
# `-test-` twin is only reached by services running DEPLOYMENT_ENV=test via
# the UTL yaml resolver, never this UAC literal (UAC is a lower tier than
# unified-trading-library, so `resolve_bucket_name()` can't be imported here).
STRATEGY_STORE_BUCKET_TEMPLATE = "strategy-store-prd-{project_id}"


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------


def bucket_template(
    asset_group: AssetGroup | str,
    *,
    kind: BucketKind | str = BucketKind.INSTRUMENTS,
    env: str = "prd",
    test_mode: bool = False,
) -> str | None:
    """Return the bucket-name template with ``{project_id}`` placeholder still
    in place.

    Use this when the caller resolves the project_id later (e.g. MDPS
    ``dependency_checker.py`` framework formats templates at lookup time).
    For immediate resolution, prefer :func:`bucket_name`.

    Args:
        asset_group: Asset group enum or lowercase string token.
        kind: Which bucket family.
        env: Deployment environment short form (``"prd"`` / ``"stg"`` /
            ``"dev"``). Defaults to ``"prd"`` — the canonical production env.
            Maps to ``DEPLOYMENT_ENV_SHORT`` in cloud-providers.yaml.
        test_mode: If True, insert ``test-`` before ``{project_id}``.
    """
    ag = AssetGroup(asset_group) if not isinstance(asset_group, AssetGroup) else asset_group
    bk = BucketKind(kind) if not isinstance(kind, BucketKind) else kind
    template = BUCKET_TEMPLATES_BY_ASSET_GROUP_KIND.get((ag, bk))
    if template is None:
        return None
    # Substitute env placeholder before the project_id placeholder so callers
    # that format the template with only ``{project_id}`` still get a valid name.
    template = template.replace("{env}", env)
    if test_mode:
        template = template.replace("-{project_id}", "-test-{project_id}")
    return template


def bucket_name(
    asset_group: AssetGroup | str,
    project_id: str,
    *,
    kind: BucketKind | str = BucketKind.INSTRUMENTS,
    env: str = "prd",
    test_mode: bool = False,
) -> str | None:
    """Resolve a bucket name for ``(asset_group, kind)``.

    Args:
        asset_group: Asset group enum or lowercase string token
            (``cefi`` / ``defi`` / ``tradfi`` / ``sports`` / ``prediction``).
        project_id: GCP project id.
        kind: Which bucket family. ``INSTRUMENTS`` for reference / availability
            parquets; ``MARKET_DATA`` for tick / book / trade snapshots.
        env: Deployment environment short form (``"prd"`` / ``"stg"`` /
            ``"dev"``). Defaults to ``"prd"`` — the canonical production env.
            Matches ``DEPLOYMENT_ENV_SHORT`` in cloud-providers.yaml. Pass
            explicitly for non-production buckets.
        test_mode: If True, insert ``test-`` before the project_id segment
            (matches Terraform test buckets at deployment-service main.tf).

    Returns:
        Bucket name. Returns ``None`` for tuples that have no bucket today
        (currently only TRADFI instruments — universe is in UAC registry).
    """
    template = bucket_template(asset_group, kind=kind, env=env, test_mode=test_mode)
    if template is None:
        return None
    return template.format(project_id=project_id)


def strategy_store_bucket(project_id: str) -> str:
    """Catalogue-artefact bucket. Single bucket regardless of asset_group."""
    return STRATEGY_STORE_BUCKET_TEMPLATE.format(project_id=project_id)


# ---------------------------------------------------------------------------
# Generic-shape templates (asset_group as a placeholder)
# ---------------------------------------------------------------------------
# Some consumers — notably MDPS ``BaseDependencyChecker`` — store template
# strings with BOTH ``{asset_group_lower}`` and ``{project_id}`` placeholders
# and resolve them at lookup time. These helpers expose those generic shapes
# so the wire format stays in this module rather than getting duplicated in
# the consumer.

_GENERIC_TEMPLATES_BY_KIND: dict[BucketKind, str] = {
    BucketKind.INSTRUMENTS: "instruments-store-{asset_group_lower}-{env}-{project_id}",
    BucketKind.MARKET_DATA: "market-data-tick-{asset_group_lower}-{env}-{project_id}",
}


def generic_bucket_template(
    *,
    kind: BucketKind | str = BucketKind.INSTRUMENTS,
    env: str = "prd",
    test_mode: bool = False,
) -> str:
    """Return a template with ``{asset_group_lower}`` AND ``{project_id}``
    placeholders (env already substituted).

    Used by lazy-resolve frameworks (e.g. MDPS ``BaseDependencyChecker``) that
    receive the asset_group at runtime and format the template once per call.
    For asset-group-specific templates use :func:`bucket_template`; for
    immediate resolution use :func:`bucket_name`.

    Args:
        kind: Which bucket family.
        env: Deployment environment short form (``"prd"`` / ``"stg"`` /
            ``"dev"``). Defaults to ``"prd"``.
        test_mode: If True, insert ``test-`` before ``{project_id}``.
    """
    bk = BucketKind(kind) if not isinstance(kind, BucketKind) else kind
    template = _GENERIC_TEMPLATES_BY_KIND.get(bk)
    if template is None:
        msg = f"unknown bucket kind: {kind!r}"
        raise ValueError(msg)
    template = template.replace("{env}", env)
    if test_mode:
        template = template.replace("-{project_id}", "-test-{project_id}")
    return template


# Sports parity import — sports has had its own facade since the phantom-row
# audit. New code should prefer ``bucket_name(AssetGroup.SPORTS, project_id)``,
# but importing ``sports_bucket_name`` from this module is the equivalent.
def sports_bucket_name(project_id: str, *, env: str = "prd") -> str:
    """Sports parity wrapper. Equivalent to
    ``bucket_name(AssetGroup.SPORTS, project_id, env=env)``."""
    return f"instruments-store-sports-{env}-{project_id}"


__all__ = [
    "BUCKET_TEMPLATES_BY_ASSET_GROUP_KIND",
    "STRATEGY_STORE_BUCKET_TEMPLATE",
    "AssetGroup",
    "BucketKind",
    "bucket_name",
    "bucket_template",
    "generic_bucket_template",
    "sports_bucket_name",
    "strategy_store_bucket",
]
