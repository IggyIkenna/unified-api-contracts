"""Canonical instrument record and related enums for reference data.

This is the SSOT for InstrumentRecord — all repos that need instrument
definitions import from here.

Schema design
-------------
22 stored fields (down from 36). Fields derivable from UAC venue mappings
(symbol, settlement_asset, data_source_constraint, etc.) are removed.
``asset_class`` is set explicitly by URDI adapters using the UAC registry
(per-instrument, not per-venue — e.g. ES futures are equity, CL futures
are commodity, even though both trade on CME).

Enums live in ``unified_api_contracts._instrument_enums`` (cycle-free module)
and are re-exported here so that ``from .internal.reference.instrument import
InstrumentType`` still works everywhere.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

# Re-export enums from cycle-free SSOT module.
from unified_api_contracts._instrument_enums import (
    AssetClass as AssetClass,
)
from unified_api_contracts._instrument_enums import (
    InstrumentStatus as InstrumentStatus,
)
from unified_api_contracts._instrument_enums import (
    InstrumentType as InstrumentType,
)
from unified_api_contracts._instrument_enums import (
    MarginType as MarginType,
)
from unified_api_contracts._instrument_enums import (
    OptionType as OptionType,
)

# Closed-set instrument-type buckets used by InstrumentRecord's
# per-asset-group model_validator (hard_schema_enforcement_2026_05_08
# Phase 1, slot 5 2026-05-11). Module-level rather than class-level so
# Pydantic v2 doesn't treat them as ``ModelPrivateAttr`` descriptors.
CEFI_PAIR_INSTRUMENT_TYPES: frozenset[InstrumentType] = frozenset({InstrumentType.SPOT_PAIR, InstrumentType.PERPETUAL})
"""CeFi spot/perp instrument types. Workspace rule: base_asset + quote_asset
must be non-empty (trading pair identity). Enforced by InstrumentRecord
model_validator."""

DEFI_ONCHAIN_INSTRUMENT_TYPES: frozenset[InstrumentType] = frozenset(
    {
        InstrumentType.POOL,
        InstrumentType.LENDING,
        InstrumentType.LST,
        InstrumentType.YIELD_BEARING,
        InstrumentType.A_TOKEN,
        InstrumentType.DEBT_TOKEN,
        InstrumentType.STAKING,
        InstrumentType.SPOT_ASSET,
        # DeFi DOES have on-chain perps (operator-locked 2026-06-01): Drift /
        # GMX / Hyperliquid are on-chain perp DEXs, so ``instrument_type=
        # perpetual`` is valid for ``asset_group=defi``. NOTE: PERPETUAL is
        # also in CEFI_PAIR_INSTRUMENT_TYPES, and the InstrumentRecord
        # model_validator checks CeFi-pair FIRST (if/elif), so a DeFi perp's
        # base/quote-asset rule is applied via the CeFi-pair branch — adding
        # it here is for membership consumers (partition-path coercion etc.)
        # and does not change validator behaviour. SSOT:
        # ``codex/02-data/defi-canonical-naming-ssot.md``.
        InstrumentType.PERPETUAL,
    }
)
"""DeFi on-chain instrument types. Workspace rule: at least one on-chain
identifier (pool_address OR base_asset_contract_address) must be non-empty.
Enforced by InstrumentRecord model_validator. Includes PERPETUAL for DeFi
on-chain perp DEXs (Drift/GMX/Hyperliquid; operator-locked 2026-06-01)."""


class InstrumentLeg(BaseModel):
    """A single leg of a multi-leg combo/spread instrument.

    Each leg references another InstrumentRecord by instrument_key.
    The referenced instrument carries its own underlying, strike, expiry, etc.
    """

    instrument_key: str = Field(description="instrument_key of the leg instrument")
    side: str = Field(description="BUY or SELL (long or short the leg)")
    ratio: int = Field(default=1, description="Leg ratio (e.g., 2 in a 1x2 ratio spread)")


class InstrumentRecord(BaseModel):
    """Canonical instrument definition for reference data adapters.

    Used by all URDI adapters to represent normalised instrument metadata
    fetched from exchange REST APIs.

    Serialization contract (model → parquet)
    ----------------------------------------
    InstrumentRecord fields are aligned 1:1 with INSTRUMENTS_PARQUET_SCHEMA
    column names. Type flattening on write:

        Decimal  → str  (parquet string column)
        enum     → str  (enum.value, e.g. InstrumentType.FUTURE → "FUTURE")
        datetime → datetime64[ns]  (timezone-naive UTC)
        bool     → bool
        str      → str

    Key field mappings (all now aligned):
        InstrumentRecord.available_from_datetime  ↔ parquet available_from_datetime
        InstrumentRecord.available_to_datetime    ↔ parquet available_to_datetime
        InstrumentRecord.min_size                 ↔ parquet min_size
        InstrumentRecord.settle_asset             ↔ parquet settle_asset
        InstrumentRecord.margin_type              ↔ parquet margin_type (str: LINEAR/INVERSE/QUANTO)
    """

    # --- Universal fields (all categories) ---
    instrument_key: str = Field(description="Unique identifier: VENUE:TYPE:SYMBOL")
    venue: str
    instrument_type: InstrumentType
    raw_symbol: str = ""
    base_asset: str = ""
    quote_asset: str = ""
    # --- Canonical product identity (additive; populated by TradFi/Databento
    #     adapters from the UAC exchange-code registry — EXCHANGE_CODE_TO_NAME /
    #     DatabentoInstrumentDef.base_asset). Optional + additive so existing
    #     CeFi/DeFi rows and the model_validator are unaffected (non-breaking:
    #     added-optional-field). ``raw_symbol`` stays the raw exchange contract
    #     code; these surface the human-canonical product so options/futures can
    #     bundle by product root even when the raw code is per-contract. ---
    canonical_instrument_id: str | None = Field(
        default=None,
        description=(
            "Human-canonical instrument identifier derived from the product root "
            "(e.g. 'CME:OPTION:SP500:2025-10:5000C'). None for instruments whose "
            "adapter does not resolve a canonical root."
        ),
    )
    product_root: str | None = Field(
        default=None,
        description=(
            "Human-canonical product root from the UAC exchange-code registry "
            "(e.g. exchange code 'ES' → 'SP500'). None when no registry mapping resolves."
        ),
    )
    # Additive + optional (non-breaking: added-optional-field), same pattern as
    # canonical_instrument_id above. Human-readable market question / title — TODAY
    # populated only by the PREDICTION adapters (Polymarket ``question`` /
    # Kalshi ``title — yes_sub_title``), which already resolve it at parse time but
    # had no field to persist it into (pydantic's default extra='ignore' silently
    # DROPPED it — that is why the prediction catalogue label fell back to the raw
    # slug). None for every instrument whose adapter does not resolve one.
    # Plan: data_status_page_ux_and_canonicalisation_2026_07_16 A4 (forward-only).
    question: str | None = Field(
        default=None,
        description=(
            "Human-readable market question / title (prediction markets: Polymarket "
            "'question' / Kalshi 'title — yes_sub_title'). None when the adapter "
            "resolves no human title (the raw symbol/slug remains the label floor)."
        ),
    )
    status: InstrumentStatus = InstrumentStatus.ACTIVE
    available_from_datetime: datetime | None = Field(
        default=None,
        description="Earliest date instrument data is available from source",
    )
    available_to_datetime: datetime | None = Field(
        default=None,
        description="Latest date instrument data is available (None = still active)",
    )

    # --- Market domain (set by adapter from UAC registry) ---
    asset_class: AssetClass = AssetClass.CRYPTO

    # --- Settlement (explicit — derivation is wrong for quanto contracts) ---
    settle_asset: str | None = None

    # --- Trading params (CeFi/TradFi, None for DeFi) ---
    tick_size: Decimal | None = None
    min_size: Decimal | None = None
    contract_size: Decimal | None = None

    # --- Derivatives (futures/options only) ---
    expiry: datetime | None = None
    strike: Decimal | None = None
    option_type: OptionType | None = None
    # AMERICAN | EUROPEAN — required by PassiveLedger synthesiser to distinguish
    # early-exercise (instruction event) from expiry-without-action (passive event).
    # Populated by Databento adapter from definition.exercise_style; None for non-options
    # and for options where the source does not provide this field.
    exercise_style: str | None = None
    underlying: str | None = None
    margin_type: MarginType | None = None

    # --- Multi-leg (COMBO instruments only) ---
    legs: list[InstrumentLeg] | None = Field(
        default=None,
        description="Leg definitions for COMBO instruments. Each leg references another instrument.",
    )

    # --- Session metadata (TradFi only, None for CeFi/DeFi) ---
    is_trading_day: bool | None = Field(default=None, description="Whether the instrument trades on the target date")
    regular_open_utc: str | None = Field(default=None, description="Regular session open as ISO datetime in UTC")
    regular_close_utc: str | None = Field(default=None, description="Regular session close as ISO datetime in UTC")
    early_close_utc: str | None = Field(
        default=None, description="Early close time as ISO datetime in UTC (shortened days)"
    )
    pre_market_open_utc: str | None = Field(default=None, description="Pre-market session open as ISO datetime in UTC")
    post_market_close_utc: str | None = Field(
        default=None, description="Post-market session close as ISO datetime in UTC"
    )
    auction_open_utc: str | None = Field(default=None, description="Opening auction start as ISO datetime in UTC")
    auction_close_utc: str | None = Field(default=None, description="Closing auction start as ISO datetime in UTC")
    holiday_calendar: str | None = Field(
        default=None, description="Exchange calendar key (e.g. XNYS, XCME) for exchange_calendars lib"
    )
    timezone: str | None = Field(
        default=None, description="Exchange timezone (e.g. America/New_York, America/Chicago, UTC)"
    )

    # --- DeFi metadata (DEX pools, lending markets, vaults; None for CeFi/TradFi) ---
    # Aligned 1:1 with INSTRUMENTS_PARQUET_SCHEMA. Several columns already
    # existed in the parquet schema (pool_address, pool_fee_tier,
    # base_asset_contract_address, quote_asset_contract_address) but were
    # not surfaced on this pydantic model — adapters had to populate them
    # via dict pass-through and they got dropped on serialisation. Lifting
    # them onto the model + adding genuinely-new fields lets MTDS DeFi
    # handlers (dex_pool_state, dex_pool_swaps, lending_indices, liquidations)
    # consume them instead of re-querying The Graph each cycle.
    # Plan: instruments_service_metadata_refactor_2026_04_29.
    pool_address: str | None = Field(
        default=None,
        description="DEX pool / lending reserve / vault / market contract address",
    )
    pool_fee_tier: int | None = Field(
        default=None,
        description="DEX pool fee in basis points (Uniswap V3 feeTier / 100, Balancer pool fee, etc.)",
    )
    base_asset_contract_address: str | None = Field(
        default=None,
        description="ERC-20 contract address for base_asset (DEX token0 / lending underlying)",
    )
    quote_asset_contract_address: str | None = Field(
        default=None,
        description="ERC-20 contract address for quote_asset (DEX token1; None for single-asset markets)",
    )
    base_asset_decimals: int | None = Field(default=None, description="Decimals for base_asset (ERC-20)")
    base_asset_symbol_onchain: str | None = Field(
        default=None, description="On-chain ERC-20 symbol for base_asset (may differ from canonical base_asset)"
    )
    quote_asset_decimals: int | None = Field(default=None, description="Decimals for quote_asset (ERC-20)")
    quote_asset_symbol_onchain: str | None = Field(default=None, description="On-chain ERC-20 symbol for quote_asset")
    atoken_address: str | None = Field(
        default=None,
        description="Aave aToken address (interest-bearing supply receipt)",
    )
    debt_token_address: str | None = Field(
        default=None,
        description="Aave variable-debt token address",
    )
    rate_method_selector: str | None = Field(
        default=None,
        description="On-chain method selector for rate queries (LST contracts); optional parity field",
    )

    # --- Archive metadata (MTDS handler URL/universe derivation — is_mtds_contract_audit_2026_05_20) ---
    # MTDS handlers MUST derive fetch URLs from these fields. Hardcoding is banned.
    source_archive_url_template: str | None = Field(
        default=None,
        description=(
            "URL template for historical data archive "
            "(e.g. 'https://drift-historical-data-v2.s3.eu-west-1.amazonaws.com/program/{program_id}/"
            "market/{market}/{record_type}/{year}/{day}'). "
            "MTDS handlers derive fetch URLs from this field — never hardcode URLs in handlers."
        ),
    )
    source_record_types: dict[str, str] | None = Field(
        default=None,
        description=(
            "Mapping of data_type → archive record-type name "
            "(e.g. {'trades': 'tradeRecords', 'funding_rate': 'fundingRateRecords'}). "
            "Serialised as JSON string in parquet."
        ),
    )
    source_coverage_start: dict[str, date] | None = Field(
        default=None,
        description=(
            "Per-data_type archive coverage start date "
            "(e.g. {'trades': date(2020, 9, 14)}). "
            "Dates before this trigger EXPECTED_PRE_SOURCE_COVERAGE_START. "
            "Serialised as JSON string {data_type: 'YYYY-MM-DD'} in parquet."
        ),
    )
    source_coverage_end: dict[str, date] | None = Field(
        default=None,
        description=(
            "Per-data_type archive coverage end date "
            "(e.g. {'trades': date(2025, 1, 8)} for Drift tradeRecords). "
            "Dates after this trigger EXPECTED_PAST_SOURCE_COVERAGE_END. "
            "Serialised as JSON string {data_type: 'YYYY-MM-DD'} in parquet."
        ),
    )
    listed_at: date | None = Field(
        default=None,
        description=(
            "Date instrument was listed/launched. "
            "Pre-listing dates trigger EXPECTED_INSTRUMENT_NOT_LISTED. "
            "Serialised as ISO date string 'YYYY-MM-DD' in parquet."
        ),
    )
    delisted_at: date | None = Field(
        default=None,
        description=(
            "Date instrument was delisted/expired. "
            "Post-delisting dates trigger EXPECTED_INSTRUMENT_DELISTED. "
            "Serialised as ISO date string 'YYYY-MM-DD' in parquet."
        ),
    )

    # ─────────────────────────────────────────────────────────────────
    # Per-asset-group hard-required field enforcement
    # (hard_schema_enforcement_2026_05_08 Phase 1 — slot 5 RE-TASK 2026-05-11)
    # ─────────────────────────────────────────────────────────────────
    # Pydantic model_validator(mode="after") enforces the per-asset-group
    # contract that workspace rules require but the schema doesn't yet
    # type-enforce. Per CLAUDE.md "Honest absence vs fake placeholders" +
    # "Shard-granularity SSOT" — adapters writing empty/null on required
    # fields produces silent data corruption downstream (1440-NaN-bar
    # incident 2026-05-05 was the canonical failure mode).
    #
    # Five asset-group rules enforced as of 2026-05-19 (all asset groups
    # complete per hard_schema_enforcement_2026_05_08 Phase 1):
    # Sports fixture_id enforcement is complete at the domain-schema level —
    # `canonical/domain/sports/{fixture_stats,lineup,events,injury,player_stats}.py`
    # all declare `fixture_id: str` (Pydantic required non-nullable; no default).
    # No InstrumentRecord rule needed: sports instruments use `instrument_key`
    # to encode fixture identity. See Phase 1 roadmap item 5 in the plan.
    #
    # 1. CeFi spot/perp (SPOT_PAIR / PERPETUAL): base_asset + quote_asset
    #    must be non-empty. These are the trading pair identity; empty
    #    means the adapter silently wrote a header-only row.
    # 2. DeFi on-chain (POOL / LENDING / LST / YIELD_BEARING / A_TOKEN /
    #    DEBT_TOKEN / STAKING / SPOT_ASSET): pool_address OR
    #    base_asset_contract_address must be non-empty. At least one
    #    on-chain identifier is required to reach the protocol.
    # 3. EVENT_CONTRACT (CME × Polymarket cross-venue arb per
    #    cme_polymarket_arb_2026_05_08): expiry must be non-null
    #    (resolution_date is the shard-atom dimension).
    #
    # Violations raise ValueError; downstream MTDS / instruments-service
    # adapters' per-row try/except routes them to
    # `record_failed(reason=RecordFailedReason.SCHEMA_VALIDATION_FAILED)`
    # (RecordFailedReason taxonomy shipped UAC@cb70b3a per slot 5
    # earlier today). Per-row routing wires in Phase 2 of
    # hard_schema_enforcement_2026_05_08; this commit ships the
    # type-system half (Phase 1).

    @model_validator(mode="after")
    def _enforce_per_asset_group_required_fields(self) -> "InstrumentRecord":
        """Per-asset-group hard-required field validator.

        Raises ``ValueError`` if a workspace-rule-required field is empty/null
        for the row's ``instrument_type``. Adapters catch the ValueError at
        the per-row try/except and route to
        ``record_failed(reason=RecordFailedReason.SCHEMA_VALIDATION_FAILED,
        ...)`` per the writegate Phase 2 + hard_schema_enforcement Phase 2
        contract.

        Closed-set rules (all complete as of 2026-05-19):

        * CeFi spot/perp → base_asset + quote_asset non-empty (slot 5 2026-05-11).
        * DeFi on-chain → pool_address OR base_asset_contract_address non-empty (slot 5 2026-05-11).
        * DeFi on-chain → base_asset_decimals non-null for all DEFI_ONCHAIN types (slot 4 2026-05-19).
        * DeFi POOL → quote_asset_decimals non-null (two-asset; slot 4 2026-05-19).
        * EVENT_CONTRACT → expiry non-null (resolution_date axis; slot 5 2026-05-11).
        * FUTURE → expiry non-null (tradfi_master Q1 gate passed 2026-05-13; slot 8 2026-05-19).
        * OPTION → expiry non-null (tradfi_master Q2 gate passed 2026-05-13; slot 8 2026-05-19).
        * Sports fixture_id: complete at domain-schema level — sports per-fixture schemas
          (fixture_stats, lineup, events, injury, player_stats) declare ``fixture_id: str``
          (Pydantic required non-nullable). No InstrumentRecord rule needed: sports instruments
          encode fixture identity in ``instrument_key``. (slot 4 2026-05-19)
        """
        # CeFi spot/perp rule
        if self.instrument_type in CEFI_PAIR_INSTRUMENT_TYPES:
            if not self.base_asset:
                raise ValueError(
                    f"InstrumentRecord(instrument_type={self.instrument_type.value}) "
                    f"requires non-empty base_asset; got {self.base_asset!r}. "
                    f"Workspace rule: CeFi spot/perp must have a trading pair identity. "
                    f"Per hard_schema_enforcement_2026_05_08 Phase 1."
                )
            if not self.quote_asset:
                raise ValueError(
                    f"InstrumentRecord(instrument_type={self.instrument_type.value}) "
                    f"requires non-empty quote_asset; got {self.quote_asset!r}. "
                    f"Workspace rule: CeFi spot/perp must have a trading pair identity. "
                    f"Per hard_schema_enforcement_2026_05_08 Phase 1."
                )
        # DeFi on-chain rule
        elif self.instrument_type in DEFI_ONCHAIN_INSTRUMENT_TYPES:
            has_pool = bool(self.pool_address)
            has_base_addr = bool(self.base_asset_contract_address)
            if not (has_pool or has_base_addr):
                raise ValueError(
                    f"InstrumentRecord(instrument_type={self.instrument_type.value}) "
                    f"requires at least one on-chain identifier: pool_address or "
                    f"base_asset_contract_address. Got pool_address={self.pool_address!r}, "
                    f"base_asset_contract_address={self.base_asset_contract_address!r}. "
                    f"Workspace rule: DeFi on-chain instruments must be reachable. "
                    f"Per hard_schema_enforcement_2026_05_08 Phase 1."
                )
            # Rule 6: base_asset_decimals required for all DeFi on-chain types
            if self.base_asset_decimals is None:
                raise ValueError(
                    f"InstrumentRecord(instrument_type={self.instrument_type.value}) "
                    f"requires non-null base_asset_decimals. "
                    f"Workspace rule: DeFi on-chain price normalisation requires primary token "
                    f"decimals (18 for most ERC-20s, 6 for USDC, 8 for WBTC). "
                    f"Null decimals = silent price normalisation bug. "
                    f"Per hard_schema_phase1_field_flip_migration_2026_05_19 Phase A."
                )
            # Rule 7: quote_asset_decimals required for POOL only (two-asset types)
            if self.instrument_type == InstrumentType.POOL and self.quote_asset_decimals is None:
                raise ValueError(
                    f"InstrumentRecord(instrument_type={InstrumentType.POOL.value}) "
                    f"requires non-null quote_asset_decimals (two-asset pool: token0 + token1). "
                    f"Workspace rule: POOL instruments require both token decimals for price "
                    f"computation. Single-asset DeFi types (LENDING/LST/etc.) may omit. "
                    f"Per hard_schema_phase1_field_flip_migration_2026_05_19 Phase A."
                )
        # EVENT_CONTRACT rule (CME × Polymarket cross-venue arb)
        elif self.instrument_type == InstrumentType.EVENT_CONTRACT:
            if self.expiry is None:
                raise ValueError(
                    f"InstrumentRecord(instrument_type={InstrumentType.EVENT_CONTRACT.value}) "
                    f"requires non-null expiry (resolution_date axis). "
                    f"Workspace rule: event contracts shard by (root, resolution_date) per "
                    f"cme_polymarket_arb_2026_05_08 Phase 3+4."
                )
        # TradFi FUTURE rule — tradfi_master Q1 gate passed 2026-05-13
        elif self.instrument_type == InstrumentType.FUTURE:
            if self.expiry is None:
                raise ValueError(
                    f"InstrumentRecord(instrument_type={InstrumentType.FUTURE.value}) "
                    f"requires non-null expiry (contract expiry datetime). "
                    f"Workspace rule: futures instruments shard by expiry for contract roll detection. "
                    f"Per hard_schema_enforcement_2026_05_08 Phase 1 (tradfi_master Q1 gate passed 2026-05-13)."
                )
        # TradFi OPTION rule — tradfi_master Q2 gate passed 2026-05-13
        elif self.instrument_type == InstrumentType.OPTION:
            if self.expiry is None:
                raise ValueError(
                    f"InstrumentRecord(instrument_type={InstrumentType.OPTION.value}) "
                    f"requires non-null expiry (option expiration datetime). "
                    f"Workspace rule: option instruments shard by (root, expiry, strike) per "
                    f"hard_schema_enforcement_2026_05_08 Phase 1 (tradfi_master Q2 gate passed 2026-05-13)."
                )
        return self
