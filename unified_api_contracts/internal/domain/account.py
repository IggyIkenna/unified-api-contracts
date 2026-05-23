"""
Trading Account Model — unified identity for CeFi, DeFi, and TradFi accounts.

Composite key: {client_id}:{venue}:{account_label}

This model flows through execution → position → risk → P&L so every
service agrees on what "an account" is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AccountType(StrEnum):
    """Type of trading account."""

    CEFI_EXCHANGE = "CEFI_EXCHANGE"
    DEFI_WALLET = "DEFI_WALLET"
    TRADFI_BROKER = "TRADFI_BROKER"
    SPORTS_BOOKMAKER = "SPORTS_BOOKMAKER"
    PREDICTION_MARKET = "PREDICTION_MARKET"


class WalletRole(StrEnum):
    """Wallet role within the IM Pooled fund-administration rail.

    TREASURY → principal account; investor deposits land here and redemptions
                settle from here; also source for capital-routing top-ups.
    TRADING  → working-capital account used by a strategy for live execution.
    RESERVE  → buffer bucket sized to ``TreasuryConfig.reserve_pct``; absorbs
                overflow from TRADING sweeps and tops up TREASURY when low.

    Additive field on ``TradingAccount`` with default None to preserve
    backwards-compatibility with SMA / DART / Reg Umbrella paths that do not
    use the treasury model.
    """

    TREASURY = "TREASURY"
    TRADING = "TRADING"
    RESERVE = "RESERVE"


@dataclass(frozen=True)
class TradingAccount:
    """Unified trading account identity.

    Supports:
    - CeFi: venue=BINANCE, account_label=main (or sub-account ID)
    - DeFi: venue=AAVE_V3-ETHEREUM, account_label=0x... (wallet address)
    - TradFi: venue=IBKR, account_label=DU1234567
    - Sports: venue=BETFAIR, account_label=main
    """

    client_id: str
    venue: str
    account_label: str  # "main", "sub-1", wallet address, broker account ID
    account_type: AccountType
    chain: str | None = None  # DeFi only — ETHEREUM, ARBITRUM, etc.
    share_class: str | None = None  # Links to treasury — USDC, ETH, etc.
    is_active: bool = True
    wallet_role: WalletRole | None = None  # IM Pooled rail only; default None

    @property
    def account_id(self) -> str:
        """Composite key used throughout the system."""
        return f"{self.client_id}:{self.venue}:{self.account_label}"


@dataclass
class AccountRegistry:
    """Registry of all trading accounts, keyed by composite ID.

    Used for:
    - Credential routing in execution-service
    - Position attribution in PBMS
    - Risk aggregation per account
    """

    _accounts: dict[str, TradingAccount] = field(default_factory=dict)

    def register(self, account: TradingAccount) -> None:
        """Register an account."""
        self._accounts[account.account_id] = account

    def get_by_id(self, account_id: str) -> TradingAccount | None:
        """Look up by composite key."""
        return self._accounts.get(account_id)

    def get_accounts(self, client_id: str, venue: str | None = None) -> list[TradingAccount]:
        """Get all accounts for a client, optionally filtered by venue."""
        return [a for a in self._accounts.values() if a.client_id == client_id and (venue is None or a.venue == venue)]

    def get_default_account(self, client_id: str, venue: str) -> TradingAccount | None:
        """Get the default (first active) account for a client at a venue."""
        accounts = [a for a in self._accounts.values() if a.client_id == client_id and a.venue == venue and a.is_active]
        if not accounts:
            return None
        # Prefer "main" label, otherwise first
        for a in accounts:
            if a.account_label == "main":
                return a
        return accounts[0]

    def get_all_active(self) -> list[TradingAccount]:
        """Get all active accounts."""
        return [a for a in self._accounts.values() if a.is_active]

    def __len__(self) -> int:
        return len(self._accounts)
