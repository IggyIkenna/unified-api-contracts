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


@dataclass(frozen=True)
class WithdrawalApprovalRule:
    """Approval rule for a withdrawal from a specific TreasurySource.

    Per ``wallet_treasury_client_flow_2026_05_10.md`` Phase 5.C.

    Defines how many approvals are required and who may approve.
    The rule applies to withdrawals above ``threshold_amount_usd``
    (exclusive); amounts at or below require a single operator.

    Fields:
        treasury_source: Which custody source this rule governs.
        amount_bucket: Human label ('SMALL' / 'MEDIUM' / 'LARGE') — informational only.
        threshold_amount_usd: Amount above which quorum is required.
            Amounts <= threshold require only 1 approver.
        required_approvers: Number of approvals N needed (N-of-M quorum).
        approver_pool: Set of operator IDs eligible to approve (pool size M >= required_approvers).
    """

    treasury_source: TreasurySource
    amount_bucket: str
    threshold_amount_usd: Decimal
    required_approvers: int
    approver_pool: frozenset[str]

    def __post_init__(self) -> None:
        if self.required_approvers < 1:
            raise ValueError(f"required_approvers must be >= 1, got {self.required_approvers}")
        if len(self.approver_pool) < self.required_approvers:
            raise ValueError(
                f"approver_pool size {len(self.approver_pool)} < required_approvers {self.required_approvers}"
            )
        if self.threshold_amount_usd < Decimal("0"):
            raise ValueError(f"threshold_amount_usd must be >= 0, got {self.threshold_amount_usd}")

    def approvers_required_for(self, amount_usd: Decimal) -> int:
        """Return number of approvals required for a given withdrawal amount."""
        if amount_usd <= self.threshold_amount_usd:
            return 1
        return self.required_approvers


# ---------------------------------------------------------------------------
# Treasury rollup schemas — Phase 3.D canonical endpoint
# Per ``api_keys_wallets_accounts_readiness_2026_05_10.md`` Phase 3.D
# Owned by: deployment-api `/api/treasury/rollup` + `/treasury/nav`
# Consumer: ``wallet_treasury_client_flow_2026_05_10.md`` Phase 6.A
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TreasurySourceBalance:
    """Balance from one custody source, as-of a specific timestamp.

    Used inside :class:`TreasuryRollupResponse` to show per-source breakdown.
    Missing source (Copper/CEFFU stub) carries ``is_stub=True`` + BLOCK_CRITICAL
    policy annotation to signal the consumer that values are demo placeholders
    until real client credentials land.
    """

    source: TreasurySource
    """Which custody source provided this balance."""

    balance_usd: Decimal
    """Total USD value at this source (converted from native via mark price)."""

    is_reachable: bool
    """Whether the source responded; False = balance derived from cached value or zero."""

    is_stub: bool = False
    """True when source SDK is not yet wired (Copper/CEFFU pre-June-1).
    Stub data is canned + should not be used for trading decisions.
    Callers MUST check this flag; BLOCK_CRITICAL policy fires if is_stub=True
    AND source is queried from a live-trading context."""

    as_of_timestamp: datetime | None = None
    """Server-reported timestamp of the balance query. None when unreachable."""

    error_message: str = ""
    """If not reachable, error reason for display."""


@dataclass(frozen=True)
class TreasuryRollupResponse:
    """Multi-source unified NAV — canonical treasury rollup.

    Combines all four source axes into a single total_nav_usd:
    - COPPER:             Copper MPC custody balance
    - CEFFU:              Binance institutional custody balance
    - Venue margin:       CeFi perp-venue margin (Binance, Bybit, OKX, etc.)
    - On-chain wallets:   DeFi hot-wallet balances per chain

    Per ``api_keys_wallets_accounts_readiness_2026_05_10.md`` Phase 3.D.

    ``wallet_treasury_client_flow_2026_05_10.md`` Phase 6.A consumes this
    and adds client-attribution on top (per-client slice of total_nav_usd).
    """

    total_nav_usd: Decimal
    """Sum of all source balances — the canonical single-number NAV."""

    per_source: list[TreasurySourceBalance]
    """Per-source breakdown ordered by TreasurySource enum value."""

    asof_timestamp: datetime
    """Timestamp of the rollup computation (UTC). Use per-source as_of_timestamp
    for source-level freshness."""

    reconciliation_status: str
    """One of: 'ok' | 'partial' (some sources unreachable) | 'stub' (any source is_stub=True)."""

    has_stubs: bool = False
    """True if any source returned stub data — downstream callers must not use for trading."""

    source_count: int = 0
    """Number of sources with is_reachable=True (out of total configured sources)."""


@dataclass(frozen=True)
class TreasuryNAVByClient:
    """Per-client NAV view — source-axis rollup filtered by client_id.

    Consumed by ``wallet_treasury_client_flow_2026_05_10.md`` Phase 6.A
    ``GET /api/clients/{id}/treasury`` which overlays client-attribution on
    top of the canonical multi-source rollup.

    Attribution logic: each source balance proportional to client's AUM share
    relative to total fund AUM. For demo MVP: single-client, attribution=100%.
    Multi-client proportional attribution is post-cutover.
    """

    client_id: str
    """Client identifier (matches client-reporting-api client_id)."""

    nav_usd: Decimal
    """Client's proportional share of total_nav_usd."""

    attribution_pct: Decimal
    """Fraction of total fund NAV attributed to this client (0–100)."""

    per_source: list[TreasurySourceBalance]
    """Per-source balances scaled by attribution_pct."""

    asof_timestamp: datetime
    """Timestamp of the per-client computation."""

    is_demo_single_client: bool = False
    """True when multi-client attribution is not yet live (May-23 MVP).
    Post-cutover this flips to False once real multi-client proportional
    attribution is wired. Successor plan:
    ``wallet_treasury_client_flow_2026_05_10.md`` Phase 6.A."""


# ---------------------------------------------------------------------------
# Per-client CONSUMER view schemas
# Used by deployment-api Phase 6.A + 6.B endpoints.
# Built on top of TreasuryRollupResponse (Phase 3.D canonical owner).
# Per wallet_treasury_client_flow_2026_05_10.md Phase 6.A + 6.B.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TreasurySourceAttribution:
    """Per-source NAV attribution for a single client.

    Derived from the canonical rollup: each source balance is multiplied by
    the client's allocation share (``allocation_pct / 100``).

    Per ``wallet_treasury_client_flow_2026_05_10.md`` Phase 6.A.
    """

    source: TreasurySource
    """Which custody source this row describes."""

    source_total_nav_usd: Decimal
    """Total NAV for this source across ALL clients (from canonical rollup)."""

    client_allocation_pct: Decimal
    """Client's effective allocation share for this source (0-100)."""

    client_nav_usd: Decimal
    """Client's attributed NAV = source_total_nav_usd × (client_allocation_pct / 100)."""

    source_reachable: bool = True
    """True if the custody endpoint was reachable at rollup time."""

    is_stub: bool = False
    """True when source SDK is not yet wired (propagated from TreasuryRollupResponse)."""


@dataclass(frozen=True)
class ClientTreasuryView:
    """Per-client treasury attribution view.

    Consumes ``GET /api/treasury/rollup`` (Phase 3.D canonical endpoint owned by
    ``api_keys_wallets_accounts_readiness_2026_05_10.md``) and filters/scales by
    the client's allocation share.

    NAV reconciliation invariant:
        sum(v.total_nav_usd for v in [all client views]) == TreasuryRollupResponse.total_nav_usd

    This endpoint is a CONSUMER ROLE — it does NOT re-fetch source balances.
    Per ``wallet_treasury_client_flow_2026_05_10.md`` Phase 6.A.
    """

    client_id: str
    """Client identifier (UUID or human-readable)."""

    total_nav_usd: Decimal
    """Sum of client-attributed NAV across all sources."""

    source_breakdown: tuple[TreasurySourceAttribution, ...]
    """Per-source breakdown. Order follows TreasurySource enum declaration."""

    asof: datetime
    """Timestamp at which the upstream canonical rollup was captured."""

    rollup_version: str = ""
    """Opaque version tag from the upstream canonical rollup (for cache-staleness detection)."""

    has_stubs: bool = False
    """Propagated from TreasuryRollupResponse.has_stubs — signals demo-mode data."""


@dataclass(frozen=True)
class ClientShareClassSubscriptionView:
    """Per-client share-class subscription entry.

    Mirrors ``ClientShareClassSubscription`` (UAC internal/domain/client_lifecycle.py)
    with added display-ready fields for the deployment-api response layer.

    Per ``wallet_treasury_client_flow_2026_05_10.md`` Phase 6.B.
    """

    client_id: str
    """Client identifier."""

    share_class_id: str
    """Share class (e.g., 'USDC_CUTOVER_V1')."""

    archetype_id: str
    """Strategy archetype (e.g., 'carry_staked_basis')."""

    allocation_pct: Decimal
    """Allocation % of client's capital to this archetype (0-100)."""

    is_active: bool
    """True if subscription is currently active (not suspended)."""

    subscribed_at: datetime
    """Subscription timestamp."""

    suspended_at: datetime | None = None
    """If suspended: timestamp of suspension. None = active."""

    suspension_reason: str = ""
    """If suspended: reason string (e.g., 'drawdown_exceeded')."""

    max_drawdown_for_suspension_pct: Decimal = Decimal("15")
    """Archetype-specific drawdown gate (may be tighter than global client preference)."""


@dataclass(frozen=True)
class ClientSubscriptionList:
    """Per-client share-class subscription list.

    Returned by ``GET /api/clients/{id}/subscriptions``.
    Per ``wallet_treasury_client_flow_2026_05_10.md`` Phase 6.B.
    """

    client_id: str
    """Client identifier."""

    subscriptions: tuple[ClientShareClassSubscriptionView, ...]
    """All subscriptions (active + suspended). Ordered by subscribed_at asc."""

    asof: datetime
    """Timestamp at which the subscription store was queried."""

    @property
    def active_count(self) -> int:
        """Number of currently active subscriptions."""
        return sum(1 for s in self.subscriptions if s.is_active)

    @property
    def total_active_allocation_pct(self) -> Decimal:
        """Sum of allocation_pct across active subscriptions (invariant: <= 100)."""
        return sum(
            (s.allocation_pct for s in self.subscriptions if s.is_active),
            start=Decimal("0"),
        )
