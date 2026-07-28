"""Order-semantics gap registry — per-venue TIF, post-only, make/take,
ref-pricing modes, multi-leg delta ownership, and auth-wiring status.

STATUS (2026-06-13): ``VENUE_ORDER_SEMANTICS`` BACKFILLED from a code-scan of
the execution-service venue adapters — every entry cites its source file:line
in ``notes``, nothing invented. Covers hyperliquid/deribit (CeFi perp +
options, fully wired), binance/bybit/okx (CeFi perp, ``NotImplementedError``
scaffolds — BLOCKED-CREDENTIALS), and aave_v3/kamino (DeFi lending, no
CLOB/TIF semantics). See ``tests/unit/test_order_semantics_sim_backfill.py``
for the full coverage assertions.

NOTE on ``TimeInForce``:
  A workspace-wide grep of UAC source confirmed NO existing ``TimeInForce``
  enum. This module defines the canonical UAC ``TimeInForce`` StrEnum.
  If a per-venue module outside UAC defines a local TIF enum, that is a
  **finding** (dual-implementation — report in findings).

``CapabilityEdgeStatus`` is REUSED from ``capability_manifest.py``.
``AtomicExecutionMode`` is REUSED from ``architecture_v2.enums``.

Codex SSOT:
  ``codex/09-strategy/architecture-v2/capability-wizard.md``
Plan:
  ``plans/active/capability_wizard_and_manifest_2026_06_11.md``
  Phase 2 [SPEC] P1.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.internal.architecture_v2.capability_manifest import (
    CapabilityEdgeStatus,
)

# AtomicExecutionMode is the canonical multi-leg execution vocabulary in UAC.
# REUSE — do NOT redefine here.
from unified_api_contracts.internal.architecture_v2.enums import AtomicExecutionMode

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TimeInForce(StrEnum):
    """Time-in-force options for order placement.

    This is the canonical UAC ``TimeInForce`` enum — no duplicate should exist
    elsewhere in the codebase. If one is found, it is a dual-implementation
    finding to remediate (see FINDINGS in the final agent report).

    Stage F wizard question: "TIF: FOK / IOC / post-only? Make or take?"
    """

    GTC = "GTC"
    """Good Till Cancelled — order remains open until filled or cancelled."""

    IOC = "IOC"
    """Immediate or Cancel — fill whatever quantity is available immediately;
    cancel the rest."""

    FOK = "FOK"
    """Fill or Kill — must be filled in full immediately or cancelled entirely."""

    GTD = "GTD"
    """Good Till Date — order remains open until a specified date/time."""

    POST_ONLY = "POST_ONLY"
    """Post-only / maker-only — order is rejected or cancelled if it would
    take liquidity (guarantees maker fee)."""

    REDUCE_ONLY = "REDUCE_ONLY"
    """Reduce-only — order may only reduce an existing position, not open a
    new one (perp venues)."""


class RefPricingMode(StrEnum):
    """Reference-pricing mode for instruction/order entry.

    Stage F wizard question: "Ref pricing: fixed entry, or delta-adjusted
    to underlying (premium-on-delta)?"
    """

    FIXED = "fixed"
    """Entry price is fixed at order submission time. No adjustment for
    underlying moves between instruction generation and execution."""

    DELTA_ADJUSTED_TO_UNDERLYING = "delta_adjusted_to_underlying"
    """Entry price is delta-adjusted relative to underlying movement between
    instruction generation and execution ('premium-on-delta'). Required for
    options and some structured spread trades."""


class MultiLegDeltaOwner(StrEnum):
    """Which component owns the inter-leg delta risk while a multi-leg
    (basis/spread/combo) instruction is being filled.

    Stage F wizard question: "Multi-leg (basis/spread/combo): atomic or
    legged? Who owns inter-leg delta risk while filling?"

    Relates to ``AtomicExecutionMode`` (REUSED from ``architecture_v2.enums``):
    - ``ATOMIC`` / ``ATOMIC_ON_CHAIN`` → no inter-leg delta (fills atomically).
    - ``LEADER_HEDGE`` / ``SEQUENCED_WITH_PACING`` → delta exists between legs;
      ownership is declared by this enum.
    """

    ATOMIC_BUNDLE = "atomic_bundle"
    """The execution algo fires all legs in a single atomic bundle; no exposed
    inter-leg delta (maps to ``AtomicExecutionMode.ATOMIC`` or
    ``AtomicExecutionMode.ATOMIC_ON_CHAIN``)."""

    EXECUTION_ALGO = "execution_algo"
    """The execution algo (SOR, sor_twap, etc.) manages the delta between
    legs during the fill sequence."""

    STRATEGY_ENGINE = "strategy_engine"
    """The strategy engine retains ownership of the inter-leg delta and hedges
    it through subsequent instruction cycles."""

    UNMANAGED = "unmanaged"
    """Inter-leg delta is not managed by any component — the strategy accepts
    the risk. Typically only valid for very short-lived fills."""


# ---------------------------------------------------------------------------
# Venue order semantics model
# ---------------------------------------------------------------------------


class VenueOrderSemantics(BaseModel):
    """Order-semantics capabilities for a single venue.

    Describes what TIF options, post-only mode, make/take preferences,
    ref-pricing modes, and multi-leg delta handling the adapter actually
    honours — as opposed to what the venue's API theoretically supports.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    venue_id: str = Field(
        description=(
            "Venue identifier matching the instruments-service / "
            "ENDPOINT_REGISTRY convention (e.g. ``'hyperliquid'``, "
            "``'binance'``, ``'deribit'``)."
        )
    )
    honored_tif: list[TimeInForce] = Field(
        default_factory=list,
        description=(
            "TIF values that the adapter actually sends and that the venue "
            "honours. Not all TIF values supported by the API may be wired "
            "in the adapter. Empty = not registered."
        ),
    )
    post_only: bool = Field(
        description=(
            "True if the adapter supports post-only order submission "
            "(i.e. ``TimeInForce.POST_ONLY`` is in ``honored_tif`` AND the "
            "venue's post-only mechanism is wired end-to-end)."
        )
    )
    make_take_modes: list[str] = Field(
        default_factory=list,
        description=(
            "Supported make/take execution modes wired in the adapter. "
            "Free-text labels (e.g. ``['make', 'take', 'best_effort']``). "
            "Empty = not registered."
        ),
    )
    ref_pricing_modes: list[RefPricingMode] = Field(
        default_factory=list,
        description=(
            "Ref-pricing modes supported by the adapter for this venue. "
            "Empty = not registered (all instructions use fixed entry by "
            "default if not registered)."
        ),
    )
    multi_leg_delta_owner: MultiLegDeltaOwner | None = Field(
        default=None,
        description=(
            "Which component owns inter-leg delta for multi-leg instructions "
            "on this venue. ``None`` = not registered or not applicable "
            "(venue does not support multi-leg orders)."
        ),
    )
    atomic_execution_modes: list[AtomicExecutionMode] = Field(
        default_factory=list,
        description=(
            "``AtomicExecutionMode`` values supported by this venue's adapter. "
            "Reuses ``AtomicExecutionMode`` from ``architecture_v2.enums``."
        ),
    )
    auth_wired: CapabilityEdgeStatus = Field(
        description=(
            "Auth-wiring status for this venue adapter. "
            "``available`` = credentials can be wired and adapter is functional. "
            "``not_registered`` = adapter exists in the registry but auth "
            "has not been tested end-to-end."
        )
    )
    notes: str = Field(
        default="",
        description=("Free-text notes on adapter limitations, known quirks, and per-venue edge cases."),
    )


# ---------------------------------------------------------------------------
# Registry — backfilled from the execution-service adapter scan (2026-06-13)
# ---------------------------------------------------------------------------

#: Per-venue order-semantics declarations.
#:
#: BACKFILLED 2026-06-13 from a code-scan of the execution-service venue
#: adapters / connectors (every entry cites its source file:line in ``notes``;
#: nothing is invented). CeFi perp order placement lives in
#: ``execution_service/trade_execution/adapters/`` (CCXT + native HMAC
#: adapters); DeFi/options placement lives in ``execution_service/venues/`` +
#: ``execution_service/defi_execution/protocols/``. The canonical adapter TIF
#: enum (``execution_service/trade_execution/order_types.py``) wires only
#: GTC / IOC / FOK / POST_ONLY — GTD / REDUCE_ONLY are NOT adapter-wired on any
#: venue today. ``auth_wired=available`` ⟺ the adapter places orders end-to-end;
#: ``not_registered`` ⟺ scaffold (``NotImplementedError`` on ``place_order``).
#: Source-scan provenance:
#: ``plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`` (the
#: auto-emitted ``gap_registry:order_semantics`` escalation).
VENUE_ORDER_SEMANTICS: Final[list[VenueOrderSemantics]] = [
    VenueOrderSemantics(
        venue_id="hyperliquid",
        honored_tif=[TimeInForce.GTC, TimeInForce.IOC, TimeInForce.FOK],
        post_only=False,
        make_take_modes=["make", "take"],
        ref_pricing_modes=[RefPricingMode.FIXED],
        multi_leg_delta_owner=None,
        atomic_execution_modes=[],
        auth_wired=CapabilityEdgeStatus.AVAILABLE,
        notes=(
            "FULLY WIRED via CCXT (trade_execution/adapters/hyperliquid_ccxt.py:75-76 — "
            "TIF sent only when != GTC). POST_ONLY not explicitly mapped; no reduce_only; "
            "no multi-leg. Auth: CCXT apiKey+secret."
        ),
    ),
    VenueOrderSemantics(
        venue_id="deribit",
        honored_tif=[TimeInForce.GTC, TimeInForce.IOC, TimeInForce.FOK],
        post_only=False,
        make_take_modes=["make", "take"],
        ref_pricing_modes=[RefPricingMode.FIXED],
        multi_leg_delta_owner=None,
        atomic_execution_modes=[],
        auth_wired=CapabilityEdgeStatus.AVAILABLE,
        notes=(
            "FULLY WIRED for perps AND options (venues/deribit_orders.py:238-239 — TIF map "
            "IOC->immediate_or_cancel, FOK->fill_or_kill, default good_til_cancelled; REST via "
            "httpx). Option instrument classification + integer-contract amount conversion wired."
        ),
    ),
    # "drift" (Solana perp DEX) VenueOrderSemantics entry removed 2026-07-16 (operator ruling: all
    # Solana perp DEXes dropped except Jupiter, not integrated).
    # SSOT: unified-trading-pm/codex/04-architecture/solana-defi-coverage.md.
    VenueOrderSemantics(
        venue_id="binance",
        honored_tif=[TimeInForce.GTC, TimeInForce.IOC, TimeInForce.FOK],
        post_only=False,
        make_take_modes=["make", "take"],
        ref_pricing_modes=[RefPricingMode.FIXED],
        multi_leg_delta_owner=None,
        atomic_execution_modes=[],
        auth_wired=CapabilityEdgeStatus.AVAILABLE,
        notes=(
            "FULLY WIRED via CCXT (trade_execution/adapters/binance_ccxt.py:79-113 — real "
            "exchange.create_market_order/create_limit_order calls, same TIF-sent-only-when-!=GTC "
            "shape as hyperliquid_ccxt.py; live-routed by factory.py's CCXT_VENUES dispatch). "
            "CORRECTION 2026-07-28 (cefi_consolidated_native_ao_extract_2026_07_25.md todo 1): this "
            "entry previously read auth_wired=not_registered / SCAFFOLD, but that described "
            "binance_native.py (a separate, NOT live-routed direct-REST scaffold — HMAC-SHA256 "
            "signing implemented, place_order raises NotImplementedError at binance_native.py:326, "
            "referenced only by its own contract tests, BLOCKED-CREDENTIALS, kept as a parked future "
            "migration mirroring kraken_rest_adapter.py's live bypass-CCXT pattern) — it never "
            "described the actually-live CCXT adapter this venue_id resolves to."
        ),
    ),
    VenueOrderSemantics(
        venue_id="bybit",
        honored_tif=[TimeInForce.GTC, TimeInForce.IOC, TimeInForce.FOK],
        post_only=False,
        make_take_modes=["make", "take"],
        ref_pricing_modes=[RefPricingMode.FIXED],
        multi_leg_delta_owner=None,
        atomic_execution_modes=[],
        auth_wired=CapabilityEdgeStatus.AVAILABLE,
        notes=(
            "FULLY WIRED via CCXT (trade_execution/adapters/bybit_ccxt.py:88-98 — real "
            "exchange.create_market_order/create_limit_order calls, same TIF-sent-only-when-!=GTC "
            "shape as hyperliquid_ccxt.py; live-routed by factory.py's CCXT_VENUES dispatch). "
            "CORRECTION 2026-07-28 (cefi_consolidated_native_ao_extract_2026_07_25.md todo 1): this "
            "entry previously read auth_wired=not_registered / SCAFFOLD, but that described "
            "bybit_native.py (a separate, NOT live-routed direct-REST scaffold — v5 API signing "
            "implemented, all methods raise NotImplementedError at bybit_native.py:318, referenced "
            "only by its own contract tests, BLOCKED-CREDENTIALS, kept as a parked future migration "
            "mirroring kraken_rest_adapter.py's live bypass-CCXT pattern) — it never described the "
            "actually-live CCXT adapter this venue_id resolves to."
        ),
    ),
    VenueOrderSemantics(
        venue_id="okx",
        honored_tif=[TimeInForce.GTC, TimeInForce.IOC, TimeInForce.FOK],
        post_only=False,
        make_take_modes=["make", "take"],
        ref_pricing_modes=[RefPricingMode.FIXED],
        multi_leg_delta_owner=None,
        atomic_execution_modes=[],
        auth_wired=CapabilityEdgeStatus.AVAILABLE,
        notes=(
            "FULLY WIRED via CCXT (trade_execution/adapters/okx_ccxt.py:75-81 — real "
            "exchange.create_market_order/create_limit_order calls, same TIF-sent-only-when-!=GTC "
            "shape as hyperliquid_ccxt.py; live-routed by factory.py's CCXT_VENUES dispatch). "
            "CORRECTION 2026-07-28 (cefi_consolidated_native_ao_extract_2026_07_25.md todo 1): this "
            "entry previously read auth_wired=not_registered / SCAFFOLD, but that described "
            "okx_native.py (a separate, NOT live-routed direct-REST scaffold — signing implemented, "
            "place_order raises NotImplementedError at okx_native.py:329, referenced only by its own "
            "contract tests, BLOCKED-CREDENTIALS, kept as a parked future migration mirroring "
            "kraken_rest_adapter.py's live bypass-CCXT pattern) — it never described the actually-live "
            "CCXT adapter this venue_id resolves to."
        ),
    ),
    # gmx_v2 VenueOrderSemantics entry removed 2026-07-25 (unreliable historical
    # funding data — see
    # unified-trading-pm/plans/active/defi_gmx_venue_removal_2026_07_25.md).
    VenueOrderSemantics(
        venue_id="aave_v3",
        honored_tif=[],
        post_only=False,
        make_take_modes=[],
        ref_pricing_modes=[],
        multi_leg_delta_owner=None,
        atomic_execution_modes=[AtomicExecutionMode.ATOMIC_ON_CHAIN],
        auth_wired=CapabilityEdgeStatus.AVAILABLE,
        notes=(
            "Lending venue — no CLOB/TIF order semantics. supply/withdraw/borrow/repay/flash_loan "
            "wired via UDEI AAVEConnector (venues/aave.py). Flash-loan legs execute ATOMIC_ON_CHAIN."
        ),
    ),
    VenueOrderSemantics(
        venue_id="kamino",
        honored_tif=[],
        post_only=False,
        make_take_modes=[],
        ref_pricing_modes=[],
        multi_leg_delta_owner=None,
        atomic_execution_modes=[],
        auth_wired=CapabilityEdgeStatus.AVAILABLE,
        notes=(
            "Lending-only — no CLOB/TIF order semantics. supply()/withdraw() wired "
            "(defi_execution/protocols/kamino.py); no perp trading."
        ),
    ),
]


__all__ = [
    "VENUE_ORDER_SEMANTICS",
    # Re-export the reused enum for convenience.
    "AtomicExecutionMode",
    "MultiLegDeltaOwner",
    "RefPricingMode",
    # Canonical UAC TIF enum — do NOT redefine elsewhere.
    "TimeInForce",
    "VenueOrderSemantics",
]
