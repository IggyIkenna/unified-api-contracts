"""IV-surface fidelity + option-venue capability — G2.9 gap #6.

Stage 3E § 2.9 gap #6 from ``codex/09-strategy/architecture-v2/uac-registry-gaps.md``.
``VOL_TRADING_OPTIONS`` and ``ARBITRAGE_PRICE_DISPERSION x option`` need
to know how rich the implied-vol surface data is per option venue:

* Deribit has a FULL surface (all strikes x expiries, live IVs).
* OKX options have a limited surface.
* CME options on futures are shallower still.
* CBOE via IBKR has full surface on SPY / QQQ / VIX.

Before this module strategies couldn't mechanically ask "can venue X
carry an iron-condor on ETH options?" — the answer depends on surface
fidelity + strikes-per-expiry + max combo legs.

Co-ordinates with gap #7 (``MultiLegOrderCapability``) — this module
is the quality-of-surface axis, gap #7 is the execution-combo axis.
Together they're sufficient to gate any options archetype.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field


class IvSurfaceFidelity(StrEnum):
    """Per-venue vol surface quality tier."""

    FULL_SURFACE = "full_surface"
    """All strikes x all expiries, tick-level IVs."""

    ATM_ONLY = "atm_only"
    """Only near-ATM strikes carry live IVs."""

    COARSE_GRID = "coarse_grid"
    """Sparse strike grid, daily snapshot."""

    NONE = "none"
    """Price only, no IV surface."""


class OptionVenueCapability(BaseModel):
    """Per-venue option capability — surface fidelity + grid shape."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue_id: str
    underlyings: tuple[str, ...]
    """Tradeable underlyings on this venue."""

    iv_surface_fidelity: IvSurfaceFidelity
    strikes_per_expiry_p50: int = Field(ge=0)
    """Median strikes per expiry — how dense the grid is."""

    expiries_per_underlying_p50: int = Field(ge=0)
    """Median distinct expiries per underlying."""

    supports_multi_leg_combos: bool
    """True iff venue accepts multi-leg combo orders."""

    max_combo_legs: int = Field(ge=0)
    """Max legs per combo; 0 if combos unsupported."""

    supported_signal_variants: tuple[str, ...] = ()
    """Signal-variant strings this venue supports (mirrors gap #2)."""

    notes: str = ""


OPTION_VENUE_CAPABILITIES: Final[tuple[OptionVenueCapability, ...]] = (
    OptionVenueCapability(
        venue_id="deribit",
        underlyings=("BTC", "ETH", "SOL"),
        iv_surface_fidelity=IvSurfaceFidelity.FULL_SURFACE,
        strikes_per_expiry_p50=40,
        expiries_per_underlying_p50=12,
        supports_multi_leg_combos=True,
        max_combo_legs=4,
        supported_signal_variants=(
            "delta_as_expression",
            "iv_dispersion",
            "vol_metric",
        ),
        notes="Deribit is the canonical crypto-options venue — deepest surface.",
    ),
    OptionVenueCapability(
        venue_id="okx",
        underlyings=("BTC", "ETH"),
        iv_surface_fidelity=IvSurfaceFidelity.ATM_ONLY,
        strikes_per_expiry_p50=15,
        expiries_per_underlying_p50=6,
        supports_multi_leg_combos=True,
        max_combo_legs=4,
        supported_signal_variants=("delta_as_expression", "vol_metric"),
    ),
    OptionVenueCapability(
        venue_id="ibkr",
        underlyings=("SPY", "QQQ", "VIX", "IWM"),
        iv_surface_fidelity=IvSurfaceFidelity.FULL_SURFACE,
        strikes_per_expiry_p50=60,
        expiries_per_underlying_p50=20,
        supports_multi_leg_combos=True,
        max_combo_legs=4,
        supported_signal_variants=(
            "delta_as_expression",
            "iv_dispersion",
            "vol_metric",
        ),
        notes="CBOE routed via IBKR — full SPX / SPY / QQQ / VIX surfaces.",
    ),
    OptionVenueCapability(
        venue_id="cme",
        underlyings=("ES", "NQ", "RTY", "CL", "GC"),
        iv_surface_fidelity=IvSurfaceFidelity.COARSE_GRID,
        strikes_per_expiry_p50=25,
        expiries_per_underlying_p50=8,
        supports_multi_leg_combos=True,
        max_combo_legs=2,
        supported_signal_variants=("delta_as_expression", "vol_metric"),
        notes="CME options on futures — coarse compared to CBOE/Deribit.",
    ),
    OptionVenueCapability(
        venue_id="bit_com",
        underlyings=("BTC", "ETH"),
        iv_surface_fidelity=IvSurfaceFidelity.COARSE_GRID,
        strikes_per_expiry_p50=10,
        expiries_per_underlying_p50=4,
        supports_multi_leg_combos=False,
        max_combo_legs=0,
        supported_signal_variants=("delta_as_expression",),
        notes="bit.com options — thin liquidity, single-leg only.",
    ),
)


class OptionVenueNotRegisteredError(LookupError):
    """Raised when ``option_venue_for(venue_id)`` can't resolve."""


def option_venue_for(
    venue_id: str,
    *,
    registry: Iterable[OptionVenueCapability] = OPTION_VENUE_CAPABILITIES,
) -> OptionVenueCapability:
    """Resolve option venue capability. Fail-loud on miss."""

    for entry in registry:
        if entry.venue_id == venue_id:
            return entry
    raise OptionVenueNotRegisteredError(
        f"venue_id={venue_id!r} not in OPTION_VENUE_CAPABILITIES",
    )


def venues_at_fidelity(
    fidelity: IvSurfaceFidelity,
    *,
    registry: Iterable[OptionVenueCapability] = OPTION_VENUE_CAPABILITIES,
) -> tuple[OptionVenueCapability, ...]:
    """All option venues at a given IV-surface fidelity tier."""

    return tuple(entry for entry in registry if entry.iv_surface_fidelity is fidelity)


def venues_trading_underlying(
    underlying: str,
    *,
    registry: Iterable[OptionVenueCapability] = OPTION_VENUE_CAPABILITIES,
) -> tuple[OptionVenueCapability, ...]:
    """All option venues that list ``underlying``."""

    return tuple(entry for entry in registry if underlying in entry.underlyings)


def _validate_registry_invariants(
    registry: Iterable[OptionVenueCapability] = OPTION_VENUE_CAPABILITIES,
) -> None:
    """Invariants:

    * ``venue_id`` unique.
    * ``underlyings`` non-empty.
    * If ``supports_multi_leg_combos=True`` → ``max_combo_legs >= 2``.
    * If ``iv_surface_fidelity == NONE`` → venue shouldn't be in the
      registry at all (absence represents missing surface).
    """

    seen: set[str] = set()
    for entry in registry:
        if entry.venue_id in seen:
            raise ValueError(
                f"duplicate venue_id in OPTION_VENUE_CAPABILITIES: {entry.venue_id!r}",
            )
        seen.add(entry.venue_id)
        if not entry.underlyings:
            raise ValueError(
                f"{entry.venue_id!r}: underlyings must be non-empty",
            )
        if entry.supports_multi_leg_combos and entry.max_combo_legs < 2:
            raise ValueError(
                f"{entry.venue_id!r}: supports_multi_leg_combos=True requires max_combo_legs>=2",
            )
        if not entry.supports_multi_leg_combos and entry.max_combo_legs > 0:
            raise ValueError(
                f"{entry.venue_id!r}: max_combo_legs>0 contradicts supports_multi_leg_combos=False",
            )
        if entry.iv_surface_fidelity is IvSurfaceFidelity.NONE:
            raise ValueError(
                f"{entry.venue_id!r}: NONE fidelity — drop the row instead of declaring it",
            )


_validate_registry_invariants()


CONSUMER_CALL_SITES: Final[tuple[str, ...]] = (
    "features-onchain-service/features_onchain_service/options/surface.py",
    "features-volatility-service/features_volatility_service/surfaces.py",
    "strategy-service/strategy_service/validation/data_certification.py",
)


__all__ = [
    "CONSUMER_CALL_SITES",
    "OPTION_VENUE_CAPABILITIES",
    "IvSurfaceFidelity",
    "OptionVenueCapability",
    "OptionVenueNotRegisteredError",
    "option_venue_for",
    "venues_at_fidelity",
    "venues_trading_underlying",
]
