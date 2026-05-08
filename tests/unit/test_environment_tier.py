"""Tests for EnvironmentTier + resolve_environment_from_* helpers + CloudTarget.

Phase A.5 of ``deployment_ui_lifecycle_tabs_2026_05_08``: pins the closed-set
3-tier hosting taxonomy + the hostname / env-var resolution rules so client
(deployment-UI) and server (deployment-api) always agree on which tier they
run in.

Mirrors the test shape of :mod:`tests.unit.test_risk_taxonomy` — top-level
``unified_api_contracts`` facade imports only.
"""

from __future__ import annotations

import pytest

from unified_api_contracts import (
    CloudTarget,
    EnvironmentTier,
    resolve_environment_from_env,
    resolve_environment_from_hostname,
)


class TestCloudTarget:
    def test_two_member_closed_set(self) -> None:
        assert {member.value for member in CloudTarget} == {"GCP", "AWS"}
        assert len(CloudTarget) == 2

    def test_member_value_equals_name(self) -> None:
        assert CloudTarget.GCP == "GCP"
        assert CloudTarget.AWS == "AWS"
        assert CloudTarget.GCP.value == CloudTarget.GCP.name
        assert CloudTarget.AWS.value == CloudTarget.AWS.name

    def test_no_local_or_multi_member(self) -> None:
        # Frozen-canonical: LOCAL is discriminated via EnvironmentTier.DEV,
        # not via CloudTarget. There must NEVER be a "LOCAL" or "MULTI"
        # member — that would let a request dispatch against an undefined
        # cloud and break the auth-on-boot pattern.
        with pytest.raises(ValueError, match="is not a valid CloudTarget"):
            CloudTarget("LOCAL")
        with pytest.raises(ValueError, match="is not a valid CloudTarget"):
            CloudTarget("MULTI")


class TestEnvironmentTierMembers:
    def test_three_member_closed_set(self) -> None:
        assert {member.value for member in EnvironmentTier} == {"DEV", "STAGING", "PROD"}
        assert len(EnvironmentTier) == 3

    def test_member_value_equals_name(self) -> None:
        assert EnvironmentTier.DEV == "DEV"
        assert EnvironmentTier.STAGING == "STAGING"
        assert EnvironmentTier.PROD == "PROD"
        for member in EnvironmentTier:
            assert member.value == member.name


class TestResolveEnvironmentFromHostname:
    def test_localhost_resolves_to_dev(self) -> None:
        assert resolve_environment_from_hostname("localhost") == EnvironmentTier.DEV

    def test_loopback_ip_resolves_to_dev(self) -> None:
        assert resolve_environment_from_hostname("127.0.0.1") == EnvironmentTier.DEV

    def test_local_tld_resolves_to_dev(self) -> None:
        assert resolve_environment_from_hostname("foo.local") == EnvironmentTier.DEV
        assert resolve_environment_from_hostname("my-mac.local") == EnvironmentTier.DEV
        assert resolve_environment_from_hostname("deployment-ui.dev.local") == EnvironmentTier.DEV

    def test_staging_subdomain_resolves_to_staging(self) -> None:
        assert resolve_environment_from_hostname("staging.example.com") == EnvironmentTier.STAGING
        assert resolve_environment_from_hostname("staging.research.internal") == EnvironmentTier.STAGING

    def test_non_dev_non_staging_resolves_to_prod(self) -> None:
        assert resolve_environment_from_hostname("research.internal") == EnvironmentTier.PROD
        assert resolve_environment_from_hostname("app.example.com") == EnvironmentTier.PROD
        assert resolve_environment_from_hostname("example.com") == EnvironmentTier.PROD

    def test_case_insensitive_localhost(self) -> None:
        assert resolve_environment_from_hostname("LOCALHOST") == EnvironmentTier.DEV
        assert resolve_environment_from_hostname("LocalHost") == EnvironmentTier.DEV

    def test_case_insensitive_local_tld(self) -> None:
        assert resolve_environment_from_hostname("FOO.LOCAL") == EnvironmentTier.DEV
        assert resolve_environment_from_hostname("Foo.Local") == EnvironmentTier.DEV

    def test_case_insensitive_staging_prefix(self) -> None:
        assert resolve_environment_from_hostname("STAGING.example.com") == EnvironmentTier.STAGING
        assert resolve_environment_from_hostname("Staging.Example.Com") == EnvironmentTier.STAGING

    def test_empty_hostname_raises(self) -> None:
        with pytest.raises(ValueError, match="empty hostname"):
            resolve_environment_from_hostname("")

    def test_whitespace_only_hostname_raises(self) -> None:
        with pytest.raises(ValueError, match="empty hostname"):
            resolve_environment_from_hostname("   ")


class TestResolveEnvironmentFromEnv:
    def test_dev_value_resolves(self) -> None:
        assert resolve_environment_from_env("DEV") == EnvironmentTier.DEV

    def test_staging_value_resolves(self) -> None:
        assert resolve_environment_from_env("STAGING") == EnvironmentTier.STAGING

    def test_prod_value_resolves(self) -> None:
        assert resolve_environment_from_env("PROD") == EnvironmentTier.PROD

    def test_lowercase_value_resolves(self) -> None:
        # Server-side env-var content can come in any case; the helper
        # uppercases before matching so misconfigured CI env vars don't
        # silently fall through to an exception.
        assert resolve_environment_from_env("dev") == EnvironmentTier.DEV
        assert resolve_environment_from_env("staging") == EnvironmentTier.STAGING
        assert resolve_environment_from_env("prod") == EnvironmentTier.PROD

    def test_whitespace_padding_stripped(self) -> None:
        assert resolve_environment_from_env(" DEV ") == EnvironmentTier.DEV
        assert resolve_environment_from_env("\tSTAGING\n") == EnvironmentTier.STAGING

    def test_none_raises(self) -> None:
        with pytest.raises(ValueError, match="from None"):
            resolve_environment_from_env(None)

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="empty env-var value"):
            resolve_environment_from_env("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="empty env-var value"):
            resolve_environment_from_env("   ")

    def test_unknown_value_raises_with_accepted_set(self) -> None:
        with pytest.raises(ValueError, match="Unrecognised CLOUD_DEPLOYMENT_ENV"):
            resolve_environment_from_env("PRODUCTION")
        with pytest.raises(ValueError, match="Unrecognised CLOUD_DEPLOYMENT_ENV"):
            resolve_environment_from_env("test")
