from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, Field

from .._base import CanonicalBase


class CanonicalPosition(CanonicalBase):
    """Normalised position — all venues."""

    instrument_id: str
    side: str = Field(description="LONG or SHORT")
    quantity: Decimal
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    leverage: Decimal | None = None
    venue: str | None = None
    timestamp: AwareDatetime | None = None
    liquidation_price: Decimal | None = None
    raw: dict[str, object] | None = None


class CanonicalBalance(CanonicalBase):
    """Normalised balance for a single currency."""

    currency: str
    free: Decimal
    locked: Decimal
    total: Decimal
    venue: str | None = None
    available: Decimal | None = None
    timestamp: AwareDatetime | None = None
    raw: dict[str, object] | None = None


class CanonicalAccountSnapshot(CanonicalBase):
    """Full account snapshot including balances and positions."""

    venue: str
    balances: list[CanonicalBalance] = []
    positions: list[CanonicalPosition] = []
    timestamp: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))


class CanonicalSettlement(CanonicalBase):
    """Settlement event for a position or balance change."""

    venue: str
    asset: str
    amount: Decimal
    settlement_type: str
    timestamp: AwareDatetime
    raw: dict[str, object] | None = None


class FeeType(StrEnum):
    MAKER = "maker"
    TAKER = "taker"
    OTHER = "other"


class CanonicalFee(CanonicalBase):
    """Normalised fee — all venues."""

    amount: Decimal = Field(description="Fee amount or rate")
    currency: str = Field(description="Fee currency")
    asset: str | None = Field(default=None, description="Asset symbol if different from currency")
    fee_type: FeeType = Field(default=FeeType.OTHER, description="maker, taker, or other")
    venue: str = Field(min_length=1)
    timestamp: AwareDatetime | None = Field(default=None)
    schema_version: str = "1.0"


# ---------------------------------------------------------------------------
# Institutional account schemas: deposits, withdrawals, sub-accounts, fees
# ---------------------------------------------------------------------------


class DepositAddress(CanonicalBase):
    """Deposit address for a network."""

    network: str = Field(..., description="Blockchain network (e.g. ETH, TRC20)")
    address: str = Field(..., description="Deposit address")
    addressTag: str | None = Field(None, description="Memo/tag (XRP, XLM, etc.)")
    url: str | None = Field(None, description="Explorer or deposit info URL")


class DepositRecord(CanonicalBase):
    """Deposit transaction record."""

    status: str = Field(..., description="Status (e.g. pending, completed, failed)")
    amount: Decimal = Field(..., description="Deposit amount")
    asset: str = Field(..., description="Asset symbol (e.g. BTC, USDT)")
    network: str = Field(..., description="Blockchain network")
    txId: str | None = Field(None, description="Transaction ID on chain")
    confirmTimes: str | None = Field(None, description="Confirmations (e.g. 12/15)")


class WithdrawalRecord(CanonicalBase):
    """Withdrawal transaction record."""

    status: str = Field(..., description="Status (e.g. pending, completed, failed)")
    amount: Decimal = Field(..., description="Withdrawal amount")
    asset: str = Field(..., description="Asset symbol")
    network: str = Field(..., description="Blockchain network")
    txId: str | None = Field(None, description="Transaction ID on chain")
    fee: Decimal | None = Field(None, description="Network fee charged")


class InternalTransfer(CanonicalBase):
    """Internal transfer between account types."""

    fromAccountType: str = Field(..., description="Source account type (e.g. SPOT, FUTURES)")
    toAccountType: str = Field(..., description="Destination account type")
    asset: str = Field(..., description="Asset symbol")
    amount: Decimal = Field(..., description="Transfer amount")


class SubAccount(CanonicalBase):
    """Sub-account entry."""

    id: str = Field(..., description="Sub-account ID")
    email: str | None = Field(default=None, description="Sub-account email", json_schema_extra={"pii": True})
    isFreeze: bool = Field(False, description="Whether sub-account is frozen")


class ExchangeFeeSchedule(CanonicalBase):
    """Fee tier schedule."""

    tier: int = Field(..., description="Fee tier level")
    makerRate: Decimal = Field(..., description="Maker fee rate")
    takerRate: Decimal = Field(..., description="Taker fee rate")
    volumeThreshold: Decimal | None = Field(None, description="Volume threshold for tier (USD)")


class PortfolioMarginAccount(CanonicalBase):
    """Portfolio margin account snapshot."""

    totalEquity: Decimal = Field(..., description="Total equity (USD)")
    actualEquity: Decimal = Field(..., description="Actual equity after unrealized PnL")
    availableBalance: Decimal = Field(..., description="Available balance for trading")
    uniMMR: Decimal | None = Field(None, description="Unified maintenance margin ratio")
    accountMaintMargin: Decimal | None = Field(None, description="Account maintenance margin")


# ---------------------------------------------------------------------------
# CEX withdrawal request/response schemas per venue
# ---------------------------------------------------------------------------


class BinanceWithdrawRequest(CanonicalBase):
    """Binance withdrawal request (POST /sapi/v1/capital/withdraw/apply)."""

    coin: str = Field(..., description="Cryptocurrency to withdraw")
    address: str = Field(..., description="Withdrawal destination address")
    amount: str = Field(..., description="Amount to withdraw")
    network: str | None = Field(None, description="Blockchain network (default if omitted)")
    addressTag: str | None = Field(None, description="Secondary address (XRP, XMR, etc.)")
    withdrawOrderId: str | None = Field(None, description="Client-side withdrawal ID")
    transactionFeeFlag: bool | None = Field(None, description="Return fees to destination")
    walletType: int | None = Field(None, description="0=spot, 1=funding")


class BinanceWithdrawResponse(CanonicalBase):
    """Binance withdrawal response."""

    id: str = Field(..., description="Withdrawal ID")


class OKXWithdrawRequest(CanonicalBase):
    """OKX withdrawal request (POST /api/v5/asset/withdrawal)."""

    ccy: str = Field(..., description="Currency (e.g. BTC, ETH)")
    amt: str = Field(..., description="Withdrawal amount")
    dest: str = Field(..., description="4=on-chain, 6=internal transfer")
    toAddr: str = Field(..., description="Destination address")
    chain: str | None = Field(None, description="Chain (e.g. ETH-ERC20)")
    fee: str | None = Field(None, description="Network fee (optional for internal)")
    clientId: str | None = Field(None, description="Client-supplied ID")


class OKXWithdrawResponse(CanonicalBase):
    """OKX withdrawal response."""

    wdId: str | None = Field(None, description="Withdrawal ID")
    ccy: str | None = None
    chain: str | None = None
    amt: str | None = None
    clientId: str | None = None


class BybitWithdrawRequest(CanonicalBase):
    """Bybit withdrawal request (POST /v5/asset/withdraw/create)."""

    coin: str = Field(..., description="Currency (e.g. BTC, USDT)")
    chain: str = Field(..., description="Chain type (e.g. ETH, TRC20)")
    address: str = Field(..., description="Destination address")
    amount: str = Field(..., description="Withdrawal amount")
    tag: str | None = Field(None, description="Memo/tag for XRP, XLM, etc.")
    forceChain: int | None = Field(None, description="0=default, 1=force chain")
    accountType: str | None = Field(None, description="UNIFIED, CONTRACT, SPOT")


class BybitWithdrawResponse(CanonicalBase):
    """Bybit withdrawal response."""

    withdrawId: str | None = Field(None, description="Withdrawal ID")
    success: bool | None = None


class UpbitWithdrawRequest(CanonicalBase):
    """Upbit withdrawal request (POST /v1/withdraws/krw or /v1/withdraws/coin)."""

    currency: str = Field(..., description="Currency (e.g. BTC, KRW)")
    amount: str = Field(..., description="Withdrawal amount")
    address: str | None = Field(None, description="Destination address (crypto)")
    secondary_address: str | None = Field(None, description="Memo/tag (crypto)")
    bank: str | None = Field(None, description="Bank code (KRW)")
    account: str | None = Field(None, description="Account number (KRW)")


class UpbitWithdrawResponse(CanonicalBase):
    """Upbit withdrawal response."""

    uuid: str | None = Field(None, description="Withdrawal ID")
    currency: str | None = None
    net_type: str | None = None
    amount: str | None = None
    state: str | None = None


class CoinbaseWithdrawRequest(CanonicalBase):
    """Coinbase withdrawal request (POST /v2/accounts/:id/transactions)."""

    type: str = Field("send", description="Transaction type (send for withdraw)")
    to: str = Field(..., description="Destination address or Coinbase ID")
    amount: str = Field(..., description="Amount to withdraw")
    currency: str = Field(..., description="Currency (e.g. BTC, ETH)")
    network: str | None = Field(None, description="Network (e.g. ethereum, bitcoin)")
    idem: str | None = Field(None, description="Idempotency key")


class CoinbaseWithdrawResponse(CanonicalBase):
    """Coinbase withdrawal response."""

    id: str | None = Field(None, description="Transaction ID")
    status: str | None = None
    amount: dict[str, object] | None = None


# ---------------------------------------------------------------------------
# On-chain transfer schemas: eth_sendRawTransaction, ERC20 calldata
# ---------------------------------------------------------------------------


ERC20_TRANSFER_SELECTOR = "0xa9059cbb"
ERC20_TRANSFER_FROM_SELECTOR = "0x23b872dd"


class EthSendRawTransactionRequest(CanonicalBase):
    """eth_sendRawTransaction JSON-RPC request shape."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str
    method: Literal["eth_sendRawTransaction"] = "eth_sendRawTransaction"
    params: list[str] = Field(..., min_length=1, max_length=1)


class EthSendRawTransactionResponse(CanonicalBase):
    """eth_sendRawTransaction JSON-RPC response."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str
    result: str | None = Field(None, description="Tx hash on success")
    error: dict[str, object] | None = Field(None, description="Error object on failure")


class EthTransactionRequest(CanonicalBase):
    """eth_sendTransaction / eth_call transaction object (unsigned)."""

    from_: str | None = Field(None, alias="from", description="Sender address")
    to: str | None = Field(None, description="Recipient (null for contract creation)")
    gas: str | None = Field(None, description="Gas limit (hex)")
    gasPrice: str | None = Field(None, description="Legacy gas price (hex)")
    maxFeePerGas: str | None = Field(None, description="EIP-1559 max fee (hex)")
    maxPriorityFeePerGas: str | None = Field(None, description="EIP-1559 priority fee (hex)")
    value: str | None = Field(None, description="Value in wei (hex)")
    data: str | None = Field(None, description="Calldata (hex)")
    nonce: str | None = Field(None, description="Nonce (hex)")
    chainId: str | None = Field(None, description="Chain ID (hex)")

    model_config = {"populate_by_name": True}


class EthSendTransactionRequest(CanonicalBase):
    """eth_sendTransaction JSON-RPC request shape."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str
    method: Literal["eth_sendTransaction"] = "eth_sendTransaction"
    params: list[EthTransactionRequest] = Field(..., min_length=1, max_length=1)


class Erc20TransferCalldata(CanonicalBase):
    """ERC20 transfer(to, amount) calldata. Selector: 0xa9059cbb."""

    selector: Literal["0xa9059cbb"] = ERC20_TRANSFER_SELECTOR
    to: str = Field(..., description="Recipient address (20 bytes)")
    amount: str = Field(..., description="Amount (uint256 wei string)")


class Erc20TransferFromCalldata(CanonicalBase):
    """ERC20 transferFrom(from, to, amount) calldata. Selector: 0x23b872dd."""

    selector: Literal["0x23b872dd"] = ERC20_TRANSFER_FROM_SELECTOR
    from_: str = Field(..., alias="from", description="Source address (20 bytes)")
    to: str = Field(..., description="Recipient address (20 bytes)")
    amount: str = Field(..., description="Amount (uint256 wei string)")

    model_config = {"populate_by_name": True}
