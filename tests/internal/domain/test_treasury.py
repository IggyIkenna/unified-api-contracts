"""Unit tests for treasury contracts."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from unified_api_contracts.internal.domain.treasury import (
    CEFFUEndpoint,
    CopperEndpoint,
    CustodyPingResult,
    DefiWalletKeyMaterial,
    SubAccountId,
    TreasurySource,
)


class TestTreasurySource:
    """Test TreasurySource enum."""

    def test_all_sources_defined(self) -> None:
        """Verify all required treasury sources are defined."""
        # SUB_ACCOUNT_DRIFT removed 2026-07-16 (operator ruling: all Solana
        # perp DEXes dropped except Jupiter, not integrated).
        expected = {
            "COPPER",
            "CEFFU",
            "DEFI_HOT_WALLET",
            "SUB_ACCOUNT_HYPERLIQUID",
            "SUB_ACCOUNT_DYDX",
        }
        actual = {source.value for source in TreasurySource}
        assert actual == expected

    def test_source_values(self) -> None:
        """Verify source values match their names."""
        assert TreasurySource.COPPER.value == "COPPER"
        assert TreasurySource.CEFFU.value == "CEFFU"
        assert TreasurySource.DEFI_HOT_WALLET.value == "DEFI_HOT_WALLET"
        assert TreasurySource.SUB_ACCOUNT_HYPERLIQUID.value == "SUB_ACCOUNT_HYPERLIQUID"
        assert TreasurySource.SUB_ACCOUNT_DYDX.value == "SUB_ACCOUNT_DYDX"

    def test_source_is_strenum(self) -> None:
        """Verify TreasurySource is a StrEnum."""
        assert isinstance(TreasurySource.COPPER, str)
        assert isinstance(TreasurySource.DEFI_HOT_WALLET, str)


class TestSubAccountId:
    """Test SubAccountId dataclass."""

    def test_subaccount_string_id(self) -> None:
        """Create sub-account with string id."""
        sub = SubAccountId(venue="HYPERLIQUID", subaccount_id="subaccount-uuid-12345")
        assert sub.venue == "HYPERLIQUID"
        assert sub.subaccount_id == "subaccount-uuid-12345"

    def test_subaccount_int_id(self) -> None:
        """Create sub-account with integer id."""
        sub = SubAccountId(venue="DYDX", subaccount_id=42)
        assert sub.venue == "DYDX"
        assert sub.subaccount_id == 42

    def test_subaccount_string_representation(self) -> None:
        """Verify __str__ formatting."""
        sub = SubAccountId(venue="DYDX", subaccount_id="dydx-acct-1")
        assert str(sub) == "DYDX/dydx-acct-1"

    def test_subaccount_frozen(self) -> None:
        """Verify SubAccountId is frozen."""
        sub = SubAccountId(venue="HYPERLIQUID", subaccount_id=1)
        with pytest.raises(AttributeError):
            sub.venue = "DYDX"


class TestCopperEndpoint:
    """Test CopperEndpoint dataclass."""

    def test_minimal_copper_endpoint(self) -> None:
        """Create minimal Copper endpoint."""
        ep = CopperEndpoint(
            portfolio_id="copper-portfolio-123",
            api_key_id="cred-key-copper",
        )
        assert ep.portfolio_id == "copper-portfolio-123"
        assert ep.api_key_id == "cred-key-copper"
        assert ep.webhook_secret_id == ""
        assert not ep.is_live
        assert ep.ping_timeout_seconds == 30

    def test_copper_endpoint_live(self) -> None:
        """Create Copper endpoint for mainnet."""
        ep = CopperEndpoint(
            portfolio_id="copper-prod",
            api_key_id="prod-key",
            webhook_secret_id="webhook-secret-prod",
            is_live=True,
        )
        assert ep.is_live
        assert ep.webhook_secret_id == "webhook-secret-prod"

    def test_copper_endpoint_credentials_by_reference(self) -> None:
        """Verify Copper endpoint uses credential registry id, never inlines secrets."""
        ep = CopperEndpoint(
            portfolio_id="port-1",
            api_key_id="registry-ref-12345",
        )
        # Only api_key_id (registry reference) is exposed, never actual secrets.
        assert ep.api_key_id == "registry-ref-12345"
        assert not hasattr(ep, "actual_api_key")
        assert not hasattr(ep, "secret")

    def test_copper_endpoint_custom_timeout(self) -> None:
        """Create Copper endpoint with custom ping timeout."""
        ep = CopperEndpoint(
            portfolio_id="port-1",
            api_key_id="key-1",
            ping_timeout_seconds=60,
        )
        assert ep.ping_timeout_seconds == 60

    def test_copper_endpoint_vault_address_derivation(self) -> None:
        """Verify vault_address_mainnet() derives address from portfolio_id."""
        ep = CopperEndpoint(
            portfolio_id="0x1234567890abcdef1234567890abcdef12345678",
            api_key_id="key-1",
        )
        addr = ep.vault_address_mainnet()
        assert addr.startswith("0x")
        assert len(addr) == 42  # 0x + 40 hex chars

    def test_copper_endpoint_frozen(self) -> None:
        """Verify Copper endpoint is frozen."""
        ep = CopperEndpoint(
            portfolio_id="port-1",
            api_key_id="key-1",
        )
        with pytest.raises(AttributeError):
            ep.is_live = True


class TestCEFFUEndpoint:
    """Test CEFFUEndpoint dataclass."""

    def test_minimal_ceffu_endpoint(self) -> None:
        """Create minimal CEFFU endpoint."""
        ep = CEFFUEndpoint(
            ceffu_uid="binance-uid-123",
            api_key_id="cred-ceffu-key",
        )
        assert ep.ceffu_uid == "binance-uid-123"
        assert ep.api_key_id == "cred-ceffu-key"
        assert not ep.is_live
        assert ep.ping_timeout_seconds == 20

    def test_ceffu_endpoint_live(self) -> None:
        """Create CEFFU endpoint for mainnet Binance."""
        ep = CEFFUEndpoint(
            ceffu_uid="uid-prod",
            api_key_id="prod-key",
            is_live=True,
        )
        assert ep.is_live

    def test_ceffu_endpoint_supported_assets(self) -> None:
        """Verify CEFFU endpoint asset support."""
        ep = CEFFUEndpoint(
            ceffu_uid="uid-1",
            api_key_id="key-1",
            supported_assets=frozenset(["USDC", "BTC", "ETH"]),
        )
        assert "USDC" in ep.supported_assets
        assert "BTC" in ep.supported_assets
        assert "ETH" in ep.supported_assets
        assert "SOL" not in ep.supported_assets

    def test_ceffu_endpoint_default_assets(self) -> None:
        """Verify default supported assets."""
        ep = CEFFUEndpoint(
            ceffu_uid="uid-1",
            api_key_id="key-1",
        )
        assert "USDC" in ep.supported_assets
        assert "USDT" in ep.supported_assets
        assert "BNB" in ep.supported_assets

    def test_ceffu_endpoint_credentials_by_reference(self) -> None:
        """Verify CEFFU endpoint uses credential registry id."""
        ep = CEFFUEndpoint(
            ceffu_uid="uid-1",
            api_key_id="registry-ceffu-key-ref",
        )
        assert ep.api_key_id == "registry-ceffu-key-ref"
        assert not hasattr(ep, "actual_secret")

    def test_ceffu_endpoint_custom_timeout(self) -> None:
        """Create CEFFU endpoint with custom timeout (usually faster)."""
        ep = CEFFUEndpoint(
            ceffu_uid="uid-1",
            api_key_id="key-1",
            ping_timeout_seconds=10,
        )
        assert ep.ping_timeout_seconds == 10

    def test_ceffu_endpoint_frozen(self) -> None:
        """Verify CEFFU endpoint is frozen."""
        ep = CEFFUEndpoint(
            ceffu_uid="uid-1",
            api_key_id="key-1",
        )
        with pytest.raises(AttributeError):
            ep.is_live = True


class TestDefiWalletKeyMaterial:
    """Test DefiWalletKeyMaterial dataclass."""

    def test_minimal_defi_wallet(self) -> None:
        """Create minimal DeFi wallet key material."""
        wallet = DefiWalletKeyMaterial(
            wallet_address="0x1234567890abcdef1234567890abcdef12345678",
            chain="ETHEREUM",
            private_key_secret_id="eth-pk-secret-uuid",
        )
        assert wallet.wallet_address == "0x1234567890abcdef1234567890abcdef12345678"
        assert wallet.chain == "ETHEREUM"
        assert wallet.private_key_secret_id == "eth-pk-secret-uuid"
        assert wallet.kms_key_uri == ""
        assert not wallet.is_testnet

    def test_defi_wallet_with_kms_uri(self) -> None:
        """Create DeFi wallet with custom KMS URI."""
        wallet = DefiWalletKeyMaterial(
            wallet_address="0xabc123",
            chain="ARBITRUM",
            private_key_secret_id="arb-pk",
            kms_key_uri="projects/123/locations/asia-northeast1/keyRings/wallets/cryptoKeys/eth-v1",
        )
        assert wallet.kms_key_uri == "projects/123/locations/asia-northeast1/keyRings/wallets/cryptoKeys/eth-v1"

    def test_defi_wallet_solana(self) -> None:
        """Create DeFi wallet for Solana."""
        wallet = DefiWalletKeyMaterial(
            wallet_address="9B5X3cg7oERKZfuNrVSe2HTDkGSLcBxJ2vAwohXMV4s",
            chain="SOLANA",
            private_key_secret_id="sol-pk",
        )
        assert wallet.chain == "SOLANA"
        assert wallet.wallet_address.startswith("9")  # Solana addresses start with 9

    def test_defi_wallet_testnet(self) -> None:
        """Create DeFi wallet for testnet."""
        wallet = DefiWalletKeyMaterial(
            wallet_address="0xtest123",
            chain="ETHEREUM",
            private_key_secret_id="eth-pk-testnet",
            is_testnet=True,
        )
        assert wallet.is_testnet
        assert not wallet.is_valid_for_live()

    def test_defi_wallet_is_valid_for_live(self) -> None:
        """Verify is_valid_for_live() checks for mainnet + full provisioning."""
        # Mainnet wallet = valid for live.
        mainnet = DefiWalletKeyMaterial(
            wallet_address="0xmainnet123",
            chain="ETHEREUM",
            private_key_secret_id="eth-pk",
            is_testnet=False,
        )
        assert mainnet.is_valid_for_live()

        # Testnet wallet = not valid for live.
        testnet = DefiWalletKeyMaterial(
            wallet_address="0xtest123",
            chain="ETHEREUM",
            private_key_secret_id="eth-pk-test",
            is_testnet=True,
        )
        assert not testnet.is_valid_for_live()

        # Missing fields = not valid for live.
        incomplete = DefiWalletKeyMaterial(
            wallet_address="",  # Empty address
            chain="ETHEREUM",
            private_key_secret_id="eth-pk",
            is_testnet=False,
        )
        assert not incomplete.is_valid_for_live()

    def test_defi_wallet_key_rotation(self) -> None:
        """Test key rotation timestamp tracking."""
        created = datetime.now(UTC)
        rotated = created + timedelta(days=30)
        wallet = DefiWalletKeyMaterial(
            wallet_address="0xaddr",
            chain="ETHEREUM",
            private_key_secret_id="eth-pk",
            created_at=created,
            last_rotated_at=rotated,
        )
        assert wallet.last_rotated_at == rotated
        assert wallet.last_rotated_at > wallet.created_at

    def test_defi_wallet_no_secret_inlined(self) -> None:
        """Verify DeFi wallet never inlines actual private key."""
        wallet = DefiWalletKeyMaterial(
            wallet_address="0xaddr",
            chain="ETHEREUM",
            private_key_secret_id="secret-registry-uuid",
        )
        # Only secret_id (registry reference) is exposed.
        assert wallet.private_key_secret_id == "secret-registry-uuid"
        assert not hasattr(wallet, "private_key")
        assert not hasattr(wallet, "secret_key")

    def test_defi_wallet_frozen(self) -> None:
        """Verify DeFi wallet key material is frozen."""
        wallet = DefiWalletKeyMaterial(
            wallet_address="0xaddr",
            chain="ETHEREUM",
            private_key_secret_id="eth-pk",
        )
        with pytest.raises(AttributeError):
            wallet.chain = "SOLANA"


class TestCustodyPingResult:
    """Test CustodyPingResult dataclass."""

    def test_successful_ping_copper(self) -> None:
        """Test successful ping to Copper endpoint."""
        result = CustodyPingResult(
            source=TreasurySource.COPPER,
            is_reachable=True,
            balance_native=Decimal("50000"),
            balance_usd=Decimal("50000"),
            as_of_timestamp=datetime.now(UTC),
            latency_ms=42,
        )
        assert result.is_reachable
        assert result.balance_native == Decimal("50000")
        assert result.balance_usd == Decimal("50000")
        assert result.latency_ms == 42

    def test_failed_ping(self) -> None:
        """Test failed ping."""
        result = CustodyPingResult(
            source=TreasurySource.CEFFU,
            is_reachable=False,
            error_message="rate_limited: 429 Too Many Requests",
        )
        assert not result.is_reachable
        assert result.balance_native is None
        assert result.balance_usd is None
        assert result.error_message == "rate_limited: 429 Too Many Requests"

    def test_ping_timeout(self) -> None:
        """Test timeout scenario."""
        result = CustodyPingResult(
            source=TreasurySource.DEFI_HOT_WALLET,
            is_reachable=False,
            error_message="timeout: exceeds 30s limit",
            latency_ms=30000,
        )
        assert not result.is_reachable
        assert "timeout" in result.error_message

    def test_ping_summary_successful(self) -> None:
        """Test summary() for successful ping."""
        result = CustodyPingResult(
            source=TreasurySource.COPPER,
            is_reachable=True,
            balance_usd=Decimal("123456.78"),
            latency_ms=75,
        )
        summary = result.summary()
        assert "COPPER" in summary
        assert "123456.78" in summary
        assert "75ms" in summary

    def test_ping_summary_failed(self) -> None:
        """Test summary() for failed ping."""
        result = CustodyPingResult(
            source=TreasurySource.CEFFU,
            is_reachable=False,
            error_message="connection refused",
        )
        summary = result.summary()
        assert "CEFFU" in summary
        assert "UNREACHABLE" in summary
        assert "connection refused" in summary

    def test_ping_summary_with_native_balance_only(self) -> None:
        """Test summary with only native balance (no USD conversion)."""
        result = CustodyPingResult(
            source=TreasurySource.DEFI_HOT_WALLET,
            is_reachable=True,
            balance_native=Decimal("10.5"),
            balance_usd=None,
            latency_ms=20,
        )
        summary = result.summary()
        assert "10.5" in summary  # Native balance should be in summary

    def test_ping_frozen(self) -> None:
        """Verify ping result is frozen."""
        result = CustodyPingResult(
            source=TreasurySource.COPPER,
            is_reachable=True,
        )
        with pytest.raises(AttributeError):
            result.is_reachable = False


class TestCustodySourceIntegration:
    """Integration tests for custody source workflows."""

    def test_multiple_sources_for_client_portfolio(self) -> None:
        """Verify a client can have multiple custody sources."""
        sources = {
            TreasurySource.COPPER: CopperEndpoint(
                portfolio_id="copper-main",
                api_key_id="copper-key",
            ),
            TreasurySource.CEFFU: CEFFUEndpoint(
                ceffu_uid="binance-uid",
                api_key_id="binance-key",
            ),
            TreasurySource.DEFI_HOT_WALLET: DefiWalletKeyMaterial(
                wallet_address="0xdefi123",
                chain="ETHEREUM",
                private_key_secret_id="defi-pk",
            ),
        }
        assert len(sources) == 3
        assert TreasurySource.COPPER in sources
        assert TreasurySource.CEFFU in sources
        assert TreasurySource.DEFI_HOT_WALLET in sources

    def test_ping_results_aggregate(self) -> None:
        """Test aggregating ping results from multiple sources."""
        pings = [
            CustodyPingResult(
                source=TreasurySource.COPPER,
                is_reachable=True,
                balance_usd=Decimal("100000"),
            ),
            CustodyPingResult(
                source=TreasurySource.CEFFU,
                is_reachable=True,
                balance_usd=Decimal("50000"),
            ),
            CustodyPingResult(
                source=TreasurySource.DEFI_HOT_WALLET,
                is_reachable=True,
                balance_usd=Decimal("75000"),
            ),
        ]
        total_usd = sum((p.balance_usd or Decimal("0")) for p in pings if p.is_reachable)
        assert total_usd == Decimal("225000")
