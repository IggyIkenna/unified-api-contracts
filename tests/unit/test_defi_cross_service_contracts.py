"""Cross-service contract consistency tests for DeFi types, enums, and registries.

Validates that all the types, enums, and registries used across services
are internally consistent -- operation types exist in both internal and
canonical layers, wrapping rules align with collateral acceptance, reward
schedules align with operation types, risk taxonomy is complete, client
config fields align with strategy requirements, and monitoring extensions
are properly structured.
"""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.risk_taxonomy import RiskType
from unified_api_contracts.canonical.crosscutting.share_class import (
    SHARE_CLASS_BASE_ASSETS,
    ShareClass,
)
from unified_api_contracts.canonical.domain.execution.base import (
    OperationType as CanonicalOperationType,
)
from unified_api_contracts.internal.domain.execution_service.types import (
    OperationType as InternalOperationType,
)
from unified_api_contracts.internal.domain.strategy_service.client_config import (
    ClientStrategyOverride,
)
from unified_api_contracts.internal.domain.strategy_service.monitoring import (
    StrategyNAV,
)
from unified_api_contracts.internal.positions.reward_position import RewardPosition
from unified_api_contracts.registry.reward_schedules import REWARD_SCHEDULES
from unified_api_contracts.registry.token_wrapping import (
    TOKEN_WRAPPING_RULES,
    needs_wrapping,
)
from unified_api_contracts.registry.venue_collateral import (
    VENUE_COLLATERAL_MATRIX,
    venue_accepts_collateral,
)

# ---------------------------------------------------------------------------
# OperationType Completeness
# ---------------------------------------------------------------------------


class TestOperationTypeCompleteness:
    """Verify all DeFi operation types exist and have correct mappings."""

    def test_claim_reward_exists_in_internal(self) -> None:
        assert hasattr(InternalOperationType, "CLAIM_REWARD")
        assert InternalOperationType.CLAIM_REWARD == "CLAIM_REWARD"

    def test_sell_reward_exists_in_internal(self) -> None:
        assert hasattr(InternalOperationType, "SELL_REWARD")
        assert InternalOperationType.SELL_REWARD == "SELL_REWARD"

    def test_claim_reward_exists_in_canonical(self) -> None:
        assert hasattr(CanonicalOperationType, "CLAIM_REWARD")
        assert CanonicalOperationType.CLAIM_REWARD == "CLAIM_REWARD"

    def test_sell_reward_exists_in_canonical(self) -> None:
        assert hasattr(CanonicalOperationType, "SELL_REWARD")
        assert CanonicalOperationType.SELL_REWARD == "SELL_REWARD"

    def test_claim_reward_benchmark_is_oracle(self) -> None:
        """CLAIM_REWARD has no execution alpha -- benchmark type is ORACLE."""
        benchmark = InternalOperationType.benchmark_type_for_operation(
            InternalOperationType.CLAIM_REWARD,
        )
        assert benchmark == "ORACLE"

    def test_sell_reward_benchmark_is_arrival(self) -> None:
        """SELL_REWARD converts claimed tokens -- benchmark is ARRIVAL."""
        benchmark = InternalOperationType.benchmark_type_for_operation(
            InternalOperationType.SELL_REWARD,
        )
        assert benchmark == "ARRIVAL"

    def test_every_defi_operation_has_benchmark_type_mapping(self) -> None:
        """Every DeFi-relevant operation has a default benchmark_type mapping."""
        defi_ops = [
            InternalOperationType.LEND,
            InternalOperationType.BORROW,
            InternalOperationType.REPAY,
            InternalOperationType.WITHDRAW,
            InternalOperationType.STAKE,
            InternalOperationType.UNSTAKE,
            InternalOperationType.SWAP,
            InternalOperationType.TRADE,
            InternalOperationType.FLASH_BORROW,
            InternalOperationType.FLASH_REPAY,
            InternalOperationType.TRANSFER,
            InternalOperationType.CLAIM_REWARD,
            InternalOperationType.SELL_REWARD,
            InternalOperationType.COLLECT_FEES,
            InternalOperationType.ADD_LIQUIDITY,
            InternalOperationType.REMOVE_LIQUIDITY,
        ]
        for op in defi_ops:
            benchmark = InternalOperationType.benchmark_type_for_operation(op)
            assert isinstance(benchmark, str), f"benchmark_type_for_operation({op.name}) returned non-string"
            assert len(benchmark) > 0, f"benchmark_type_for_operation({op.name}) returned empty string"

    def test_all_required_defi_operations_exist_in_internal(self) -> None:
        """All 16 DeFi operation type values exist."""
        required = {
            "LEND",
            "BORROW",
            "REPAY",
            "WITHDRAW",
            "STAKE",
            "UNSTAKE",
            "SWAP",
            "TRADE",
            "FLASH_BORROW",
            "FLASH_REPAY",
            "TRANSFER",
            "CLAIM_REWARD",
            "SELL_REWARD",
            "COLLECT_FEES",
            "ADD_LIQUIDITY",
            "REMOVE_LIQUIDITY",
        }
        internal_members = {m.name for m in InternalOperationType}
        missing = required - internal_members
        assert not missing, f"Missing from internal OperationType: {missing}"

    def test_all_required_defi_operations_exist_in_canonical(self) -> None:
        """All DeFi operations also exist in the canonical layer."""
        required = {
            "LEND",
            "BORROW",
            "REPAY",
            "WITHDRAW",
            "STAKE",
            "UNSTAKE",
            "SWAP",
            "FLASH_BORROW",
            "FLASH_REPAY",
            "CLAIM_REWARD",
            "SELL_REWARD",
            "COLLECT_FEES",
            "ADD_LIQUIDITY",
            "REMOVE_LIQUIDITY",
        }
        canonical_members = {m.name for m in CanonicalOperationType}
        missing = required - canonical_members
        assert not missing, f"Missing from canonical OperationType: {missing}"


# ---------------------------------------------------------------------------
# Token Wrapping <-> Venue Collateral Consistency
# ---------------------------------------------------------------------------


class TestTokenWrappingVenueCollateralConsistency:
    """Verify that wrapped tokens are accepted by the venues that need wrapping."""

    def test_eth_wraps_to_weth_and_aave_accepts_weth(self) -> None:
        """ETH wraps to WETH, and AAVEV3-ETHEREUM accepts WETH."""
        wrap_needed, target = needs_wrapping("ETH", "AAVEV3")
        assert wrap_needed is True
        assert target == "WETH"
        assert venue_accepts_collateral("AAVEV3-ETHEREUM", "WETH")

    def test_eeth_wraps_to_weeth_and_aave_accepts_weeth(self) -> None:
        """eETH wraps to weETH, and AAVEV3-ETHEREUM accepts weETH."""
        wrap_needed, target = needs_wrapping("eETH", "AAVEV3")
        assert wrap_needed is True
        assert target == "weETH"
        assert venue_accepts_collateral("AAVEV3-ETHEREUM", "weETH")

    def test_steth_wraps_to_wsteth_and_aave_accepts_wsteth(self) -> None:
        """stETH wraps to wstETH, and AAVEV3-ETHEREUM accepts wstETH."""
        wrap_needed, target = needs_wrapping("stETH", "AAVEV3")
        assert wrap_needed is True
        assert target == "wstETH"
        assert venue_accepts_collateral("AAVEV3-ETHEREUM", "wstETH")

    def test_hyperliquid_only_accepts_usdc(self) -> None:
        """HYPERLIQUID only accepts USDC; ETH/WETH/weETH are rejected."""
        assert venue_accepts_collateral("HYPERLIQUID", "USDC")
        assert not venue_accepts_collateral("HYPERLIQUID", "ETH")
        assert not venue_accepts_collateral("HYPERLIQUID", "WETH")
        assert not venue_accepts_collateral("HYPERLIQUID", "weETH")

    def test_every_wrapped_token_accepted_by_at_least_one_venue(self) -> None:
        """Every wrapped token in TOKEN_WRAPPING_RULES is accepted somewhere."""
        accepted_tokens = {e.token for e in VENUE_COLLATERAL_MATRIX if e.accepted}
        for rule in TOKEN_WRAPPING_RULES:
            assert rule.wrapped in accepted_tokens, (
                f"Wrapped token {rule.wrapped} from wrapping rule "
                f"({rule.unwrapped} -> {rule.wrapped}) is not accepted by any venue"
            )

    def test_wrapping_rules_consistent_with_venue_acceptance(self) -> None:
        """No wrapping rule produces a token that no venue accepts."""
        accepted_tokens = {e.token for e in VENUE_COLLATERAL_MATRIX if e.accepted}
        for rule in TOKEN_WRAPPING_RULES:
            assert rule.wrapped in accepted_tokens, (
                f"Wrapping rule {rule.unwrapped} -> {rule.wrapped} produces a token not accepted by any venue"
            )


# ---------------------------------------------------------------------------
# Share Class <-> Risk Taxonomy Consistency
# ---------------------------------------------------------------------------


class TestShareClassRiskTaxonomyConsistency:
    """Verify share class and risk taxonomy are complete and aligned."""

    def test_every_share_class_has_base_assets(self) -> None:
        """Every ShareClass enum value has a corresponding entry in SHARE_CLASS_BASE_ASSETS."""
        for sc in ShareClass:
            assert sc.value in SHARE_CLASS_BASE_ASSETS, (
                f"ShareClass.{sc.name} ({sc.value}) has no entry in SHARE_CLASS_BASE_ASSETS"
            )

    def test_oracle_depeg_risk_type_exists(self) -> None:
        assert RiskType.ORACLE_DEPEG == "oracle_depeg"

    def test_stablecoin_depeg_risk_type_exists(self) -> None:
        assert RiskType.STABLECOIN_DEPEG == "stablecoin_depeg"

    def test_borrow_rate_spread_risk_type_exists(self) -> None:
        assert RiskType.BORROW_RATE_SPREAD == "borrow_rate_spread"

    def test_withdrawal_delay_risk_type_exists(self) -> None:
        assert RiskType.WITHDRAWAL_DELAY == "withdrawal_delay"

    def test_defi_risk_types_cover_monitoring(self) -> None:
        """DeFi-specific risk types cover all DeFi risk monitoring dimensions."""
        defi_risk_types = {
            RiskType.ORACLE_DEPEG,
            RiskType.STABLECOIN_DEPEG,
            RiskType.BORROW_RATE_SPREAD,
            RiskType.WITHDRAWAL_DELAY,
            RiskType.EMERGENCY_CLOSE_COST,
            RiskType.REBALANCE_COST,
        }
        all_risk_types = set(RiskType)
        assert defi_risk_types.issubset(all_risk_types), f"Missing DeFi risk types: {defi_risk_types - all_risk_types}"


# ---------------------------------------------------------------------------
# Reward Schedule <-> OperationType Consistency
# ---------------------------------------------------------------------------


class TestRewardScheduleOperationTypeConsistency:
    """Verify reward schedules are backed by CLAIM_REWARD/SELL_REWARD operations."""

    def test_eigenlayer_reward_schedule_exists(self) -> None:
        """EIGENLAYER reward schedule exists."""
        protocols = [s.protocol for s in REWARD_SCHEDULES]
        assert "EIGENLAYER" in protocols

    def test_etherfi_reward_schedule_exists(self) -> None:
        """ETHERFI reward schedule exists."""
        protocols = [s.protocol for s in REWARD_SCHEDULES]
        assert "ETHERFI" in protocols

    def test_reward_schedules_reference_valid_protocols(self) -> None:
        """Every reward schedule references a known protocol name."""
        known_protocols = {"EIGENLAYER", "ETHERFI"}
        for entry in REWARD_SCHEDULES:
            assert entry.protocol in known_protocols, f"Unknown protocol in reward schedule: {entry.protocol}"

    def test_claim_reward_operation_exists_for_reward_schedules(self) -> None:
        """CLAIM_REWARD operation type exists to handle reward claiming."""
        assert len(REWARD_SCHEDULES) > 0
        assert hasattr(InternalOperationType, "CLAIM_REWARD")
        assert hasattr(CanonicalOperationType, "CLAIM_REWARD")

    def test_sell_reward_exists_for_converting_claimed_tokens(self) -> None:
        """SELL_REWARD must exist for converting claimed tokens to base currency."""
        assert hasattr(InternalOperationType, "SELL_REWARD")
        assert hasattr(CanonicalOperationType, "SELL_REWARD")

    def test_reward_schedules_have_sell_routing(self) -> None:
        """Each reward schedule specifies sell_venue and sell_pair."""
        for entry in REWARD_SCHEDULES:
            assert entry.sell_venue, f"Reward schedule for {entry.protocol}/{entry.reward_token} has no sell_venue"
            assert entry.sell_pair, f"Reward schedule for {entry.protocol}/{entry.reward_token} has no sell_pair"


# ---------------------------------------------------------------------------
# Client Config <-> Strategy Config Alignment
# ---------------------------------------------------------------------------


class TestClientConfigStrategyAlignment:
    """Verify ClientStrategyOverride has all fields needed by strategy execution."""

    def test_has_allowed_perp_venues(self) -> None:
        assert "allowed_perp_venues" in ClientStrategyOverride.model_fields

    def test_has_multi_coin_rotation(self) -> None:
        assert "multi_coin_rotation" in ClientStrategyOverride.model_fields

    def test_has_fixed_basis_coin(self) -> None:
        assert "fixed_basis_coin" in ClientStrategyOverride.model_fields

    def test_default_multi_coin_rotation_is_true(self) -> None:
        """multi_coin_rotation defaults to True (enabled)."""
        override = ClientStrategyOverride(client_id="test", strategy_id="test")
        assert override.multi_coin_rotation is True

    def test_fixed_basis_coin_default_is_none(self) -> None:
        """fixed_basis_coin defaults to None (no fixed coin)."""
        override = ClientStrategyOverride(client_id="test", strategy_id="test")
        assert override.fixed_basis_coin is None

    def test_allowed_perp_venues_default_is_none(self) -> None:
        """allowed_perp_venues defaults to None (unrestricted)."""
        override = ClientStrategyOverride(client_id="test", strategy_id="test")
        assert override.allowed_perp_venues is None


# ---------------------------------------------------------------------------
# RewardPosition Model Validation
# ---------------------------------------------------------------------------


class TestRewardPositionModel:
    """Verify RewardPosition can be instantiated for known reward tokens."""

    def test_eigen_reward_position_with_accrued(self) -> None:
        """RewardPosition can be instantiated for EIGEN with accrued > 0."""
        pos = RewardPosition(
            protocol="EIGENLAYER",
            reward_token="EIGEN",
            accrued_amount=Decimal("100.5"),
            accrued_value_usd=Decimal("350.75"),
        )
        assert pos.protocol == "EIGENLAYER"
        assert pos.reward_token == "EIGEN"
        assert pos.accrued_amount > 0
        assert pos.accrued_value_usd > 0

    def test_ethfi_reward_position_with_claimed(self) -> None:
        """RewardPosition can be instantiated for ETHFI with claimed > 0."""
        pos = RewardPosition(
            protocol="ETHERFI",
            reward_token="ETHFI",
            claimed_amount=Decimal("50.0"),
            claimed_value_usd=Decimal("125.00"),
        )
        assert pos.protocol == "ETHERFI"
        assert pos.reward_token == "ETHFI"
        assert pos.claimed_amount > 0
        assert pos.claimed_value_usd > 0

    def test_reward_position_tracks_usd_values(self) -> None:
        """RewardPosition tracks USD values for both accrued and claimed."""
        pos = RewardPosition(
            protocol="EIGENLAYER",
            reward_token="EIGEN",
            accrued_amount=Decimal("200"),
            accrued_value_usd=Decimal("700"),
            claimed_amount=Decimal("50"),
            claimed_value_usd=Decimal("175"),
        )
        assert pos.accrued_value_usd == Decimal("700")
        assert pos.claimed_value_usd == Decimal("175")


# ---------------------------------------------------------------------------
# Monitoring Extensions (StrategyNAV)
# ---------------------------------------------------------------------------


class TestMonitoringExtensions:
    """Verify StrategyNAV has share-class and delta fields."""

    def test_strategy_nav_has_nav_in_share_class(self) -> None:
        nav = StrategyNAV(strategy_id="test", timestamp="2026-04-01T00:00:00Z")
        assert hasattr(nav, "nav_in_share_class")
        assert nav.nav_in_share_class == Decimal("0")

    def test_strategy_nav_has_delta_vs_base(self) -> None:
        nav = StrategyNAV(strategy_id="test", timestamp="2026-04-01T00:00:00Z")
        assert hasattr(nav, "delta_vs_base")
        assert nav.delta_vs_base == Decimal("0")

    def test_strategy_nav_has_delta_vs_base_pct(self) -> None:
        nav = StrategyNAV(strategy_id="test", timestamp="2026-04-01T00:00:00Z")
        assert hasattr(nav, "delta_vs_base_pct")
        assert nav.delta_vs_base_pct == Decimal("0")

    def test_strategy_nav_has_delta_rebalance_needed(self) -> None:
        nav = StrategyNAV(strategy_id="test", timestamp="2026-04-01T00:00:00Z")
        assert hasattr(nav, "delta_rebalance_needed")
        assert nav.delta_rebalance_needed is False

    def test_strategy_nav_has_pnl_fields(self) -> None:
        nav = StrategyNAV(
            strategy_id="test",
            timestamp="2026-04-01T00:00:00Z",
            nav_in_share_class=Decimal("100000"),
            nav_in_usd=Decimal("100000"),
            pnl_share_class=Decimal("5000"),
            pnl_usd=Decimal("5000"),
        )
        assert nav.pnl_share_class == Decimal("5000")
        assert nav.pnl_usd == Decimal("5000")
