"""Universal LedgerRow base model + 4-SSOT-ledger type aliases.

All four SSOT ledgers (Instruction / Passive / Treasury / Pricing) share the
same :class:`LedgerRow` schema. Type discriminants (:attr:`LedgerRow.event_origin`
and :attr:`LedgerRow.event_type`) route rows to the correct derived-ledger
computation in strategy-service.

HARD RULE: :attr:`LedgerRow.counterparty_client_id`, when set, MUST equal
:attr:`LedgerRow.client_id`. The validator :func:`assert_no_cross_client_transfer`
raises :exc:`CrossClientTransferForbiddenError` for any row that violates this.
Funds NEVER move between clients (custody + legal boundary). SSOT:
``codex/04-architecture/client-funds-isolation.md``.

SSOT plan: ``plans/active/global_ledger_pnl_attribution_discovery_2026_05_21.md``
Phase 2 — UAC schema spec (draft — migration sub-plan forthcoming).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ._enums import AssetClass, Direction, EventOrigin, EventType, OptionRight


class CrossClientTransferForbiddenError(RuntimeError):
    """Raised when a LedgerRow implies a cross-client fund movement.

    ``counterparty_client_id``, when set, MUST equal ``client_id``.
    Funds NEVER move between clients — each client is a separately-managed
    account under its own custody / legal entity.
    See SSOT: ``codex/04-architecture/client-funds-isolation.md``.
    """

    def __init__(self, client_id: str, counterparty_client_id: str) -> None:
        super().__init__(
            f"Cross-client transfer forbidden: client_id={client_id!r} "
            f"!= counterparty_client_id={counterparty_client_id!r}. "
            "Funds may never move between clients."
        )
        self.client_id = client_id
        self.counterparty_client_id = counterparty_client_id


def assert_no_cross_client_transfer(client_id: str, counterparty_client_id: str | None) -> None:
    """Assert that counterparty belongs to the same client as the actor.

    Call this at every transfer/bridge row construction site.
    Raises :exc:`CrossClientTransferForbiddenError` if the assertion fails.
    """
    if counterparty_client_id is not None and counterparty_client_id != client_id:
        raise CrossClientTransferForbiddenError(client_id, counterparty_client_id)


class LedgerRow(BaseModel):
    """Universal SSOT ledger row — shared by all four SSOT ledgers.

    One row = one asset delta on one account at one point in time.
    Multi-asset transactions (e.g. DeFi swap: ETH out, USDC in) produce
    one row per asset, linked by a shared ``event_id`` + distinct ``row_id``
    suffixes (``<event_id>.0``, ``<event_id>.1``, …).

    Routing:
    - ``event_origin=INSTRUCTION`` → InstructionLedger (execution-service writer)
    - ``event_origin=PASSIVE, event_type in {FUNDING_ACCRUAL, …}`` → PassiveLedger
    - ``event_type=MARK_UPDATE`` → PricingLedger (MTDS writer)
    - Treasury events (deposits, withdrawals with ``counterparty_client_id=None``) →
      TreasuryLedger (strategy-service writer — see Phase 4 TreasuryLedger split decision)

    ``parent_event_id`` linkage convention
    ──────────────────────────────────────
    Set whenever a row is derived from or corrects an earlier row:

    1. **Settlement rows** — futures/options settled at expiry. The settlement
       row's ``parent_event_id`` = the original TRADE or STAKE ``event_id`` that
       opened the position.  ``event_type=SETTLEMENT`` or ``EXPIRY``.

    2. **Funding accrual rows** — perpetual funding payments.
       ``parent_event_id`` = the TRADE ``event_id`` of the perp fill that created
       the position being funded. Allows join back to the opening fill for
       per-position P&L attribution.

    3. **Dividend rows** — cash or stock dividends on equity positions.
       ``parent_event_id`` = the TRADE ``event_id`` of the buy fill on the ex-date.

    4. **Staking reward / lending interest rows** — passive yield on staked or
       lent assets.  ``parent_event_id`` = the STAKE or BORROW ``event_id`` that
       opened the earning position.

    5. **Late-arriving enrichment rows** — data known only after settlement
       (e.g. final fee, FX rate lock, clearing-house ID).  Append a NEW row
       with ``parent_event_id`` = the original ``event_id`` and
       ``event_type=<same_type>_ENRICHMENT`` (provisional — see Phase 3
       late-arriving-data discipline decision).  Do NOT mutate the original row.

    When ``parent_event_id`` is ``None``, the row is an autonomous originating
    event (a trade fill, a bridge, a mark update).

    Greek + carry-family rate columns (PricingLedger MARK_UPDATE enrichment)
    ──────────────────────────────────────────────────────────────────────────
    The following nullable :class:`~decimal.Decimal` columns are populated by
    greeks-service when emitting :attr:`EventType.MARK_UPDATE` rows for
    options / futures / perps. They are :data:`None` on every other
    ``event_type`` (and on MARK_UPDATE rows for instruments where they don't
    apply, e.g. spot equity has no greeks; non-perp spot has no
    ``funding_rate``):

    - **Greeks** (option / derivative sensitivities):
      ``option_delta`` (∂P/∂S — note: the asset-quantity field ``delta`` is
      distinct and predates this field; greeks-service emits ``option_delta``
      to avoid collision), ``gamma`` (∂²P/∂S²), ``theta`` (∂P/∂t per day),
      ``vega`` (∂P/∂Vol), ``rho`` (∂P/∂r).

    - **Carry-family rates** (per-unit-time rates affecting forward
      valuation): ``funding_rate`` (perp funding — MTDS ``perp_funding``),
      ``lending_rate`` (supply APR — MTDS ``lending_indices.liquidity_rate``),
      ``borrow_rate`` (variable APR — MTDS
      ``lending_indices.variable_borrow_rate``), ``staking_apy`` (LST/native
      APY — MTDS ``staking_yields.apy`` or ``lst_rates`` derived),
      ``dividend_yield`` (annualised, from IS ``CanonicalCorporateAction``;
      per-event accrual ALSO emitted as a PassiveLedger ``DIVIDEND`` row),
      ``rebase_rate`` (per-snapshot LST ``exchange_rate`` delta — cumulative
      ``exchange_rate`` lives in IS ``lst_rates``; per-event accrual ALSO
      emitted as a PassiveLedger ``STAKING_REWARD`` /
      ``LENDING_INTEREST`` row).

    ``accrual_period_start_utc`` / ``accrual_period_end_utc`` convention
    ─────────────────────────────────────────────────────────────────────
    Required on every ``EventOrigin.PASSIVE`` row.  ``None`` on INSTRUCTION rows.

    The pair represents the closed interval ``[start, end)`` during which the
    passive cash flow accrued, in UTC:

    - **FUNDING_ACCRUAL** — CeFi perps: 8-hour funding window
      (e.g. 00:00→08:00, 08:00→16:00, 16:00→00:00 UTC for Binance / Bybit /
      OKX). DeFi perps (Hyperliquid, Drift): block-level accrual; start =
      previous block timestamp, end = current block timestamp.

    - **DIVIDEND** — start = ex-dividend date 00:00 UTC;
      end = payment date 00:00 UTC.

    - **STAKING_REWARD** — LST rebase (stETH): start = previous oracle report
      block timestamp, end = current oracle report block timestamp.
      Validator yield (JitoSOL, mSOL): start = epoch start, end = epoch end.

    - **LENDING_INTEREST** — Aave / Compound / Morpho: start = previous
      liquidity-index snapshot block timestamp, end = current block timestamp.
      For daily summaries: start = 00:00 UTC of day, end = 00:00 UTC next day.

    The ``accrual_period_end_utc`` SHOULD equal ``timestamp_utc`` for rows
    where the payment is realised at the period boundary.  For look-back
    enrichments written after the fact, ``timestamp_utc`` reflects the original
    event time and the accrual pair reflects the true earning window.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # ── Identity & discriminators ──────────────────────────────────────────────
    event_id: str = Field(
        description=(
            "Globally unique event identifier. On-chain: tx_hash. Off-chain: exec_id. Settlement: settlement_id."
        )
    )
    row_id: str = Field(
        description=("Unique per row within a multi-asset event. Format: '<event_id>.<n>' where n is 0-based index.")
    )
    event_origin: EventOrigin
    event_type: EventType
    trade_id: str | None = Field(
        default=None,
        description="Logical strategy/structure group (e.g. carry trade pair id).",
    )
    strategy_id: str | None = Field(
        default=None,
        description=(
            "Canonical @-qualified strategy id (ARCHETYPE@slot-label) for cross-ledger "
            "grouping/drilldown. None for non-strategy rows."
        ),
    )
    leg_id: str | None = Field(
        default=None,
        description="Leg within a trade_id (e.g. 'long_leg', 'hedge_leg').",
    )
    parent_event_id: str | None = Field(
        default=None,
        description=(
            "Links derived rows to the originating event. "
            "Settlement rows → trade event_id; funding rows → perp fill event_id; "
            "dividend rows → buy fill event_id; staking/lending rows → stake/borrow event_id; "
            "enrichment rows → original event_id. None on autonomous originating events. "
            "See class docstring for full linkage convention."
        ),
    )
    timestamp_utc: datetime = Field(
        description="Event timestamp in UTC. Naive datetimes are rejected.",
    )

    # ── Where ─────────────────────────────────────────────────────────────────
    asset_group: str = Field(
        description="Asset group discriminant: cefi | defi | tradfi | sports | prediction.",
    )
    venue: str = Field(
        description="Canonical venue name (e.g. 'BINANCE-FUTURES', 'AAVE_V3', 'CME').",
    )
    chain: str | None = Field(
        default=None,
        description="EVM chain name for on-chain events (e.g. 'ethereum', 'arbitrum', 'solana').",
    )
    chain_tx_hash: str | None = Field(
        default=None,
        description="On-chain transaction hash (hex with 0x prefix for EVM, base58 for Solana).",
    )
    chain_block_number: int | None = Field(
        default=None,
        description="Block number at which the on-chain event was confirmed.",
    )
    gas_paid_native: Decimal | None = Field(
        default=None,
        description="Gas fee in the chain's native token (wei for EVM, lamports for Solana).",
    )
    gas_currency: str | None = Field(
        default=None,
        description="Native token symbol for gas_paid_native (e.g. 'ETH', 'SOL', 'MATIC').",
    )

    # ── Account / counterparty ─────────────────────────────────────────────────
    account_id: str = Field(
        description="Exchange sub-account or on-chain wallet address.",
    )
    client_id: str = Field(
        description=(
            "Owning client. HARD RULE: counterparty_client_id must equal this "
            "when set. Funds never move between clients."
        ),
    )
    counterparty_account: str | None = Field(
        default=None,
        description="Counterparty exchange account or destination wallet address.",
    )
    counterparty_client_id: str | None = Field(
        default=None,
        description=(
            "Counterparty's client_id. MUST equal client_id when set. CrossClientTransferForbiddenError if violated."
        ),
    )

    # ── Asset moved ────────────────────────────────────────────────────────────
    asset_symbol: str = Field(
        description="Human-readable asset symbol (e.g. 'USDC', 'stETH', 'NGZ26P3.50').",
    )
    asset_canonical_id: str = Field(
        description=(
            "Canonical asset identifier: on-chain contract address (ERC-20) | "
            "OCC symbol | CUSIP | ISIN | prediction event slug."
        ),
    )
    asset_class: AssetClass
    delta: Decimal = Field(
        description="Signed quantity delta: positive = received, negative = sent.",
    )
    price: Decimal | None = Field(
        default=None,
        description="Quote-currency price per unit at execution time.",
    )
    quote_currency: str | None = Field(
        default=None,
        description="Quote currency for price and fees_in_quote (e.g. 'USDT', 'USD').",
    )
    fees_in_quote: Decimal | None = Field(
        default=None,
        description="Total fees charged in quote_currency (exchange fee + gas FX-converted).",
    )

    # ── Instrument detail (nullable per asset_class) ──────────────────────────
    underlying: str | None = Field(
        default=None,
        description="Underlying asset symbol for derivatives and prediction contracts.",
    )
    expiry_date: date | None = Field(
        default=None,
        description="Contract expiry date (UTC) for futures, options, and binary contracts.",
    )
    option_right: OptionRight | None = Field(
        default=None,
        description="Option right: C (call) or P (put). None for non-option assets.",
    )
    strike: Decimal | None = Field(
        default=None,
        description="Option strike price in quote_currency.",
    )
    contract_multiplier: int | None = Field(
        default=None,
        description="Number of underlying units per contract (e.g. 100 for equity options).",
    )
    selection: str | None = Field(
        default=None,
        description="Sports/prediction outcome label (e.g. 'HOME_WIN', 'OVER_2.5', 'BTC_UP').",
    )
    direction: Direction | None = Field(
        default=None,
        description="Trade direction in the natural language of the asset class.",
    )

    # ── Combo / structured trade ───────────────────────────────────────────────
    combo_id: str | None = Field(
        default=None,
        description="Identifier for a multi-leg structured transaction.",
    )
    combo_price: Decimal | None = Field(
        default=None,
        description="Net price for the combo (may differ from sum of leg prices).",
    )

    # ── Passive-event-only ────────────────────────────────────────────────────
    accrual_period_start_utc: datetime | None = Field(
        default=None,
        description=(
            "Start of the accrual period for passive events — required on all PASSIVE rows, None on INSTRUCTION rows. "
            "Closed interval [start, end): funding=8h window start; dividend=ex-dividend date 00:00 UTC; "
            "LST rebase=previous oracle report block; validator=epoch start; lending=previous liquidity-index block. "
            "See class docstring for per-event-type convention."
        ),
    )
    accrual_period_end_utc: datetime | None = Field(
        default=None,
        description=(
            "End of the accrual period for passive events — required on all PASSIVE rows, None on INSTRUCTION rows. "
            "Closed interval [start, end): funding=8h window end; dividend=payment date 00:00 UTC; "
            "LST rebase=current oracle report block; validator=epoch end; lending=current block. "
            "SHOULD equal timestamp_utc when payment is realised at the period boundary. "
            "See class docstring for per-event-type convention."
        ),
    )

    # ── Greeks (MARK_UPDATE enrichment for options / derivatives) ────────────
    # Populated by greeks-service for EventType.MARK_UPDATE rows on
    # options / futures / perps; None on every other event_type.
    # NB: the asset-quantity column ``delta`` (signed received/sent) is a
    # distinct, non-greek field defined above and predates these columns —
    # the greek is emitted as ``option_delta`` to avoid collision.
    option_delta: Decimal | None = Field(
        default=None,
        description="∂Price/∂Underlying — first-order price sensitivity (greek delta).",
    )
    gamma: Decimal | None = Field(
        default=None,
        description="∂²Price/∂Underlying² — second-order price sensitivity.",
    )
    theta: Decimal | None = Field(
        default=None,
        description="∂Price/∂Time — time decay (per day).",
    )
    vega: Decimal | None = Field(
        default=None,
        description="∂Price/∂Vol — vol sensitivity.",
    )
    rho: Decimal | None = Field(
        default=None,
        description="∂Price/∂InterestRate — rates sensitivity.",
    )

    # ── Carry-family rates (MARK_UPDATE enrichment from MTDS rate feeds) ─────
    # Per-unit-time rates affecting forward valuation; populated by
    # greeks-service for MARK_UPDATE rows on the relevant instrument.
    # Per-event accrual ALSO flows through PassiveLedger
    # (FUNDING_ACCRUAL / DIVIDEND / STAKING_REWARD / LENDING_INTEREST) rows.
    funding_rate: Decimal | None = Field(
        default=None,
        description="Perp funding rate (CeFi 8h / DeFi block cadence). Source: MTDS perp_funding.",
    )
    lending_rate: Decimal | None = Field(
        default=None,
        description="Lending supply APR. Source: MTDS lending_indices.liquidity_rate.",
    )
    borrow_rate: Decimal | None = Field(
        default=None,
        description="Variable borrow APR. Source: MTDS lending_indices.variable_borrow_rate.",
    )
    staking_apy: Decimal | None = Field(
        default=None,
        description="Staking APY (LST/native). Source: MTDS staking_yields.apy or lst_rates.exchange_rate-derived.",
    )
    dividend_yield: Decimal | None = Field(
        default=None,
        description=(
            "Annualised dividend yield derived from IS CanonicalCorporateAction "
            "(per-event row also emitted as PassiveLedger DIVIDEND)."
        ),
    )
    rebase_rate: Decimal | None = Field(
        default=None,
        description=(
            "Per-snapshot rebase delta (LST exchange_rate delta). Cumulative exchange_rate stays in IS lst_rates."
        ),
    )

    @model_validator(mode="after")
    def _assert_no_cross_client_transfer(self) -> LedgerRow:
        """Enforce HARD RULE: counterparty_client_id must equal client_id."""
        assert_no_cross_client_transfer(self.client_id, self.counterparty_client_id)
        return self


# ── 4 SSOT ledger type aliases ─────────────────────────────────────────────────
# These are semantic aliases of LedgerRow, not subclasses.
# Partition key in GCS: ledger_type=instruction|passive|treasury|pricing
# Each ledger is written by its designated service (see SSOT plan Phase 2).

#: InstructionLedger: rows where event_origin=INSTRUCTION.
#: Writer: execution-service. Partition: ledger_type=instruction.
InstructionLedger = LedgerRow

#: PassiveLedger: rows where event_origin=PASSIVE.
#: Writer: strategy-service PassiveLedger synthesiser. Partition: ledger_type=passive.
PassiveLedger = LedgerRow

#: TreasuryLedger: rows for client fund inflows/outflows (deposits, withdrawals).
#: Writer: strategy-service or execution-service (split decision pending Phase 4).
#: Partition: ledger_type=treasury.
TreasuryLedger = LedgerRow

#: PricingLedger: rows where event_type=MARK_UPDATE (mid/bid/ask/IV/greek snapshots).
#: Writer: MTDS. Partition: ledger_type=pricing.
PricingLedger = LedgerRow
