"""Binance account schemas: balances, margin, withdrawals, transfers."""

__api_version__ = "v3"  # matches provider_api_versions.yaml

from pydantic import BaseModel


class BinanceMarginBalanceResponse(BaseModel):
    """Binance futures margin/balance (GET /fapi/v2/balance or /dapi/v2/balance)."""

    asset: str | None = None
    balance: str | None = None
    availableBalance: str | None = None
    crossWalletBalance: str | None = None
    crossUnPnl: str | None = None
    availableWithdrawBalance: str | None = None


class BinanceRealizedPnlResponse(BaseModel):
    """Binance realized PnL from income history (GET /fapi/v1/income or /dapi/v1/income).

    incomeType: REALIZED_PNL, FUNDING_FEE, COMMISSION, etc.
    """

    symbol: str | None = None
    incomeType: str | None = None
    income: str | None = None
    asset: str | None = None
    info: str | None = None
    time: int | None = None
    tranId: str | None = None


class BinanceWithdrawalRequest(BaseModel):
    """Binance withdrawal request (POST /sapi/v1/capital/withdraw/apply)."""

    coin: str
    withdrawOrderId: str | None = None  # client id, optional
    network: str | None = None
    address: str
    amount: str
    transactionFeeFlag: bool | None = None
    name: str | None = None  # address tag name
    walletType: int | None = None  # 0=spot, 1=funding


class BinanceWithdrawalResponse(BaseModel):
    """Binance withdrawal response (returns id for tracking)."""

    id: str | None = None


class BinanceIncome(BaseModel):
    """Binance income history (GET /fapi/v1/income, /dapi/v1/income, /papi/v1/cm/income).

    PnL/funding history. Coin-M uses 'income'; USD-M uses 'amount'. Both have tradeId.
    """

    symbol: str | None = None
    incomeType: str  # TRANSFER, FUNDING_FEE, REALIZED_PNL, COMMISSION, etc.
    income: str | None = None  # Coin-M
    amount: str | None = None  # USD-M (some income types)
    asset: str
    info: str | None = None
    time: int  # timestamp ms
    tranId: str | None = None  # transaction id; API may return int or str
    tradeId: str | None = None


class BinanceDepositAddress(BaseModel):
    """Binance deposit address (GET /sapi/v1/capital/deposit/address)."""

    address: str
    coin: str | None = None
    tag: str | None = None  # address tag / memo
    url: str | None = None
    network: str | None = None


class BinanceDepositHistory(BaseModel):
    """Binance deposit history item (GET /sapi/v1/capital/deposit/hisrec)."""

    id: str | None = None
    amount: str | None = None
    coin: str | None = None
    network: str | None = None
    status: int | None = None
    address: str | None = None
    addressTag: str | None = None
    txId: str | None = None
    insertTime: int | None = None
    confirmTimes: str | None = None
    completeTime: int | None = None


class BinanceWithdrawalHistory(BaseModel):
    """Binance withdrawal history item (GET /sapi/v1/capital/withdraw/history)."""

    id: str | None = None
    amount: str | None = None
    transactionFee: str | None = None
    coin: str | None = None
    status: int | None = None
    address: str | None = None
    txId: str | None = None
    network: str | None = None
    applyTime: str | None = None
    completeTime: str | None = None


class BinanceFeeRate(BaseModel):
    """Binance trade fee rate (GET /sapi/v1/asset/tradeFee)."""

    symbol: str
    makerCommission: str
    takerCommission: str


class BinanceInternalTransfer(BaseModel):
    """Binance universal transfer request/response (POST /sapi/v1/asset/transfer)."""

    fromAccountType: str  # SPOT, USDT_FUTURE, COIN_FUTURE, etc.
    toAccountType: str
    asset: str
    amount: str
    txnId: str | None = None
    clientTranId: str | None = None


class BinanceSubAccount(BaseModel):
    """Binance sub-account (GET /sapi/v1/sub-account/list)."""

    email: str | None = None
    isFreeze: bool | None = None
    createTime: int | None = None


class BinanceSubAccountAssets(BaseModel):
    """Binance sub-account consolidated balances (GET /sapi/v1/sub-account/assets)."""

    balances: list[dict[str, object]] | None = None
    totalAssetOfBtc: str | None = None


class BinancePapiAccount(BaseModel):
    """Binance portfolio margin account (GET /papi/v1/account)."""

    accountEquity: str | None = None
    actualEquity: str | None = None
    accountMaintMargin: str | None = None
    uniMMR: str | None = None
    accountStatus: str | None = None
    virtualMaxWithdrawAmount: str | None = None
    totalWalletBalance: str | None = None
    totalUnrealizedProfit: str | None = None
    totalMarginBalance: str | None = None
    totalPositionInitialMargin: str | None = None
    totalOpenOrderInitialMargin: str | None = None
    totalCrossWalletBalance: str | None = None
    totalCrossUnPnl: str | None = None


class BinancePapiBalance(BaseModel):
    """Binance portfolio margin balance (GET /papi/v1/balance)."""

    asset: str | None = None
    balance: str | None = None
    crossWalletBalance: str | None = None
    crossUnPnl: str | None = None
    availableBalance: str | None = None
    maxWithdrawAmount: str | None = None


class BinancePapiPosition(BaseModel):
    """Binance portfolio margin UM position (GET /papi/v1/um/positionRisk)."""

    symbol: str | None = None
    positionAmt: str | None = None
    entryPrice: str | None = None
    markPrice: str | None = None
    liquidationPrice: str | None = None
    unRealizedProfit: str | None = None
    leverage: str | None = None
    positionSide: str | None = None
    marginType: str | None = None
    notional: str | None = None
    isolatedMargin: str | None = None


class BinanceDualInvestmentProduct(BaseModel):
    """GET /sapi/v1/simple-earn/dualInvestment/product/list.

    Structured product: deposit + embedded short option auto-exercised at expiry.
    EAPI is separate from FAPI/DAPI; base URL eapi.binance.com.
    """

    id: str | None = None
    investCoin: str | None = None
    exercisedCoin: str | None = None
    subscribeStartTime: int | None = None
    subscribeEndTime: int | None = None
    deliveryDate: int | None = None
    strikePrice: str | None = None
    apy: str | None = None
    minAmount: str | None = None
    maxAmount: str | None = None
