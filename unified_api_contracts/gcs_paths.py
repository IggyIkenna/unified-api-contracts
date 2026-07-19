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
from unified_api_contracts.canonical.gcs_paths import generic_bucket_template as generic_bucket_template
from unified_api_contracts.canonical.gcs_paths import sports_bucket_name as sports_bucket_name
from unified_api_contracts.canonical.gcs_paths import strategy_store_bucket as strategy_store_bucket
from unified_api_contracts.canonical.partition_paths import (
    ASSET_GROUP_HIVE_KEY as ASSET_GROUP_HIVE_KEY,
)
from unified_api_contracts.canonical.partition_paths import (
    CEFI_CHAIN_INSTRUMENT_TYPES as CEFI_CHAIN_INSTRUMENT_TYPES,
)
from unified_api_contracts.canonical.partition_paths import (
    RAW_TICK_DATA_PREFIX as RAW_TICK_DATA_PREFIX,
)
from unified_api_contracts.canonical.partition_paths import (
    TRADFI_CHAIN_INSTRUMENT_TYPES as TRADFI_CHAIN_INSTRUMENT_TYPES,
)
from unified_api_contracts.canonical.partition_paths import (
    TRADFI_SINGLE_INSTRUMENT_TYPES as TRADFI_SINGLE_INSTRUMENT_TYPES,
)
from unified_api_contracts.canonical.partition_paths import (
    build_cefi_partition_path as build_cefi_partition_path,
)
from unified_api_contracts.canonical.partition_paths import (
    build_defi_partition_path as build_defi_partition_path,
)
from unified_api_contracts.canonical.partition_paths import (
    build_prediction_partition_path as build_prediction_partition_path,
)
from unified_api_contracts.canonical.partition_paths import (
    build_tradfi_partition_path as build_tradfi_partition_path,
)
from unified_api_contracts.canonical.partition_paths import (
    candidate_parquet_paths as candidate_parquet_paths,
)

__all__ = [
    "ASSET_GROUP_HIVE_KEY",
    "BUCKET_TEMPLATES_BY_ASSET_GROUP_KIND",
    "CEFI_CHAIN_INSTRUMENT_TYPES",
    "RAW_TICK_DATA_PREFIX",
    "STRATEGY_STORE_BUCKET_TEMPLATE",
    "TRADFI_CHAIN_INSTRUMENT_TYPES",
    "TRADFI_SINGLE_INSTRUMENT_TYPES",
    "AssetGroup",
    "BucketKind",
    "bucket_name",
    "bucket_template",
    "build_cefi_partition_path",
    "build_defi_partition_path",
    "build_prediction_partition_path",
    "build_tradfi_partition_path",
    "candidate_parquet_paths",
    "generic_bucket_template",
    "sports_bucket_name",
    "strategy_store_bucket",
]
