"""Tests for data_locality.py — DATA_LOCALITY_REGION / CLOUD_PROVIDER check."""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.crosscutting.data_locality import (
    DATA_LOCALITY_REGION_AWS,
    DATA_LOCALITY_REGION_GCP,
    check_data_locality,
)


def test_check_returns_none_when_cloud_provider_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUD_PROVIDER", raising=False)
    monkeypatch.delenv("DATA_LOCALITY_REGION", raising=False)
    assert check_data_locality() is None


def test_check_skipped_when_data_locality_region_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUD_PROVIDER", "aws")
    monkeypatch.delenv("DATA_LOCALITY_REGION", raising=False)
    result = check_data_locality()
    assert result is not None
    assert result.skipped is True
    assert result.ok is True


def test_ok_when_same_cloud_gcp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUD_PROVIDER", "gcp")
    monkeypatch.setenv("DATA_LOCALITY_REGION", DATA_LOCALITY_REGION_GCP)
    result = check_data_locality()
    assert result is not None
    assert result.ok is True
    assert result.skipped is False
    assert result.service_cloud == "gcp"
    assert result.data_cloud == "gcp"


def test_ok_when_same_cloud_aws(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUD_PROVIDER", "aws")
    monkeypatch.setenv("DATA_LOCALITY_REGION", DATA_LOCALITY_REGION_AWS)
    result = check_data_locality()
    assert result is not None
    assert result.ok is True
    assert result.data_cloud == "aws"


def test_violation_when_gcp_reads_aws_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUD_PROVIDER", "gcp")
    monkeypatch.setenv("DATA_LOCALITY_REGION", DATA_LOCALITY_REGION_AWS)
    result = check_data_locality()
    assert result is not None
    assert result.ok is False
    assert result.service_cloud == "gcp"
    assert result.data_cloud == "aws"
    assert result.skipped is False


def test_violation_when_aws_reads_gcp_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUD_PROVIDER", "aws")
    monkeypatch.setenv("DATA_LOCALITY_REGION", DATA_LOCALITY_REGION_GCP)
    result = check_data_locality()
    assert result is not None
    assert result.ok is False
    assert result.service_cloud == "aws"
    assert result.data_cloud == "gcp"


def test_local_always_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUD_PROVIDER", "local")
    monkeypatch.setenv("DATA_LOCALITY_REGION", DATA_LOCALITY_REGION_AWS)
    result = check_data_locality()
    assert result is not None
    assert result.ok is True


def test_canonical_region_values() -> None:
    assert DATA_LOCALITY_REGION_GCP == "gcp:asia-northeast1"
    assert DATA_LOCALITY_REGION_AWS == "aws:ap-northeast-1"
