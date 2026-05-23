"""Closed-set enums for the global ledger SSOT model.

Extension via PR only — these are structural discriminants used in parquet
partition keys, event routing, and join predicates. Adding a value is
backwards-compatible; removing or renaming is a breaking schema change.

SSOT plan: ``plans/active/global_ledger_pnl_attribution_discovery_2026_05_21.md``
Phase 2 — UAC schema spec.
"""

from __future__ import annotations

from enum import StrEnum


class EventOrigin(StrEnum):
    """Discriminates instruction-driven vs passive (non-instruction) events.

    - ``INSTRUCTION``: event arose from an explicit agent action (order, transfer,
      stake command, bridge call, rebalance instruction). Owner: execution-service
      InstructionLedger.
    - ``PASSIVE``: event arose without an explicit instruction (funding rate accrual,
      dividend payment, staking reward, lending interest, settlement at expiry,
      mark-to-market price move). Owner: strategy-service PassiveLedger synthesiser.
    """

    INSTRUCTION = "instruction"
    PASSIVE = "passive"


class EventType(StrEnum):
    """Closed-set event type discriminant for LedgerRow routing.

    Instruction-driven (EventOrigin.INSTRUCTION):
    - TRADE / TRANSFER / STAKE / UNSTAKE / BORROW / REPAY / BRIDGE / LIQUIDATION

    Passive (EventOrigin.PASSIVE):
    - FUNDING_ACCRUAL / DIVIDEND / STAKING_REWARD / LENDING_INTEREST /
      SETTLEMENT / EXPIRY / MARK_UPDATE

    Extension requires PR review — changing routing affects PnL reconciliation.
    """

    # Instruction-driven
    TRADE = "trade"
    """Fill on a CeFi/DeFi/TradFi/sports/prediction order."""

    TRANSFER = "transfer"
    """On-chain or off-chain asset movement (deposit, withdrawal, bridge, sub-account move)."""

    STAKE = "stake"
    """LST mint / DeFi protocol deposit (asset locked, receipt token received)."""

    UNSTAKE = "unstake"
    """LST burn / DeFi protocol withdrawal."""

    BORROW = "borrow"
    """Collateralised borrow (Aave, Compound, Morpho)."""

    REPAY = "repay"
    """Repayment of a borrow position."""

    BRIDGE = "bridge"
    """Cross-chain bridge movement (CCTP, Across, Stargate, Wormhole)."""

    LIQUIDATION = "liquidation"
    """Forced liquidation by venue/protocol (partial or full)."""

    # Passive — synthesised without an explicit instruction
    FUNDING_ACCRUAL = "funding_accrual"
    """Perpetual funding payment received or paid (CeFi perps: 8h cadence; DeFi: block-level)."""

    DIVIDEND = "dividend"
    """Cash/stock dividend on equity or futures."""

    STAKING_REWARD = "staking_reward"
    """LST/validator staking reward (e.g. stETH rebase, JitoSOL yield)."""

    LENDING_INTEREST = "lending_interest"
    """Aave/Compound/Morpho interest accrual on supplied collateral."""

    SETTLEMENT = "settlement"
    """Futures/options settlement at expiry (cash or physical delivery)."""

    EXPIRY = "expiry"
    """Options expiry — position zeroed at zero value (OTM)."""

    MARK_UPDATE = "mark_update"
    """Mark price / IV / greek snapshot update — PricingLedger only."""


class AssetClass(StrEnum):
    """Asset class discriminant for LedgerRow.asset_class.

    Drives attribution bucketing, margin calculations, and passive-event synthesis.
    """

    SPOT_TOKEN = "spot_token"
    """CEX spot or plain ERC-20/SPL token."""

    ATOKEN = "atoken"
    """Aave aToken (e.g. aUSDC, aWETH) — represents supplied collateral."""

    DEBT_TOKEN = "debt_token"
    """Aave variableDebtToken — represents borrow position."""

    LST = "lst"
    """Liquid staking token (stETH, rETH, cbETH, JitoSOL, mSOL)."""

    LRT = "lrt"
    """Liquid restaking token (eETH, weETH, rsETH)."""

    VAULT_SHARE = "vault_share"
    """Yield vault share (Yearn, ERC-4626, Morpho MetaMorpho)."""

    FUTURE = "future"
    """Exchange-traded or OTC futures contract."""

    PERP = "perp"
    """Perpetual swap / inverse perp."""

    OPTION = "option"
    """Vanilla or exotic option."""

    PREDICTION_CONTRACT = "prediction_contract"
    """Binary prediction market contract (Polymarket CLOB, Kalshi)."""

    SPORTS_OUTCOME = "sports_outcome"
    """Sports betting outcome / odds contract."""

    CURRENCY = "currency"
    """Fiat currency or stablecoin used as quote / margin."""

    GAS_TOKEN = "gas_token"
    """Native chain gas token used to pay tx fees (ETH, SOL, MATIC)."""

    UNKNOWN = "unknown"
    """Unresolved asset class — must be enriched before settlement."""


class Direction(StrEnum):
    """Directional discriminant for instruction events.

    Maps to the natural language of each asset class:
    - CeFi/TradFi: BUY / SELL
    - Options: BUY / SELL (for opening) + EXERCISE / ASSIGN (for closing)
    - Sports: BACK / LAY
    - Prediction: YES / NO
    - DeFi: LONG / SHORT (perps), SUPPLY / WITHDRAW (lending)
    """

    BUY = "buy"
    SELL = "sell"
    BACK = "back"
    LAY = "lay"
    YES = "yes"
    NO = "no"
    LONG = "long"
    SHORT = "short"
    SUPPLY = "supply"
    WITHDRAW = "withdraw"
    EXERCISE = "exercise"
    ASSIGN = "assign"


class OptionRight(StrEnum):
    """Option right discriminant — call or put."""

    CALL = "C"
    PUT = "P"
