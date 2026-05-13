"""Unit tests for UAC HWM ledger contracts.

Tests cover (≥25 total):
 1. CrystallizationCadence: all 4 enum values, StrEnum check
 2. HighWaterMarkLedgerRow: instantiation, frozen, delta semantics, period boundaries
 3. FeeRecognitionType: all 4 enum values, StrEnum check
 4. FeeRecognitionRow: instantiation, frozen, zero-amount, period span
 5. ShareClassPerfFeeConfig: defaults, custom values, frozen
 6. Registry: known share class, unknown raises, all configs valid

Per ``wallet_treasury_client_flow_2026_05_10.md`` Phase 4.C.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from unified_api_contracts.internal.domain.hwm_ledger import (
    CrystallizationCadence,
    FeeRecognitionRow,
    FeeRecognitionType,
    HighWaterMarkLedgerRow,
    ShareClassPerfFeeConfig,
)
from unified_api_contracts.registry.client_share_classes import (
    SHARE_CLASS_PERF_FEE_CONFIGS,
    get_share_class_perf_fee_config,
)

_NOW = datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC)
_PERIOD_START = datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC)
_PERIOD_END = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# 1. CrystallizationCadence enum
# ---------------------------------------------------------------------------


def test_crystallization_cadence_all_values() -> None:
    """All 4 cadence values exist."""
    values = {c.value for c in CrystallizationCadence}
    assert values == {"DAILY", "WEEKLY", "MONTHLY", "QUARTERLY"}


def test_crystallization_cadence_strenum() -> None:
    """CrystallizationCadence is a StrEnum — members compare equal to strings."""
    assert CrystallizationCadence.DAILY == "DAILY"
    assert CrystallizationCadence.WEEKLY == "WEEKLY"
    assert CrystallizationCadence.MONTHLY == "MONTHLY"
    assert CrystallizationCadence.QUARTERLY == "QUARTERLY"


def test_crystallization_cadence_from_string() -> None:
    """Can construct cadence from plain string."""
    assert CrystallizationCadence("DAILY") is CrystallizationCadence.DAILY
    assert CrystallizationCadence("QUARTERLY") is CrystallizationCadence.QUARTERLY


# ---------------------------------------------------------------------------
# 2. HighWaterMarkLedgerRow
# ---------------------------------------------------------------------------


def _hwm_row(
    nav: Decimal = Decimal("1050"),
    prior_peak_nav: Decimal = Decimal("1000"),
    delta: Decimal = Decimal("50"),
    crystallization_due: bool = False,
) -> HighWaterMarkLedgerRow:
    return HighWaterMarkLedgerRow(
        client_id="c1",
        share_class_id="USDC_CUTOVER_V1",
        as_of=_NOW,
        nav=nav,
        prior_peak_nav=prior_peak_nav,
        delta=delta,
        crystallization_due=crystallization_due,
        period_start=_PERIOD_START,
        period_end=_PERIOD_END,
    )


def test_hwm_row_instantiation() -> None:
    row = _hwm_row()
    assert row.client_id == "c1"
    assert row.share_class_id == "USDC_CUTOVER_V1"
    assert row.nav == Decimal("1050")
    assert row.prior_peak_nav == Decimal("1000")
    assert row.delta == Decimal("50")
    assert row.crystallization_due is False


def test_hwm_row_frozen() -> None:
    """HighWaterMarkLedgerRow is frozen — mutation raises FrozenInstanceError."""
    row = _hwm_row()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        row.nav = Decimal("9999")  # type: ignore[misc]


def test_hwm_row_positive_delta_above_hwm() -> None:
    """When nav > prior_peak_nav, delta is positive."""
    row = _hwm_row(nav=Decimal("1100"), prior_peak_nav=Decimal("1000"), delta=Decimal("100"))
    assert row.delta > Decimal("0")
    assert row.delta == Decimal("100")


def test_hwm_row_zero_delta_underwater() -> None:
    """When nav < prior_peak_nav, delta is 0 (no new high)."""
    row = _hwm_row(nav=Decimal("900"), prior_peak_nav=Decimal("1000"), delta=Decimal("0"))
    assert row.delta == Decimal("0")


def test_hwm_row_zero_delta_at_hwm() -> None:
    """When nav == prior_peak_nav exactly, delta is 0."""
    row = _hwm_row(nav=Decimal("1000"), prior_peak_nav=Decimal("1000"), delta=Decimal("0"))
    assert row.delta == Decimal("0")


def test_hwm_row_crystallization_due_true() -> None:
    row = _hwm_row(crystallization_due=True)
    assert row.crystallization_due is True


def test_hwm_row_period_boundaries_stored() -> None:
    row = _hwm_row()
    assert row.period_start == _PERIOD_START
    assert row.period_end == _PERIOD_END


# ---------------------------------------------------------------------------
# 3. FeeRecognitionType enum
# ---------------------------------------------------------------------------


def test_fee_recognition_type_all_values() -> None:
    """All 4 fee recognition type values exist."""
    values = {t.value for t in FeeRecognitionType}
    assert values == {
        "PERFORMANCE_FEE_CRYSTALLIZATION",
        "MANAGEMENT_FEE",
        "FLAT_FEE",
        "PLATFORM_FEE",
    }


def test_fee_recognition_type_strenum() -> None:
    """FeeRecognitionType is a StrEnum."""
    assert FeeRecognitionType.PERFORMANCE_FEE_CRYSTALLIZATION == "PERFORMANCE_FEE_CRYSTALLIZATION"
    assert FeeRecognitionType.MANAGEMENT_FEE == "MANAGEMENT_FEE"
    assert FeeRecognitionType.FLAT_FEE == "FLAT_FEE"
    assert FeeRecognitionType.PLATFORM_FEE == "PLATFORM_FEE"


# ---------------------------------------------------------------------------
# 4. FeeRecognitionRow
# ---------------------------------------------------------------------------


def _fee_row(
    recognition_type: FeeRecognitionType = FeeRecognitionType.PERFORMANCE_FEE_CRYSTALLIZATION,
    amount_usd: Decimal = Decimal("200"),
) -> FeeRecognitionRow:
    return FeeRecognitionRow(
        client_id="c1",
        share_class_id="USDC_CUTOVER_V1",
        period_start=_PERIOD_START,
        period_end=_PERIOD_END,
        recognition_type=recognition_type,
        amount_usd=amount_usd,
        recognized_at=_NOW,
        source_event_id="evt-perf-001",
    )


def test_fee_row_instantiation() -> None:
    row = _fee_row()
    assert row.client_id == "c1"
    assert row.recognition_type == FeeRecognitionType.PERFORMANCE_FEE_CRYSTALLIZATION
    assert row.amount_usd == Decimal("200")
    assert row.source_event_id == "evt-perf-001"


def test_fee_row_frozen() -> None:
    """FeeRecognitionRow is frozen."""
    row = _fee_row()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        row.amount_usd = Decimal("9999")  # type: ignore[misc]


def test_fee_row_zero_amount_underwater() -> None:
    """Underwater case emits FeeRecognitionRow with amount=0."""
    row = _fee_row(amount_usd=Decimal("0"))
    assert row.amount_usd == Decimal("0")


def test_fee_row_period_span() -> None:
    """Period boundaries are stored correctly."""
    row = _fee_row()
    assert row.period_start == _PERIOD_START
    assert row.period_end == _PERIOD_END
    assert row.period_end > row.period_start


def test_fee_row_management_fee_type() -> None:
    row = _fee_row(recognition_type=FeeRecognitionType.MANAGEMENT_FEE, amount_usd=Decimal("50"))
    assert row.recognition_type == FeeRecognitionType.MANAGEMENT_FEE
    assert row.amount_usd == Decimal("50")


def test_fee_row_flat_fee_type() -> None:
    row = _fee_row(recognition_type=FeeRecognitionType.FLAT_FEE, amount_usd=Decimal("5"))
    assert row.recognition_type == FeeRecognitionType.FLAT_FEE


# ---------------------------------------------------------------------------
# 5. ShareClassPerfFeeConfig
# ---------------------------------------------------------------------------


def test_share_class_config_defaults() -> None:
    """Default values for optional fields are zero."""
    cfg = ShareClassPerfFeeConfig(
        share_class_id="TEST",
        crystallization_cadence=CrystallizationCadence.MONTHLY,
        perf_fee_rate=Decimal("0.20"),
    )
    assert cfg.management_fee_rate_annual == Decimal("0")
    assert cfg.flat_fee_per_trade == Decimal("0")


def test_share_class_config_custom_values() -> None:
    cfg = ShareClassPerfFeeConfig(
        share_class_id="CUSTOM",
        crystallization_cadence=CrystallizationCadence.QUARTERLY,
        perf_fee_rate=Decimal("0.25"),
        management_fee_rate_annual=Decimal("0.02"),
        flat_fee_per_trade=Decimal("5"),
    )
    assert cfg.perf_fee_rate == Decimal("0.25")
    assert cfg.management_fee_rate_annual == Decimal("0.02")
    assert cfg.flat_fee_per_trade == Decimal("5")
    assert cfg.crystallization_cadence == CrystallizationCadence.QUARTERLY


def test_share_class_config_frozen() -> None:
    cfg = ShareClassPerfFeeConfig(
        share_class_id="TEST",
        crystallization_cadence=CrystallizationCadence.DAILY,
        perf_fee_rate=Decimal("0.10"),
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        cfg.perf_fee_rate = Decimal("0.99")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6. Registry: get_share_class_perf_fee_config
# ---------------------------------------------------------------------------


def test_registry_known_share_class_usdc() -> None:
    cfg = get_share_class_perf_fee_config("USDC_CUTOVER_V1")
    assert cfg.share_class_id == "USDC_CUTOVER_V1"
    assert cfg.crystallization_cadence == CrystallizationCadence.MONTHLY
    assert cfg.perf_fee_rate == Decimal("0.20")
    assert cfg.management_fee_rate_annual == Decimal("0.02")
    assert cfg.flat_fee_per_trade == Decimal("0")


def test_registry_known_share_class_eth() -> None:
    cfg = get_share_class_perf_fee_config("ETH_FLAGSHIP")
    assert cfg.share_class_id == "ETH_FLAGSHIP"
    assert cfg.crystallization_cadence == CrystallizationCadence.QUARTERLY
    assert cfg.perf_fee_rate == Decimal("0.25")


def test_registry_unknown_raises_key_error() -> None:
    with pytest.raises(KeyError):
        get_share_class_perf_fee_config("UNKNOWN_SHARE_CLASS")


def test_registry_all_configs_valid() -> None:
    """All registry entries have valid field types and non-negative rates."""
    for key, cfg in SHARE_CLASS_PERF_FEE_CONFIGS.items():
        assert cfg.share_class_id == key
        assert isinstance(cfg.crystallization_cadence, CrystallizationCadence)
        assert cfg.perf_fee_rate >= Decimal("0")
        assert cfg.management_fee_rate_annual >= Decimal("0")
        assert cfg.flat_fee_per_trade >= Decimal("0")
