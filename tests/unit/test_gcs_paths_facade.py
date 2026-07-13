"""Tests for the cross-asset-group bucket-naming facade.

Verifies wire-format parity with the deployed Terraform at
``deployment-service/terraform/gcp/main.tf`` and
``deployment-service/configs/cloud-providers.yaml`` (canonical source).

Canonical form is env-tiered: ``{prefix}-{ag}-prd-{project_id}`` where
``prd`` = DEPLOYMENT_ENV_SHORT default. The no-env form
``{prefix}-{ag}-{project_id}`` is legacy and no longer emitted by this facade.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.gcs_paths import (
    AssetGroup,
    BucketKind,
    bucket_name,
    bucket_template,
    generic_bucket_template,
    sports_bucket_name,
    strategy_store_bucket,
)

PID = "test-project"
ENV = "prd"  # canonical production env short form


@pytest.mark.parametrize(
    ("asset_group", "expected"),
    [
        (AssetGroup.CEFI, f"instruments-store-cefi-{ENV}-{PID}"),
        (AssetGroup.DEFI, f"instruments-store-defi-{ENV}-{PID}"),
        (AssetGroup.SPORTS, f"instruments-store-sports-{ENV}-{PID}"),
        # Prediction is ABBREVIATED "pred" (fixed 2026-07-08 — the prior unabbreviated
        # "instruments-store-prediction-..." template was a dead bucket name that has
        # never existed; the real bucket is "instruments-store-pred-...", confirmed
        # live with 33,122 blobs). See gcs_paths.py's BUCKET_TEMPLATES_BY_ASSET_GROUP_KIND
        # comment for the full history.
        (AssetGroup.PREDICTION, f"instruments-store-pred-{ENV}-{PID}"),
    ],
)
def test_instruments_bucket_per_asset_group(asset_group: AssetGroup, expected: str) -> None:
    """Instruments buckets emit the canonical env-tiered -prd- form."""
    assert bucket_name(asset_group, PID, kind=BucketKind.INSTRUMENTS) == expected


def test_tradfi_instruments_returns_none() -> None:
    """TradFi has no instruments bucket today — universe is in UAC registry."""
    assert bucket_name(AssetGroup.TRADFI, PID, kind=BucketKind.INSTRUMENTS) is None


@pytest.mark.parametrize(
    ("asset_group", "expected"),
    [
        (AssetGroup.CEFI, f"market-data-tick-cefi-{ENV}-{PID}"),
        (AssetGroup.DEFI, f"market-data-tick-defi-{ENV}-{PID}"),
        (AssetGroup.TRADFI, f"market-data-tick-tradfi-{ENV}-{PID}"),
        (AssetGroup.SPORTS, f"market-data-tick-sports-{ENV}-{PID}"),
        (AssetGroup.PREDICTION, f"market-data-tick-prediction-{ENV}-{PID}"),
    ],
)
def test_market_data_bucket_per_asset_group(asset_group: AssetGroup, expected: str) -> None:
    """Market-data buckets emit the canonical env-tiered -prd- form."""
    assert bucket_name(asset_group, PID, kind=BucketKind.MARKET_DATA) == expected


def test_test_mode_swaps_suffix() -> None:
    """Test mode buckets insert ``test-`` before the project_id segment (env still present)."""
    assert (
        bucket_name(AssetGroup.CEFI, PID, kind=BucketKind.MARKET_DATA, test_mode=True)
        == f"market-data-tick-cefi-{ENV}-test-{PID}"
    )
    assert (
        bucket_name(AssetGroup.SPORTS, PID, kind=BucketKind.INSTRUMENTS, test_mode=True)
        == f"instruments-store-sports-{ENV}-test-{PID}"
    )


def test_staging_env_explicit() -> None:
    """Callers can pass env='stg' for staging buckets."""
    assert bucket_name(AssetGroup.SPORTS, PID, env="stg") == f"instruments-store-sports-stg-{PID}"


def test_string_input_accepted() -> None:
    """Lowercase string tokens (matching dict keys) work too."""
    assert bucket_name("cefi", PID) == f"instruments-store-cefi-{ENV}-{PID}"
    assert bucket_name("sports", PID, kind="market_data") == f"market-data-tick-sports-{ENV}-{PID}"


def test_sports_facade_parity() -> None:
    assert sports_bucket_name(PID) == bucket_name(AssetGroup.SPORTS, PID)


def test_strategy_store_bucket() -> None:
    """Catalogue artefacts live in the unified FLAT strategy-store bucket
    (cloud-providers.yaml kind ``strategy-store`` — no asset-group segment; see
    plans/active/issues/strategy_store_split_brain_2026_07_13.md)."""
    assert strategy_store_bucket(PID) == f"strategy-store-{PID}"


def test_generic_bucket_template_keeps_both_placeholders() -> None:
    """``generic_bucket_template`` keeps ``{asset_group_lower}`` + ``{project_id}``
    placeholders; ``{env}`` is resolved to the default 'prd'."""
    assert (
        generic_bucket_template(kind=BucketKind.INSTRUMENTS)
        == f"instruments-store-{{asset_group_lower}}-{ENV}-{{project_id}}"
    )
    assert (
        generic_bucket_template(kind=BucketKind.MARKET_DATA)
        == f"market-data-tick-{{asset_group_lower}}-{ENV}-{{project_id}}"
    )
    assert (
        generic_bucket_template(kind=BucketKind.MARKET_DATA, test_mode=True)
        == f"market-data-tick-{{asset_group_lower}}-{ENV}-test-{{project_id}}"
    )


def test_bucket_template_keeps_project_id_placeholder() -> None:
    """``bucket_template`` returns a string with ``{project_id}`` still present
    and ``{env}`` already resolved to 'prd'. Used by callers that resolve
    project_id later (e.g. MDPS dependency_checker)."""
    assert bucket_template(AssetGroup.CEFI) == f"instruments-store-cefi-{ENV}-{{project_id}}"
    assert (
        bucket_template(AssetGroup.SPORTS, kind=BucketKind.MARKET_DATA)
        == f"market-data-tick-sports-{ENV}-{{project_id}}"
    )
    assert (
        bucket_template(AssetGroup.SPORTS, kind=BucketKind.MARKET_DATA, test_mode=True)
        == f"market-data-tick-sports-{ENV}-test-{{project_id}}"
    )
    assert bucket_template(AssetGroup.TRADFI, kind=BucketKind.INSTRUMENTS) is None
