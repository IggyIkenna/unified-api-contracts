"""High-water mark (HWM) ledger contracts + fee recognition types.

SSOT for:
  - CrystallizationCadence: per-share-class crystallization period enum.
  - HighWaterMarkLedgerRow: per-(client, share_class) HWM snapshot per trade.
  - FeeRecognitionType: closed-set fee recognition reason enum.
  - FeeRecognitionRow: single fee recognition event (management, performance, flat, platform).
  - ShareClassPerfFeeConfig: per-share-class HWM + perf-fee configuration.

Per ``wallet_treasury_client_flow_2026_05_10.md`` Phase 4.C.

FeeRecognitionRow is the cross-plan SSOT for fee recognition events, decoupled from
PnLAttributionRow's factor x layer axis. See banner in wallet_treasury plan top-of-file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class CrystallizationCadence(StrEnum):
    """Per-share-class HWM crystallization period.

    DAILY: crystallize every UTC midnight.
    WEEKLY: crystallize every Monday UTC 00:00.
    MONTHLY: crystallize first day of month UTC 00:00.
    QUARTERLY: crystallize first day of Q1/Q2/Q3/Q4 UTC 00:00.
    """

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


@dataclass(frozen=True)
class HighWaterMarkLedgerRow:
    """Per-(client, share_class) HWM snapshot at a point in time.

    Emitted on every trade-settled event; HWM advances when nav > prior_peak_nav.
    crystallization_due fires when wall-clock crosses period boundary.

    Fields:
        client_id: Client identifier.
        share_class_id: Share class identifier.
        as_of: Timestamp of this HWM snapshot (UTC).
        nav: Current net asset value (USD).
        prior_peak_nav: Highest NAV ever reached — the HWM.
        delta: max(0, nav - prior_peak_nav). Positive means new all-time high.
        crystallization_due: True if period boundary crossed since last crystallization.
        period_start: Start of current crystallization period (UTC).
        period_end: End of current crystallization period (UTC, exclusive).
    """

    client_id: str
    share_class_id: str
    as_of: datetime
    nav: Decimal
    prior_peak_nav: Decimal
    delta: Decimal
    crystallization_due: bool
    period_start: datetime
    period_end: datetime


class FeeRecognitionType(StrEnum):
    """Closed-set fee recognition reasons.

    PERFORMANCE_FEE_CRYSTALLIZATION: HWM crystallization triggers perf fee.
    MANAGEMENT_FEE: AUM-based annual management fee (daily accrual).
    FLAT_FEE: Per-trade flat fee charge.
    PLATFORM_FEE: Platform/infrastructure fee.
    """

    PERFORMANCE_FEE_CRYSTALLIZATION = "PERFORMANCE_FEE_CRYSTALLIZATION"
    MANAGEMENT_FEE = "MANAGEMENT_FEE"
    FLAT_FEE = "FLAT_FEE"
    PLATFORM_FEE = "PLATFORM_FEE"


@dataclass(frozen=True)
class FeeRecognitionRow:
    """SSOT for fee recognition events.

    Replaces direct PnLAttributionRow factor encoding for fee events.
    HWM crystallization (Phase 5.G PerformanceFeeCrystallizedEvent) emits one of these
    per (client, share_class, period). Zero-fee underwater case still emits with amount=0.

    Stored at:
      gs://{pid}-client-statements/{client_id}/fee_recognition/{YYYY-MM-DD}/*.parquet

    Per cross-plan banner: decoupled from PnLAttributionRow's factor x layer axis.
    Fee recognition does NOT participate in attribution decomposition.

    Fields:
        client_id: Client identifier.
        share_class_id: Share class identifier.
        period_start: Start of the fee period (UTC).
        period_end: End of the fee period (UTC, exclusive).
        recognition_type: Fee type — closed set from FeeRecognitionType.
        amount_usd: Fee amount in USD. Always >= 0. Zero = fee computed but underwater.
        recognized_at: Wall-clock time of fee recognition (UTC).
        source_event_id: UUID of triggering event (e.g., PerformanceFeeCrystallizedEvent).
    """

    client_id: str
    share_class_id: str
    period_start: datetime
    period_end: datetime
    recognition_type: FeeRecognitionType
    amount_usd: Decimal
    recognized_at: datetime
    source_event_id: str


@dataclass(frozen=True)
class ShareClassPerfFeeConfig:
    """Per-share-class HWM + perf-fee configuration.

    Lives in registry/client_share_classes.py (get_share_class_perf_fee_config).

    Fields:
        share_class_id: Share class identifier (must match registry key).
        crystallization_cadence: How often HWM crystallizes.
        perf_fee_rate: Performance fee rate over HWM. e.g., 0.20 = 20%.
        management_fee_rate_annual: Annual management fee rate. e.g., 0.02 = 2%/yr.
            0 = no management fee.
        flat_fee_per_trade: USD per trade flat fee. 0 = no flat fee.
    """

    share_class_id: str
    crystallization_cadence: CrystallizationCadence
    perf_fee_rate: Decimal
    management_fee_rate_annual: Decimal = field(default=Decimal("0"))
    flat_fee_per_trade: Decimal = field(default=Decimal("0"))
