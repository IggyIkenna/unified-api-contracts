"""Cross-asset-group GCS bucket-naming facade.

Citadel import surface — services should import from here, never from
``unified_api_contracts.canonical.*`` directly.

For per-asset-group partition layouts (the path inside each bucket), use the
domain facades: ``unified_api_contracts.sports`` already exposes
``candidate_parquet_paths``; ``unified_api_contracts.cefi`` / ``.defi`` /
``.tradfi`` / ``.prediction`` will too once each domain's
``canonical/domain/<ag>/gcs_paths.py`` lands.
"""

from __future__ import annotations

from unified_api_contracts.canonical.gcs_paths import (
    BUCKET_TEMPLATES_BY_ASSET_GROUP_KIND as BUCKET_TEMPLATES_BY_ASSET_GROUP_KIND,
)
from unified_api_contracts.canonical.gcs_paths import (
    STRATEGY_STORE_BUCKET_TEMPLATE as STRATEGY_STORE_BUCKET_TEMPLATE,
)
from unified_api_contracts.canonical.gcs_paths import AssetGroup as AssetGroup
from unified_api_contracts.canonical.gcs_paths import BucketKind as BucketKind
from unified_api_contracts.canonical.gcs_paths import bucket_name as bucket_name
from unified_api_contracts.canonical.gcs_paths import bucket_template as bucket_template
from unified_api_contracts.canonical.gcs_paths import sports_bucket_name as sports_bucket_name
from unified_api_contracts.canonical.gcs_paths import strategy_store_bucket as strategy_store_bucket

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
