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

    Late-arriving enrichments: append a new row with ``parent_event_id`` set to the
    original ``event_id`` and ``event_type=<same type>_ENRICHMENT`` (provisional —
    see Phase 3 late-arriving-data discipline decision).
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
    leg_id: str | None = Field(
        default=None,
        description="Leg within a trade_id (e.g. 'long_leg', 'hedge_leg').",
    )
    parent_event_id: str | None = Field(
        default=None,
        description=(
            "Links settlement/funding/dividend rows to the originating event. "
            "Also used for late-arriving enrichment rows."
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
            "Start of the accrual period for passive events (funding, dividend, "
            "staking reward, lending interest). Required on all PASSIVE rows."
        ),
    )
    accrual_period_end_utc: datetime | None = Field(
        default=None,
        description="End of the accrual period for passive events.",
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
