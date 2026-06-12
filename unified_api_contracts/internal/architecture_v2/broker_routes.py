"""Broker → routed-venue declaration (Phase 6A, F38).

WHY THIS MODULE EXISTS (operator-caught, 2026-06-12 — a system-design floor):
A *broker* is NOT a venue. IBKR (Interactive Brokers) is a broker that ROUTES
orders to the actual exchanges (CME, ICE, CBOE, NASDAQ, NYSE, FX); the *exchange*
is the venue where price discovery + the matching engine live. The data pipeline
and the strategy logic are identical regardless of which broker the final routing
hop goes through — so the broker is an execution/custody routing AXIS, never a
peer venue the wizard offers as a selectable market.

Today ``ENDPOINT_REGISTRY`` carries ``venue="ibkr"`` (load-bearing as a tradfi
data-pipeline SOURCE id — do NOT rename it; see the F38 comment at that entry).
This module is the MANIFEST-LAYER declaration that lets the exporter classify
ibkr as a ``broker`` node + emit ``venue ⇠routed_via⇢ broker`` edges, and lets the
wizard render a broker as a routing sub-choice under its routed venues
("CME — routed via IBKR (broker)") rather than as a peer venue card.

SOURCE OF TRUTH (transcribed declaratively — file:line citations per rule):
  - ``execution_service/trade_execution/adapters/ibkr_tradfi.py:38-46``
    ``IbkrTradFiAdapter.VENUE_TO_EXCHANGE`` — the broker's per-venue exchange
    routing map: ``CME → GLOBEX``, ``CBOE → CBOE``, ``NASDAQ → NASDAQ``,
    ``NYSE → NYSE``, ``ICE → ICE``, ``FX → IDEALPRO``. Each KEY is a venue IBKR
    routes to; the subclass adapters (``CMEAdapter``/``ICEAdapter``/``CBOEAdapter``/
    ``NASDAQAdapter``/``NYSEAdapter``/``FXAdapter``, each ``extends IbkrTradFiAdapter``
    with ``venue_name="CME"`` etc.) confirm the routed-venue set.
  - ``execution_service/trade_execution/adapters/ibkr_tradfi.py:34`` docstring:
    "Supports CME, CBOE, NASDAQ, NYSE, ICE, FX. Execution routes through IBKR."

The deeper ``ENDPOINT_REGISTRY`` key migration (a venue-axis vocabulary plan that
splits the ``venue="ibkr"`` SOURCE id from a true broker id) is a TRACKED FOLLOW-UP
— this module is intentionally the manifest layer only, with NO pipeline-key rename.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.internal.architecture_v2.enums import VenueCategoryV2

# ---------------------------------------------------------------------------
# Broker vocabulary
# ---------------------------------------------------------------------------


class BrokerKind(StrEnum):
    """How a broker intermediates execution.

    - ``order_router`` — accepts an order + routes it to an exchange's matching
      engine (IBKR → CME/ICE/CBOE…); the broker is NOT the price-discovery venue.
    - ``prime`` — prime-brokerage / custody-plus-execution (none in the MVP set).
    """

    ORDER_ROUTER = "order_router"
    PRIME = "prime"


class BrokerRoute(BaseModel):
    """A broker and the venues it routes orders to.

    The ``routed_venue_ids`` are the EXCHANGE venue ids (the actual market /
    matching engine); ``venue_categories`` is the category set those venues fall
    into (all TRADFI for IBKR today). ``broker_id`` is the canonical broker
    identifier; it is intentionally DISTINCT from any ``ENDPOINT_REGISTRY`` source
    id (which stays ``"ibkr"`` for the tradfi data pipeline).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    broker_id: str = Field(
        description="Stable broker identifier (e.g. ``'ibkr'``).",
    )
    label: str = Field(
        description="Human-readable broker label (e.g. ``'Interactive Brokers'``).",
    )
    kind: BrokerKind = Field(
        description="How the broker intermediates execution.",
    )
    routed_venue_ids: tuple[str, ...] = Field(
        description=(
            "Exchange venue ids this broker routes orders to (the actual "
            "price-discovery venues). Each is a peer of CME/ICE/CBOE, never the "
            "broker itself."
        ),
    )
    venue_categories: tuple[VenueCategoryV2, ...] = Field(
        description="Category set the routed venues fall into (TRADFI for IBKR).",
    )
    source_of_truth: str = Field(
        description="Code path / docstring this routing declaration was transcribed from.",
    )


# ---------------------------------------------------------------------------
# Seeded routes (IBKR → {CME, ICE, CBOE, NASDAQ, NYSE, FX})
# ---------------------------------------------------------------------------

_IBKR_SRC: Final[str] = (
    "execution_service/trade_execution/adapters/ibkr_tradfi.py:38-46 "
    "(IbkrTradFiAdapter.VENUE_TO_EXCHANGE: CME->GLOBEX, CBOE->CBOE, NASDAQ->NASDAQ, "
    "NYSE->NYSE, ICE->ICE, FX->IDEALPRO) + the CMEAdapter/ICEAdapter/CBOEAdapter/"
    "NASDAQAdapter/NYSEAdapter/FXAdapter subclasses (each extends IbkrTradFiAdapter)"
)

BROKER_ROUTES: Final[dict[str, BrokerRoute]] = {
    "ibkr": BrokerRoute(
        broker_id="ibkr",
        label="Interactive Brokers",
        kind=BrokerKind.ORDER_ROUTER,
        # The exchange venue ids IBKR routes to (price-discovery venues).
        # CME/ICE/CBOE are the operator-named TradFi venues; NASDAQ/NYSE/FX
        # round out VENUE_TO_EXCHANGE. Sorted for deterministic output.
        routed_venue_ids=("cboe", "cme", "fx", "ice", "nasdaq", "nyse"),
        venue_categories=(VenueCategoryV2.TRADFI,),
        source_of_truth=_IBKR_SRC,
    ),
}


def broker_for_venue(venue_id: str) -> str | None:
    """Return the broker id that routes to ``venue_id`` (case-insensitive), else None.

    A venue is "broker-routed" when it appears in some ``BrokerRoute.routed_venue_ids``.
    Used by the exporter's orphan heuristic + the wizard's broker grouping.
    """

    needle = venue_id.strip().lower()
    for route in BROKER_ROUTES.values():
        if needle in {v.lower() for v in route.routed_venue_ids}:
            return route.broker_id
    return None


def is_broker(venue_or_broker_id: str) -> bool:
    """Return True iff ``venue_or_broker_id`` is a declared broker id (case-insensitive).

    The orphan heuristic uses this to flag a venue-classed node that is actually a
    broker (it appears as a ``BROKER_ROUTES`` key, e.g. ``ibkr``).
    """

    needle = venue_or_broker_id.strip().lower()
    return any(needle == bid.lower() for bid in BROKER_ROUTES)


def routed_venue_ids() -> tuple[str, ...]:
    """All venue ids reachable through any broker (sorted, deduplicated)."""

    seen: set[str] = set()
    for route in BROKER_ROUTES.values():
        seen.update(route.routed_venue_ids)
    return tuple(sorted(seen))
