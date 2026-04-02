"""Tests for capability.py's error classes and validation logic.

Tests that validate_mode_env_auth() correctly raises UnsupportedModeError
and UnsupportedEnvironmentError when mode/env is unsupported by a capability.

Error classes are now defined directly in UAC's registry.capability module
(no UTL dependency needed).
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.capability import (
    CapabilityResolutionError,
    SourceCapability,
    UnsupportedEnvironmentError,
    UnsupportedModeError,
    register_capability,
    resolve_capability,
    validate_mode_env_auth,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def batch_only_cap() -> SourceCapability:
    """A source that supports batch only (no live)."""
    cap = SourceCapability(
        source="test-batch-only",
        domains=["market"],
        crosscutting=["errors"],
        supports_live=False,
        supports_batch=True,
        supports_historical=True,
        supports_testnet=False,
        supports_mainnet=True,
    )
    register_capability(cap)
    return cap


@pytest.fixture()
def live_only_cap() -> SourceCapability:
    """A source that supports live only (no batch)."""
    cap = SourceCapability(
        source="test-live-only",
        domains=["execution"],
        crosscutting=["rate_limits"],
        supports_live=True,
        supports_batch=False,
        supports_historical=False,
        supports_testnet=True,
        supports_mainnet=True,
    )
    register_capability(cap)
    return cap


@pytest.fixture()
def mainnet_only_cap() -> SourceCapability:
    """A source that supports mainnet only (no testnet)."""
    cap = SourceCapability(
        source="test-mainnet-only",
        domains=["market"],
        crosscutting=[],
        supports_live=True,
        supports_batch=True,
        supports_testnet=False,
        supports_mainnet=True,
    )
    register_capability(cap)
    return cap


# ---------------------------------------------------------------------------
# Test: SourceCapability instantiation and registry round-trip
# ---------------------------------------------------------------------------


class TestCapabilityRegistryRoundTrip:
    """register_capability + resolve_capability must round-trip cleanly."""

    def test_register_and_resolve(self, batch_only_cap: SourceCapability) -> None:
        resolved = resolve_capability("test-batch-only")
        assert resolved is batch_only_cap
        assert resolved.source == "test-batch-only"
        assert resolved.supports_batch is True
        assert resolved.supports_live is False

    def test_resolve_unknown_raises(self) -> None:
        with pytest.raises(CapabilityResolutionError) as exc_info:
            resolve_capability("nonexistent-source-xyz")
        assert exc_info.value.source == "nonexistent-source-xyz"
        assert exc_info.value.operation == "*"

    def test_source_capability_fields(self, live_only_cap: SourceCapability) -> None:
        assert live_only_cap.domains == ["execution"]
        assert live_only_cap.crosscutting == ["rate_limits"]
        assert live_only_cap.supports_testnet is True

    def test_source_capability_with_operations(self) -> None:
        """SourceCapability must support the operations dict field."""
        cap = SourceCapability(
            source="test-with-ops",
            domains=["market"],
            crosscutting=[],
            operations={"market": ["ticker", "orderbook", "trades"]},
        )
        assert cap.operations["market"] == ["ticker", "orderbook", "trades"]

    def test_source_capability_auth_fields(self) -> None:
        """SourceCapability must support auth_scope and auth_environments."""
        cap = SourceCapability(
            source="test-auth",
            domains=["execution"],
            crosscutting=[],
            auth_scope=["api_key", "oauth"],
            auth_environments={"test": "testnet_key", "prod": "prod_key"},
        )
        assert "api_key" in cap.auth_scope
        assert cap.auth_environments["prod"] == "prod_key"


# ---------------------------------------------------------------------------
# Test: validate_mode_env_auth raises error classes
# ---------------------------------------------------------------------------


class TestValidateModeEnvAuthErrors:
    """validate_mode_env_auth must raise appropriate error classes."""

    def test_live_on_batch_only_raises_unsupported_mode_error(self, batch_only_cap: SourceCapability) -> None:
        with pytest.raises(UnsupportedModeError) as exc_info:
            validate_mode_env_auth(batch_only_cap, mode="live")

        err = exc_info.value
        assert err.source == "test-batch-only"
        assert err.requested_mode == "live"
        assert "batch" in err.supported_modes
        assert "live" not in err.supported_modes
        assert isinstance(err.suggested_resolution, str)

    def test_batch_on_live_only_raises_unsupported_mode_error(self, live_only_cap: SourceCapability) -> None:
        with pytest.raises(UnsupportedModeError) as exc_info:
            validate_mode_env_auth(live_only_cap, mode="batch")

        err = exc_info.value
        assert err.source == "test-live-only"
        assert err.requested_mode == "batch"
        assert "live" in err.supported_modes

    def test_testnet_on_mainnet_only_raises_unsupported_env_error(self, mainnet_only_cap: SourceCapability) -> None:
        with pytest.raises(UnsupportedEnvironmentError) as exc_info:
            validate_mode_env_auth(mainnet_only_cap, env="testnet")

        err = exc_info.value
        assert err.source == "test-mainnet-only"
        assert err.requested_env == "testnet"
        assert "mainnet" in err.supported_envs
        assert isinstance(err.suggested_resolution, str)

    def test_unsupported_mode_error_message_format(self, batch_only_cap: SourceCapability) -> None:
        """The error message must include source name and supported modes."""
        with pytest.raises(UnsupportedModeError) as exc_info:
            validate_mode_env_auth(batch_only_cap, mode="live")

        msg = str(exc_info.value)
        assert "test-batch-only" in msg
        assert "live" in msg


# ---------------------------------------------------------------------------
# Test: validate_mode_env_auth passes for valid combinations
# ---------------------------------------------------------------------------


class TestValidateModeEnvAuthPasses:
    """validate_mode_env_auth must not raise for valid mode/env combos."""

    def test_batch_on_batch_capable_passes(self, batch_only_cap: SourceCapability) -> None:
        validate_mode_env_auth(batch_only_cap, mode="batch")

    def test_live_on_live_capable_passes(self, live_only_cap: SourceCapability) -> None:
        validate_mode_env_auth(live_only_cap, mode="live")

    def test_testnet_on_testnet_capable_passes(self, live_only_cap: SourceCapability) -> None:
        validate_mode_env_auth(live_only_cap, env="testnet")

    def test_no_mode_no_env_passes(self, batch_only_cap: SourceCapability) -> None:
        validate_mode_env_auth(batch_only_cap)

    def test_mode_and_env_combined(self, live_only_cap: SourceCapability) -> None:
        validate_mode_env_auth(live_only_cap, mode="live", env="testnet")

    def test_none_mode_none_env_passes(self, batch_only_cap: SourceCapability) -> None:
        """Explicit None values must be handled the same as omitted args."""
        validate_mode_env_auth(batch_only_cap, mode=None, env=None)
