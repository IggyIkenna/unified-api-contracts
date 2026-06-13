"""Closed-set enums for the global ledger SSOT model.

Extension via PR only — these are structural discriminants used in parquet
partition keys, event routing, and join predicates. Adding a value is
backwards-compatible; removing or renaming is a breaking schema change.

SSOT plan: ``plans/active/global_ledger_pnl_attribution_discovery_2026_05_21.md``
Phase 2 — UAC schema spec.

Codex SSOT: ``codex/02-data/ledger-event-taxonomy.md``.
"""

from __future__ import annotations

from enum import StrEnum


class EventOrigin(StrEnum):
    """Discriminates instruction-driven vs passive (non-instruction) events.

    - ``INSTRUCTION``: event arose from an explicit agent action (order, transfer,
      stake command, bridge call, rebalance instruction, swap, wrap, deposit).
      Owner: execution-service InstructionLedger.
    - ``PASSIVE``: event arose without an explicit instruction (funding rate accrual,
      dividend payment, staking reward, lending interest, rebase, validator reward,
      MEV reward, airdrop, coupon, sports/prediction resolution, slashing, gas refund,
      auto-compound, interest accrual, settlement at expiry, mark-to-market price move).
      Owner: strategy-service PassiveLedger synthesiser.
    """

    INSTRUCTION = "instruction"
    PASSIVE = "passive"


class EventType(StrEnum):
    """Closed-set event type discriminant for LedgerRow routing.

    Instruction-driven (EventOrigin.INSTRUCTION) — 19 values:
    - TRADE / SWAP / TRANSFER / STAKE / UNSTAKE / BORROW / REPAY / BRIDGE /
      SUPPLY / WITHDRAW / WRAP / UNWRAP / EARLY_EXERCISE / CASH_OUT /
      DEPOSIT / WITHDRAWAL_TO_BANK / CUSTODY_MOVE / FX_CONVERSION / LIQUIDATION

    Passive (EventOrigin.PASSIVE) — 18 values:
    - FUNDING_ACCRUAL / DIVIDEND / STAKING_REWARD / LENDING_INTEREST /
      REBASE / VALIDATOR_REWARD / MEV_REWARD / AIRDROP / COUPON /
      SPORTS_RESOLUTION / PREDICTION_RESOLUTION / SLASHING / GAS_REFUND /
      AUTO_COMPOUND / INTEREST_ACCRUAL / SETTLEMENT / EXPIRY / MARK_UPDATE

    Extension requires PR review — changing routing affects PnL reconciliation.

    NOTE — ``MARK_UPDATE`` stays in this single ``EventType`` enum (rather than
    being lifted to a separate ``PricingEventType``) because the codex routing
    table (``codex/02-data/ledger-event-taxonomy.md`` § "Routing Summary")
    discriminates the PricingLedger by ``event_type=MARK_UPDATE`` alone — i.e.
    the PricingLedger reuses the same ``LedgerRow`` schema + same EventType
    enum, just filtered on this value. Splitting the enum would break that
    routing convention and force a second discriminant column.

    NOTE — ``SETTLEMENT`` and ``EXPIRY`` are intentionally distinct per codex:
    SETTLEMENT is the cash-flow event at expiry (futures cash/physical
    delivery; ITM option exercise cash), EXPIRY is the position-zeroing event
    for OTM options. Both carry distinct PnL/attribution semantics so both
    must stay in the closed set.
    """

    # ── Instruction-driven ────────────────────────────────────────────────────
    TRADE = "trade"
    """Fill on a CeFi/DeFi/TradFi/sports/prediction order."""

    SWAP = "swap"
    """DEX swap (Uniswap, Curve, Balancer, Sushi, PancakeSwap, Phoenix, Orca,
    Raydium, Drift) — token-in / token-out atomic exchange. Distinct from
    TRADE because there is no order/fill semantics on-chain — the swap is the
    primitive."""

    TRANSFER = "transfer"
    """On-chain or off-chain asset movement (deposit, withdrawal, sub-account move)."""

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

    SUPPLY = "supply"
    """Lending-protocol supply / deposit of collateral (Aave aToken mint,
    Compound cToken mint, Morpho supply). Receipt token represents the
    supplied position. Distinct from STAKE because the asset earns interest
    rather than staking rewards."""

    WITHDRAW = "withdraw"
    """Lending-protocol withdraw of supplied collateral (aToken / cToken burn).
    Distinct from UNSTAKE which closes a STAKE position."""

    WRAP = "wrap"
    """Wrap native asset into ERC-20 (ETH → WETH, SOL → wSOL) or wrap one
    receipt token into another (stETH → wstETH, eETH → weETH). 1:1 conversion
    with no price discovery."""

    UNWRAP = "unwrap"
    """Inverse of WRAP — burn wrapped token to redeem the underlying."""

    EARLY_EXERCISE = "early_exercise"
    """Holder-initiated early exercise of an American option before expiry.
    Distinct from SETTLEMENT/EXPIRY (passive at-expiry events) because this
    is an explicit agent instruction."""

    CASH_OUT = "cash_out"
    """Prediction-market / sports-book cash-out of an open position before
    resolution (operator-initiated close at the book's current quote).
    Distinct from TRADE because it is a venue-mediated unwind, not an
    order-book fill."""

    DEPOSIT = "deposit"
    """Client funds inflow to a venue/account/wallet from an external source
    (bank wire, on-chain incoming transfer from a non-tracked address).
    Treasury event — feeds TreasuryLedger when counterparty_client_id is
    None."""

    WITHDRAWAL_TO_BANK = "withdrawal_to_bank"
    """Client funds outflow from a venue/account/wallet to an off-platform
    destination (bank wire, on-chain outgoing transfer to a non-tracked
    address). Treasury event — feeds TreasuryLedger when
    counterparty_client_id is None."""

    CUSTODY_MOVE = "custody_move"
    """Movement of assets between custody providers / sub-custodians for the
    same client (Copper ↔ CEFFU ↔ on-chain wallet ↔ KMS-encrypted hot
    wallet). HARD RULE: counterparty_client_id == client_id (client funds
    isolation)."""

    FX_CONVERSION = "fx_conversion"
    """Stablecoin / fiat / currency conversion that is not order-book mediated
    (e.g. on-chain stablecoin swap via a 1:1 oracle, custodian-quoted FX
    fill, USDC ↔ USDT bridge-equivalent). Distinct from TRADE/SWAP to make
    margin / quote-currency attribution explicit."""

    COLLATERAL_POSTED = "collateral_posted"
    """Collateral / margin posted to a venue or protocol to support a position
    (CeFi margin deposit, DeFi supply-as-collateral). Instruction-driven: the
    strategy explicitly moves collateral. Margin-traceability event — pairs with
    a ``TransferIntent`` whose ``transfer_purpose`` is ``MARGIN_DEPOSIT`` /
    ``COLLATERAL_POSTING`` so posted collateral is traceable end-to-end."""

    MARGIN_RELEASED = "margin_released"
    """Collateral / margin released back from a venue or protocol after a
    position closes or de-risks. Pairs with a ``MARGIN_WITHDRAWAL`` /
    ``COLLATERAL_RELEASE`` ``TransferIntent``. Margin-traceability event."""

    LIQUIDATION = "liquidation"
    """Forced liquidation by venue/protocol (partial or full). Counted as
    instruction-driven because the venue's keeper acts as the instructing
    agent on behalf of the protocol, and the resulting fill / collateral
    seizure is order-book / contract-call mediated."""

    # ── Passive — synthesised without an explicit instruction ─────────────────
    FUNDING_ACCRUAL = "funding_accrual"
    """Perpetual funding payment received or paid (CeFi perps: 8h cadence; DeFi: block-level)."""

    DIVIDEND = "dividend"
    """Cash/stock dividend on equity or futures."""

    STAKING_REWARD = "staking_reward"
    """LST/validator staking reward (e.g. stETH rebase aggregate, JitoSOL yield)."""

    LENDING_INTEREST = "lending_interest"
    """Aave/Compound/Morpho interest accrual on supplied collateral."""

    REBASE = "rebase"
    """Token-supply rebase event (stETH, ampleforth-style). Balance changes
    without a transfer — synthesised from the liquidity-index / share-price
    delta between two blocks. Distinct from STAKING_REWARD because rebase is
    the per-block mechanism; STAKING_REWARD is the aggregate yield label."""

    VALIDATOR_REWARD = "validator_reward"
    """Direct validator block / attestation reward credited to a tracked
    validator (native ETH/SOL staking, NOT via an LST). Synthesised from
    consensus-layer events for ETH (beacon-chain) or epoch-end credits for
    SOL."""

    MEV_REWARD = "mev_reward"
    """Maximal Extractable Value reward — proposer / searcher tip credited
    outside the staking reward stream (e.g. Flashbots block-builder
    payments). Distinct from VALIDATOR_REWARD because the cash flow path and
    tax treatment differ."""

    AIRDROP = "airdrop"
    """Token airdrop received without an explicit claim instruction (push
    airdrop) OR initial credit balance from a passive-eligibility snapshot.
    Pull-airdrop claims are TRADE/SWAP events."""

    COUPON = "coupon"
    """Bond/note coupon payment received (TradFi fixed income). Periodic
    fixed cash flow tied to a bond holding."""

    SPORTS_RESOLUTION = "sports_resolution"
    """Sports-market settlement at event conclusion — winning / losing
    selection cash flow credited / debited. Distinct from SETTLEMENT
    (futures/options-style) because the resolution oracle, fee model, and
    risk semantics are sports-book specific."""

    PREDICTION_RESOLUTION = "prediction_resolution"
    """Prediction-market binary contract resolution (Polymarket CLOB, Kalshi).
    YES/NO shares settle to 1.00 / 0.00 at resolution. Distinct from
    SETTLEMENT for the same reason as SPORTS_RESOLUTION."""

    SLASHING = "slashing"
    """Validator slashing penalty (native staking) or protocol-penalty debit
    (LST slashing-pass-through, lending bad-debt socialisation).
    Negative-cash-flow passive event."""

    GAS_REFUND = "gas_refund"
    """Gas refund event — EIP-3529 SSTORE-clear refund, L2 sequencer refund,
    or relayer rebate credited after the originating transaction. Linked via
    parent_event_id to the original on-chain event."""

    AUTO_COMPOUND = "auto_compound"
    """Vault / yield-aggregator auto-compound event — protocol re-stakes
    accrued rewards into the supplied position (Yearn harvest, ERC-4626
    autocompound, Morpho MetaMorpho rebalance). Increases position balance
    without a STAKE/SUPPLY instruction from us."""

    INTEREST_ACCRUAL = "interest_accrual"
    """Generic interest accrual for non-lending-protocol contexts — CeFi
    margin-account interest, money-market-fund yield, custodian-paid cash
    interest. Distinct from LENDING_INTEREST (Aave/Compound/Morpho specific)
    so the cash-flow source and attribution differ."""

    SETTLEMENT = "settlement"
    """Futures/options settlement at expiry — cash flow for cash-settled
    contracts OR physical delivery accounting. The ITM cash-flow counterpart
    to EXPIRY."""

    EXPIRY = "expiry"
    """Options expiry — position zeroed at zero value (OTM). The position-
    zeroing counterpart to SETTLEMENT; kept distinct because no cash flow
    occurs and PnL attribution differs (premium decay realises fully)."""

    MARK_UPDATE = "mark_update"
    """Mark price / IV / greek snapshot update — **PricingLedger only**
    (MTDS writer). Routes via discriminator `event_type == MARK_UPDATE` per
    codex routing summary; do not split this into a separate enum."""


class AssetClass(StrEnum):
    """Asset class discriminant for LedgerRow.asset_class.

    Drives attribution bucketing, margin calculations, and passive-event synthesis.
    17 values.
    """

    SPOT_TOKEN = "spot_token"
    """CEX spot or plain ERC-20/SPL token (non-stablecoin)."""

    STABLE = "stable"
    """Stablecoin (USDC, USDT, DAI, USDe, PYUSD, FDUSD, USDS). Held distinct
    from SPOT_TOKEN because peg-deviation risk, attribution against quote
    currency, and treasury-management semantics differ."""

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

    ETF = "etf"
    """Exchange-traded fund share (TradFi: SPY, QQQ, IBIT etc.). Held distinct
    from SPOT_TOKEN because dividend handling, settlement venue, and
    regulatory treatment differ from on-chain spot tokens."""

    NFT = "nft"
    """Non-fungible token (ERC-721 / ERC-1155). Held primarily for collateral
    and protocol-rewards positions; unit semantics (delta is always integer
    1) differ from fungible asset classes."""

    PREDICTION_CONTRACT = "prediction_contract"
    """Binary prediction market contract (Polymarket CLOB, Kalshi)."""

    SPORTS_OUTCOME = "sports_outcome"
    """Sports betting outcome / odds contract."""

    CURRENCY = "currency"
    """Fiat currency used as quote / margin. (Stablecoins → STABLE.)"""

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
