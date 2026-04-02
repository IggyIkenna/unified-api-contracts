"""Wallet mapping configuration for DeFi custody management.

Maps custodian wallets (treasury + trading) per share class.
Treasury is keyed by share class (USDC, ETH, SOL, BTC), not chain.
Once funds hit the trading wallet, the strategy decides which chains/venues.

Same config structure for mainnet/testnet — only addresses differ.

GCS config path: wallet-config/{chain_env}/wallet_mapping.json
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


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
