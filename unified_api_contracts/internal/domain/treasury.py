"""Treasury contracts: custody sources, endpoints, wallet key material.

Per ``wallet_treasury_client_flow_2026_05_10.md`` Phase 1.C + ``api_keys_wallets_accounts_readiness_2026_05_10.md``
Phase 3.B custody endpoint wiring.

Custody is abstracted per source: Copper MPC (co-managed), CEFFU (Binance institutional), DeFi hot wallet (HSM),
Sub-account (venue-specific). Pre-trade ping verifies endpoint reachability; withdrawal executor routes per source.

Credentials are NEVER inlined — always referenced by credential-registry id per
``interface-credential-convention.md`` § Credential Reference Pattern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class TreasurySource(StrEnum):
    """Closed-set treasury custody source.

    Routes custody pinger (pre-trade balance check) + withdrawal executor
    (execution-service integration).
    """

    COPPER = "COPPER"
    """Copper.co MPC signing. Co-managed key shards."""

    CEFFU = "CEFFU"
    """Binance institutional (CEFFU) API. Centralized Binance venue settlement."""

    DEFI_HOT_WALLET = "DEFI_HOT_WALLET"
    """DeFi hot wallet: private key in Secret Manager, envelope-encrypted via Cloud HSM
    per ``wallet_config.py`` SigningSurface.CLOUD_KMS_ENCRYPTED."""

    SUB_ACCOUNT_HYPERLIQUID = "SUB_ACCOUNT_HYPERLIQUID"
    """Hyperliquid sub-account. Routed through Hyperliquid REST API."""

    SUB_ACCOUNT_DRIFT = "SUB_ACCOUNT_DRIFT"
    """DRIFT Protocol sub-account. Routed through DRIFT on-chain contract."""

    SUB_ACCOUNT_DYDX = "SUB_ACCOUNT_DYDX"
    """dYdX v4 sub-account. Routed through dYdX v4 API."""


@dataclass(frozen=True)
class SubAccountId:
    """Sub-account identifier per venue.

    Used when TreasurySource is SUB_ACCOUNT_* and the venue itself manages
    account hierarchy (e.g., Hyperliquid sub-accounts are numerically indexed).
    """

    venue: str
    """Venue name (e.g., 'HYPERLIQUID', 'DRIFT', 'DYDX')."""

    subaccount_id: str | int
    """Venue-specific sub-account identifier (string for some venues, int for others)."""

    def __str__(self) -> str:
        return f"{self.venue}/{self.subaccount_id}"


@dataclass(frozen=True)
class CopperEndpoint:
    """Copper.co MPC custody endpoint + credential reference.

    Per-client Copper portfolio (co-managed key shards). Credentials reference credential-registry id.
    Pinger uses Copper SDK; executor uses same SDK for withdrawal signing.

    Per ``custody-providers.md`` § 2 Copper factory routing + 2026-05-10 execution-service
    Phase 3.B credential wiring.
    """

    portfolio_id: str
    """Copper portfolio ID (Copper-assigned). Never credential material."""

    api_key_id: str
    """Credential-registry id for Copper API key (NOT the key itself)."""

    webhook_secret_id: str = ""
    """Credential-registry id for webhook HMAC secret (for trade fills + balance updates).
    Empty if webhooks disabled."""

    is_live: bool = False
    """True for mainnet Copper; False for testnet."""

    ping_timeout_seconds: int = 30
    """Pre-trade ping timeout."""

    def vault_address_mainnet(self) -> str:
        """Return expected mainnet vault address (derived from portfolio_id; for pre-ping validation)."""
        return f"0x{self.portfolio_id.lstrip('0x')[:40]}" if self.portfolio_id else ""


@dataclass(frozen=True)
class CEFFUEndpoint:
    """Binance CEFFU (Centralized Exchange For Funds Users) endpoint.

    Institutional Binance account routing. Credentials reference credential-registry id.
    Executor uses CEFFU REST API (managed withdrawal + balance queries).

    Per ``custody-providers.md`` § 2 + master plan Group F item 19 (June-1 credential delivery).
    """

    ceffu_uid: str
    """CEFFU account UID assigned by Binance. Public; not a credential."""

    api_key_id: str
    """Credential-registry id for CEFFU API key (NOT the key itself)."""

    is_live: bool = False
    """True for mainnet Binance; False for testnet."""

    ping_timeout_seconds: int = 20
    """Pre-trade ping timeout (CEFFU API is typically faster than self-hosted custodians)."""

    supported_assets: frozenset[str] = field(default_factory=lambda: frozenset(["USDC", "USDT", "BNB"]))
    """Assets supported on CEFFU (informational; endpoint doesn't validate)."""


@dataclass(frozen=True)
class DefiWalletKeyMaterial:
    """DeFi hot wallet private key reference + chain assignment.

    Key lives in Secret Manager (envelope-encrypted via Cloud HSM).
    This class carries the Secret Manager reference + metadata only.

    Per ``wallet_config.py`` WalletProvisioningConfig + ``interface-credential-convention.md``
    § Credential Reference Pattern.
    """

    wallet_address: str
    """On-chain wallet address (0x... for EVM; different format for Solana)."""

    chain: str
    """Chain where wallet lives (e.g., 'ETHEREUM', 'SOLANA', 'ARBITRUM')."""

    private_key_secret_id: str
    """Secret Manager secret id holding envelope-encrypted private key
    (e.g., 'eth-trading-pk' or 'arn:aws:secretsmanager:...')."""

    kms_key_uri: str = ""
    """KMS CMK URI for envelope decryption. If empty, use default project CMK per cloud config."""

    public_key: str = ""
    """Optional: public key for validation. Mostly informational; Solana optional."""

    created_at: datetime = field(default_factory=datetime.utcnow)
    """Wallet creation / import timestamp."""

    last_rotated_at: datetime | None = None
    """Last key rotation (post-cutover cold-wallet rotation feature)."""

    is_testnet: bool = False
    """True if key is for testnet (never mix testnet + mainnet)."""

    def is_valid_for_live(self) -> bool:
        """Returns True if wallet is provisioned for live trading."""
        return not self.is_testnet and bool(self.wallet_address) and bool(self.private_key_secret_id)


@dataclass(frozen=True)
class CustodyPingResult:
    """Result of a pre-trade custody endpoint ping.

    Emitted by ``unified_trading_library.treasury.custody_pinger.CustodyPinger`` for each source.
    Failure here fires ``CUSTODY_DISCONNECT`` breaker per ``disaster_recovery_circuit_breakers_2026_05_10``.
    """

    source: TreasurySource
    """Which source was pinged."""

    is_reachable: bool
    """True if endpoint responded within timeout."""

    balance_native: Decimal | None = None
    """Balance in native token (USDC for most, ETH for some DeFi). None if unreachable."""

    balance_usd: Decimal | None = None
    """Converted USD balance (derived from price feed). None if unreachable."""

    as_of_timestamp: datetime | None = None
    """Server timestamp of balance query (may differ from local time)."""

    error_message: str = ""
    """If unreachable, human-readable error (rate-limited, network timeout, etc.)."""

    latency_ms: int = 0
    """Round-trip latency in milliseconds."""

    def summary(self) -> str:
        """Human-readable summary for logging."""
        if self.is_reachable:
            return f"{self.source.value}: {self.balance_usd or self.balance_native} USD/native, {self.latency_ms}ms"
        return f"{self.source.value}: UNREACHABLE ({self.error_message})"
