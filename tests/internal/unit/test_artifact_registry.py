"""Tests for architecture_v2 artifact registry schemas (Phase 8)."""

from __future__ import annotations

import pytest

from unified_api_contracts.internal import (
    ArtifactKind,
    ArtifactMetadata,
    ArtifactPublishedPayload,
    ArtifactRef,
)


def test_artifact_ref_render_is_family_at_v_version() -> None:
    ref = ArtifactRef(kind=ArtifactKind.ML_MODEL, family="CRYPTO_BTC_CATBOOST_V4", version=3)
    assert ref.ref == "CRYPTO_BTC_CATBOOST_V4@v3"


def test_artifact_ref_parse_roundtrip() -> None:
    parsed = ArtifactRef.parse(ArtifactKind.FEATURE_GROUP, "crypto-ohlc-5m@v7")
    assert parsed.family == "crypto-ohlc-5m"
    assert parsed.version == 7
    assert parsed.ref == "crypto-ohlc-5m@v7"


def test_artifact_ref_parse_rejects_implicit_latest() -> None:
    with pytest.raises(ValueError, match="implicit-latest is forbidden"):
        _ = ArtifactRef.parse(ArtifactKind.ML_MODEL, "CRYPTO_BTC_CATBOOST_V4")


def test_artifact_ref_parse_rejects_non_integer_version() -> None:
    with pytest.raises(ValueError, match="non-integer version suffix"):
        _ = ArtifactRef.parse(ArtifactKind.ML_MODEL, "model@v1.2.3")


def test_artifact_metadata_ref_and_as_ref() -> None:
    meta = ArtifactMetadata(
        kind=ArtifactKind.FEATURE_GROUP,
        family="crypto-onchain-ethereum",
        version=4,
        content_hash="abcdef0123456789",
        created_by="features-onchain-service",
        dependencies=[],
    )
    assert meta.ref == "crypto-onchain-ethereum@v4"
    projected = meta.as_ref()
    assert projected.kind == ArtifactKind.FEATURE_GROUP
    assert projected.family == "crypto-onchain-ethereum"
    assert projected.version == 4


def test_artifact_metadata_rejects_non_16_hex_content_hash() -> None:
    with pytest.raises(ValueError):
        _ = ArtifactMetadata(
            kind=ArtifactKind.ML_MODEL,
            family="SPORTS_EPL_1X2_CATBOOST_V3",
            version=5,
            content_hash="tooshort",
        )


def test_artifact_metadata_rejects_version_zero() -> None:
    with pytest.raises(ValueError):
        _ = ArtifactMetadata(
            kind=ArtifactKind.FEATURE_GROUP,
            family="crypto-ohlc-5m",
            version=0,
            content_hash="0123456789abcdef",
        )


def test_artifact_published_payload_carries_dependencies() -> None:
    deps = [
        ArtifactRef(kind=ArtifactKind.FEATURE_GROUP, family="crypto-ohlc-5m", version=7),
        ArtifactRef(kind=ArtifactKind.FEATURE_GROUP, family="crypto-onchain-ethereum", version=4),
    ]
    meta = ArtifactMetadata(
        kind=ArtifactKind.ML_MODEL,
        family="CRYPTO_BTC_CATBOOST_V4",
        version=3,
        content_hash="deadbeefcafef00d",
        created_by="ml-training-service",
        dependencies=deps,
    )
    payload = ArtifactPublishedPayload(metadata=meta, replaces_version=2)
    assert payload.metadata.ref == "CRYPTO_BTC_CATBOOST_V4@v3"
    assert payload.replaces_version == 2
    assert {d.family for d in payload.metadata.dependencies} == {
        "crypto-ohlc-5m",
        "crypto-onchain-ethereum",
    }
