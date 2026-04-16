"""Execution cost estimation schemas.

Provides a unified cost model for estimating total execution cost of a
strategy instruction across all venue types (CeFi, DeFi, sports).

Used by:
- execution-service to produce cost estimates for given instruments/venues
- strategy-service to filter signals where cost exceeds expected alpha
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ExecutionCostEstimate:
    """Estimated total cost of executing a strategy instruction.

    All bps fields are in basis points (1 bps = 0.01%).
    All USD fields are in absolute dollar terms.
    """

    venue: str
    instrument_id: str

    # --- Cost components (bps of notional) ---
    exchange_fee_bps: Decimal
    """Maker/taker fee in basis points."""

    spread_cost_bps: Decimal
    """Estimated bid-ask spread cost in basis points."""

    slippage_estimate_bps: Decimal
    """Estimated market impact / slippage in basis points."""

    funding_rate_cost_bps: Decimal
    """Funding rate drag for perpetual positions (0 for spot)."""

    # --- Fixed costs (USD) ---
    gas_cost_usd: Decimal
    """On-chain gas cost; 0 for CeFi."""

    bridge_cost_usd: Decimal
    """Cross-chain bridge cost; 0 if same chain or CeFi."""

    # --- Totals ---
    total_cost_bps: Decimal
    """Sum of all bps components."""

    total_fixed_cost_usd: Decimal
    """Sum of all USD fixed costs (gas + bridge)."""

    # --- Metadata ---
    confidence: float
    """0.0-1.0, how confident the estimate is (1.0 = from live data)."""

    timestamp: datetime
    """When this estimate was produced."""

    chain: str = ""
    """Chain name for DeFi venues (empty for CeFi)."""

    notes: list[str] = field(default_factory=list)
    """Human-readable notes about the estimate."""

    def total_cost_bps_with_fixed(self, notional_usd: Decimal) -> Decimal:
        """Convert fixed USD costs to bps and add to total_cost_bps.

        Args:
            notional_usd: Trade notional value in USD.

        Returns:
            Total cost in bps including fixed costs converted to bps.
        """
        if notional_usd <= 0:
            return self.total_cost_bps
        fixed_as_bps = self.total_fixed_cost_usd / notional_usd * Decimal("10000")
        return self.total_cost_bps + fixed_as_bps


__all__ = ["ExecutionCostEstimate"]
