"""Specialized per-domain instruction builders.

Split out of :mod:`unified_api_contracts.internal.domain.strategy_service.instruction`
(2026-06-11 >900-line ratchet). Each dataclass wraps a
:class:`~unified_api_contracts.internal.domain.strategy_service._instruction_base.StrategyInstruction`
with domain-specific context (transfer / prediction bet / sports bet /
sports exchange order / futures roll / options combo).

Import surface is UNCHANGED for consumers: every name here is re-exported by
``instruction`` (and the strategy_service / internal facades) — import from there.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, cast

from unified_api_contracts.canonical.domain.derivatives.futures import (
    FuturesContractLifecyclePhase,
)
from unified_api_contracts.internal.domain.execution_service.types import (
    OperationType,
    OrderType,
)
from unified_api_contracts.internal.domain.strategy_service._instruction_base import (
    MetadataMap,
    StrategyInstruction,
    metadata_or_empty,
)

# ---------------------------------------------------------------------------
# Specialized instruction builders for each domain
# ---------------------------------------------------------------------------


@dataclass
class TransferInstruction:
    """Execution instruction for cross-venue asset transfers (CEX <-> DeFi wallet).

    Covers three scenarios:
    - CEX -> DeFi wallet: Fund a DeFi strategy from exchange holdings
    - DeFi wallet -> CEX: Return funds after closing a DeFi position
    - Sweep: Consolidate small balances from multiple wallets to main wallet
    - ETH reserve top-up: Ensure DeFi wallets maintain minimum ETH for gas
    """

    instruction: StrategyInstruction
    transfer_reason: str  # "FUND_DEFI" | "RETURN_TO_CEX" | "SWEEP" | "ETH_RESERVE"

    @staticmethod
    def create(
        *,
        strategy_id: str,
        timestamp: datetime,
        from_venue: str,
        to_venue: str,
        token: str,
        quantity: Decimal,
        transfer_reason: str,
        metadata: MetadataMap | None = None,
    ) -> "TransferInstruction":
        """Create a TRANSFER instruction for moving assets between venues.

        Args:
            strategy_id: Owning strategy identifier.
            timestamp: Signal generation timestamp.
            from_venue: Source venue (e.g. "BINANCE-SPOT" or "AAVE-ETHEREUM").
            to_venue: Destination venue.
            token: Asset to transfer (e.g. "USDC", "ETH").
            quantity: Amount to transfer.
            transfer_reason: Why the transfer is needed.
            metadata: Additional key-value metadata.

        Returns:
            TransferInstruction wrapping a StrategyInstruction with TRANSFER operation.
        """
        combined_metadata: MetadataMap = {
            "transfer_reason": transfer_reason,
            **metadata_or_empty(metadata),
        }
        instr = StrategyInstruction(
            instruction_id="",
            strategy_id=strategy_id,
            timestamp=timestamp,
            operation=OperationType.TRANSFER,
            instrument_id=f"{from_venue}:TRANSFER:{token}",
            from_venue=from_venue,
            to_venue=to_venue,
            token_in=token,
            amount=quantity,
            metadata=combined_metadata,
        )
        return TransferInstruction(
            instruction=instr,
            transfer_reason=transfer_reason,
        )


@dataclass
class PredictionBetInstruction:
    """Execution instruction for a prediction market bet (e.g. Polymarket, Kalshi)."""

    instruction: StrategyInstruction
    market_id: str
    outcome_side: str  # "YES" or "NO"
    implied_probability: Decimal
    max_cost_usd: Decimal

    @staticmethod
    def create(
        *,
        strategy_id: str,
        timestamp: datetime,
        venue: str,
        instrument_id: str,
        market_id: str,
        outcome_side: str,
        implied_probability: Decimal,
        amount: Decimal,
        max_cost_usd: Decimal,
        limit_price: Decimal | None = None,
        metadata: MetadataMap | None = None,
    ) -> "PredictionBetInstruction":
        instr = StrategyInstruction(
            instruction_id="",
            strategy_id=strategy_id,
            timestamp=timestamp,
            operation=OperationType.PREDICTION_BET,
            instrument_id=instrument_id,
            from_venue=venue,
            to_venue=venue,
            token_in="USDC",
            amount=amount,
            limit_price=limit_price,
            order_type=OrderType.LIMIT if limit_price else OrderType.MARKET,
            metadata=metadata_or_empty(metadata),
        )
        return PredictionBetInstruction(
            instruction=instr,
            market_id=market_id,
            outcome_side=outcome_side,
            implied_probability=implied_probability,
            max_cost_usd=max_cost_usd,
        )


@dataclass
class SportsBetInstruction:
    """Execution instruction for a fixed-odds sports bet (bookmaker API or web)."""

    instruction: StrategyInstruction
    event_id: str
    outcome: str
    bookmaker: str
    decimal_odds: Decimal
    stake_fraction: Decimal

    @staticmethod
    def create(
        *,
        strategy_id: str,
        timestamp: datetime,
        venue: str,
        instrument_id: str,
        event_id: str,
        outcome: str,
        bookmaker: str,
        decimal_odds: Decimal,
        amount: Decimal,
        stake_fraction: Decimal,
        metadata: MetadataMap | None = None,
    ) -> "SportsBetInstruction":
        instr = StrategyInstruction(
            instruction_id="",
            strategy_id=strategy_id,
            timestamp=timestamp,
            operation=OperationType.SPORTS_BET,
            instrument_id=instrument_id,
            from_venue="BANKROLL",
            to_venue=venue,
            token_in="GBP",
            amount=amount,
            metadata=metadata_or_empty(metadata),
        )
        return SportsBetInstruction(
            instruction=instr,
            event_id=event_id,
            outcome=outcome,
            bookmaker=bookmaker,
            decimal_odds=decimal_odds,
            stake_fraction=stake_fraction,
        )


@dataclass
class SportsExchangeOrderInstruction:
    """Execution instruction for a sports exchange order (Betfair, Smarkets, etc.)."""

    instruction: StrategyInstruction
    market_id: str
    selection_id: str
    side: str  # "BACK" or "LAY"
    decimal_odds: Decimal
    persistence_type: str = "LAPSE"

    @staticmethod
    def create(
        *,
        strategy_id: str,
        timestamp: datetime,
        venue: str,
        instrument_id: str,
        market_id: str,
        selection_id: str,
        side: str,
        decimal_odds: Decimal,
        amount: Decimal,
        persistence_type: str = "LAPSE",
        metadata: MetadataMap | None = None,
    ) -> "SportsExchangeOrderInstruction":
        instr = StrategyInstruction(
            instruction_id="",
            strategy_id=strategy_id,
            timestamp=timestamp,
            operation=OperationType.SPORTS_EXCHANGE_ORDER,
            instrument_id=instrument_id,
            from_venue=venue,
            to_venue=venue,
            token_in="GBP",
            amount=amount,
            limit_price=decimal_odds,
            order_type=OrderType.LIMIT,
            metadata=metadata_or_empty(metadata),
        )
        return SportsExchangeOrderInstruction(
            instruction=instr,
            market_id=market_id,
            selection_id=selection_id,
            side=side,
            decimal_odds=decimal_odds,
            persistence_type=persistence_type,
        )


@dataclass
class FuturesRollInstruction:
    """Execution instruction for rolling a futures position from near to far contract."""

    instruction: StrategyInstruction
    near_contract_id: str
    far_contract_id: str
    roll_spread: Decimal | None = None
    lifecycle_phase: FuturesContractLifecyclePhase | None = None

    @staticmethod
    def create(
        *,
        strategy_id: str,
        timestamp: datetime,
        venue: str,
        near_contract_id: str,
        far_contract_id: str,
        amount: Decimal,
        direction: "Literal['LONG', 'SHORT', 'FLAT']",
        roll_spread: Decimal | None = None,
        lifecycle_phase: FuturesContractLifecyclePhase | None = None,
        metadata: MetadataMap | None = None,
    ) -> "FuturesRollInstruction":
        instr = StrategyInstruction(
            instruction_id="",
            strategy_id=strategy_id,
            timestamp=timestamp,
            operation=OperationType.FUTURES_ROLL,
            instrument_id=near_contract_id,
            from_venue=venue,
            to_venue=venue,
            token_in="USD",
            amount=amount,
            direction=direction,
            metadata=metadata_or_empty(metadata),
        )
        return FuturesRollInstruction(
            instruction=instr,
            near_contract_id=near_contract_id,
            far_contract_id=far_contract_id,
            roll_spread=roll_spread,
            lifecycle_phase=lifecycle_phase,
        )


@dataclass
class OptionsComboInstruction:
    """Execution instruction for a multi-leg options combination."""

    legs: list[StrategyInstruction]
    combo_type: str
    net_premium: Decimal | None = None
    strategy_id: str = ""
    timestamp: datetime | None = None

    @staticmethod
    def create(
        *,
        strategy_id: str,
        timestamp: datetime,
        venue: str,
        legs: list[dict[str, object]],
        combo_type: str,
        net_premium: Decimal | None = None,
        metadata: MetadataMap | None = None,
    ) -> "OptionsComboInstruction":
        built_legs: list[StrategyInstruction] = []
        for leg in legs:
            instrument_id_val = leg.get("instrument_id")
            if not isinstance(instrument_id_val, str) or not instrument_id_val:
                raise ValueError("Each options combo leg requires a non-empty instrument_id")
            amount_val = leg.get("amount")
            if amount_val is None:
                raise ValueError(f"Missing amount for options combo leg {instrument_id_val}")
            instr = StrategyInstruction(
                instruction_id="",
                strategy_id=strategy_id,
                timestamp=timestamp,
                operation=OperationType.OPTIONS_COMBO,
                instrument_id=instrument_id_val,
                from_venue=venue,
                to_venue=venue,
                token_in="USD",
                amount=Decimal(str(amount_val)),
                direction=cast("Literal['LONG', 'SHORT', 'FLAT'] | None", leg.get("direction")),
                limit_price=Decimal(str(leg["limit_price"])) if leg.get("limit_price") else None,
                order_type=OrderType.LIMIT,
                metadata=metadata_or_empty(metadata),
            )
            built_legs.append(instr)
        return OptionsComboInstruction(
            legs=built_legs,
            combo_type=combo_type,
            net_premium=net_premium,
            strategy_id=strategy_id,
            timestamp=timestamp,
        )
