"""Per-venue supported signal variants — G2.9 gap #2.

Stage 3E § 2.9 gap #2 from ``codex/09-strategy/architecture-v2/uac-registry-gaps.md``.
A venue supporting ``PERPETUAL`` is silent about *why* we trade perp
there — is price the signal, is funding-rate the signal, is basis?
This registry makes that explicit so strategy-service can reject a
config that asks for funding-rate-arb on a venue that only supports
price-based trading.

Shipped as a standalone companion registry (rather than adding a
field to the large shared ``VenueCapabilityV2``) to avoid churn in
``schemas.py``. Consumers co-query by venue_id:

    from unified_api_contracts.internal.architecture_v2.venue_signal_variants import (
        signal_variants_for,
    )
    variants = signal_variants_for("binance", ArchetypeInstrumentType.PERP)
    if SignalVariant.FUNDING_RATE not in variants:
        raise ConfigError(...)

Signal-variant vocabulary mirrors
``archetype_capability.ArchetypeCapabilityCell.signal_variants`` so the
matrix parity is mechanical — parity tests can enforce that every
variant appearing in the archetype matrix is a known variant here.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ArchetypeInstrumentType,
)


class SignalVariant(StrEnum):
    """Canonical signal-variant vocabulary.

    Mirrors the free-form ``str`` values used in the archetype
    capability matrix; typing them here lets consumers get completion +
    QG enforcement on typos.
    """

    PRICE = "price"
    """Spot / perp price, tick-level orderbook available."""

    FUNDING_RATE = "funding_rate"
    """Perp funding rate tradeable + measurable."""

    BASIS = "basis"
    """Spot↔future or spot↔perp basis tradeable."""

    IV_DISPERSION = "iv_dispersion"
    """Vol-surface IV deltas between venues tradeable."""

    VOL_METRIC = "vol_metric"
    """IV vs RV, skew, term-structure."""

    RATE_SPREAD = "rate_spread"
    """Cross-venue lending-rate spread."""

    LIQUIDATION_BONUS = "liquidation_bonus"
    """On-chain liquidator role active."""

    ODDS = "odds"
    """Event-settled odds bid/ask."""

    EVENT_SURPRISE = "event_surprise"
    """Calendar events (macro / earnings / release) tradeable."""

    DELTA_AS_EXPRESSION = "delta_as_expression"
    """Option used to express directional view (not vol trade)."""


class VenueInstrumentSignalSupport(BaseModel):
    """Per (venue_id, instrument_type) supported signal variants."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue_id: str
    instrument_type: ArchetypeInstrumentType
    supported_signal_variants: frozenset[SignalVariant]
    notes: str = ""


# Each row is one (venue, instrument_type) combination with the signal
# variants the venue can actually carry. Keep declaration order
# venue-then-instrument for readability.
VENUE_SIGNAL_VARIANT_REGISTRY: Final[tuple[VenueInstrumentSignalSupport, ...]] = (
    # ── Binance ────────────────────────────────────────────────────────
    VenueInstrumentSignalSupport(
        venue_id="binance",
        instrument_type=ArchetypeInstrumentType.SPOT,
        supported_signal_variants=frozenset({SignalVariant.PRICE}),
    ),
    VenueInstrumentSignalSupport(
        venue_id="binance",
        instrument_type=ArchetypeInstrumentType.PERP,
        supported_signal_variants=frozenset(
            {SignalVariant.PRICE, SignalVariant.FUNDING_RATE, SignalVariant.BASIS},
        ),
    ),
    # ── Coinbase ───────────────────────────────────────────────────────
    VenueInstrumentSignalSupport(
        venue_id="coinbase",
        instrument_type=ArchetypeInstrumentType.SPOT,
        supported_signal_variants=frozenset({SignalVariant.PRICE}),
    ),
    # ── Deribit — full options vol surface ─────────────────────────────
    VenueInstrumentSignalSupport(
        venue_id="deribit",
        instrument_type=ArchetypeInstrumentType.OPTION,
        supported_signal_variants=frozenset(
            {
                SignalVariant.DELTA_AS_EXPRESSION,
                SignalVariant.IV_DISPERSION,
                SignalVariant.VOL_METRIC,
            },
        ),
    ),
    VenueInstrumentSignalSupport(
        venue_id="deribit",
        instrument_type=ArchetypeInstrumentType.DATED_FUTURE,
        supported_signal_variants=frozenset({SignalVariant.PRICE, SignalVariant.BASIS}),
    ),
    # ── Hyperliquid ────────────────────────────────────────────────────
    VenueInstrumentSignalSupport(
        venue_id="hyperliquid",
        instrument_type=ArchetypeInstrumentType.PERP,
        supported_signal_variants=frozenset(
            {SignalVariant.PRICE, SignalVariant.FUNDING_RATE, SignalVariant.BASIS},
        ),
    ),
    # ── CME futures ────────────────────────────────────────────────────
    VenueInstrumentSignalSupport(
        venue_id="cme",
        instrument_type=ArchetypeInstrumentType.DATED_FUTURE,
        supported_signal_variants=frozenset({SignalVariant.PRICE, SignalVariant.BASIS}),
    ),
    VenueInstrumentSignalSupport(
        venue_id="cme",
        instrument_type=ArchetypeInstrumentType.OPTION,
        supported_signal_variants=frozenset(
            {SignalVariant.DELTA_AS_EXPRESSION, SignalVariant.VOL_METRIC},
        ),
        notes="CME options on futures — coarser vol surface than Deribit.",
    ),
    # ── IBKR (TradFi cash + options) ───────────────────────────────────
    VenueInstrumentSignalSupport(
        venue_id="ibkr",
        instrument_type=ArchetypeInstrumentType.SPOT,
        supported_signal_variants=frozenset({SignalVariant.PRICE}),
    ),
    VenueInstrumentSignalSupport(
        venue_id="ibkr",
        instrument_type=ArchetypeInstrumentType.OPTION,
        supported_signal_variants=frozenset(
            {
                SignalVariant.DELTA_AS_EXPRESSION,
                SignalVariant.IV_DISPERSION,
                SignalVariant.VOL_METRIC,
            },
        ),
    ),
    # ── Aave (on-chain lending / liquidations) ─────────────────────────
    VenueInstrumentSignalSupport(
        venue_id="aave",
        instrument_type=ArchetypeInstrumentType.LENDING,
        supported_signal_variants=frozenset(
            {SignalVariant.LIQUIDATION_BONUS, SignalVariant.RATE_SPREAD},
        ),
    ),
    # ── Betfair sports ─────────────────────────────────────────────────
    VenueInstrumentSignalSupport(
        venue_id="betfair",
        instrument_type=ArchetypeInstrumentType.EVENT_SETTLED,
        supported_signal_variants=frozenset({SignalVariant.ODDS, SignalVariant.EVENT_SURPRISE}),
    ),
)


class VenueInstrumentNotRegisteredError(LookupError):
    """Raised when ``signal_variants_for(venue, instrument)`` can't resolve."""


def signal_variants_for(
    venue_id: str,
    instrument_type: ArchetypeInstrumentType,
    *,
    registry: Iterable[VenueInstrumentSignalSupport] = VENUE_SIGNAL_VARIANT_REGISTRY,
) -> frozenset[SignalVariant]:
    """Return the set of supported signal variants for (venue, instrument).

    Fail-loud: raises ``VenueInstrumentNotRegisteredError`` on miss.
    """

    for entry in registry:
        if entry.venue_id == venue_id and entry.instrument_type == instrument_type:
            return entry.supported_signal_variants
    raise VenueInstrumentNotRegisteredError(
        f"(venue_id={venue_id!r}, instrument_type={instrument_type.value!r}) not in registry",
    )


def venue_supports_variant(
    venue_id: str,
    instrument_type: ArchetypeInstrumentType,
    variant: SignalVariant,
    *,
    registry: Iterable[VenueInstrumentSignalSupport] = VENUE_SIGNAL_VARIANT_REGISTRY,
) -> bool:
    """True iff venue supports ``variant`` on ``instrument_type``.

    Silent on unknown (venue, instrument) — returns False rather than
    raising. This keeps strategy-service config validation
    non-exceptional when iterating across many venues.
    """

    try:
        return variant in signal_variants_for(venue_id, instrument_type, registry=registry)
    except VenueInstrumentNotRegisteredError:
        return False


def venues_supporting(
    variant: SignalVariant,
    *,
    instrument_type: ArchetypeInstrumentType | None = None,
    registry: Iterable[VenueInstrumentSignalSupport] = VENUE_SIGNAL_VARIANT_REGISTRY,
) -> tuple[VenueInstrumentSignalSupport, ...]:
    """All (venue, instrument) pairs carrying ``variant``.

    Pass ``instrument_type`` to restrict to one instrument type.
    """

    return tuple(
        entry
        for entry in registry
        if variant in entry.supported_signal_variants
        and (instrument_type is None or entry.instrument_type == instrument_type)
    )


def _validate_registry_invariants(
    registry: Iterable[VenueInstrumentSignalSupport] = VENUE_SIGNAL_VARIANT_REGISTRY,
) -> None:
    """Invariants:

    * ``(venue_id, instrument_type)`` pair unique in registry.
    * ``supported_signal_variants`` non-empty — a venue listed in the
      registry must support at least one variant (absence is represented
      by absence from the registry, not by an empty set).
    """

    seen: set[tuple[str, ArchetypeInstrumentType]] = set()
    for entry in registry:
        key = (entry.venue_id, entry.instrument_type)
        if key in seen:
            raise ValueError(
                f"duplicate (venue_id, instrument_type) in registry: {key!r}",
            )
        seen.add(key)
        if not entry.supported_signal_variants:
            raise ValueError(
                f"{key!r}: supported_signal_variants must be non-empty (drop the row instead of declaring no variants)",
            )


_validate_registry_invariants()


CONSUMER_CALL_SITES: Final[tuple[str, ...]] = (
    "strategy-service/strategy_service/validation/data_certification.py",
    "strategy-service/strategy_service/portfolio_allocator/service.py",
    "execution-service/execution_service/v2/handlers.py",
)


__all__ = [
    "CONSUMER_CALL_SITES",
    "VENUE_SIGNAL_VARIANT_REGISTRY",
    "SignalVariant",
    "VenueInstrumentNotRegisteredError",
    "VenueInstrumentSignalSupport",
    "signal_variants_for",
    "venue_supports_variant",
    "venues_supporting",
]
