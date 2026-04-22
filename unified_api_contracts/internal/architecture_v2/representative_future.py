"""Representative-future registry + roll-trigger policy — G2.9 gap #11.

Stage 3E § 2.9 gap #11 from ``codex/09-strategy/architecture-v2/uac-registry-gaps.md``.
Under-pins the BL-10 dated-future auto-roll mechanism. Declares the
set of underlyings, the feature group feeding the liquidity measure,
and the roll-trigger policy per underlying.

See ``project_dated_future_rolls_architecture_2026_04_19`` memory for
the full architecture. Summary:

* Strategies on dated futures use rolling continuous underlyings by
  default. Slot-label convention: ``-dated-`` (rolling, default) vs
  ``-fixed-{contract}-`` (expiry-anchored).
* features-service computes ``representative_future(underlying)``
  deterministically from liquidity features.
* representative-future-service emits ``REPRESENTATIVE_FUTURE_CHANGED``
  on state transitions.
* strategy-service instances on ``-dated-`` slots react by emitting
  ``FUTURES_ROLL`` (ATOMIC combo).

This module is the SSOT for the set of declared underlyings + their
roll policies. The ``REPRESENTATIVE_FUTURE_CHANGED`` event schema
lives alongside for consumers to import.

Consumer integration:

* features-service (or features-commodity / features-cross-instrument)
  computes rolling liquidity per underlying.
* representative-future-service (NOT present in this workspace as of
  2026-04-22 — scaffolded in a follow-up plan) reads the registry on
  startup + runs the roll-decision state machine.
* strategy-service on ``-dated-`` slots subscribes to the event.
* execution-service SOR uses the registry's ``has_listed_calendar_combo``
  flag to pick between listed-combo vs synthetic-combo roll paths.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field


class UnderlyingCategory(StrEnum):
    """Coarse category grouping underlyings by macro-characteristic."""

    CRYPTO_DATED = "crypto_dated"
    """Deribit BTC/ETH dated futures."""

    EQUITY_INDEX = "equity_index"
    """CME ES, NQ, RTY, YM."""

    COMMODITY = "commodity"
    """CME CL, GC, NG, HG; ICE Brent."""

    FX = "fx"
    """CME 6E, 6B, 6J."""


class RollTriggerPolicy(BaseModel):
    """Liquidity-margin-driven roll trigger policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    liquidity_feature_group_ref: str
    """Feature group ref providing per-contract liquidity measure.
    Must publish at least open_interest, volume_24h, bid_ask_depth_notional."""

    liquidity_margin_bps: int = Field(ge=0, le=10_000)
    """Roll when next contract's liquidity > current's by this bps."""

    liquidity_confirmation_windows: int = Field(ge=1)
    """Consecutive measurement windows of margin before roll triggers."""

    expiry_buffer_days: int = Field(default=2, ge=0)
    """Don't roll within N days of current contract's expiry if it
    still has higher liquidity (prevents thrash as contract decays)."""


class UnderlyingDeclaration(BaseModel):
    """One representative-future underlying declaration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    underlying_id: str
    """Stable underlying ID (e.g. "BTC-USD-DERIBIT-DATED")."""

    category: UnderlyingCategory
    venue_id: str
    base_symbol: str
    quote_currency: str
    contract_code_format: str
    """Regex or strftime-like template for contract codes."""

    roll_policy: RollTriggerPolicy
    has_listed_calendar_combo: bool
    """True iff venue exposes listed calendar-spread combo tickers."""

    max_roll_slippage_bps: int = Field(default=15, ge=0, le=1_000)
    """Max permissible synthetic-combo slippage when listed combo missing."""

    feed_staleness_soft_freeze_seconds: int = Field(default=60, ge=0)
    """Feed staleness threshold for soft-freeze circuit breaker."""

    consecutive_failure_escalation_threshold: int = Field(default=3, ge=1)
    """Consecutive roll failures before escalation."""


REPRESENTATIVE_FUTURE_REGISTRY: Final[tuple[UnderlyingDeclaration, ...]] = (
    # ── Crypto dated (Deribit) ─────────────────────────────────────────
    UnderlyingDeclaration(
        underlying_id="BTC-USD-DERIBIT-DATED",
        category=UnderlyingCategory.CRYPTO_DATED,
        venue_id="deribit",
        base_symbol="BTC",
        quote_currency="USD",
        contract_code_format=r"BTC-\d+[A-Z]{3}\d+",
        roll_policy=RollTriggerPolicy(
            liquidity_feature_group_ref="deribit-dated-liquidity@v1",
            liquidity_margin_bps=1000,
            liquidity_confirmation_windows=3,
            expiry_buffer_days=2,
        ),
        has_listed_calendar_combo=True,
        max_roll_slippage_bps=20,
    ),
    UnderlyingDeclaration(
        underlying_id="ETH-USD-DERIBIT-DATED",
        category=UnderlyingCategory.CRYPTO_DATED,
        venue_id="deribit",
        base_symbol="ETH",
        quote_currency="USD",
        contract_code_format=r"ETH-\d+[A-Z]{3}\d+",
        roll_policy=RollTriggerPolicy(
            liquidity_feature_group_ref="deribit-dated-liquidity@v1",
            liquidity_margin_bps=1000,
            liquidity_confirmation_windows=3,
            expiry_buffer_days=2,
        ),
        has_listed_calendar_combo=True,
        max_roll_slippage_bps=25,
    ),
    # ── Equity index (CME) ─────────────────────────────────────────────
    UnderlyingDeclaration(
        underlying_id="ES-USD-CME",
        category=UnderlyingCategory.EQUITY_INDEX,
        venue_id="cme",
        base_symbol="ES",
        quote_currency="USD",
        contract_code_format=r"ES[A-Z]\d+",
        roll_policy=RollTriggerPolicy(
            liquidity_feature_group_ref="cme-equity-index-liquidity@v1",
            liquidity_margin_bps=800,
            liquidity_confirmation_windows=3,
            expiry_buffer_days=3,
        ),
        has_listed_calendar_combo=True,
        max_roll_slippage_bps=10,
    ),
    UnderlyingDeclaration(
        underlying_id="NQ-USD-CME",
        category=UnderlyingCategory.EQUITY_INDEX,
        venue_id="cme",
        base_symbol="NQ",
        quote_currency="USD",
        contract_code_format=r"NQ[A-Z]\d+",
        roll_policy=RollTriggerPolicy(
            liquidity_feature_group_ref="cme-equity-index-liquidity@v1",
            liquidity_margin_bps=800,
            liquidity_confirmation_windows=3,
            expiry_buffer_days=3,
        ),
        has_listed_calendar_combo=True,
        max_roll_slippage_bps=12,
    ),
    UnderlyingDeclaration(
        underlying_id="RTY-USD-CME",
        category=UnderlyingCategory.EQUITY_INDEX,
        venue_id="cme",
        base_symbol="RTY",
        quote_currency="USD",
        contract_code_format=r"RTY[A-Z]\d+",
        roll_policy=RollTriggerPolicy(
            liquidity_feature_group_ref="cme-equity-index-liquidity@v1",
            liquidity_margin_bps=1200,
            liquidity_confirmation_windows=3,
            expiry_buffer_days=3,
        ),
        has_listed_calendar_combo=True,
        max_roll_slippage_bps=18,
    ),
    # ── Commodity (CME / ICE) ──────────────────────────────────────────
    UnderlyingDeclaration(
        underlying_id="CL-USD-CME",
        category=UnderlyingCategory.COMMODITY,
        venue_id="cme",
        base_symbol="CL",
        quote_currency="USD",
        contract_code_format=r"CL[A-Z]\d+",
        roll_policy=RollTriggerPolicy(
            liquidity_feature_group_ref="cme-commodity-liquidity@v1",
            liquidity_margin_bps=900,
            liquidity_confirmation_windows=3,
            expiry_buffer_days=2,
        ),
        has_listed_calendar_combo=True,
        max_roll_slippage_bps=15,
    ),
    UnderlyingDeclaration(
        underlying_id="BRN-USD-ICE",
        category=UnderlyingCategory.COMMODITY,
        venue_id="ice",
        base_symbol="BRENT",
        quote_currency="USD",
        contract_code_format=r"BRN[A-Z]\d+",
        roll_policy=RollTriggerPolicy(
            liquidity_feature_group_ref="ice-commodity-liquidity@v1",
            liquidity_margin_bps=1000,
            liquidity_confirmation_windows=3,
            expiry_buffer_days=2,
        ),
        has_listed_calendar_combo=True,
        max_roll_slippage_bps=20,
    ),
    # ── FX (CME) ───────────────────────────────────────────────────────
    UnderlyingDeclaration(
        underlying_id="6E-USD-CME",
        category=UnderlyingCategory.FX,
        venue_id="cme",
        base_symbol="6E",
        quote_currency="USD",
        contract_code_format=r"6E[A-Z]\d+",
        roll_policy=RollTriggerPolicy(
            liquidity_feature_group_ref="cme-fx-liquidity@v1",
            liquidity_margin_bps=1200,
            liquidity_confirmation_windows=3,
            expiry_buffer_days=2,
        ),
        has_listed_calendar_combo=True,
        max_roll_slippage_bps=10,
    ),
)


class RepresentativeFutureChangedEvent(BaseModel):
    """UAC event schema — emitted by representative-future-service on roll.

    UTL constant lives in
    ``unified_trading_library/events/event_types.py::
    REPRESENTATIVE_FUTURE_CHANGED`` (registered in a paired UTL PR per
    G2.9 handoff). Consumers subscribe to the Pub/Sub topic and
    deserialise into this BaseModel.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: Literal["REPRESENTATIVE_FUTURE_CHANGED"] = "REPRESENTATIVE_FUTURE_CHANGED"
    underlying_id: str
    prior_contract: str
    """Prior contract code, e.g. "BTC-26DEC25"."""

    new_contract: str
    """New contract code, e.g. "BTC-27MAR26"."""

    decision_features: dict[str, float]
    """Snapshot of liquidity features that drove the decision."""

    decision_at_utc: str
    policy_content_hash: str
    """Content-hash of the active RollTriggerPolicy at decision-time."""

    correlation_id: str
    """For tracing downstream FUTURES_ROLL instructions."""


class UnderlyingNotRegisteredError(LookupError):
    """Raised when ``underlying_declaration_for(...)`` can't resolve."""


def underlying_declaration_for(
    underlying_id: str,
    *,
    registry: Iterable[UnderlyingDeclaration] = REPRESENTATIVE_FUTURE_REGISTRY,
) -> UnderlyingDeclaration:
    """Resolve an underlying declaration by ID. Fail-loud on miss."""

    for entry in registry:
        if entry.underlying_id == underlying_id:
            return entry
    raise UnderlyingNotRegisteredError(
        f"underlying_id={underlying_id!r} not in REPRESENTATIVE_FUTURE_REGISTRY",
    )


def underlyings_by_venue(
    venue_id: str,
    *,
    registry: Iterable[UnderlyingDeclaration] = REPRESENTATIVE_FUTURE_REGISTRY,
) -> tuple[UnderlyingDeclaration, ...]:
    """All underlyings tied to a given venue."""

    return tuple(entry for entry in registry if entry.venue_id == venue_id)


def underlyings_in_category(
    category: UnderlyingCategory,
    *,
    registry: Iterable[UnderlyingDeclaration] = REPRESENTATIVE_FUTURE_REGISTRY,
) -> tuple[UnderlyingDeclaration, ...]:
    """All underlyings in a given category."""

    return tuple(entry for entry in registry if entry.category is category)


def _validate_registry_invariants(
    registry: Iterable[UnderlyingDeclaration] = REPRESENTATIVE_FUTURE_REGISTRY,
) -> None:
    """Invariants:

    * ``underlying_id`` unique.
    * ``contract_code_format`` non-empty.
    * ``quote_currency`` is 3-4 uppercase letters.
    """

    seen: set[str] = set()
    for entry in registry:
        if entry.underlying_id in seen:
            raise ValueError(
                f"duplicate underlying_id in REPRESENTATIVE_FUTURE_REGISTRY: {entry.underlying_id!r}",
            )
        seen.add(entry.underlying_id)
        if not entry.contract_code_format:
            raise ValueError(
                f"{entry.underlying_id!r}: contract_code_format must be non-empty",
            )
        qc = entry.quote_currency
        if not (3 <= len(qc) <= 5) or not qc.isupper():
            raise ValueError(
                f"{entry.underlying_id!r}: quote_currency {qc!r} must be 3-5 upper letters",
            )


_validate_registry_invariants()


# NOTE: representative-future-service is NOT present in this workspace
# as of 2026-04-22 — scaffolded in a follow-up plan. features-service
# also absent; features-commodity-service / features-delta-one-service
# are the closest existing siblings that would implement the liquidity
# measure. strategy-service remains the anchor consumer for the event
# subscription.
CONSUMER_CALL_SITES: Final[tuple[str, ...]] = (
    "strategy-service/strategy_service/engine/slot_executor.py",
    "strategy-service/strategy_service/validation/freshness_gate.py",
    # representative-future-service (pending scaffold):
    "representative-future-service/representative_future_service/roll_engine.py",
    # features (choose commodity or delta-one based on category):
    "features-commodity-service/features_commodity_service/liquidity.py",
)


__all__ = [
    "CONSUMER_CALL_SITES",
    "REPRESENTATIVE_FUTURE_REGISTRY",
    "RepresentativeFutureChangedEvent",
    "RollTriggerPolicy",
    "UnderlyingCategory",
    "UnderlyingDeclaration",
    "UnderlyingNotRegisteredError",
    "underlying_declaration_for",
    "underlyings_by_venue",
    "underlyings_in_category",
]
