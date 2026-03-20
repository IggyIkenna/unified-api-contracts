"""Integration tests for resolve_venue_context() and compose_validation().

Validates full round-trip through the three registries:
  1. SourceCapability + operation_details (capability.py)
  2. SportsVenueType + SportsAuthMethod + CAPTCHA_RISK (sports_venue_constants.py)
  3. InstructionConstraint (instruction_constraints.py)

All tests bootstrap the real capability declarations (not mocks).
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry import (
    bootstrap_capabilities,
    compose_validation,
    resolve_venue_context,
)
from unified_api_contracts.registry.capability import (
    OperationEnvDetail,
    UnsupportedOperationError,
)
from unified_api_contracts.registry.instruction_constraints import (
    InstructionValidationError,
)
from unified_api_contracts.registry.venue_context import VenueContext


@pytest.fixture(autouse=True, scope="module")
def _bootstrap() -> None:
    """Register all built-in capability declarations once per module."""
    bootstrap_capabilities()


# ---------------------------------------------------------------------------
# resolve_venue_context() tests
# ---------------------------------------------------------------------------


class TestResolveVenueContextCLOB:
    """CLOB venue (CeFi): HYPERLIQUID."""

    def test_hyperliquid_execution_pattern(self) -> None:
        ctx = resolve_venue_context("HYPERLIQUID", "place_order", "mainnet")
        assert ctx.execution_pattern == "clob_api"

    def test_hyperliquid_signing_scheme(self) -> None:
        ctx = resolve_venue_context("HYPERLIQUID", "place_order", "mainnet")
        assert ctx.operation_env_detail is not None
        assert ctx.operation_env_detail.signing_scheme == "l1_action"

    def test_hyperliquid_margin_model(self) -> None:
        ctx = resolve_venue_context("HYPERLIQUID", "place_order", "mainnet")
        assert ctx.margin_model_value == "cross"

    def test_hyperliquid_base_url(self) -> None:
        ctx = resolve_venue_context("HYPERLIQUID", "place_order", "mainnet")
        assert ctx.base_url is not None
        assert "hyperliquid" in ctx.base_url

    def test_hyperliquid_venue_category(self) -> None:
        ctx = resolve_venue_context("HYPERLIQUID", "place_order", "mainnet")
        assert ctx.venue_category == "cefi"

    def test_hyperliquid_returns_venue_context_type(self) -> None:
        ctx = resolve_venue_context("HYPERLIQUID", "place_order", "mainnet")
        assert isinstance(ctx, VenueContext)


class TestResolveVenueContextDeFi:
    """DeFi venue: AAVE_V3."""

    def test_aave_v3_execution_pattern(self) -> None:
        ctx = resolve_venue_context("AAVE_V3", "supply", "mainnet")
        assert ctx.execution_pattern == "on_chain_tx"

    def test_aave_v3_venue_category(self) -> None:
        ctx = resolve_venue_context("AAVE_V3", "supply", "mainnet")
        assert ctx.venue_category == "defi"

    def test_aave_v3_signing_scheme(self) -> None:
        ctx = resolve_venue_context("AAVE_V3", "supply", "mainnet")
        assert ctx.operation_env_detail is not None
        assert ctx.operation_env_detail.signing_scheme == "on_chain"

    def test_aave_v3_required_credential(self) -> None:
        ctx = resolve_venue_context("AAVE_V3", "supply", "mainnet")
        assert ctx.operation_env_detail is not None
        assert ctx.operation_env_detail.required_credential == "wallet_private_key"


class TestResolveVenueContextWebScraper:
    """Web scraper venue (sports bookmaker web): DRAFTKINGS."""

    def test_draftkings_execution_pattern(self) -> None:
        ctx = resolve_venue_context("DRAFTKINGS")
        assert ctx.execution_pattern == "web_scraper"

    def test_draftkings_captcha_risk(self) -> None:
        ctx = resolve_venue_context("DRAFTKINGS")
        assert ctx.captcha_risk is True

    def test_draftkings_sports_venue_type(self) -> None:
        ctx = resolve_venue_context("DRAFTKINGS")
        assert ctx.sports_venue_type is not None
        assert ctx.sports_venue_type == "web_scraper"

    def test_draftkings_sports_auth_method(self) -> None:
        ctx = resolve_venue_context("DRAFTKINGS")
        assert ctx.sports_auth_method is not None
        assert ctx.sports_auth_method == "login_credentials"


class TestResolveVenueContextSportsExchange:
    """Sports exchange: BETFAIR."""

    def test_betfair_execution_pattern(self) -> None:
        ctx = resolve_venue_context("BETFAIR", "place_orders", "mainnet")
        assert ctx.execution_pattern == "clob_api"

    def test_betfair_sports_venue_type(self) -> None:
        ctx = resolve_venue_context("BETFAIR")
        assert ctx.sports_venue_type == "exchange_api"

    def test_betfair_supported_market_types(self) -> None:
        ctx = resolve_venue_context("BETFAIR")
        assert len(ctx.supported_market_types) > 0, "BETFAIR should have supported market types"

    def test_betfair_venue_category(self) -> None:
        ctx = resolve_venue_context("BETFAIR")
        assert ctx.venue_category == "sports"

    def test_betfair_auth_method(self) -> None:
        ctx = resolve_venue_context("BETFAIR")
        assert ctx.sports_auth_method == "session_token"


class TestResolveVenueContextDataOnly:
    """Data-only venue: yahoo_finance."""

    def test_yahoo_finance_execution_pattern(self) -> None:
        ctx = resolve_venue_context("yahoo_finance", "ohlcv", "mainnet")
        assert ctx.execution_pattern == "data_only"

    def test_yahoo_finance_no_sports_metadata(self) -> None:
        ctx = resolve_venue_context("yahoo_finance")
        assert ctx.sports_venue_type is None
        assert ctx.captcha_risk is False

    def test_yahoo_finance_base_url(self) -> None:
        ctx = resolve_venue_context("yahoo_finance", "ohlcv", "mainnet")
        assert ctx.base_url is not None
        assert "yahoo" in ctx.base_url


class TestResolveVenueContextIBKRPaper:
    """IBKR paper trading (testnet)."""

    def test_ibkr_paper_execution_pattern(self) -> None:
        ctx = resolve_venue_context("IBKR", "place_order", "testnet")
        assert ctx.execution_pattern == "ib_gateway"

    def test_ibkr_paper_data_fidelity(self) -> None:
        ctx = resolve_venue_context("IBKR", "place_order", "testnet")
        assert ctx.operation_env_detail is not None
        assert ctx.operation_env_detail.data_fidelity == "production"

    def test_ibkr_supports_testnet(self) -> None:
        ctx = resolve_venue_context("IBKR", "place_order", "testnet")
        assert ctx.supports_testnet is True


class TestResolveVenueContextUnknownVenue:
    """Unknown venue: graceful degradation with defaults, no crash."""

    def test_unknown_venue_returns_venue_context(self) -> None:
        ctx = resolve_venue_context("TOTALLY_UNKNOWN_VENUE_XYZ")
        assert isinstance(ctx, VenueContext)

    def test_unknown_venue_has_defaults(self) -> None:
        ctx = resolve_venue_context("TOTALLY_UNKNOWN_VENUE_XYZ")
        assert ctx.venue == "TOTALLY_UNKNOWN_VENUE_XYZ"
        assert ctx.venue_category is None
        assert ctx.sports_venue_type is None
        assert ctx.captcha_risk is False
        assert ctx.operation_env_detail is None

    def test_unknown_venue_execution_pattern(self) -> None:
        ctx = resolve_venue_context("TOTALLY_UNKNOWN_VENUE_XYZ")
        assert ctx.execution_pattern == "data_only"


# ---------------------------------------------------------------------------
# compose_validation() tests
# ---------------------------------------------------------------------------


class TestComposeValidationHappyPath:
    """Compose validation: structural + runtime validation in one call."""

    def test_trade_hyperliquid_limit_perpetual_mainnet(self) -> None:
        """TRADE + HYPERLIQUID + LIMIT + PERPETUAL + mainnet returns l1_action signing."""
        result = compose_validation(
            venue="HYPERLIQUID",
            instruction_type="TRADE",
            operation="place_order",
            env="mainnet",
            order_type="LIMIT",
            instrument_type="PERPETUAL",
        )
        assert isinstance(result, OperationEnvDetail)
        assert result.signing_scheme == "l1_action"
        assert result.required_credential == "api_wallet"

    def test_zero_alpha_aave_v3_market_lending_mainnet(self) -> None:
        """ZERO_ALPHA + AAVE_V3 + MARKET + LENDING + mainnet returns on_chain signing."""
        result = compose_validation(
            venue="AAVE_V3",
            instruction_type="ZERO_ALPHA",
            operation="supply",
            env="mainnet",
            order_type="MARKET",
            instrument_type="LENDING",
        )
        assert isinstance(result, OperationEnvDetail)
        assert result.signing_scheme == "on_chain"
        assert result.required_credential == "wallet_private_key"


class TestComposeValidationSwapUniswap:
    """SWAP + UNISWAPV3_ETH: structural validation passes, runtime depends on source resolution.

    UNISWAPV3-ETH lowercases to "uniswapv3_eth"; the capability source is "uniswap".
    The alias resolution strips the "eth" suffix yielding "uniswapv3", which still
    doesn't match "uniswap". This means compose_validation raises CapabilityResolutionError.
    We test that structural validation (SWAP + MARKET + POOL + defi) passes by verifying
    the error is CapabilityResolutionError (not InstructionValidationError).
    """

    def test_swap_uniswap_pool_market_raises_capability_error(self) -> None:
        """SWAP + UNISWAPV3-ETH + MARKET + POOL + mainnet raises CapabilityResolutionError.

        Structural validation passes (SWAP allows MARKET, POOL, defi), but
        the source alias "uniswapv3_eth" does not resolve to a registered capability.
        """
        from unified_api_contracts.registry.capability import CapabilityResolutionError

        with pytest.raises(CapabilityResolutionError):
            compose_validation(
                venue="UNISWAPV3-ETH",
                instruction_type="SWAP",
                operation="swap_events",
                env="mainnet",
                order_type="MARKET",
                instrument_type="POOL",
            )


class TestComposeValidationUnsupportedOperation:
    """compose_validation raises UnsupportedOperationError for unsupported ops."""

    def test_hyperliquid_usd_class_transfer_testnet_raises(self) -> None:
        """TRADE + HYPERLIQUID + usd_class_transfer + testnet raises UnsupportedOperationError."""
        with pytest.raises(UnsupportedOperationError) as exc_info:
            compose_validation(
                venue="HYPERLIQUID",
                instruction_type="TRADE",
                operation="usd_class_transfer",
                env="testnet",
                order_type="LIMIT",
                instrument_type="PERPETUAL",
            )
        err = exc_info.value
        assert err.source == "hyperliquid"
        assert err.operation == "usd_class_transfer"
        assert err.env == "testnet"


class TestComposeValidationInstructionConstraintViolation:
    """compose_validation raises InstructionValidationError for invalid combos."""

    def test_trade_pool_instrument_type_raises(self) -> None:
        """TRADE + HYPERLIQUID + LIMIT + POOL raises InstructionValidationError.

        POOL is not in TRADE's allowed instrument_types.
        """
        with pytest.raises(InstructionValidationError) as exc_info:
            compose_validation(
                venue="HYPERLIQUID",
                instruction_type="TRADE",
                operation="place_order",
                env="mainnet",
                order_type="LIMIT",
                instrument_type="POOL",
            )
        err = exc_info.value
        assert err.instruction_type == "TRADE"
        assert err.field == "instrument_type"
        assert err.value == "POOL"


class TestComposeValidationPredictionBet:
    """PREDICTION_BET + KALSHI + LIMIT + PREDICTION_MARKET + testnet."""

    def test_prediction_bet_kalshi_testnet(self) -> None:
        """Returns rsa_pkcs1v15_sha256 signing with synthetic data."""
        result = compose_validation(
            venue="KALSHI",
            instruction_type="PREDICTION_BET",
            operation="create_order",
            env="testnet",
            order_type="LIMIT",
            instrument_type="PREDICTION_MARKET",
        )
        assert isinstance(result, OperationEnvDetail)
        assert result.signing_scheme == "rsa_pkcs1v15_sha256"
        assert result.data_fidelity == "synthetic"


# ---------------------------------------------------------------------------
# Parametrized cross-cutting tests
# ---------------------------------------------------------------------------


class TestResolveVenueContextParametrized:
    """Parametrized tests across multiple venue types."""

    @pytest.mark.parametrize(
        ("venue", "expected_category"),
        [
            ("HYPERLIQUID", "cefi"),
            ("AAVE_V3", "defi"),
            ("UNISWAPV3-ETH", "defi"),
            ("BETFAIR", "sports"),
            ("DRAFTKINGS", "sports"),
            ("KALSHI", "sports"),
        ],
    )
    def test_venue_category_mapping(self, venue: str, expected_category: str) -> None:
        ctx = resolve_venue_context(venue)
        assert ctx.venue_category == expected_category

    @pytest.mark.parametrize(
        ("venue", "expected_pattern"),
        [
            ("HYPERLIQUID", "clob_api"),
            ("AAVE_V3", "on_chain_tx"),
            ("DRAFTKINGS", "web_scraper"),
            ("BETFAIR", "clob_api"),
        ],
    )
    def test_execution_pattern_no_operation(self, venue: str, expected_pattern: str) -> None:
        """Execution pattern derivation without specifying an operation."""
        ctx = resolve_venue_context(venue)
        assert ctx.execution_pattern == expected_pattern

    @pytest.mark.parametrize(
        ("venue", "operation", "env", "expected_signing"),
        [
            ("HYPERLIQUID", "place_order", "mainnet", "l1_action"),
            ("HYPERLIQUID", "place_order", "testnet", "l1_action"),
            ("AAVE_V3", "supply", "mainnet", "on_chain"),
            ("IBKR", "place_order", "mainnet", "ib_gateway"),
            ("IBKR", "place_order", "testnet", "ib_gateway"),
        ],
    )
    def test_signing_scheme_by_venue_operation_env(
        self, venue: str, operation: str, env: str, expected_signing: str
    ) -> None:
        ctx = resolve_venue_context(venue, operation, env)
        assert ctx.operation_env_detail is not None
        assert ctx.operation_env_detail.signing_scheme == expected_signing
