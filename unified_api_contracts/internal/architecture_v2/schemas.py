"""Strategy Architecture v2 — Pydantic schemas.

Polymorphic StrategyInstruction variants, AccountInstruction,
AllocationDirective, VenueCapabilityV2, identity tuples.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from unified_api_contracts.internal.architecture_v2.enums import (
    AccountActionV2,
    AllocatorArchetype,
    AtomicExecutionMode,
    CommissionStructureType,
    CompensationPolicy,
    InstructionActionV2,
    MarginMode,
    RiskGateDecision,
    RiskGateLayer,
    ShareClass,
    StrategyArchetype,
    StrategyFamily,
    Urgency,
    VenueCategoryV2,
    VenueFeature,
    VenueRoutingMode,
    VenueType,
)

# ---------------------------------------------------------------------------
# Venue capability v2
# ---------------------------------------------------------------------------


class LtvAndHaircut(BaseModel):
    asset: str
    max_ltv: Decimal
    haircut: Decimal
    liquidation_bonus: Decimal = Decimal("0")
    liquidation_threshold: Decimal | None = None


class CollateralRulesV2(BaseModel):
    eligible_assets: list[LtvAndHaircut] = Field(default_factory=list)
    interest_on_collateral: bool = False
    cross_margin_supported: bool = False
    portfolio_margin_supported: bool = False


class NettingRule(BaseModel):
    hedged_pair: tuple[str, str]
    netting_factor: Decimal
    description: str = ""


class MarginSpec(BaseModel):
    mode: MarginMode
    initial_margin_pct: Decimal | None = None
    maintenance_margin_pct: Decimal | None = None
    netting_rules: list[NettingRule] = Field(default_factory=list)
    portfolio_margin_greek_model: str | None = None
    min_cross_margin_pct_hedged: Decimal | None = None


class CommissionTier(BaseModel):
    tier_name: str
    volume_threshold_usd_30d: Decimal | None = None
    fee_bps_maker: Decimal
    fee_bps_taker: Decimal


class CommissionStructureV2(BaseModel):
    structure_type: CommissionStructureType
    tiers: list[CommissionTier] = Field(default_factory=list)
    flat_commission_bps: Decimal | None = None
    commission_on_win_bps: Decimal | None = None
    promotion_active: bool = False


class RegionalRestrictions(BaseModel):
    blocked_jurisdictions: list[str] = Field(default_factory=list)
    allowed_jurisdictions: list[str] = Field(default_factory=list)
    reg_notes: str = ""


class RateLimitsV2(BaseModel):
    per_second: int | None = None
    per_minute: int | None = None
    per_day: int | None = None
    weight_per_minute: int | None = None


class UnityChildVenue(BaseModel):
    child_venue_id: str
    display_name: str
    commission_bps: Decimal
    commission_type: CommissionStructureType = CommissionStructureType.FLAT
    supported_sports: list[str] = Field(default_factory=list)
    max_bet_usd: Decimal | None = None
    notes: str = ""
    confirmed: bool = True


class ChildVenueDecl(BaseModel):
    child_venue_id: str
    parent_venue_id: str
    display_name: str
    commission_bps: Decimal | None = None
    commission_type: CommissionStructureType = CommissionStructureType.FLAT
    supported_operations: list[str] = Field(default_factory=list)
    supported_instruments: list[str] = Field(default_factory=list)
    notes: str = ""


class VenueCapabilityV2(BaseModel):
    """v2 venue capability — adds haircuts, LTV, portfolio margin, child venues."""

    venue_id: str
    venue_type: VenueType
    category: VenueCategoryV2
    display_name: str
    supported_operations: list[str] = Field(default_factory=list)
    supported_instruments: list[str] = Field(default_factory=list)
    collateral_rules: CollateralRulesV2 | None = None
    margin_spec: MarginSpec | None = None
    liquidation_bonus_bps: Decimal | None = None
    commission_structure: CommissionStructureV2 | None = None
    regional_restrictions: RegionalRestrictions = Field(default_factory=RegionalRestrictions)
    rate_limits: RateLimitsV2 | None = None
    features: list[VenueFeature] = Field(default_factory=list)
    child_venues: list[ChildVenueDecl] = Field(default_factory=list)
    notes: str = ""


# ---------------------------------------------------------------------------
# Strategy identity
# ---------------------------------------------------------------------------


class StrategyInstanceIdentity(BaseModel):
    family: StrategyFamily
    archetype_id: StrategyArchetype
    archetype_build_version: str
    strategy_instance_id: str
    slot_version: int = 1
    config_hash: str
    config_version: int
    client_id: str
    share_class: ShareClass
    env: Literal["prod", "paper", "canary", "dev"] = "prod"
    holding_wallet: str | None = None
    """Mirrors ``StrategyInstanceDefinition.holding_wallet`` — the
    wallet address that holds the strategy's on-chain positions.
    Surfaced on the identity (not just the definition) so the engine
    can look it up at tick time without a definition round-trip. The
    runner copies this from the definition when constructing the
    identity in V2EngineOrchestrator.register_instance."""


class StrategyInstanceDefinition(BaseModel):
    strategy_instance_id: str
    archetype_id: StrategyArchetype
    family: StrategyFamily
    client_id: str
    capital_budget_amount: Decimal
    capital_budget_share_class: ShareClass
    share_class: ShareClass
    env: Literal["prod", "paper", "canary", "dev"] = "prod"
    created_at_utc: datetime
    created_by: str
    retired_at_utc: datetime | None = None
    retired_reason: str | None = None
    slot_version: int = 1
    notes: str = ""
    holding_wallet: str | None = None
    """The wallet/account address that holds the strategy's positions on
    chain (or sub-account id for CEX strategies). Restaking-aware
    archetypes use this to claim per-strategy seasonal rewards from the
    daily ``lst_seasonal_rewards`` parquet — the
    ``ParquetDustLoader`` filters parquet rows where ``recipient_address
    == holding_wallet``. None for asset_groups that don't need wallet-
    attributed reward streams (CEX-only, sports, prediction). Plumbed
    through ``StrategyInstanceIdentity`` -> ``BaseArchetypeEngineV2``
    -> Phase6Driver dust loader."""


# ---------------------------------------------------------------------------
# Polymorphic StrategyInstruction v2
# ---------------------------------------------------------------------------


class VenueConstraints(BaseModel):
    max_notional_usd: Decimal | None = None
    min_liquidity_usd: Decimal | None = None
    fee_tier: str | None = None
    max_slippage_bps: int | None = None


class StrategyInstructionEnvelope(BaseModel):
    instruction_id: str
    emitted_at_utc: datetime
    identity: StrategyInstanceIdentity
    urgency: Urgency = Urgency.MEDIUM
    deadline_utc: datetime | None = None
    execution_policy_ref: str | None = None
    attestations: dict[str, str] = Field(default_factory=dict)
    correlation_id: str | None = None
    eligible_venues: list[str] = Field(default_factory=list)
    venue_constraints: dict[str, VenueConstraints] = Field(default_factory=dict)
    venue_routing_mode: VenueRoutingMode = VenueRoutingMode.SOR_AT_EXECUTION
    target_venue: str | None = None
    chain: str | None = None


class TradeInstruction(StrategyInstructionEnvelope):
    action: Literal[InstructionActionV2.TRADE] = InstructionActionV2.TRADE
    target_position_units: Decimal
    target_instrument: str
    direction: Literal["LONG", "SHORT", "FLAT"] | None = None
    max_price: Decimal | None = None
    min_price: Decimal | None = None
    stop_loss_price: Decimal | None = None
    take_profit_price: Decimal | None = None


class SwapInstruction(StrategyInstructionEnvelope):
    action: Literal[InstructionActionV2.SWAP] = InstructionActionV2.SWAP
    in_asset: str
    out_asset: str
    in_amount: Decimal
    min_out_amount: Decimal
    route_hint: str | None = None
    mev_policy_ref: str | None = None


class LendInstruction(StrategyInstructionEnvelope):
    action: Literal[InstructionActionV2.LEND] = InstructionActionV2.LEND
    protocol: str
    asset: str
    target_supplied_amount: Decimal
    min_apy_bps: int | None = None


class BorrowInstruction(StrategyInstructionEnvelope):
    action: Literal[InstructionActionV2.BORROW] = InstructionActionV2.BORROW
    protocol: str
    asset: str
    target_debt_amount: Decimal
    max_borrow_apy_bps: int | None = None
    collateral_health_min: Decimal | None = None


class StakeInstruction(StrategyInstructionEnvelope):
    action: Literal[InstructionActionV2.STAKE] = InstructionActionV2.STAKE
    protocol: str
    asset: str
    target_staked_amount: Decimal
    lst_asset: str | None = None


class UnstakeInstruction(StrategyInstructionEnvelope):
    action: Literal[InstructionActionV2.UNSTAKE] = InstructionActionV2.UNSTAKE
    protocol: str
    asset: str
    amount: Decimal
    exit_queue_ok: bool = True


class QuoteInstruction(StrategyInstructionEnvelope):
    action: Literal[InstructionActionV2.QUOTE] = InstructionActionV2.QUOTE
    instrument: str
    reference_price: Decimal
    half_spread_bps: int
    max_inventory_abs: Decimal
    skew_on_inventory: bool = True
    refresh_cadence_ms: int = 1000


class TransferInstructionV2(StrategyInstructionEnvelope):
    action: Literal[InstructionActionV2.TRANSFER] = InstructionActionV2.TRANSFER
    asset: str
    venue_from: str
    venue_to: str
    target_balance_at_destination: Decimal
    max_cost_bps: int | None = None


class BridgeInstructionV2(StrategyInstructionEnvelope):
    action: Literal[InstructionActionV2.BRIDGE] = InstructionActionV2.BRIDGE
    asset: str
    chain_from: str
    chain_to: str
    target_balance_at_destination: Decimal
    bridge_hint: str | None = None


class AtomicLeg(BaseModel):
    leg_index: int
    action: InstructionActionV2
    instrument: str
    side: Literal["BUY", "SELL"] | None = None
    size_units: Decimal | None = None
    venue: str | None = None
    weight: Decimal | None = None
    params: dict[str, str] = Field(default_factory=dict)


class AtomicInstruction(StrategyInstructionEnvelope):
    action: Literal[InstructionActionV2.ATOMIC] = InstructionActionV2.ATOMIC
    legs: list[AtomicLeg]
    execution_mode: AtomicExecutionMode
    leader_leg: int | None = None
    hedge_deadline_ms: int | None = None
    compensation_policy: CompensationPolicy | None = None
    balance_mode: str | None = None
    max_total_slippage_bps: int | None = None


class CancelInstruction(StrategyInstructionEnvelope):
    action: Literal[InstructionActionV2.CANCEL] = InstructionActionV2.CANCEL
    cancel_instruction_id: str
    cancel_scope: Literal["SINGLE", "ALL_FOR_STRATEGY_INSTANCE"] = "SINGLE"


StrategyInstructionV2 = (
    TradeInstruction
    | SwapInstruction
    | LendInstruction
    | BorrowInstruction
    | StakeInstruction
    | UnstakeInstruction
    | QuoteInstruction
    | TransferInstructionV2
    | BridgeInstructionV2
    | AtomicInstruction
    | CancelInstruction
)


# ---------------------------------------------------------------------------
# AccountInstruction (operator-driven)
# ---------------------------------------------------------------------------


class AccountInstruction(BaseModel):
    instruction_id: str
    emitted_at_utc: datetime
    client_id: str
    initiating_operator: str
    authorization_id: str | None = None
    venue: str
    account_id: str
    action: AccountActionV2
    params: dict[str, str] = Field(default_factory=dict)
    rationale: str = ""
    strategy_instance_id: str | None = None


# ---------------------------------------------------------------------------
# AllocationDirective
# ---------------------------------------------------------------------------


class StrategyEquityDirective(BaseModel):
    strategy_instance_id: str
    target_equity: Decimal
    target_equity_share_class: Decimal
    share_class: ShareClass
    weight_pct: Decimal
    delta_vs_previous_pct: Decimal | None = None


class AllocationDirective(BaseModel):
    allocation_directive_id: str
    client_id: str
    allocator_id: str
    allocator_archetype: AllocatorArchetype
    allocator_version: int
    cadence_tick_utc: datetime
    total_client_equity_reporting_currency: Decimal
    reporting_currency: ShareClass
    directives: list[StrategyEquityDirective]
    rationale: list[str] = Field(default_factory=list)
    guard_rails_triggered: list[str] = Field(default_factory=list)
    shadow_mode: bool = False


# ---------------------------------------------------------------------------
# Risk gate result (dataclass — lightweight)
# ---------------------------------------------------------------------------


@dataclass
class RiskGateResult:
    layer: RiskGateLayer
    decision: RiskGateDecision
    reason: str = ""
    suggested_size: Decimal | None = None
    alternate_venue: str | None = None


# ---------------------------------------------------------------------------
# Compatibility matrix
# ---------------------------------------------------------------------------


class CompatibilityEntry(BaseModel):
    archetype: StrategyArchetype
    venue_category: VenueCategoryV2
    action: InstructionActionV2
    instrument_type: str
    supported: bool
    notes: str = ""


COMPATIBILITY_SEED: list[CompatibilityEntry] = [
    CompatibilityEntry(
        archetype=StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS,
        venue_category=VenueCategoryV2.CEFI,
        action=InstructionActionV2.TRADE,
        instrument_type="SPOT",
        supported=True,
    ),
    CompatibilityEntry(
        archetype=StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS,
        venue_category=VenueCategoryV2.CEFI,
        action=InstructionActionV2.TRADE,
        instrument_type="PERP",
        supported=True,
    ),
    CompatibilityEntry(
        archetype=StrategyArchetype.CARRY_RECURSIVE_STAKED,
        venue_category=VenueCategoryV2.DEFI,
        action=InstructionActionV2.ATOMIC,
        instrument_type="LEVERAGED_LENDING_LOOP",
        supported=True,
    ),
    CompatibilityEntry(
        archetype=StrategyArchetype.LIQUIDATION_CAPTURE,
        venue_category=VenueCategoryV2.DEFI,
        action=InstructionActionV2.ATOMIC,
        instrument_type="FLASH_LOAN",
        supported=True,
    ),
    CompatibilityEntry(
        archetype=StrategyArchetype.MARKET_MAKING_EVENT_SETTLED,
        venue_category=VenueCategoryV2.SPORTS,
        action=InstructionActionV2.QUOTE,
        instrument_type="BET_BACK",
        supported=True,
    ),
    CompatibilityEntry(
        archetype=StrategyArchetype.MARKET_MAKING_EVENT_SETTLED,
        venue_category=VenueCategoryV2.SPORTS,
        action=InstructionActionV2.QUOTE,
        instrument_type="BET_LAY",
        supported=True,
    ),
    CompatibilityEntry(
        archetype=StrategyArchetype.VOL_TRADING_OPTIONS,
        venue_category=VenueCategoryV2.CEFI,
        action=InstructionActionV2.ATOMIC,
        instrument_type="STRADDLE",
        supported=True,
    ),
    CompatibilityEntry(
        archetype=StrategyArchetype.STAT_ARB_CROSS_SECTIONAL,
        venue_category=VenueCategoryV2.TRADFI,
        action=InstructionActionV2.ATOMIC,
        instrument_type="BASKET",
        supported=True,
    ),
]


__all__ = [
    "COMPATIBILITY_SEED",
    "AccountInstruction",
    "AllocationDirective",
    "AtomicInstruction",
    "AtomicLeg",
    "BorrowInstruction",
    "BridgeInstructionV2",
    "CancelInstruction",
    "ChildVenueDecl",
    "CollateralRulesV2",
    "CommissionStructureV2",
    "CommissionTier",
    "CompatibilityEntry",
    "LendInstruction",
    "LtvAndHaircut",
    "MarginSpec",
    "NettingRule",
    "QuoteInstruction",
    "RateLimitsV2",
    "RegionalRestrictions",
    "RiskGateResult",
    "StakeInstruction",
    "StrategyEquityDirective",
    "StrategyInstanceDefinition",
    "StrategyInstanceIdentity",
    "StrategyInstructionEnvelope",
    "SwapInstruction",
    "TradeInstruction",
    "TransferInstructionV2",
    "UnityChildVenue",
    "UnstakeInstruction",
    "VenueCapabilityV2",
    "VenueConstraints",
]
