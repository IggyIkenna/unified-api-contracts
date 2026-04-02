"""Tests for Decimal price fields in features.py (Stream A4)."""

from __future__ import annotations

from decimal import Decimal
from typing import get_type_hints

import pytest

from unified_api_contracts.internal.features import (
    CrossInstrumentFeatures,
    FuturesTermStructureRecord,
)


class TestFuturesTermStructureDecimalFields:
    """Verify that price-derived fields in FuturesTermStructureRecord are Decimal."""

    def test_basis_field_type_annotation_is_decimal(self) -> None:
        """basis field must have Decimal | None annotation."""
        hints = get_type_hints(FuturesTermStructureRecord)
        # Union[Decimal, None] — check Decimal is involved
        basis_hint = hints.get("basis")
        assert basis_hint is not None, "basis field must exist"
        # Decimal | None → __args__ contains Decimal
        args = getattr(basis_hint, "__args__", (basis_hint,))
        assert Decimal in args, f"basis must be Decimal | None, got {basis_hint}"

    def test_basis_pct_field_type_annotation_is_decimal(self) -> None:
        """basis_pct field must have Decimal | None annotation."""
        hints = get_type_hints(FuturesTermStructureRecord)
        basis_pct_hint = hints.get("basis_pct")
        assert basis_pct_hint is not None
        args = getattr(basis_pct_hint, "__args__", (basis_pct_hint,))
        assert Decimal in args, f"basis_pct must be Decimal | None, got {basis_pct_hint}"

    def test_annualized_basis_field_type_annotation_is_decimal(self) -> None:
        """annualized_basis field must have Decimal | None annotation."""
        hints = get_type_hints(FuturesTermStructureRecord)
        ann_hint = hints.get("annualized_basis")
        assert ann_hint is not None
        args = getattr(ann_hint, "__args__", (ann_hint,))
        assert Decimal in args, f"annualized_basis must be Decimal | None, got {ann_hint}"

    def test_futures_basis_decimal_precision(self) -> None:
        """Compute basis from two large Decimal prices — no float precision loss."""
        from datetime import UTC, datetime

        spot = Decimal("50000.123456789012345678")
        front = Decimal("49950.987654321098765432")
        expected_basis = spot - front  # pure Decimal arithmetic

        record = FuturesTermStructureRecord(
            timestamp=datetime.now(UTC),
            timestamp_out=datetime.now(UTC),
            venue="TEST",
            underlying_symbol="BTC",
            spot_price=spot,
            front_month_price=front,
            basis=expected_basis,
        )

        # basis stored as Decimal — must match exactly, not via float approximation
        assert record.basis == expected_basis
        assert isinstance(record.basis, Decimal)

    def test_dimensionless_fields_remain_float(self) -> None:
        """Dimensionless statistical fields (curve_slope, roll_yield) stay float."""
        hints = get_type_hints(FuturesTermStructureRecord)
        # curve_slope is a dimensionless term-structure metric — must remain float
        curve_slope_hint = hints.get("curve_slope")
        assert curve_slope_hint is not None
        args = getattr(curve_slope_hint, "__args__", (curve_slope_hint,))
        assert float in args, f"curve_slope should remain float | None, got {curve_slope_hint}"


class TestCrossInstrumentFeaturesDecimalFields:
    """Verify that price-derived fields in CrossInstrumentFeatures are Decimal."""

    @pytest.mark.parametrize(
        "field_name",
        [
            "price_ratio",
            "price_ratio_ma_20",
            "price_ratio_std_20",
            "basis",
            "basis_pct",
            "annualized_carry",
        ],
    )
    def test_price_derived_field_is_decimal(self, field_name: str) -> None:
        """Price-derived ratio/differential fields must be Decimal | None."""
        hints = get_type_hints(CrossInstrumentFeatures)
        hint = hints.get(field_name)
        assert hint is not None, f"Field {field_name} must exist in CrossInstrumentFeatures"
        args = getattr(hint, "__args__", (hint,))
        assert Decimal in args, f"{field_name} must be Decimal | None, got {hint}"

    def test_dimensionless_fields_remain_float(self) -> None:
        """Correlation and z-score fields are dimensionless — must remain float."""
        hints = get_type_hints(CrossInstrumentFeatures)
        for field_name in ("correlation_1h", "spread_z_score", "cointegration_score"):
            hint = hints.get(field_name)
            if hint is None:
                continue
            args = getattr(hint, "__args__", (hint,))
            assert float in args, f"{field_name} should remain float | None, got {hint}"
