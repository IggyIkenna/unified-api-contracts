"""Cost & capacity model — full fee stack, breakeven AUM, capacity ceiling.

Wave-2 enhancement #8 of the capability-wizard plan (operator signed off
2026-06-13). For a configured strategy (a set of venues x instrument types),
this module computes:

* the **full per-trade fee stack** (exchange maker/taker from
  ``FEES_REGISTRY``, on-chain gas from ``FEES_REGISTRY`` GAS units x a
  caller-supplied gas price, caller-supplied slippage, and a variable
  funding-passthrough rate),
* the **annualised total cost** of running the strategy at a given notional,
* the **breakeven AUM** — the AUM at which a configured gross edge exactly
  covers the annualised cost, and
* a **capacity-ceiling** note (parameterised by venue min-ticket / liquidity
  inputs — an HONEST gap where per-venue liquidity data is absent).

Sourcing discipline (HARD)
--------------------------
NEVER invent a number. Every FIXED value comes from a cited registry:

* exchange maker/taker bps + DeFi gas units  -> ``FEES_REGISTRY``
  (``fees_registry.py``; each entry self-cites in ``source_note``).

Everything else is a typed INPUT parameter whose docstring names its
source/owner, because it is genuinely variable or caller-predicted:

* ``funding_rate_bps``    — variable per-interval perp funding (market data;
  owner: market-tick-data-service funding feed). NOT a fixed registry number.
* ``slippage_bps``        — execution-cost-prediction OUTPUT (owner:
  execution-service cost predictor). A caller-supplied estimate, never invented
  here.
* ``gas_price_gwei`` + ``native_token_price_usd`` — live chain gas price + the
  native-token USD price (owner: on-chain gas oracle / pricing feed). Convert
  registry GAS units to USD at runtime; both are inputs (a fixed gas price
  would be an invented number).
* ``infra_cost_usd_per_day`` — per-``lifecycle_class`` infrastructure
  cost-to-serve (owner: deployment-service / commercial model). Parameterised
  honestly: there is NO single committed per-lifecycle_class USD/day constant
  in ``codex/05-infrastructure`` (cost depends on machine type x cloud x
  region), so the caller supplies it. See
  ``codex/14-customer-journeys/commercial-model/`` for cost-build worksheets.
* ``gross_edge_bps_per_year`` — the strategy's expected gross annual edge in
  bps of deployed notional (owner: the backtest / strategy spec). Drives
  breakeven.

Codex SSOT:
  ``codex/09-strategy/architecture-v2/capability-wizard.md``
Plan:
  ``plans/active/capability_wizard_and_manifest_2026_06_11.md`` Wave-2 #8.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.canonical.crosscutting.lifecycle_class import LifecycleClass
from unified_api_contracts.internal.architecture_v2.fees_registry import (
    FEES_REGISTRY,
    FeeComponent,
    FeeSchedule,
    FeeUnit,
)

# ---------------------------------------------------------------------------
# Conversion constants (mathematical identities — NOT invented market numbers)
# ---------------------------------------------------------------------------

#: Basis points per unit fraction (1 = 10_000 bps). A definitional identity.
_BPS_PER_UNIT: Final[Decimal] = Decimal("10000")

#: Gwei per native-token unit (1 ETH = 1e9 gwei). EVM definitional identity.
_GWEI_PER_NATIVE_TOKEN: Final[Decimal] = Decimal("1000000000")


# ---------------------------------------------------------------------------
# Per-venue fee-component breakdown
# ---------------------------------------------------------------------------


class VenueFeeBreakdown(BaseModel):
    """The fee stack for ONE (venue, instrument_type) cell at a given notional.

    All ``*_usd`` fields are the cost of a SINGLE round-trip-eligible fill of
    ``notional`` USD (taker-side, the conservative assumption). The bps fields
    are transcribed from ``FEES_REGISTRY`` (cited there); funding/slippage are
    caller-supplied inputs (see module docstring).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue_id: str = Field(description="Venue identifier (``FEES_REGISTRY`` convention).")
    instrument_type: str = Field(description="Instrument type this breakdown covers (e.g. ``'perp'``, ``'swap'``).")
    notional_usd: Decimal = Field(description="Notional this breakdown was computed for (USD).")

    taker_fee_bps: Decimal = Field(
        description="Exchange taker fee in bps, from FEES_REGISTRY (0 if the venue has no taker entry)."
    )
    taker_fee_usd: Decimal = Field(description="``taker_fee_bps`` applied to ``notional_usd``.")

    slippage_bps: Decimal = Field(
        description="Caller-supplied execution-cost-prediction slippage estimate (bps). NOT invented here."
    )
    slippage_usd: Decimal = Field(description="``slippage_bps`` applied to ``notional_usd``.")

    funding_bps: Decimal = Field(
        description=(
            "Caller-supplied per-trade funding-passthrough rate (bps), variable market data. "
            "0 for non-funding instruments."
        )
    )
    funding_usd: Decimal = Field(description="``funding_bps`` applied to ``notional_usd``.")

    gas_usd: Decimal = Field(
        description=(
            "On-chain gas cost in USD = FEES_REGISTRY GAS units x ``gas_price_gwei`` x ``native_token_price_usd``. "
            "0 for venues with no GAS entry (CeFi)."
        )
    )

    total_usd: Decimal = Field(description="Sum of taker + slippage + funding + gas for this cell.")


# ---------------------------------------------------------------------------
# Top-level model
# ---------------------------------------------------------------------------


class CostCapacityModel(BaseModel):
    """Computed cost & capacity model for a configured strategy.

    Frozen, ``extra='forbid'``, Decimal throughout — a deterministic pure
    function of its inputs (no I/O, no clock, no randomness).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # --- echoed inputs (provenance) ---
    venues: tuple[str, ...] = Field(description="Venue ids the model was computed over.")
    instrument_types: tuple[str, ...] = Field(description="Instrument types the model was computed over.")
    notional_usd: Decimal = Field(description="Per-fill notional the fee stack was computed at (USD).")
    funding_rate_bps: Decimal = Field(
        description="INPUT: variable funding-passthrough rate (bps). See module docstring."
    )
    slippage_bps: Decimal = Field(description="INPUT: caller-supplied slippage estimate (bps). See module docstring.")
    gas_price_gwei: Decimal = Field(description="INPUT: live chain gas price (gwei). See module docstring.")
    native_token_price_usd: Decimal = Field(
        description="INPUT: native-token (e.g. ETH) USD price for gas conversion. See module docstring."
    )
    infra_cost_usd_per_day: Decimal = Field(
        description="INPUT: per-lifecycle_class infra cost-to-serve (USD/day). Parameterised honestly."
    )
    infra_lifecycle_class: LifecycleClass = Field(
        description="The lifecycle class ``infra_cost_usd_per_day`` is attributed to."
    )
    gross_edge_bps_per_year: Decimal = Field(
        description="INPUT: expected gross annual edge in bps of deployed notional (backtest/strategy spec)."
    )
    trades_per_year: Decimal = Field(description="INPUT: expected fills per year (drives annualised trading cost).")

    # --- computed ---
    per_venue: tuple[VenueFeeBreakdown, ...] = Field(description="Per-(venue, instrument_type) fee breakdown.")
    total_fee_stack_usd: Decimal = Field(
        description="Sum of all per-cell ``total_usd`` for ONE pass over the configured venues (per-fill cost)."
    )
    total_fee_stack_bps: Decimal = Field(description="``total_fee_stack_usd`` expressed in bps of ``notional_usd``.")
    annualised_trading_cost_usd: Decimal = Field(
        description="``total_fee_stack_usd`` x ``trades_per_year`` — the variable cost of trading for a year."
    )
    annualised_infra_cost_usd: Decimal = Field(
        description="``infra_cost_usd_per_day`` x 365 — the fixed cost of running for a year."
    )
    annualised_total_cost_usd: Decimal = Field(
        description="``annualised_trading_cost_usd`` + ``annualised_infra_cost_usd``."
    )
    breakeven_aum_usd: Decimal | None = Field(
        description=(
            "AUM at which gross edge covers annualised total cost: "
            "``annualised_total_cost_usd / (gross_edge_bps_per_year / 10_000)``. "
            "``None`` when ``gross_edge_bps_per_year <= 0`` (no positive edge -> breakeven undefined)."
        )
    )
    capacity_ceiling_usd: Decimal | None = Field(
        description=(
            "HONEST GAP: per-venue liquidity / order-book depth data is NOT in the registries, so an absolute "
            "capacity ceiling cannot be computed from sourced numbers. ``None`` unless the caller supplies a "
            "liquidity bound; see ``capacity_ceiling_note``."
        )
    )
    capacity_ceiling_note: str = Field(
        description="Free-text explanation of the capacity-ceiling gap and what input would close it."
    )


# ---------------------------------------------------------------------------
# Registry lookup helpers (concrete typing — no Any)
# ---------------------------------------------------------------------------


def _taker_bps_for(venue_id: str, instrument_type: str) -> Decimal:
    """Exchange taker fee (bps) for a (venue, instrument_type) from FEES_REGISTRY.

    Prefers an entry whose ``instrument_type`` matches exactly; falls back to a
    venue-wide entry (``instrument_type is None``). Returns ``Decimal('0')`` if
    the venue has no taker entry (honest absence, not invented).
    """
    exact: Decimal | None = None
    venue_wide: Decimal | None = None
    for entry in FEES_REGISTRY:
        sched: FeeSchedule = entry
        if sched.venue_id != venue_id or sched.component is not FeeComponent.EXCHANGE_TAKER:
            continue
        if sched.unit is not FeeUnit.BPS:
            continue
        if sched.instrument_type == instrument_type:
            exact = sched.value
        elif sched.instrument_type is None:
            venue_wide = sched.value
    if exact is not None:
        return exact
    if venue_wide is not None:
        return venue_wide
    return Decimal("0")


def _gas_units_for(venue_id: str, instrument_type: str) -> Decimal:
    """On-chain GAS units for a (venue, instrument_type) from FEES_REGISTRY.

    Returns ``Decimal('0')`` for venues without a GAS entry (CeFi venues).
    """
    exact: Decimal | None = None
    venue_wide: Decimal | None = None
    for entry in FEES_REGISTRY:
        sched: FeeSchedule = entry
        if sched.venue_id != venue_id or sched.component is not FeeComponent.GAS:
            continue
        if sched.unit is not FeeUnit.GAS_UNITS:
            continue
        if sched.instrument_type == instrument_type:
            exact = sched.value
        elif sched.instrument_type is None:
            venue_wide = sched.value
    if exact is not None:
        return exact
    if venue_wide is not None:
        return venue_wide
    return Decimal("0")


# ---------------------------------------------------------------------------
# Pure computation
# ---------------------------------------------------------------------------

#: Days per year used to annualise the daily infra cost (calendar year).
_DAYS_PER_YEAR: Final[Decimal] = Decimal("365")


def compute_cost_capacity(
    venues: tuple[str, ...],
    instrument_types: tuple[str, ...],
    notional: Decimal,
    funding_rate_bps: Decimal,
    slippage_bps: Decimal,
    gas_price_gwei: Decimal,
    infra_cost_usd_per_day: Decimal,
    *,
    native_token_price_usd: Decimal,
    infra_lifecycle_class: LifecycleClass = LifecycleClass.LONG_LIVED_LIVE,
    gross_edge_bps_per_year: Decimal = Decimal("0"),
    trades_per_year: Decimal = Decimal("1"),
    capacity_liquidity_bound_usd: Decimal | None = None,
) -> CostCapacityModel:
    """Compute the cost & capacity model for a configured strategy.

    Pure + deterministic: a function only of its arguments. Fixed fee numbers
    are read from ``FEES_REGISTRY`` (cited there); every other value is a typed
    input (see the module docstring for source/owner of each).

    Args:
        venues: Venue ids (``FEES_REGISTRY`` convention) the strategy trades.
        instrument_types: Instrument types traded; the cross product with
            ``venues`` defines the fee-stack cells.
        notional: Per-fill notional in USD.
        funding_rate_bps: Variable per-trade funding-passthrough rate in bps
            (applied only to funding-bearing instrument types: ``'perp'``).
        slippage_bps: Caller-supplied execution-cost-prediction slippage (bps).
        gas_price_gwei: Live chain gas price (gwei) for the DeFi gas conversion.
        infra_cost_usd_per_day: Per-lifecycle_class infra cost-to-serve
            (USD/day) — parameterised honestly (no committed constant).
        native_token_price_usd: Native-token (e.g. ETH) USD price; converts
            registry GAS units to USD.
        infra_lifecycle_class: Lifecycle class the infra cost is attributed to.
        gross_edge_bps_per_year: Expected gross annual edge (bps of notional);
            drives breakeven. ``<= 0`` -> ``breakeven_aum_usd is None``.
        trades_per_year: Expected fills/year (annualises the per-fill cost).
        capacity_liquidity_bound_usd: Optional caller-supplied absolute
            liquidity/min-ticket bound. When ``None`` the capacity ceiling is an
            honest ``None`` gap (registries carry no liquidity data).

    Returns:
        A fully-populated, frozen :class:`CostCapacityModel`.
    """
    gas_per_unit_usd = (gas_price_gwei / _GWEI_PER_NATIVE_TOKEN) * native_token_price_usd

    breakdowns: list[VenueFeeBreakdown] = []
    for venue_id in venues:
        for instrument_type in instrument_types:
            taker_bps = _taker_bps_for(venue_id, instrument_type)
            taker_usd = notional * (taker_bps / _BPS_PER_UNIT)

            slip_usd = notional * (slippage_bps / _BPS_PER_UNIT)

            # Funding only applies to funding-bearing instruments (perps).
            funding_bps = funding_rate_bps if instrument_type == "perp" else Decimal("0")
            funding_usd = notional * (funding_bps / _BPS_PER_UNIT)

            gas_units = _gas_units_for(venue_id, instrument_type)
            gas_usd = gas_units * gas_per_unit_usd

            cell_total = taker_usd + slip_usd + funding_usd + gas_usd
            breakdowns.append(
                VenueFeeBreakdown(
                    venue_id=venue_id,
                    instrument_type=instrument_type,
                    notional_usd=notional,
                    taker_fee_bps=taker_bps,
                    taker_fee_usd=taker_usd,
                    slippage_bps=slippage_bps,
                    slippage_usd=slip_usd,
                    funding_bps=funding_bps,
                    funding_usd=funding_usd,
                    gas_usd=gas_usd,
                    total_usd=cell_total,
                )
            )

    total_fee_stack_usd = sum((b.total_usd for b in breakdowns), Decimal("0"))
    total_fee_stack_bps = (total_fee_stack_usd / notional) * _BPS_PER_UNIT if notional > Decimal("0") else Decimal("0")

    annualised_trading_cost_usd = total_fee_stack_usd * trades_per_year
    annualised_infra_cost_usd = infra_cost_usd_per_day * _DAYS_PER_YEAR
    annualised_total_cost_usd = annualised_trading_cost_usd + annualised_infra_cost_usd

    breakeven_aum_usd: Decimal | None
    if gross_edge_bps_per_year > Decimal("0"):
        edge_fraction = gross_edge_bps_per_year / _BPS_PER_UNIT
        breakeven_aum_usd = annualised_total_cost_usd / edge_fraction
    else:
        breakeven_aum_usd = None

    if capacity_liquidity_bound_usd is not None:
        capacity_ceiling_usd: Decimal | None = capacity_liquidity_bound_usd
        capacity_ceiling_note = (
            "Capacity ceiling = caller-supplied liquidity/min-ticket bound "
            f"({capacity_liquidity_bound_usd} USD). Registries do not carry per-venue order-book depth; "
            "this bound is an execution/market-data input, not a sourced registry number."
        )
    else:
        capacity_ceiling_usd = None
        capacity_ceiling_note = (
            "HONEST GAP: no per-venue liquidity / order-book-depth / min-ticket data exists in FEES_REGISTRY or "
            "COLLATERAL_REGISTRY, so an absolute capacity ceiling cannot be computed from sourced numbers. "
            "Supply ``capacity_liquidity_bound_usd`` (owner: execution-service market-impact model / venue "
            "liquidity feed) to populate it."
        )

    return CostCapacityModel(
        venues=venues,
        instrument_types=instrument_types,
        notional_usd=notional,
        funding_rate_bps=funding_rate_bps,
        slippage_bps=slippage_bps,
        gas_price_gwei=gas_price_gwei,
        native_token_price_usd=native_token_price_usd,
        infra_cost_usd_per_day=infra_cost_usd_per_day,
        infra_lifecycle_class=infra_lifecycle_class,
        gross_edge_bps_per_year=gross_edge_bps_per_year,
        trades_per_year=trades_per_year,
        per_venue=tuple(breakdowns),
        total_fee_stack_usd=total_fee_stack_usd,
        total_fee_stack_bps=total_fee_stack_bps,
        annualised_trading_cost_usd=annualised_trading_cost_usd,
        annualised_infra_cost_usd=annualised_infra_cost_usd,
        annualised_total_cost_usd=annualised_total_cost_usd,
        breakeven_aum_usd=breakeven_aum_usd,
        capacity_ceiling_usd=capacity_ceiling_usd,
        capacity_ceiling_note=capacity_ceiling_note,
    )


__all__ = [
    "CostCapacityModel",
    "VenueFeeBreakdown",
    "compute_cost_capacity",
]
