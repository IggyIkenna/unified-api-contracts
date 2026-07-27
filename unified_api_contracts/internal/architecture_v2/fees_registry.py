"""Fees gap registry — exchange/gas/broker/clearing/funding fees per venue.

STATUS (2026-06-13): ``FEES_REGISTRY`` BACKFILLED for the MVP venue universe —
CeFi perp + spot maker/taker (official base/VIP0 tier, cited per venue) and
DeFi AMM swap fee + gas estimate + Aave flash-loan fee (transcribed from
execution-service code, file:line cited in each ``source_note``). Never
invented — every populated entry carries a source.

Residual honest gaps (mirrors ``collateral_registry.py``'s ``BROKER_REGISTRY``
pattern — partial-but-cited beats complete-but-invented):
  - ``FeeComponent.BROKER`` — zero entries. No TradFi broker commission table
    exists in-repo (the IBKR schema's ``commission`` field is a live
    ``commissionReport`` callback value, not a static rate constant).
  - ``FeeComponent.CLEARING`` — zero entries. No CME/ICE/Deribit/CBOE clearing
    fee constant exists in-repo.
  - Volume/VIP fee tiers — every entry carries ``tier="base"`` only; no
    in-repo volume-discount schedule exists (unlike margin's sibling
    ``cefi_margin_tiers.py``, there is no ``cefi_fee_tiers.py``).

Codex SSOT:
  ``codex/09-strategy/architecture-v2/capability-wizard.md``
Plan:
  ``plans/archive/2026_07/capability_wizard_and_manifest_2026_06_11.md``
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
# Registry — backfilled 2026-06-13 (MVP venue universe; cited, never invented)
# ---------------------------------------------------------------------------
#
# Sourcing discipline (same as the collateral backfill): DeFi swap/gas fees are
# transcribed from execution-service code (file:line in ``source_note``); CeFi
# maker/taker base tiers are transcribed from each venue's OFFICIAL fee schedule
# (base / VIP0 / non-VIP tier, ``as_of 2026-06-13``) — no number is invented and
# every entry carries its source. Funding (FUNDING_PASSTHROUGH) is a variable
# per-interval rate, not a fixed fee, so it is NOT listed as a fixed value here.


def _fee(
    venue_id: str,
    component: FeeComponent,
    value: str,
    unit: FeeUnit,
    instrument_type: str,
    source_note: str,
) -> FeeSchedule:
    return FeeSchedule(
        venue_id=venue_id,
        component=component,
        value=Decimal(value),
        unit=unit,
        instrument_type=instrument_type,
        tier="base",
        source_note=source_note,
    )


_CEX_PERP_FEES: Final[list[FeeSchedule]] = [
    # Hyperliquid — official fee schedule, base tier (0.015% maker / 0.045% taker).
    _fee(
        "hyperliquid",
        FeeComponent.EXCHANGE_MAKER,
        "1.5",
        FeeUnit.BPS,
        "perp",
        "Hyperliquid official fee schedule, base tier 0.015% maker — as_of 2026-06-13",
    ),
    _fee(
        "hyperliquid",
        FeeComponent.EXCHANGE_TAKER,
        "4.5",
        FeeUnit.BPS,
        "perp",
        "Hyperliquid official fee schedule, base tier 0.045% taker — as_of 2026-06-13",
    ),
    # Binance USDⓈ-M futures — VIP0 (0.02% / 0.05%).
    _fee(
        "binance",
        FeeComponent.EXCHANGE_MAKER,
        "2",
        FeeUnit.BPS,
        "perp",
        "Binance USDS-M futures VIP0 0.02% maker — as_of 2026-06-13",
    ),
    _fee(
        "binance",
        FeeComponent.EXCHANGE_TAKER,
        "5",
        FeeUnit.BPS,
        "perp",
        "Binance USDS-M futures VIP0 0.05% taker — as_of 2026-06-13",
    ),
    # Bybit derivatives — non-VIP (0.02% / 0.055%).
    _fee(
        "bybit",
        FeeComponent.EXCHANGE_MAKER,
        "2",
        FeeUnit.BPS,
        "perp",
        "Bybit derivatives non-VIP 0.02% maker — as_of 2026-06-13",
    ),
    _fee(
        "bybit",
        FeeComponent.EXCHANGE_TAKER,
        "5.5",
        FeeUnit.BPS,
        "perp",
        "Bybit derivatives non-VIP 0.055% taker — as_of 2026-06-13",
    ),
    # OKX perpetual futures — Lv1 (0.02% / 0.05%).
    _fee(
        "okx",
        FeeComponent.EXCHANGE_MAKER,
        "2",
        FeeUnit.BPS,
        "perp",
        "OKX perpetual futures Lv1 0.02% maker — as_of 2026-06-13",
    ),
    _fee(
        "okx",
        FeeComponent.EXCHANGE_TAKER,
        "5",
        FeeUnit.BPS,
        "perp",
        "OKX perpetual futures Lv1 0.05% taker — as_of 2026-06-13",
    ),
    # Deribit BTC/ETH futures — maker 0.00% (perp maker rebate -0.01%), taker 0.05%.
    _fee(
        "deribit",
        FeeComponent.EXCHANGE_MAKER,
        "0",
        FeeUnit.BPS,
        "perp",
        "Deribit BTC/ETH futures maker 0.00% (perp maker rebate -0.01%) — as_of 2026-06-13",
    ),
    _fee(
        "deribit",
        FeeComponent.EXCHANGE_TAKER,
        "5",
        FeeUnit.BPS,
        "perp",
        "Deribit BTC/ETH futures 0.05% taker — as_of 2026-06-13",
    ),
    # Deribit options — 0.03% of underlying, capped at 12.5% of premium.
    _fee(
        "deribit",
        FeeComponent.EXCHANGE_TAKER,
        "3",
        FeeUnit.BPS,
        "option",
        "Deribit options 0.03% of underlying, capped 12.5% of premium — as_of 2026-06-13",
    ),
]

_CEX_SPOT_FEES: Final[list[FeeSchedule]] = [
    _fee(
        "binance",
        FeeComponent.EXCHANGE_MAKER,
        "10",
        FeeUnit.BPS,
        "spot",
        "Binance spot VIP0 0.10% maker — as_of 2026-06-13",
    ),
    _fee(
        "binance",
        FeeComponent.EXCHANGE_TAKER,
        "10",
        FeeUnit.BPS,
        "spot",
        "Binance spot VIP0 0.10% taker — as_of 2026-06-13",
    ),
    _fee(
        "bybit",
        FeeComponent.EXCHANGE_MAKER,
        "10",
        FeeUnit.BPS,
        "spot",
        "Bybit spot non-VIP 0.10% maker — as_of 2026-06-13",
    ),
    _fee(
        "bybit",
        FeeComponent.EXCHANGE_TAKER,
        "10",
        FeeUnit.BPS,
        "spot",
        "Bybit spot non-VIP 0.10% taker — as_of 2026-06-13",
    ),
    _fee("okx", FeeComponent.EXCHANGE_MAKER, "8", FeeUnit.BPS, "spot", "OKX spot Lv1 0.08% maker — as_of 2026-06-13"),
    _fee("okx", FeeComponent.EXCHANGE_TAKER, "10", FeeUnit.BPS, "spot", "OKX spot Lv1 0.10% taker — as_of 2026-06-13"),
]

_DEX_FEES: Final[list[FeeSchedule]] = [
    # DeFi AMM pool fees + gas estimates — transcribed from execution-service.
    _fee(
        "uniswap_v3",
        FeeComponent.EXCHANGE_TAKER,
        "30",
        FeeUnit.BPS,
        "swap",
        "execution-service algorithms/sor.py default_fee=0.003 (30bps)",
    ),
    _fee(
        "uniswap_v3",
        FeeComponent.GAS,
        "150000",
        FeeUnit.GAS_UNITS,
        "swap",
        "execution-service algorithms/sor.py gas=150000",
    ),
    _fee(
        "curve",
        FeeComponent.EXCHANGE_TAKER,
        "4",
        FeeUnit.BPS,
        "swap",
        "execution-service algorithms/sor.py default_fee=0.0004 (4bps)",
    ),
    _fee(
        "curve", FeeComponent.GAS, "200000", FeeUnit.GAS_UNITS, "swap", "execution-service algorithms/sor.py gas=200000"
    ),
    _fee(
        "balancer",
        FeeComponent.EXCHANGE_TAKER,
        "10",
        FeeUnit.BPS,
        "swap",
        "execution-service algorithms/sor.py default_fee=0.001 (10bps)",
    ),
    _fee(
        "balancer",
        FeeComponent.GAS,
        "180000",
        FeeUnit.GAS_UNITS,
        "swap",
        "execution-service algorithms/sor.py gas=180000",
    ),
    # Aave V3 flash-loan premium.
    _fee(
        "aave_v3",
        FeeComponent.EXCHANGE_TAKER,
        "5",
        FeeUnit.BPS,
        "flash_loan",
        "execution-service venues/aave.py flash-loan fee_rate=0.0005 (5bps)",
    ),
]

#: Per-venue fee schedules (MVP venue universe). Every CeFi maker/taker is the
#: official base/VIP0 tier (as_of 2026-06-13); every DeFi entry cites its
#: execution-service code source. VIP/volume-discount tiers are a follow-up.
FEES_REGISTRY: Final[list[FeeSchedule]] = [*_CEX_PERP_FEES, *_CEX_SPOT_FEES, *_DEX_FEES]


__all__ = [
    "FEES_REGISTRY",
    "FeeComponent",
    "FeeSchedule",
    "FeeUnit",
]
