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

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

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
