"""Sports / prediction lay-side execution semantics — G2.9 gap #9.

Stage 3E § 2.9 gap #9 from ``codex/09-strategy/architecture-v2/uac-registry-gaps.md``.
``MARKET_MAKING_EVENT_SETTLED`` needs per-venue semantics for lay-side
bets because every venue is different:

* **Betfair direct** — bankroll-as-collateral, lay liability
  ``= (odds - 1) x stake``, fully collateralised.
* **Smarkets** — similar to Betfair, different commission timing
  (on winnings vs on turnover).
* **Matchbook direct** — different margin rules (implicit).
* **Polymarket** — no "lay" primitive — buy/sell binary Yes/No (CLOB).
* **Unity (Feed Connector)** — place-only, no MM / quoting.

Before this module these differences were buried in adapter code.
Execution-service could not validate per-venue lay policy without a
declaration — leading to BL-6 (Unity MM BLOCKED cell).

Consumer integration:

* ``execution-service/execution_service/sports_execution/adapters/exchanges/betfair.py``
  reads ``liability_formula_ref`` at submit-time for pre-trade reserve.
* Execution-service ``MARKET_MAKING_EVENT_SETTLED`` algo refuses to
  quote on any venue with ``supports_mm_quoting=False`` (e.g. Unity).
* Risk-and-exposure service uses ``commission_basis`` to gate net-pnl
  calculations — commission on winnings vs turnover matters for
  capital-efficiency modelling.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field


class LayBookType(StrEnum):
    """Lay-book type per sports / prediction venue."""

    FULL_LAY = "full_lay"
    """Betfair-style lay with liability = (odds-1)*stake."""

    BINARY_CLOB = "binary_clob"
    """Polymarket-style Yes/No CLOB — no "lay" primitive."""

    BACK_ONLY = "back_only"
    """Unity-style child book — no lay on our side."""

    EXCHANGE_LAY_NO_COMMISSION_ON_TURNOVER = "exchange_lay_no_commission_on_turnover"
    """Exchange that charges commission on winnings only, not turnover."""

    EXCHANGE_LAY_COMMISSION_ON_WIN_ONLY = "exchange_lay_commission_on_win_only"
    """Exchange that charges commission only on winning wagers."""


CommissionBasis = Literal["winnings", "turnover", "none"]
InPlayPolicy = Literal["lock_new_quotes", "soft_lock", "unrestricted"]


class LiabilityFormula(StrEnum):
    """Formula for computing lay-side liability from (odds, stake).

    These are pointers to registered formulas rather than inline
    maths; consumer (execution-service) resolves the formula at
    runtime. Keeps UAC side schema-only.
    """

    BETFAIR_STANDARD = "betfair_standard"
    """liability = (odds - 1) * stake"""

    BINARY_FIXED_NOTIONAL = "binary_fixed_notional"
    """liability = stake (fixed notional Yes/No)"""

    NO_LAY = "no_lay"
    """No lay permitted — liability formula inapplicable."""


class LaySideExecutionSemantics(BaseModel):
    """One venue's lay-side semantics declaration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue_id: str
    lay_book_type: LayBookType
    supports_mm_quoting: bool
    """True iff MM can quote (add back + lay quotes to book)."""

    liability_formula_ref: LiabilityFormula
    commission_basis: CommissionBasis
    min_quote_refresh_ms: int = Field(ge=0)
    """Minimum interval between successive quote updates (rate limit)."""

    in_play_policy: InPlayPolicy
    notes: str = ""


LAY_SIDE_EXECUTION_SEMANTICS: Final[tuple[LaySideExecutionSemantics, ...]] = (
    LaySideExecutionSemantics(
        venue_id="betfair",
        lay_book_type=LayBookType.FULL_LAY,
        supports_mm_quoting=True,
        liability_formula_ref=LiabilityFormula.BETFAIR_STANDARD,
        commission_basis="winnings",
        min_quote_refresh_ms=200,
        in_play_policy="soft_lock",
        notes="Betfair Exchange — canonical full-lay venue. Commission on winnings.",
    ),
    LaySideExecutionSemantics(
        venue_id="smarkets",
        lay_book_type=LayBookType.EXCHANGE_LAY_NO_COMMISSION_ON_TURNOVER,
        supports_mm_quoting=True,
        liability_formula_ref=LiabilityFormula.BETFAIR_STANDARD,
        commission_basis="winnings",
        min_quote_refresh_ms=250,
        in_play_policy="soft_lock",
        notes="Smarkets — commission on net winnings only, not on turnover.",
    ),
    LaySideExecutionSemantics(
        venue_id="matchbook",
        lay_book_type=LayBookType.FULL_LAY,
        supports_mm_quoting=True,
        liability_formula_ref=LiabilityFormula.BETFAIR_STANDARD,
        commission_basis="winnings",
        min_quote_refresh_ms=300,
        in_play_policy="soft_lock",
    ),
    LaySideExecutionSemantics(
        venue_id="polymarket",
        lay_book_type=LayBookType.BINARY_CLOB,
        supports_mm_quoting=True,
        liability_formula_ref=LiabilityFormula.BINARY_FIXED_NOTIONAL,
        commission_basis="none",
        min_quote_refresh_ms=500,
        in_play_policy="lock_new_quotes",
        notes="Polymarket — binary Yes/No CLOB. MM by providing both sides.",
    ),
    LaySideExecutionSemantics(
        venue_id="unity",
        lay_book_type=LayBookType.BACK_ONLY,
        supports_mm_quoting=False,
        liability_formula_ref=LiabilityFormula.NO_LAY,
        commission_basis="none",
        min_quote_refresh_ms=0,
        in_play_policy="lock_new_quotes",
        notes="Unity Feed Connector — place-only; MM slot BLOCKED per BL-6.",
    ),
)


class LayVenueNotRegisteredError(LookupError):
    """Raised when ``lay_semantics_for(venue_id)`` can't resolve."""


def lay_semantics_for(
    venue_id: str,
    *,
    registry: Iterable[LaySideExecutionSemantics] = LAY_SIDE_EXECUTION_SEMANTICS,
) -> LaySideExecutionSemantics:
    """Resolve lay-side semantics for a venue. Fail-loud on miss."""

    for entry in registry:
        if entry.venue_id == venue_id:
            return entry
    raise LayVenueNotRegisteredError(
        f"venue_id={venue_id!r} not in LAY_SIDE_EXECUTION_SEMANTICS",
    )


def mm_quoting_venues(
    *,
    registry: Iterable[LaySideExecutionSemantics] = LAY_SIDE_EXECUTION_SEMANTICS,
) -> tuple[LaySideExecutionSemantics, ...]:
    """All venues where MM quoting is allowed."""

    return tuple(entry for entry in registry if entry.supports_mm_quoting)


def venues_by_book_type(
    book_type: LayBookType,
    *,
    registry: Iterable[LaySideExecutionSemantics] = LAY_SIDE_EXECUTION_SEMANTICS,
) -> tuple[LaySideExecutionSemantics, ...]:
    """All venues with a given lay-book type."""

    return tuple(entry for entry in registry if entry.lay_book_type is book_type)


def _validate_registry_invariants(
    registry: Iterable[LaySideExecutionSemantics] = LAY_SIDE_EXECUTION_SEMANTICS,
) -> None:
    """Invariants:

    * ``venue_id`` unique.
    * ``BACK_ONLY`` implies ``supports_mm_quoting=False`` +
      ``liability_formula_ref == NO_LAY``.
    * ``FULL_LAY`` / ``BINARY_CLOB`` imply non-``NO_LAY`` formula.
    """

    seen: set[str] = set()
    for entry in registry:
        if entry.venue_id in seen:
            raise ValueError(
                f"duplicate venue_id in LAY_SIDE_EXECUTION_SEMANTICS: {entry.venue_id!r}",
            )
        seen.add(entry.venue_id)

        if entry.lay_book_type is LayBookType.BACK_ONLY:
            if entry.supports_mm_quoting:
                raise ValueError(
                    f"{entry.venue_id!r}: BACK_ONLY contradicts supports_mm_quoting=True",
                )
            if entry.liability_formula_ref is not LiabilityFormula.NO_LAY:
                raise ValueError(
                    f"{entry.venue_id!r}: BACK_ONLY must have liability_formula_ref=NO_LAY",
                )
        elif entry.lay_book_type in (
            LayBookType.FULL_LAY,
            LayBookType.BINARY_CLOB,
            LayBookType.EXCHANGE_LAY_NO_COMMISSION_ON_TURNOVER,
            LayBookType.EXCHANGE_LAY_COMMISSION_ON_WIN_ONLY,
        ):
            if entry.liability_formula_ref is LiabilityFormula.NO_LAY:
                raise ValueError(
                    f"{entry.venue_id!r}: lay-capable book must have a real liability formula",
                )


_validate_registry_invariants()


CONSUMER_CALL_SITES: Final[tuple[str, ...]] = (
    "execution-service/execution_service/sports_execution/adapters/exchanges/betfair.py",
    "execution-service/execution_service/sports_execution/adapters/exchanges/__init__.py",
    "strategy-service/strategy_service/validation/data_certification.py",
)


__all__ = [
    "CONSUMER_CALL_SITES",
    "LAY_SIDE_EXECUTION_SEMANTICS",
    "CommissionBasis",
    "InPlayPolicy",
    "LayBookType",
    "LaySideExecutionSemantics",
    "LayVenueNotRegisteredError",
    "LiabilityFormula",
    "lay_semantics_for",
    "mm_quoting_venues",
    "venues_by_book_type",
]
