"""Multi-leg order capability per venue — G2.9 gap #7.

Stage 3E § 2.9 gap #7 from ``codex/09-strategy/architecture-v2/uac-registry-gaps.md``.
Declares per-venue support for multi-leg / combo orders used by:

* ``VOL_TRADING_OPTIONS`` — calendar spreads, butterflies, straddles,
  iron condors, risk reversals.
* ``STAT_ARB_CROSS_SECTIONAL`` — basket orders (e.g. equity pairs).
* ``MARKET_MAKING_CONTINUOUS`` on options — multi-leg quote submissions.
* ``ATOMIC`` bundled instructions via ``AtomicInstruction``.
* ``BL-10`` — dated-future roll combos (listed calendar-spread tickers
  on CME / Deribit + synthetic combo fallback).

Two orthogonal capability axes:

* ``supports_listed_combos`` — venue exposes combo tickers as a single
  product (e.g. CME ``ESH6-ESU6`` calendar spread).
* ``supports_synthetic_combos`` — venue accepts multi-leg orders as a
  single atomic submission (e.g. Deribit multi-leg orders). When
  neither is true + the archetype needs multiple legs, execution-service
  falls back to a ``LEADER_HEDGE`` pattern with ``leader_hedge_min_interval_ms``
  spacing.

Consumer integration points (Option X — all validation lives at UAC
import + allocator-time; services just call the helpers):

* ``execution-service/execution_service/algo_library/*`` — algo
  capability gating; refuses to deploy a combo algo on a venue with
  ``max_legs < required_legs``.
* ``execution-service/execution_service/v2/handlers.py`` —
  ``AtomicInstruction`` dispatch picks listed-combo path vs synthetic
  path vs leader-hedge fallback.
* Representative-future service (G2.9 gap #11) uses this to decide
  whether a venue exposes a listed calendar-spread combo or requires
  synthesised two-leg roll.

Gates **G2.5** (Execution Algo Catalogue refactor). See
``plans/active/refactor_g2_5_execution_algo_catalogue_refactor_2026_04_20.plan.md``.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field


class ListedComboType(StrEnum):
    """Types of venue-listed combo tickers we know about.

    Expanded from the ad-hoc ``tuple[str, ...]`` in the gap-tracker
    proposal to a typed enum so consumers get editor completion + QG
    enforcement on typos. Venues may support a subset.
    """

    CALENDAR_SPREAD = "calendar_spread"
    """Buy one expiry, sell another (futures) — CME standard combo."""

    BUTTERFLY = "butterfly"
    """3-leg option combo — long body / short wings or vice-versa."""

    IRON_CONDOR = "iron_condor"
    """4-leg option combo — two vertical spreads."""

    RISK_REVERSAL = "risk_reversal"
    """Long call + short put (or vice-versa) — directional with vol tilt."""

    STRADDLE = "straddle"
    """Long / short both a call and a put at the same strike + expiry."""

    STRANGLE = "strangle"
    """Long / short a call and a put at different strikes."""

    VERTICAL_SPREAD = "vertical_spread"
    """2-leg spread at same expiry, different strikes."""

    RATIO_SPREAD = "ratio_spread"
    """Uneven-quantity multi-leg (e.g. 1x3 call ratio)."""


class MultiLegOrderCapability(BaseModel):
    """Per-venue multi-leg / combo order support declaration.

    Attached to a venue either inline on ``VenueCapabilityV2`` (preferred
    long-term) or queried standalone via ``multi_leg_capability_for(venue_id)``.
    ``max_legs == 0`` is the sentinel for "no multi-leg support at all"
    — listed AND synthetic must both be False in that case.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue_id: str
    """Stable venue ID from the venue registry (e.g. "cme", "deribit")."""

    supports_listed_combos: bool
    """Venue exposes venue-listed combo tickers as single products."""

    supports_synthetic_combos: bool
    """Venue accepts multi-leg orders as a single atomic submission."""

    max_legs: int = Field(ge=0, le=32)
    """Maximum legs per combo. 0 == no multi-leg support; 2-4 typical."""

    listed_combo_types: tuple[ListedComboType, ...] = ()
    """Subset of ``ListedComboType`` the venue exposes as listed tickers.
    Empty tuple when ``supports_listed_combos=False``."""

    leader_hedge_min_interval_ms: int = Field(default=0, ge=0)
    """Minimum ms between leg submissions for the LEADER_HEDGE fallback
    when synthetic combos aren't accepted atomically. 0 means N/A."""

    notes: str = ""
    """Free-form author notes; not surfaced in prospect UI."""


MULTI_LEG_ORDER_CAPABILITY_REGISTRY: Final[tuple[MultiLegOrderCapability, ...]] = (
    # ── CME — listed calendar spreads + vertical spreads (futures) ───
    MultiLegOrderCapability(
        venue_id="cme",
        supports_listed_combos=True,
        supports_synthetic_combos=False,
        max_legs=4,
        listed_combo_types=(
            ListedComboType.CALENDAR_SPREAD,
            ListedComboType.VERTICAL_SPREAD,
            ListedComboType.BUTTERFLY,
        ),
        leader_hedge_min_interval_ms=0,
        notes=(
            "CME calendar spreads + vertical spreads are native listed products. "
            "Option strategies on CME use Globex UDS."
        ),
    ),
    # ── Deribit — full multi-leg options book ──────────────────────────
    MultiLegOrderCapability(
        venue_id="deribit",
        supports_listed_combos=True,
        supports_synthetic_combos=True,
        max_legs=4,
        listed_combo_types=(
            ListedComboType.CALENDAR_SPREAD,
            ListedComboType.BUTTERFLY,
            ListedComboType.IRON_CONDOR,
            ListedComboType.RISK_REVERSAL,
            ListedComboType.STRADDLE,
            ListedComboType.STRANGLE,
            ListedComboType.VERTICAL_SPREAD,
            ListedComboType.RATIO_SPREAD,
        ),
        leader_hedge_min_interval_ms=0,
        notes="Deribit /private/combos API supports native multi-leg submission.",
    ),
    # ── OKX options — limited combos + synthetic fallback ──────────────
    MultiLegOrderCapability(
        venue_id="okx",
        supports_listed_combos=False,
        supports_synthetic_combos=True,
        max_legs=4,
        listed_combo_types=(),
        leader_hedge_min_interval_ms=50,
        notes="OKX options supports synthetic multi-leg; no listed combo products.",
    ),
    # ── IBKR — synthetic combo orders through TWS bag orders ──────────
    MultiLegOrderCapability(
        venue_id="ibkr",
        supports_listed_combos=False,
        supports_synthetic_combos=True,
        max_legs=4,
        listed_combo_types=(),
        leader_hedge_min_interval_ms=100,
        notes="IBKR BAG orders execute multi-leg atomically when all legs cross.",
    ),
    # ── Binance spot / perp — no multi-leg support ─────────────────────
    MultiLegOrderCapability(
        venue_id="binance",
        supports_listed_combos=False,
        supports_synthetic_combos=False,
        max_legs=0,
        listed_combo_types=(),
        leader_hedge_min_interval_ms=0,
        notes=(
            "Binance has no multi-leg atomic submission; basket fills use LEADER_HEDGE with venue-specific sequencing."
        ),
    ),
    # ── Hyperliquid — no multi-leg support ─────────────────────────────
    MultiLegOrderCapability(
        venue_id="hyperliquid",
        supports_listed_combos=False,
        supports_synthetic_combos=False,
        max_legs=0,
        listed_combo_types=(),
        leader_hedge_min_interval_ms=0,
        notes="Hyperliquid perps have no combo primitive. Multi-leg archetypes must synthesise.",
    ),
    # ── ICE — listed energy calendar spreads ───────────────────────────
    MultiLegOrderCapability(
        venue_id="ice",
        supports_listed_combos=True,
        supports_synthetic_combos=False,
        max_legs=3,
        listed_combo_types=(
            ListedComboType.CALENDAR_SPREAD,
            ListedComboType.VERTICAL_SPREAD,
        ),
        leader_hedge_min_interval_ms=0,
        notes=(
            "ICE Brent/WTI/NG calendar spreads native. Cross-product spreads "
            "(Brent vs WTI) require CME-ICE routing policy (G2.9 gap #10)."
        ),
    ),
)


class VenueNotRegisteredError(LookupError):
    """Raised when ``multi_leg_capability_for(venue_id)`` can't resolve."""


def multi_leg_capability_for(
    venue_id: str,
    *,
    registry: Iterable[MultiLegOrderCapability] = MULTI_LEG_ORDER_CAPABILITY_REGISTRY,
) -> MultiLegOrderCapability:
    """Resolve the multi-leg capability row for a venue.

    Fail-loud: returns a concrete capability or raises.
    Consumers that want "unknown venue -> no multi-leg" behaviour wrap
    in ``try / except VenueNotRegisteredError`` explicitly.
    """

    for entry in registry:
        if entry.venue_id == venue_id:
            return entry
    raise VenueNotRegisteredError(
        f"venue_id={venue_id!r} not in MULTI_LEG_ORDER_CAPABILITY_REGISTRY",
    )


def venues_supporting_combo_type(
    combo_type: ListedComboType,
    *,
    registry: Iterable[MultiLegOrderCapability] = MULTI_LEG_ORDER_CAPABILITY_REGISTRY,
) -> tuple[MultiLegOrderCapability, ...]:
    """All venues that expose ``combo_type`` as a listed combo ticker."""

    return tuple(entry for entry in registry if entry.supports_listed_combos and combo_type in entry.listed_combo_types)


def venues_supporting_legs(
    required_legs: int,
    *,
    require_atomic: bool = False,
    registry: Iterable[MultiLegOrderCapability] = MULTI_LEG_ORDER_CAPABILITY_REGISTRY,
) -> tuple[MultiLegOrderCapability, ...]:
    """Venues whose ``max_legs >= required_legs``.

    ``require_atomic=True`` additionally requires
    ``supports_listed_combos or supports_synthetic_combos`` — i.e. the
    venue can execute all legs atomically rather than via LEADER_HEDGE.
    """

    out: list[MultiLegOrderCapability] = []
    for entry in registry:
        if entry.max_legs < required_legs:
            continue
        if require_atomic and not (entry.supports_listed_combos or entry.supports_synthetic_combos):
            continue
        out.append(entry)
    return tuple(out)


def _validate_registry_invariants(
    registry: Iterable[MultiLegOrderCapability] = MULTI_LEG_ORDER_CAPABILITY_REGISTRY,
) -> None:
    """Import-time invariant enforcement.

    * ``venue_id`` unique across the registry.
    * ``max_legs == 0`` implies neither listed nor synthetic combos.
    * ``supports_listed_combos=True`` implies ``listed_combo_types``
      non-empty (no lying by omission).
    * ``max_legs >= 2`` when any combo support is declared (a 1-leg
      "combo" is by definition a single order).
    """

    seen: set[str] = set()
    for entry in registry:
        if entry.venue_id in seen:
            raise ValueError(
                f"duplicate venue_id in MULTI_LEG_ORDER_CAPABILITY_REGISTRY: {entry.venue_id!r}",
            )
        seen.add(entry.venue_id)

        any_combo_support = entry.supports_listed_combos or entry.supports_synthetic_combos
        if entry.max_legs == 0 and any_combo_support:
            raise ValueError(
                f"venue {entry.venue_id!r}: max_legs=0 contradicts combo support flags",
            )
        if any_combo_support and entry.max_legs < 2:
            raise ValueError(
                f"venue {entry.venue_id!r}: combo support declared but max_legs<2 ({entry.max_legs})",
            )
        if entry.supports_listed_combos and not entry.listed_combo_types:
            raise ValueError(
                f"venue {entry.venue_id!r}: supports_listed_combos=True but listed_combo_types is empty",
            )
        if not entry.supports_listed_combos and entry.listed_combo_types:
            raise ValueError(
                f"venue {entry.venue_id!r}: listed_combo_types populated but supports_listed_combos=False",
            )


_validate_registry_invariants()


# ── Consumer reference SSOT ───────────────────────────────────────────
# Declared call-sites for this capability declaration. Listed here so
# downstream agents can find the integration points deterministically +
# so we can assert (in tests) that we haven't shipped an orphan UAC
# type. Each entry is a POSIX-style repo-relative path to the consumer
# module that imports this registry / helper.
#
# Integration is tracked in
# ``plans/active/refactor_g2_5_execution_algo_catalogue_refactor_2026_04_20.plan.md``.
# G2.9 ships the UAC declaration + registry; G2.5 wires the call-sites.
CONSUMER_CALL_SITES: Final[tuple[str, ...]] = (
    "execution-service/execution_service/algo_library/base_algorithm.py",
    "execution-service/execution_service/v2/handlers.py",
    "execution-service/execution_service/v2/router.py",
)


__all__ = [
    "CONSUMER_CALL_SITES",
    "MULTI_LEG_ORDER_CAPABILITY_REGISTRY",
    "ListedComboType",
    "MultiLegOrderCapability",
    "VenueNotRegisteredError",
    "multi_leg_capability_for",
    "venues_supporting_combo_type",
    "venues_supporting_legs",
]
