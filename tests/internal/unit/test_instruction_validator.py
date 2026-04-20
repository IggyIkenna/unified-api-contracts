"""Unit tests for G1.2 InstructionValidator.

Coverage targets (≥ 30 cases):
* Every one of the 8 required fields rejected when omitted / malformed
  (8 cases, Pydantic-layer).
* Each BL-1..BL-10 block-list group surfaces as a
  ``category+instrument_type`` rejection with a readable ``why`` (10
  cases).
* Venue not in archetype's ``supported_venues`` (3 cases across
  CeFi / DeFi / Sports).
* ``integration_depth`` scoring boundary cases: minimum-viable
  instruction, maximally-rich instruction, mixed (≥ 5 cases).
* Happy-path acceptance (≥ 3 cases).

SSOT:
- ``codex/14-playbooks/infra-spec/stage-3b-instruction-schema-contract.md`` §2
- ``codex/09-strategy/architecture-v2/category-instrument-coverage.md``
  (BL-1..BL-10).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.instruction import (
    AtomicLeg,
    ClientInstruction,
    InstructionAction,
    InstructionFieldError,
    InstructionValidationResult,
    InstructionValidator,
    InstrumentVenueContext,
    KillSwitchCondition,
    LifecycleReplaceCancel,
    LifecycleSemantic,
    OrderConstraints,
    RiskAndAllocationConstraints,
    SizeOrTargetExposure,
    StrategyInstructionId,
    TimeframeMode,
    TimeframeUrgency,
)
from unified_api_contracts.internal.architecture_v2.enums import VenueCategoryV2
from unified_api_contracts.strategy import ArchetypeInstrumentType

# ---------------------------------------------------------------------------
# Fixtures — reusable happy-path building blocks
# ---------------------------------------------------------------------------


def _ctx_cefi_perp_binance() -> InstrumentVenueContext:
    return InstrumentVenueContext(
        instrument_id="BTCUSDT",
        venue="binance",
        category=VenueCategoryV2.CEFI,
        instrument_type=ArchetypeInstrumentType.PERP,
    )


def _qty_size() -> SizeOrTargetExposure:
    return SizeOrTargetExposure(quantity_value=Decimal("0.5"), quantity_unit="BTC")


def _notional_size() -> SizeOrTargetExposure:
    return SizeOrTargetExposure(notional_value=Decimal("10000"), notional_currency="USDT")


def _weight_size() -> SizeOrTargetExposure:
    return SizeOrTargetExposure(target_portfolio_weight=Decimal("0.1"))


def _market_timeframe() -> TimeframeUrgency:
    return TimeframeUrgency(mode=TimeframeMode.MARKET)


def _minimal_constraints() -> OrderConstraints:
    return OrderConstraints()


def _rich_constraints() -> OrderConstraints:
    return OrderConstraints(
        price_limit=Decimal("60000"),
        max_participation_pct=Decimal("10"),
        slippage_budget_bps=Decimal("5"),
    )


def _strategy_id() -> StrategyInstructionId:
    return StrategyInstructionId(client_strategy_id="strategy-x", instruction_id="inst-001")


def _lifecycle_new() -> LifecycleReplaceCancel:
    return LifecycleReplaceCancel(semantic=LifecycleSemantic.NEW)


def _minimal_risk() -> RiskAndAllocationConstraints:
    return RiskAndAllocationConstraints(per_instruction_max_loss=Decimal("100"))


def _rich_risk() -> RiskAndAllocationConstraints:
    return RiskAndAllocationConstraints(
        per_instruction_max_loss=Decimal("100"),
        per_client_allocation_cap=Decimal("0.2"),
        kill_switch_conditions=(KillSwitchCondition(metric="drawdown_bps", threshold=Decimal("500")),),
    )


def _make_instruction(
    *,
    ctx: InstrumentVenueContext | None = None,
    action: InstructionAction = InstructionAction.BUY,
    size: SizeOrTargetExposure | None = None,
    timeframe: TimeframeUrgency | None = None,
    constraints: OrderConstraints | None = None,
    lifecycle: LifecycleReplaceCancel | None = None,
    risk: RiskAndAllocationConstraints | None = None,
) -> ClientInstruction:
    return ClientInstruction(
        instrument_venue_context=ctx or _ctx_cefi_perp_binance(),
        intended_action=action,
        size_or_target_exposure=size or _qty_size(),
        timeframe_urgency=timeframe or _market_timeframe(),
        order_constraints=constraints or _minimal_constraints(),
        strategy_instruction_id=_strategy_id(),
        lifecycle_replace_cancel=lifecycle or _lifecycle_new(),
        risk_and_allocation_constraints=risk or _minimal_risk(),
    )


# ---------------------------------------------------------------------------
# 1. Required-field Pydantic-layer rejection (8 cases — one per field)
# ---------------------------------------------------------------------------


def _base_payload() -> dict[str, object]:
    return {
        "instrument_venue_context": {
            "instrument_id": "BTCUSDT",
            "venue": "binance",
            "category": "CEFI",
            "instrument_type": "perp",
        },
        "intended_action": "BUY",
        "size_or_target_exposure": {"quantity_value": "0.5", "quantity_unit": "BTC"},
        "timeframe_urgency": {"mode": "MARKET"},
        "order_constraints": {},
        "strategy_instruction_id": {
            "client_strategy_id": "s-1",
            "instruction_id": "i-1",
        },
        "lifecycle_replace_cancel": {"semantic": "NEW"},
        "risk_and_allocation_constraints": {"per_instruction_max_loss": "100"},
    }


@pytest.mark.parametrize(
    "missing_field",
    [
        "instrument_venue_context",
        "intended_action",
        "size_or_target_exposure",
        "timeframe_urgency",
        "order_constraints",
        "strategy_instruction_id",
        "lifecycle_replace_cancel",
        "risk_and_allocation_constraints",
    ],
)
def test_missing_required_field_rejected(missing_field: str) -> None:
    """Every one of the 8 required fields must be enforced by Pydantic."""

    payload = _base_payload()
    del payload[missing_field]
    with pytest.raises(ValidationError) as exc_info:
        ClientInstruction.model_validate(payload)
    errors = InstructionValidator.errors_from_pydantic(exc_info.value.errors())
    assert any(missing_field in err.field for err in errors), (
        f"expected an error targeting {missing_field} — got {[e.field for e in errors]}"
    )


# ---------------------------------------------------------------------------
# 2. Block-list groups BL-1..BL-10 — each surfaces as pair-level rejection
# ---------------------------------------------------------------------------


BLOCK_LIST_CASES: list[tuple[str, VenueCategoryV2, ArchetypeInstrumentType, str]] = [
    # (ref, category, instrument_type, representative_venue)
    ("BL-1", VenueCategoryV2.DEFI, ArchetypeInstrumentType.OPTION, "uniswap_v3"),
    ("BL-2", VenueCategoryV2.DEFI, ArchetypeInstrumentType.DATED_FUTURE, "uniswap_v3"),
    ("BL-3", VenueCategoryV2.CEFI, ArchetypeInstrumentType.LENDING, "binance"),
    ("BL-4", VenueCategoryV2.SPORTS, ArchetypeInstrumentType.SPOT, "unity"),
    ("BL-5", VenueCategoryV2.PREDICTION, ArchetypeInstrumentType.PERP, "polymarket"),
    ("BL-6", VenueCategoryV2.TRADFI, ArchetypeInstrumentType.PERP, "ibkr"),
    ("BL-7", VenueCategoryV2.CEFI, ArchetypeInstrumentType.STAKING, "binance"),
    ("BL-8", VenueCategoryV2.TRADFI, ArchetypeInstrumentType.STAKING, "ibkr"),
    ("BL-9", VenueCategoryV2.CEFI, ArchetypeInstrumentType.LP, "binance"),
    ("BL-10", VenueCategoryV2.CEFI, ArchetypeInstrumentType.EVENT_SETTLED, "binance"),
]


@pytest.mark.parametrize(
    "ref,category,instrument_type,venue",
    BLOCK_LIST_CASES,
    ids=[case[0] for case in BLOCK_LIST_CASES],
)
def test_block_list_group_rejection(
    ref: str,
    category: VenueCategoryV2,
    instrument_type: ArchetypeInstrumentType,
    venue: str,
) -> None:
    """Each BL-* group must surface a pair-level FieldError with clear copy.

    The validator consults ``archetypes_for_pair()`` which respects the
    BL-* groupings baked into the G1.8 manifest — we don't need to
    re-enforce them here, we just verify rejection routes correctly.
    """

    # Construct a ClientInstruction targeting a blocked pair.
    ctx = InstrumentVenueContext(
        instrument_id="SOMETHING",
        venue=venue,
        category=category,
        instrument_type=instrument_type,
        chain="eth" if category == VenueCategoryV2.DEFI else None,
    )
    instruction = _make_instruction(ctx=ctx)

    validator = InstructionValidator()
    result = validator.validate(instruction)

    assert not result.ok, f"{ref}: expected rejection, got ok"
    assert result.integration_depth == 0.0
    assert any("category+instrument_type" in err.field for err in result.errors), (
        f"{ref}: expected category+instrument_type error, got {[e.field for e in result.errors]}"
    )
    first = next(err for err in result.errors if "category+instrument_type" in err.field)
    assert category.value in first.violation
    assert instrument_type.value in first.violation
    assert "UAC ArchetypeCapabilityRegistry" in first.why


# ---------------------------------------------------------------------------
# 3. Venue-mismatch (3 cases)
# ---------------------------------------------------------------------------


def test_venue_mismatch_cefi_perp() -> None:
    """Valid pair but venue not in any archetype's supported_venues."""
    ctx = InstrumentVenueContext(
        instrument_id="BTCUSDT",
        venue="nonexistent_exchange_xyz",
        category=VenueCategoryV2.CEFI,
        instrument_type=ArchetypeInstrumentType.PERP,
    )
    instruction = _make_instruction(ctx=ctx)
    result = InstructionValidator().validate(instruction)
    assert not result.ok
    assert any(err.field.endswith(".venue") for err in result.errors)


def test_venue_mismatch_defi_spot() -> None:
    """DeFi spot pair is supported; unknown venue id rejected."""
    ctx = InstrumentVenueContext(
        instrument_id="WETH",
        venue="made_up_dex_xyz",
        category=VenueCategoryV2.DEFI,
        instrument_type=ArchetypeInstrumentType.SPOT,
        chain="eth",
    )
    instruction = _make_instruction(ctx=ctx)
    result = InstructionValidator().validate(instruction)
    assert not result.ok
    # Expect a venue error (pair-level OK since DeFi spot is SUPPORTED).
    assert any(err.field.endswith(".venue") for err in result.errors)


def test_venue_mismatch_sports_event_settled() -> None:
    """Sports pair OK, venue is an unregistered sportsbook — reject."""
    ctx = InstrumentVenueContext(
        instrument_id="EV-42",
        venue="mystery_sportsbook",
        category=VenueCategoryV2.SPORTS,
        instrument_type=ArchetypeInstrumentType.EVENT_SETTLED,
    )
    instruction = _make_instruction(ctx=ctx)
    result = InstructionValidator().validate(instruction)
    assert not result.ok
    assert any(err.field.endswith(".venue") for err in result.errors)


# ---------------------------------------------------------------------------
# 4. Nested-field validators (Pydantic raises; not validator.validate)
# ---------------------------------------------------------------------------


def test_defi_without_chain_rejected() -> None:
    """DEFI context without ``chain`` populated is invalid."""
    with pytest.raises(ValidationError):
        InstrumentVenueContext(
            instrument_id="WETH",
            venue="uniswap_v3",
            category=VenueCategoryV2.DEFI,
            instrument_type=ArchetypeInstrumentType.SPOT,
            chain=None,
        )


def test_size_requires_exactly_one() -> None:
    """Populating two of {quantity, notional, target_weight} is a validation error."""
    with pytest.raises(ValidationError):
        SizeOrTargetExposure(
            quantity_value=Decimal("1"),
            quantity_unit="BTC",
            target_portfolio_weight=Decimal("0.1"),
        )


def test_size_requires_at_least_one() -> None:
    """Populating none of {quantity, notional, target_weight} is a validation error."""
    with pytest.raises(ValidationError):
        SizeOrTargetExposure()


def test_timeframe_time_window_requires_window_minutes() -> None:
    """TIME_WINDOW mode requires window_minutes."""
    with pytest.raises(ValidationError):
        TimeframeUrgency(mode=TimeframeMode.TIME_WINDOW, deadline="2026-04-21T00:00:00Z")


def test_replace_requires_supersedes() -> None:
    """REPLACE lifecycle semantic requires supersedes_instruction_id."""
    with pytest.raises(ValidationError):
        LifecycleReplaceCancel(semantic=LifecycleSemantic.REPLACE)


def test_risk_requires_at_least_one_anchor() -> None:
    """RiskAndAllocationConstraints needs one of the two required anchors."""
    with pytest.raises(ValidationError):
        RiskAndAllocationConstraints()


def test_atomic_requires_legs() -> None:
    """ATOMIC action requires at least 2 legs in order_constraints."""
    with pytest.raises(ValidationError):
        _make_instruction(action=InstructionAction.ATOMIC)


def test_atomic_accepts_two_legs() -> None:
    """Supplying two legs under ATOMIC passes construction."""
    legs = (
        AtomicLeg(
            instrument_id="BTCUSDT",
            action=InstructionAction.BUY,
            size=_qty_size(),
        ),
        AtomicLeg(
            instrument_id="ETHUSDT",
            action=InstructionAction.SELL,
            size=_qty_size(),
        ),
    )
    constraints = OrderConstraints(legs=legs)
    instruction = _make_instruction(
        action=InstructionAction.ATOMIC,
        constraints=constraints,
    )
    assert instruction.intended_action == InstructionAction.ATOMIC
    assert len(instruction.order_constraints.legs) == 2


# ---------------------------------------------------------------------------
# 5. Integration-depth scoring (5+ boundary cases)
# ---------------------------------------------------------------------------


def test_integration_depth_minimal_instruction() -> None:
    """A just-barely-valid instruction (minimal risk, empty constraints) scores strictly < 1.0."""
    instruction = _make_instruction()  # minimal constraints + minimal risk
    result = InstructionValidator().validate(instruction)
    assert result.ok
    # 7/8 fields are structured; risk is bare-minimum + constraints empty.
    assert 0.6 <= result.integration_depth < 1.0


def test_integration_depth_rich_instruction() -> None:
    """Fully populated instruction hits the structured-score plateau."""
    instruction = _make_instruction(
        constraints=_rich_constraints(),
        risk=_rich_risk(),
    )
    result = InstructionValidator().validate(instruction)
    assert result.ok
    # With rich constraints (3 of 5 structured) + rich risk (3 anchors), all 8 weights → 1.0.
    assert result.integration_depth >= 0.95


def test_integration_depth_hybrid_constraints() -> None:
    """Two structured constraint fields → hybrid weight 0.5 on that axis."""
    hybrid_constraints = OrderConstraints(
        price_limit=Decimal("60000"),
        time_in_force=None,
        slippage_budget_bps=Decimal("5"),
    )
    instruction = _make_instruction(constraints=hybrid_constraints, risk=_rich_risk())
    result = InstructionValidator().validate(instruction)
    assert result.ok
    # 7 structured + 1 hybrid = 7.5 / 8 = 0.9375
    assert 0.9 <= result.integration_depth < 1.0


def test_integration_depth_notional_size_structured() -> None:
    """Notional size (structured oneof) scores 1.0 on the size axis."""
    instruction = _make_instruction(size=_notional_size())
    result = InstructionValidator().validate(instruction)
    assert result.ok
    assert result.integration_depth > 0.0


def test_integration_depth_target_weight_size_structured() -> None:
    """Target-portfolio-weight size is structured."""
    instruction = _make_instruction(size=_weight_size(), risk=_rich_risk())
    result = InstructionValidator().validate(instruction)
    assert result.ok
    assert result.integration_depth > 0.0


def test_integration_depth_bounds_always_in_unit_interval() -> None:
    """Integration-depth is always in [0, 1]."""
    instruction = _make_instruction(constraints=_rich_constraints(), risk=_rich_risk())
    result = InstructionValidator().validate(instruction)
    assert 0.0 <= result.integration_depth <= 1.0


def test_integration_depth_zero_on_failure() -> None:
    """Rejected instructions carry integration_depth = 0.0 by contract."""
    ctx = InstrumentVenueContext(
        instrument_id="X",
        venue="uniswap_v3",
        category=VenueCategoryV2.DEFI,
        instrument_type=ArchetypeInstrumentType.OPTION,  # BL-1
        chain="eth",
    )
    instruction = _make_instruction(ctx=ctx)
    result = InstructionValidator().validate(instruction)
    assert not result.ok
    assert result.integration_depth == 0.0


# ---------------------------------------------------------------------------
# 6. Happy-path acceptance (3+ cases across categories)
# ---------------------------------------------------------------------------


def test_happy_path_cefi_perp_binance() -> None:
    instruction = _make_instruction()
    result = InstructionValidator().validate(instruction)
    assert result.ok
    assert result.errors == ()
    assert 0.0 < result.integration_depth <= 1.0


def test_happy_path_defi_spot_uniswap() -> None:
    ctx = InstrumentVenueContext(
        instrument_id="WETH",
        venue="uniswap_v3",
        category=VenueCategoryV2.DEFI,
        instrument_type=ArchetypeInstrumentType.SPOT,
        chain="eth",
    )
    instruction = _make_instruction(ctx=ctx)
    result = InstructionValidator().validate(instruction)
    assert result.ok


def test_happy_path_sports_event_settled_betfair() -> None:
    ctx = InstrumentVenueContext(
        instrument_id="EV-42",
        venue="betfair_direct",
        category=VenueCategoryV2.SPORTS,
        instrument_type=ArchetypeInstrumentType.EVENT_SETTLED,
    )
    instruction = _make_instruction(ctx=ctx, action=InstructionAction.BACK)
    result = InstructionValidator().validate(instruction)
    assert result.ok


def test_happy_path_tradfi_dated_future_cme() -> None:
    ctx = InstrumentVenueContext(
        instrument_id="ES-Z6",
        venue="cme",
        category=VenueCategoryV2.TRADFI,
        instrument_type=ArchetypeInstrumentType.DATED_FUTURE,
    )
    instruction = _make_instruction(ctx=ctx)
    result = InstructionValidator().validate(instruction)
    assert result.ok


# ---------------------------------------------------------------------------
# 7. InstructionValidationResult invariants
# ---------------------------------------------------------------------------


def test_ok_true_cannot_carry_errors() -> None:
    with pytest.raises(ValidationError):
        InstructionValidationResult(
            ok=True,
            integration_depth=0.5,
            errors=(
                InstructionFieldError(
                    field="x",
                    violation="y",
                    allowed=(),
                    why="z",
                ),
            ),
        )


def test_ok_false_requires_errors() -> None:
    with pytest.raises(ValidationError):
        InstructionValidationResult(ok=False, integration_depth=0.0, errors=())


def test_integration_depth_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        InstructionValidationResult(ok=True, integration_depth=1.5, errors=())


# ---------------------------------------------------------------------------
# 8. errors_from_pydantic translation utility
# ---------------------------------------------------------------------------


def test_errors_from_pydantic_translates_shape() -> None:
    """Utility translates pydantic ValidationError.errors() into FieldError[]."""
    payload = _base_payload()
    del payload["strategy_instruction_id"]
    with pytest.raises(ValidationError) as exc:
        ClientInstruction.model_validate(payload)
    errors = InstructionValidator.errors_from_pydantic(exc.value.errors())
    assert len(errors) > 0
    for err in errors:
        assert isinstance(err, InstructionFieldError)
        assert err.field
        assert err.violation
