"""Tests for validate_operation() and operation-level capability types.

Tests the new operation-level validation layer:
- OperationEnvDetail / OperationDetail model construction
- validate_operation() happy path, error, fallback, unknown source
- Integration with bootstrap_capabilities() across all populated sources
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.capability import (
    CapabilityResolutionError,
    OperationDetail,
    OperationEnvDetail,
    SourceCapability,
    UnsupportedOperationError,
    register_capability,
    validate_operation,
)
from unified_api_contracts.registry.capability_data import (
    CAPABILITY_DECLARATIONS,
    bootstrap_capabilities,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _bootstrap() -> None:
    """Bootstrap all capability declarations before each test."""
    bootstrap_capabilities()


@pytest.fixture()
def _cap_with_details() -> SourceCapability:
    """Register a test source with detailed operation_details."""
    cap = SourceCapability(
        source="test-detailed",
        domains=["market", "execution"],
        crosscutting=["errors"],
        supports_live=True,
        supports_batch=True,
        supports_testnet=True,
        supports_mainnet=True,
        base_urls={"mainnet": "https://api.test.com", "testnet": "https://testnet.test.com"},
        margin_model={"mainnet": "cross", "testnet": "unified"},
        operation_details={
            "place_order": OperationDetail(
                environments={
                    "mainnet": OperationEnvDetail(
                        signing_scheme="hmac_sha256",
                        required_credential="api_key",
                    ),
                    "testnet": OperationEnvDetail(
                        signing_scheme="hmac_sha256",
                        required_credential="api_key",
                        data_fidelity="synthetic",
                    ),
                }
            ),
            "transfer": OperationDetail(
                environments={
                    "mainnet": OperationEnvDetail(
                        signing_scheme="user_signed",
                        required_credential="main_wallet",
                    ),
                    "testnet": OperationEnvDetail(
                        supported=False,
                        notes="Transfer not available on testnet via API",
                    ),
                }
            ),
            "ticker": OperationDetail(
                environments={
                    "mainnet": OperationEnvDetail(
                        signing_scheme="none",
                        required_credential="none",
                    ),
                }
            ),
        },
    )
    register_capability(cap)
    return cap


@pytest.fixture()
def _cap_no_details() -> SourceCapability:
    """Register a test source with no operation_details (fallback only)."""
    cap = SourceCapability(
        source="test-no-details",
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
# Test: OperationEnvDetail / OperationDetail model construction
# ---------------------------------------------------------------------------


class TestOperationModels:
    """Verify Pydantic model construction and defaults."""

    def test_env_detail_defaults(self) -> None:
        detail = OperationEnvDetail()
        assert detail.supported is True
        assert detail.signing_scheme is None
        assert detail.required_credential is None
        assert detail.base_url is None
        assert detail.data_fidelity is None
        assert detail.notes is None

    def test_env_detail_with_values(self) -> None:
        detail = OperationEnvDetail(
            supported=False,
            signing_scheme="l1_action",
            required_credential="api_wallet",
            base_url="https://api.test.xyz",
            data_fidelity="synthetic",
            notes="Test note",
        )
        assert detail.supported is False
        assert detail.signing_scheme == "l1_action"
        assert detail.required_credential == "api_wallet"
        assert detail.base_url == "https://api.test.xyz"
        assert detail.data_fidelity == "synthetic"
        assert detail.notes == "Test note"

    def test_operation_detail_empty(self) -> None:
        detail = OperationDetail()
        assert detail.environments == {}

    def test_operation_detail_with_envs(self) -> None:
        detail = OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac"),
                "testnet": OperationEnvDetail(supported=False),
            }
        )
        assert detail.environments["mainnet"].signing_scheme == "hmac"
        assert detail.environments["testnet"].supported is False

    def test_source_capability_new_fields_default_empty(self) -> None:
        cap = SourceCapability(source="test-defaults", domains=[], crosscutting=[])
        assert cap.operation_details == {}
        assert cap.base_urls == {}
        assert cap.margin_model == {}


# ---------------------------------------------------------------------------
# Test: validate_operation() — happy path
# ---------------------------------------------------------------------------


class TestValidateOperationHappyPath:
    """validate_operation() returns correct OperationEnvDetail for valid combos."""

    def test_returns_detail_for_known_operation(self, _cap_with_details: SourceCapability) -> None:
        detail = validate_operation("test-detailed", "place_order", "mainnet")
        assert detail.signing_scheme == "hmac_sha256"
        assert detail.required_credential == "api_key"

    def test_returns_testnet_detail(self, _cap_with_details: SourceCapability) -> None:
        detail = validate_operation("test-detailed", "place_order", "testnet")
        assert detail.signing_scheme == "hmac_sha256"
        assert detail.data_fidelity == "synthetic"

    def test_returns_public_endpoint_detail(self, _cap_with_details: SourceCapability) -> None:
        detail = validate_operation("test-detailed", "ticker", "mainnet")
        assert detail.signing_scheme == "none"
        assert detail.required_credential == "none"


# ---------------------------------------------------------------------------
# Test: validate_operation() — UnsupportedOperationError
# ---------------------------------------------------------------------------


class TestValidateOperationUnsupported:
    """validate_operation() raises UnsupportedOperationError for blocked ops."""

    def test_raises_for_unsupported_env(self, _cap_with_details: SourceCapability) -> None:
        with pytest.raises(UnsupportedOperationError) as exc_info:
            validate_operation("test-detailed", "transfer", "testnet")

        err = exc_info.value
        assert err.source == "test-detailed"
        assert err.operation == "transfer"
        assert err.env == "testnet"
        assert "Transfer not available" in (err.notes or "")

    def test_error_message_includes_context(self, _cap_with_details: SourceCapability) -> None:
        with pytest.raises(UnsupportedOperationError) as exc_info:
            validate_operation("test-detailed", "transfer", "testnet")

        msg = str(exc_info.value)
        assert "test-detailed" in msg
        assert "transfer" in msg
        assert "testnet" in msg


# ---------------------------------------------------------------------------
# Test: validate_operation() — fallback to source-level
# ---------------------------------------------------------------------------


class TestValidateOperationFallback:
    """validate_operation() falls back to source-level when no operation_details."""

    def test_fallback_returns_empty_detail(self, _cap_no_details: SourceCapability) -> None:
        detail = validate_operation("test-no-details", "any_operation", "mainnet")
        assert detail.signing_scheme is None
        assert detail.required_credential is None

    def test_fallback_for_unknown_operation_on_detailed_source(self, _cap_with_details: SourceCapability) -> None:
        detail = validate_operation("test-detailed", "unknown_op", "mainnet")
        assert detail.signing_scheme is None

    def test_fallback_for_known_op_unknown_env(self, _cap_with_details: SourceCapability) -> None:
        detail = validate_operation("test-detailed", "ticker", "testnet")
        assert detail.signing_scheme is None


# ---------------------------------------------------------------------------
# Test: validate_operation() — unknown source
# ---------------------------------------------------------------------------


class TestValidateOperationUnknownSource:
    """validate_operation() raises CapabilityResolutionError for unknown sources."""

    def test_raises_for_unknown_source(self) -> None:
        with pytest.raises(CapabilityResolutionError):
            validate_operation("nonexistent-source-xyz", "place_order", "mainnet")


# ---------------------------------------------------------------------------
# Test: Real sources — Hyperliquid (most detailed)
# ---------------------------------------------------------------------------


class TestHyperliquidOperationDetails:
    """Validate Hyperliquid's operation_details are correctly populated."""

    def test_place_order_mainnet(self) -> None:
        detail = validate_operation("hyperliquid", "place_order", "mainnet")
        assert detail.signing_scheme == "l1_action"
        assert detail.required_credential == "api_wallet"

    def test_place_order_testnet(self) -> None:
        detail = validate_operation("hyperliquid", "place_order", "testnet")
        assert detail.signing_scheme == "l1_action"
        assert detail.required_credential == "api_wallet"
        assert detail.data_fidelity == "synthetic"

    def test_usd_class_transfer_blocked_on_testnet(self) -> None:
        with pytest.raises(UnsupportedOperationError) as exc_info:
            validate_operation("hyperliquid", "usd_class_transfer", "testnet")
        assert "API wallet cannot transfer" in (exc_info.value.notes or "")

    def test_usd_class_transfer_mainnet_needs_main_wallet(self) -> None:
        detail = validate_operation("hyperliquid", "usd_class_transfer", "mainnet")
        assert detail.signing_scheme == "user_signed"
        assert detail.required_credential == "main_wallet"

    def test_all_mids_public(self) -> None:
        detail = validate_operation("hyperliquid", "all_mids", "mainnet")
        assert detail.signing_scheme == "none"
        assert detail.required_credential == "none"

    def test_base_urls(self) -> None:
        from unified_api_contracts.registry.capability import resolve_capability

        cap = resolve_capability("hyperliquid")
        assert cap.base_urls["mainnet"] == "https://api.hyperliquid.xyz"
        assert cap.base_urls["testnet"] == "https://api.hyperliquid-testnet.xyz"

    def test_margin_model(self) -> None:
        from unified_api_contracts.registry.capability import resolve_capability

        cap = resolve_capability("hyperliquid")
        assert cap.margin_model["mainnet"] == "cross"
        assert cap.margin_model["testnet"] == "unified"


# ---------------------------------------------------------------------------
# Test: Real sources — cross-domain spot checks
# ---------------------------------------------------------------------------


class TestCrossDomainSpotChecks:
    """Spot-check operation_details for sources across different domains."""

    def test_binance_order_signing(self) -> None:
        detail = validate_operation("binance", "new_order", "mainnet")
        assert detail.signing_scheme == "hmac_sha256"
        assert detail.required_credential == "api_key"

    def test_aave_flash_loan_on_chain(self) -> None:
        detail = validate_operation("aave", "flash_loan", "mainnet")
        assert detail.signing_scheme == "on_chain"
        assert detail.required_credential == "wallet_private_key"

    def test_polymarket_eip712(self) -> None:
        detail = validate_operation("polymarket", "create_order", "mainnet")
        assert detail.signing_scheme == "eip712"
        assert detail.required_credential == "wallet_private_key"

    def test_ibkr_paper_trading_production_fidelity(self) -> None:
        detail = validate_operation("ibkr", "place_order", "testnet")
        assert detail.signing_scheme == "ib_gateway"
        assert detail.data_fidelity == "production"

    def test_defillama_no_auth(self) -> None:
        detail = validate_operation("defillama", "tvl", "mainnet")
        assert detail.signing_scheme == "none"
        assert detail.required_credential == "none"

    def test_kalshi_testnet_synthetic(self) -> None:
        detail = validate_operation("kalshi", "create_order", "testnet")
        assert detail.signing_scheme == "rsa_pkcs1v15_sha256"
        assert detail.data_fidelity == "synthetic"


# ---------------------------------------------------------------------------
# Test: Parametrized — all sources with operation_details bootstrap correctly
# ---------------------------------------------------------------------------


_SOURCES_WITH_DETAILS = [cap.source for cap in CAPABILITY_DECLARATIONS if cap.operation_details]


@pytest.mark.parametrize("source", _SOURCES_WITH_DETAILS)
def test_source_operation_details_resolvable(source: str) -> None:
    """Every source with operation_details must resolve without error."""
    from unified_api_contracts.registry.capability import resolve_capability

    cap = resolve_capability(source)
    assert cap.operation_details, f"{source} has empty operation_details after bootstrap"

    for op_name, op_detail in cap.operation_details.items():
        for env_name, env_detail in op_detail.environments.items():
            if env_detail.supported:
                result = validate_operation(source, op_name, env_name)
                assert result.supported is True, f"{source}.{op_name}/{env_name} should be supported"
            else:
                with pytest.raises(UnsupportedOperationError):
                    validate_operation(source, op_name, env_name)
