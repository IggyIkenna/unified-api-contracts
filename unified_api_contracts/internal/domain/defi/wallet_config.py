"""Wallet mapping configuration for DeFi custody management.

Maps custodian wallets (treasury + trading) per share class.
Treasury is keyed by share class (USDC, ETH, SOL, BTC), not chain.
Once funds hit the trading wallet, the strategy decides which chains/venues.

Same config structure for mainnet/testnet — only addresses differ.

GCS config path: wallet-config/{chain_env}/wallet_mapping.json

Per-wallet provisioning surface (added 2026-05-12 slot 4 per
``api_keys_wallets_accounts_readiness_2026_05_10.md`` Phase 3.C + Phase 4.A):

- :class:`SigningSurface` — closed-set enum of HSM tiers (LOCAL_KEY /
  CLOUD_KMS_ENCRYPTED / COPPER_MPC / FIREBLOCKS_MPC / MOCK). May-23 cutover
  ships on CLOUD_KMS_ENCRYPTED; June-1 integration of client-provided
  Copper + Fireblocks credentials flips the field per wallet without
  touching strategy code (per ``custody-providers.md`` § 1 factory pattern).
- :class:`WalletKind` — TREASURY / HOT_TRADING / GAS_RESERVE / FLASH_LOAN_RECEIVER.
- :class:`SpendingCaps` — per-wallet per-tx + per-hour + per-day caps,
  consumed by ``risk-and-exposure-service`` pre-flight check + wallet-tier
  kill-switch hook.
- :class:`WalletProvisioningConfig` — the per-wallet operational envelope
  (chain + protocol allowlist + signing surface + spending caps +
  kill-switch hook reference). Composes with the existing per-share-class
  mapping above.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum


class SigningSurface(StrEnum):
    """Closed-set HSM tier for wallet transaction signing.

    Routes :func:`get_custody_provider` in execution-service to the right
    :class:`CustodyProvider` implementation. Switchable per-wallet without
    strategy code changes per ``custody-providers.md`` § 1.

    May-23 cutover default: ``CLOUD_KMS_ENCRYPTED`` (HSM-backed CMK; raw
    key envelope-encrypted at rest; in-memory decrypt only inside the
    trading VM via service-account-bound IAM). June-1 client-provided
    custody flips per-wallet to ``COPPER_MPC`` or ``FIREBLOCKS_MPC`` via
    config without recompile.

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with ``custody-providers.md`` § 2 (``CustodyProvider`` factory
    routing) and ``WalletMappingConfig.custodian`` (the legacy top-level
    field continues to declare the default surface; per-wallet
    :class:`WalletProvisioningConfig.signing_surface` overrides).
    """

    LOCAL_KEY = "LOCAL_KEY"
    """Raw private key from Secret Manager, web3.py signing. Dev + testnet only."""

    CLOUD_KMS_ENCRYPTED = "CLOUD_KMS_ENCRYPTED"
    """Envelope-encrypted private key in Secret Manager; decrypted via
    HSM-backed CMK (GCP Cloud HSM / AWS CloudHSM, FIPS 140-2 L3). VM SA
    is the only principal with KMS Decrypter on the CMK. **May-23 cutover
    default** until client-provided Copper/Fireblocks creds land June-1."""

    COPPER_MPC = "COPPER_MPC"
    """Copper.co MPC signing. Sub-2s latency. Key shards never reassembled.
    Activates per-wallet from June-1 onwards (client-provided creds)."""

    FIREBLOCKS_MPC = "FIREBLOCKS_MPC"
    """Fireblocks MPC vault signing. 100-500ms latency. HD-derivation under
    Fireblocks master key supports N×M wallets. Activates per-wallet from
    June-1 onwards (client-provided creds)."""

    MOCK = "MOCK"
    """Deterministic SHA256 fake signing. Test-only."""


class WalletKind(StrEnum):
    """Closed-set wallet role classifier.

    Drives risk-engine + position-balance-monitor routing decisions. Treasury
    wallets surface in client-deposit/withdraw flows; HOT_TRADING wallets are
    per-archetype-per-chain; GAS_RESERVE holds native gas tokens shared across
    archetypes; FLASH_LOAN_RECEIVER is the deployed Solidity-contract wallet
    address (already in UAC ``testnet_contracts.yaml``).
    """

    TREASURY = "TREASURY"
    """Per-share-class client-facing deposit/withdraw wallet. 20% of AUM."""

    HOT_TRADING = "HOT_TRADING"
    """Per-archetype-per-chain strategy execution wallet. 80% of AUM."""

    GAS_RESERVE = "GAS_RESERVE"
    """Per-chain native gas-token reserve (ETH on mainnet, MATIC on Polygon,
    SOL on Solana). Shared across archetypes on the same chain."""

    FLASH_LOAN_RECEIVER = "FLASH_LOAN_RECEIVER"
    """Deployed Solidity flash-loan receiver contract. Address per
    UAC ``config/testnet_contracts.yaml`` ``FLASH_LOAN_RECEIVER``."""


@dataclass(frozen=True)
class SpendingCaps:
    """Per-wallet spending caps consumed by risk-engine + kill-switch.

    All caps in USD-equivalent at the time of execution. Per-protocol caps
    are checked against the (protocol, wallet) pair; per-tx caps fire
    immediately; per-hour + per-day caps are accumulator-based via
    ``position-balance-monitor`` rolling windows.

    Cap exceedance fires :class:`unified_api_contracts.alerting.AlertCode`
    ``WALLET_CAP_EXCEEDED`` with severity per cap class (per-tx = CRITICAL;
    per-hour = HIGH; per-day = WARN). May ALSO arm the wallet's
    ``kill_switch_id`` per :class:`WalletProvisioningConfig`.
    """

    per_tx_usd: Decimal | None = None
    """Single-transaction cap; None = no limit (use sparingly)."""

    per_hour_usd: Decimal | None = None
    """Rolling 1-hour cap; None = no limit."""

    per_day_usd: Decimal | None = None
    """Rolling 24-hour cap; None = no limit."""

    per_protocol_usd: dict[str, Decimal] = field(default_factory=dict)
    """Per-protocol notional cap (e.g. ``{"AAVE_V3": 50000, "UNISWAP_V3": 25000}``).
    Protocol key matches UAC ``transfer_types.VENUE_WALLET_CAPABILITIES`` venue
    name. Missing protocol = inherit per_tx/per_hour/per_day caps."""

    def is_within_per_tx(self, amount_usd: Decimal) -> bool:
        """Returns True if amount is within per-tx cap (or no cap set)."""
        return self.per_tx_usd is None or amount_usd <= self.per_tx_usd

    def per_protocol_limit(self, protocol: str) -> Decimal | None:
        """Returns the per-protocol cap, or None if not specified."""
        return self.per_protocol_usd.get(protocol)


@dataclass(frozen=True)
class WalletProvisioningConfig:
    """Per-wallet operational envelope: signing surface + allowlists + caps.

    Composes with :class:`WalletConfig` (which carries the static identity
    fields: wallet_id, address, chain). Loaded alongside ``WalletMappingConfig``
    from GCS at ``wallet-config/{chain_env}/wallet_provisioning.json`` (or
    inlined per-wallet in the existing ``wallet_mapping.json`` — readers
    accept both shapes during the cross-tab handoff window).

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with:

    - :class:`unified_api_contracts.canonical.crosscutting.kill_switch.KillSwitchId`
      via ``kill_switch_id`` — wallet-tier kill-switch wiring per
      ``codex/04-architecture/kill-switch-circuit-breaker.md``. Per-wallet
      kill-switch is the FINEST-grain switch beyond per-venue + per-archetype.
    - :class:`SigningSurface` enum (above) routes to the right
      :class:`CustodyProvider` at runtime.
    - :class:`SpendingCaps` (above) for per-wallet risk envelope.
    - ``allowed_protocols`` is checked against UAC
      ``transfer_types.VENUE_WALLET_CAPABILITIES`` venue names —
      ``classify_transfer_type`` rejects any execution path not in this set.
    - ``allowed_destinations`` is the withdraw-whitelist (custody Copper
      whitelist + Fireblocks AddressBook). Empty set = no withdrawals
      allowed from this wallet (safe default for HOT_TRADING).
    """

    wallet_id: str
    """Custodian wallet identifier — MUST match :class:`WalletConfig.wallet_id`."""

    chain: str
    """Chain canonical name — MUST match :class:`WalletConfig.chain`."""

    kind: WalletKind
    """Wallet role classifier."""

    signing_surface: SigningSurface
    """HSM tier for transaction signing."""

    # --- Provisioning credential pointers (one populated per signing_surface) ---

    private_key_secret_ref: str = ""
    """Secret Manager ref for LOCAL_KEY surface (e.g. ``eth-trading-pk``).
    Required when signing_surface == LOCAL_KEY. Empty otherwise."""

    kms_key_uri: str = ""
    """KMS CMK URI for CLOUD_KMS_ENCRYPTED surface
    (e.g. ``projects/{pid}/locations/asia-northeast1/keyRings/wallets/cryptoKeys/hot-trading-eth-v1``
    or ``arn:aws:kms:ap-northeast-1:{acct}:key/...``). Required when
    signing_surface == CLOUD_KMS_ENCRYPTED. Empty otherwise."""

    custodian_wallet_id: str = ""
    """Custodian-side wallet handle for COPPER_MPC / FIREBLOCKS_MPC
    (e.g. Copper portfolioId or Fireblocks vaultAccountId). Required when
    signing_surface == COPPER_MPC | FIREBLOCKS_MPC. Empty otherwise."""

    # --- Risk envelope ---

    allowed_protocols: frozenset[str] = field(default_factory=frozenset)
    """Closed set of protocol/venue names this wallet may interact with.
    Keys match UAC ``transfer_types.VENUE_WALLET_CAPABILITIES``.
    Empty set = reject all (safe default for newly-provisioned wallets)."""

    allowed_destinations: frozenset[str] = field(default_factory=frozenset)
    """Withdraw-whitelist of destination addresses (custody + Fireblocks
    AddressBook). Empty = no withdrawals (HOT_TRADING / GAS_RESERVE default).
    TREASURY wallets populate this with client-deposit-source addresses."""

    spending_caps: SpendingCaps = field(default_factory=SpendingCaps)
    """Per-wallet risk caps."""

    # --- Kill-switch wiring ---

    kill_switch_id: str = ""
    """:class:`KillSwitchId` value (StrEnum value, not the enum itself,
    to avoid UAC inter-module import cycles). Empty = inherit from
    archetype-level kill-switch. Wallet-tier kill-switch is the FINEST-grain
    switch; arming it freezes this wallet only without affecting other
    wallets of the same archetype.

    Per ``kill-switch-circuit-breaker.md`` § 7, valid values:
    ``KILL_PER_ARCHETYPE_*`` / ``KILL_PER_VENUE_*`` /
    ``KILL_PER_ASSET_GROUP_*`` / ``KILL_ALL_LIVE`` from
    :class:`unified_api_contracts.kill_switch.KillSwitchId`."""

    # --- Optional metadata ---

    archetype_id: str = ""
    """Strategy/archetype binding for HOT_TRADING wallets. Empty for
    TREASURY / GAS_RESERVE / FLASH_LOAN_RECEIVER (shared)."""

    derivation_path: str = ""
    """HD derivation path under Fireblocks/Copper master key
    (e.g. ``m/44'/60'/0'/0/{idx}``). Empty for non-HD surfaces."""

    label: str = ""
    """Human-readable description for ops dashboards."""

    def validate(self) -> None:
        """Raise :class:`WalletProvisioningError` on invalid configuration.

        Enforces:

        1. signing_surface ↔ credential pointer presence (LOCAL_KEY needs
           private_key_secret_ref; CLOUD_KMS_ENCRYPTED needs kms_key_uri;
           COPPER_MPC / FIREBLOCKS_MPC need custodian_wallet_id; MOCK needs
           none).
        2. HOT_TRADING wallets MUST declare ``archetype_id``.
        3. Non-empty ``allowed_destinations`` only when ``kind`` permits
           withdrawals (TREASURY).
        4. ``kill_switch_id`` if present matches the known prefixes.
        """
        if self.signing_surface == SigningSurface.LOCAL_KEY and not self.private_key_secret_ref:
            raise WalletProvisioningError(
                f"wallet {self.wallet_id}: signing_surface=LOCAL_KEY requires private_key_secret_ref",
            )
        if self.signing_surface == SigningSurface.CLOUD_KMS_ENCRYPTED and not self.kms_key_uri:
            raise WalletProvisioningError(
                f"wallet {self.wallet_id}: signing_surface=CLOUD_KMS_ENCRYPTED requires kms_key_uri",
            )
        if self.signing_surface in {SigningSurface.COPPER_MPC, SigningSurface.FIREBLOCKS_MPC}:
            if not self.custodian_wallet_id:
                raise WalletProvisioningError(
                    f"wallet {self.wallet_id}: signing_surface={self.signing_surface.value} "
                    "requires custodian_wallet_id",
                )
        if self.kind == WalletKind.HOT_TRADING and not self.archetype_id:
            raise WalletProvisioningError(
                f"wallet {self.wallet_id}: kind=HOT_TRADING requires archetype_id",
            )
        if self.kind in {WalletKind.HOT_TRADING, WalletKind.GAS_RESERVE} and self.allowed_destinations:
            raise WalletProvisioningError(
                f"wallet {self.wallet_id}: kind={self.kind.value} MUST have empty "
                "allowed_destinations (only TREASURY may withdraw to external addresses)",
            )
        if self.kill_switch_id:
            valid_prefixes = (
                "KILL_ALL_LIVE",
                "KILL_PER_ARCHETYPE_",
                "KILL_PER_VENUE_",
                "KILL_PER_ASSET_GROUP_",
            )
            if not self.kill_switch_id.startswith(valid_prefixes):
                raise WalletProvisioningError(
                    f"wallet {self.wallet_id}: kill_switch_id={self.kill_switch_id!r} "
                    f"must start with one of {valid_prefixes}",
                )

    def permits_protocol(self, protocol: str) -> bool:
        """Returns True if this wallet may execute against ``protocol``."""
        return protocol in self.allowed_protocols

    def permits_destination(self, address: str) -> bool:
        """Returns True if ``address`` is in the withdraw allowlist.

        Note: lowercase-normalized comparison for EVM (case-insensitive).
        Solana addresses are case-sensitive; comparison is exact.
        """
        if not self.allowed_destinations:
            return False
        if address.startswith("0x") or address.startswith("0X"):
            lower = address.lower()
            return any(d.lower() == lower for d in self.allowed_destinations)
        return address in self.allowed_destinations


class WalletProvisioningError(ValueError):
    """Raised when :meth:`WalletProvisioningConfig.validate` fails."""


@dataclass
class WalletConfig:
    """Configuration for a single custodian wallet."""

    wallet_id: str
    """Custodian wallet identifier (e.g. 'vault-eth-main', 'trading-aave-eth')."""

    address: str
    """On-chain address (0x... for EVM, base58 for Solana)."""

    chain: str
    """Chain where this wallet lives (ETHEREUM, ARBITRUM, SOLANA, etc.)."""

    label: str = ""
    """Human-readable label for the wallet."""


@dataclass
class TradingWalletConfig:
    """Trading wallet assigned to a specific strategy."""

    wallet_id: str
    """Custodian wallet identifier."""

    address: str
    """On-chain address."""

    strategy_id: str
    """Strategy this wallet is allocated to."""

    chain: str = ""
    """Chain where this wallet lives (may differ from treasury chain)."""

    max_allocation_usd: Decimal | None = None
    """Maximum USD allocation for this strategy wallet."""


@dataclass
class ShareClassWalletMapping:
    """Wallet mapping for a single share class.

    Treasury is per share class — clients deposit based on their fund's
    base currency. The chain is just where the treasury wallet lives.
    Trading wallets can be on any chain; the strategy decides internally.
    """

    share_class: str
    """Share class base currency (USDC, ETH, SOL, BTC)."""

    treasury_wallet: WalletConfig
    """Treasury wallet for this share class — client deposits land here."""

    trading_wallets: list[TradingWalletConfig] = field(default_factory=list)
    """Per-strategy trading wallets (can span multiple chains)."""

    def get_trading_wallet(self, strategy_id: str) -> TradingWalletConfig | None:
        """Look up trading wallet for a strategy."""
        for tw in self.trading_wallets:
            if tw.strategy_id == strategy_id:
                return tw
        return None


# Keep ChainWalletMapping as alias for backwards compat during migration
ChainWalletMapping = ShareClassWalletMapping


@dataclass
class WalletMappingConfig:
    """Full wallet mapping configuration for a custodian environment.

    Loaded from GCS: wallet-config/{chain_env}/wallet_mapping.json

    Keyed by share class — each share class has a treasury wallet where
    clients deposit, and trading wallets where strategies operate.

    Structure:
        custodian: "copper" | "fireblocks" | "mock"
        chain_env: "mainnet" | "testnet" | "fork"
        share_classes: {share_class: ShareClassWalletMapping}

    Example:
        WalletMappingConfig(
            custodian="copper",
            chain_env="testnet",
            share_classes={
                "USDC": ShareClassWalletMapping(
                    share_class="USDC",
                    treasury_wallet=WalletConfig(
                        wallet_id="vault-usdc-eth",
                        address="0x...",
                        chain="ETHEREUM",
                    ),
                    trading_wallets=[
                        TradingWalletConfig(
                            wallet_id="trading-aave-sep",
                            address="0x...",
                            strategy_id="AAVE_LENDING",
                            chain="ETHEREUM",
                        ),
                        TradingWalletConfig(
                            wallet_id="trading-l2-basis-sep",
                            address="0x...",
                            strategy_id="L2_BASIS",
                            chain="ARBITRUM",
                        ),
                    ],
                ),
            },
        )
    """

    custodian: str
    """Custodian provider name (copper, fireblocks, mock)."""

    chain_env: str
    """Chain environment (mainnet, testnet, fork)."""

    share_classes: dict[str, ShareClassWalletMapping] = field(default_factory=dict)
    """Per-share-class wallet mappings."""

    reserve_pct: Decimal = Decimal("20")
    """Target treasury reserve as % of total AUM."""

    min_threshold_pct: Decimal = Decimal("10")
    """Below this: TREASURY_LOW event."""

    max_threshold_pct: Decimal = Decimal("30")
    """Above this: TREASURY_HIGH event."""

    def get_treasury_address(self, share_class: str) -> str:
        """Get treasury wallet address for a share class."""
        mapping = self.share_classes.get(share_class)
        if not mapping:
            return ""
        return mapping.treasury_wallet.address

    def get_treasury_chain(self, share_class: str) -> str:
        """Get the chain where the treasury wallet lives for a share class."""
        mapping = self.share_classes.get(share_class)
        if not mapping:
            return ""
        return mapping.treasury_wallet.chain

    def get_trading_address(self, share_class: str, strategy_id: str) -> str:
        """Get trading wallet address for a strategy within a share class."""
        mapping = self.share_classes.get(share_class)
        if not mapping:
            return ""
        tw = mapping.get_trading_wallet(strategy_id)
        return tw.address if tw else ""

    def get_all_strategy_ids(self) -> list[str]:
        """Get all strategy IDs with trading wallets across all share classes."""
        ids: set[str] = set()
        for sc_mapping in self.share_classes.values():
            for tw in sc_mapping.trading_wallets:
                ids.add(tw.strategy_id)
        return sorted(ids)


# GCS config path template
WALLET_CONFIG_GCS_PATH = "wallet-config/{chain_env}/wallet_mapping.json"


def wallet_config_gcs_path(chain_env: str) -> str:
    """Get the GCS path for a wallet mapping config."""
    return WALLET_CONFIG_GCS_PATH.format(chain_env=chain_env)
