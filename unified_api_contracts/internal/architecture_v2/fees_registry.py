"""Fees gap registry — exchange/gas/broker/clearing/funding fees per venue.

STATUS: schema shipped; ``FEES_REGISTRY`` is intentionally empty because
per-venue fee schedules (maker/taker tiers, gas units, broker rates) are not
derivable from existing UAC constants or docs without a dedicated per-venue
code scan.

Honest ``not_registered`` gap — the manifest emits this dimension as missing
rather than omitting it.

Codex SSOT:
  ``codex/09-strategy/architecture-v2/capability-wizard.md``
Plan:
  ``plans/active/capability_wizard_and_manifest_2026_06_11.md``
  Phase 2 [SPEC] P1.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FeeComponent(StrEnum):
    """The type of fee this schedule entry describes.

    Used by the wizard to build the full fee stack at a given size
    (Stage F question: "Full fee stack at my size").
    """

    EXCHANGE_MAKER = "exchange_maker"
    """Exchange rebate or fee charged when an order adds liquidity."""

    EXCHANGE_TAKER = "exchange_taker"
    """Exchange fee charged when an order removes liquidity."""

    GAS = "gas"
    """On-chain gas cost (DeFi). Value expressed in ``gas_units`` or USD."""

    BROKER = "broker"
    """TradFi broker commission."""

    CLEARING = "clearing"
    """Clearing-house fee (TradFi, e.g. CME clearing)."""

    FUNDING_PASSTHROUGH = "funding_passthrough"
    """Perp funding rate passed through to the position P&L."""


class FeeUnit(StrEnum):
    """Unit in which a fee value is expressed."""

    BPS = "bps"
    """Basis points (1 bps = 0.01 %). Most exchange maker/taker fees."""

    ABSOLUTE = "absolute"
    """Absolute amount in the settlement currency (USD, USDT, etc.)."""

    GAS_UNITS = "gas_units"
    """Raw EVM/SVM gas units. Convert to USD at runtime using gas price."""


# ---------------------------------------------------------------------------
# Fee schedule model
# ---------------------------------------------------------------------------


class FeeSchedule(BaseModel):
    """A single fee schedule entry for a (venue, component, [instrument_type]) cell.

    Tier-granular entries may be added by populating ``tier``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue_id: str = Field(
        description=(
            "Venue identifier matching the instruments-service / "
            "ENDPOINT_REGISTRY convention (e.g. ``'hyperliquid'``, "
            "``'binance'``, ``'interactive_brokers'``)."
        )
    )
    component: FeeComponent = Field(description="Which component of the fee stack this entry describes.")
    value: Decimal = Field(
        description=(
            "Numeric fee value. Interpretation depends on ``unit``. "
            "For ``bps``: 5 = 0.05 %. "
            "For ``absolute``: amount in settlement currency. "
            "For ``gas_units``: estimated gas units per transaction."
        )
    )
    unit: FeeUnit = Field(description="Unit for the ``value`` field.")
    instrument_type: str | None = Field(
        default=None,
        description=(
            "Optional instrument-type scope for this schedule entry "
            "(e.g. ``'perp'``, ``'spot'``, ``'option'``). "
            "``None`` = applies to all instrument types at this venue."
        ),
    )
    tier: str | None = Field(
        default=None,
        description=(
            "Optional trading-tier label (e.g. ``'VIP1'``, ``'level_2'``). ``None`` = default / un-tiered rate."
        ),
    )
    source_note: str = Field(
        default="",
        description=(
            "Where this fee was sourced from. Required when ``value`` is "
            "populated (e.g. ``'Binance spot fee schedule 2026-05'``)."
        ),
    )


# ---------------------------------------------------------------------------
# Registry — intentionally empty (honest gap)
# ---------------------------------------------------------------------------

#: Per-venue fee schedules.
#: Empty: per-venue fee tiers are not derivable from existing UAC constants
#: without a dedicated per-venue code scan. The manifest will emit
#: ``not_registered`` edges for this dimension until entries are backfilled.
FEES_REGISTRY: Final[list[FeeSchedule]] = []


__all__ = [
    "FEES_REGISTRY",
    "FeeComponent",
    "FeeSchedule",
    "FeeUnit",
]
