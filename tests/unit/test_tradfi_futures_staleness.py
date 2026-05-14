"""Unit tests for is_tradfi_futures_instrument_active (Phase 4.3 staleness gate).

Tests the UAC pure-function per-contract expiry gate that filters expired
futures contracts from the MTDS Tier-3 honest-coverage sentinel denominator.

Plan: tradfi_canonical_futures_contract_hard_required_fields_2026_05_13.md
Phase 4.3 — mtds-tradfi-staleness per-contract gate.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry import is_tradfi_futures_instrument_active


class TestIsTradfiFuturesInstrumentActive:
    """Tests for is_tradfi_futures_instrument_active()."""

    # -----------------------------------------------------------------------
    # Active contracts — as_of_date is before or within the contract month
    # -----------------------------------------------------------------------

    @pytest.mark.unit
    def test_active_front_month_same_month(self) -> None:
        """ESH26 on 2026-03-01 (same month as contract month H=March) → active."""
        assert is_tradfi_futures_instrument_active("ESH26", "2026-03-01") is True

    @pytest.mark.unit
    def test_active_front_month_last_day(self) -> None:
        """ESH26 on 2026-03-31 (last day of contract month) → active (conservative)."""
        assert is_tradfi_futures_instrument_active("ESH26", "2026-03-31") is True

    @pytest.mark.unit
    def test_active_before_contract_month(self) -> None:
        """ESH26 on 2026-02-01 (before March 2026) → active (far from expiry)."""
        assert is_tradfi_futures_instrument_active("ESH26", "2026-02-01") is True

    @pytest.mark.unit
    def test_active_far_future_contract(self) -> None:
        """ESZ26 on 2026-03-01 (December 2026 contract, months away) → active."""
        assert is_tradfi_futures_instrument_active("ESZ26", "2026-03-01") is True

    @pytest.mark.unit
    def test_active_cl_energy_futures(self) -> None:
        """CLM26 (WTI Crude June 2026) on 2026-05-01 → active."""
        assert is_tradfi_futures_instrument_active("CLM26", "2026-05-01") is True

    @pytest.mark.unit
    def test_active_single_digit_year(self) -> None:
        """CLZ6 (December 2006 format — but 1-digit year still parses) → active in past year."""
        # 1-digit year: 6 → 2006. On 2006-11-01, December 2006 is active.
        assert is_tradfi_futures_instrument_active("CLZ6", "2006-11-01") is True

    # -----------------------------------------------------------------------
    # Expired contracts — as_of_date is past the last day of contract month
    # -----------------------------------------------------------------------

    @pytest.mark.unit
    def test_expired_one_month_past(self) -> None:
        """ESH26 (March 2026) on 2026-04-01 → expired (past last day of March)."""
        assert is_tradfi_futures_instrument_active("ESH26", "2026-04-01") is False

    @pytest.mark.unit
    def test_expired_many_months_past(self) -> None:
        """ESH26 (March 2026) on 2027-01-01 → expired."""
        assert is_tradfi_futures_instrument_active("ESH26", "2027-01-01") is False

    @pytest.mark.unit
    def test_expired_december_rollover(self) -> None:
        """ESZ25 (December 2025) on 2026-01-01 → expired (year rollover)."""
        assert is_tradfi_futures_instrument_active("ESZ25", "2026-01-01") is False

    @pytest.mark.unit
    def test_expired_cl_futures(self) -> None:
        """CLH25 (WTI March 2025) on 2025-05-14 → expired."""
        assert is_tradfi_futures_instrument_active("CLH25", "2025-05-14") is False

    @pytest.mark.unit
    def test_expired_gc_gold_futures(self) -> None:
        """GCQ25 (Gold August 2025 — Q = August) on 2025-09-01 → expired."""
        assert is_tradfi_futures_instrument_active("GCQ25", "2025-09-01") is False

    # -----------------------------------------------------------------------
    # Edge cases — same day as last day of contract month
    # -----------------------------------------------------------------------

    @pytest.mark.unit
    def test_boundary_last_day_of_month_active(self) -> None:
        """ESM26 (June 2026) on 2026-06-30 (last day) → active (inclusive boundary)."""
        assert is_tradfi_futures_instrument_active("ESM26", "2026-06-30") is True

    @pytest.mark.unit
    def test_boundary_day_after_last_day_expired(self) -> None:
        """ESM26 (June 2026) on 2026-07-01 (day after last day) → expired."""
        assert is_tradfi_futures_instrument_active("ESM26", "2026-07-01") is False

    @pytest.mark.unit
    def test_boundary_february_last_day(self) -> None:
        """ESG26 (February 2026) on 2026-02-28 → active (last day of Feb non-leap)."""
        assert is_tradfi_futures_instrument_active("ESG26", "2026-02-28") is True

    @pytest.mark.unit
    def test_boundary_february_march_1(self) -> None:
        """ESG26 (February 2026) on 2026-03-01 → expired (day after Feb 28)."""
        assert is_tradfi_futures_instrument_active("ESG26", "2026-03-01") is False

    # -----------------------------------------------------------------------
    # Symbol format variants (fail-open for unknown)
    # -----------------------------------------------------------------------

    @pytest.mark.unit
    def test_dot_separator_brn(self) -> None:
        """BRN.H26 (Brent Crude March 2026) on 2026-01-01 → active."""
        assert is_tradfi_futures_instrument_active("BRN.H26", "2026-01-01") is True

    @pytest.mark.unit
    def test_dot_separator_cl_f27(self) -> None:
        """CL.F27 (WTI January 2027) on 2026-12-01 → active."""
        assert is_tradfi_futures_instrument_active("CL.F27", "2026-12-01") is True

    @pytest.mark.unit
    def test_numeric_prefix_6e_fx(self) -> None:
        """6EZ26 (Euro FX December 2026) on 2026-10-01 → active."""
        assert is_tradfi_futures_instrument_active("6EZ26", "2026-10-01") is True

    @pytest.mark.unit
    def test_unparseable_symbol_fail_open(self) -> None:
        """Unknown/unparseable symbol → fail-open (returns True, don't suppress)."""
        assert is_tradfi_futures_instrument_active("NOT-A-FUTURE", "2026-05-01") is True

    @pytest.mark.unit
    def test_empty_string_fail_open(self) -> None:
        """Empty string → fail-open."""
        assert is_tradfi_futures_instrument_active("", "2026-05-01") is True

    @pytest.mark.unit
    def test_options_symbol_fail_open(self) -> None:
        """Options symbol (BTC-28JUN24-70000-C) → fail-open (not a futures format)."""
        assert is_tradfi_futures_instrument_active("BTC-28JUN24-70000-C", "2026-05-01") is True

    @pytest.mark.unit
    def test_spot_symbol_fail_open(self) -> None:
        """BTCUSD spot pair → fail-open."""
        assert is_tradfi_futures_instrument_active("BTCUSD", "2026-05-01") is True

    @pytest.mark.unit
    def test_invalid_date_fail_open(self) -> None:
        """Invalid date string → fail-open."""
        assert is_tradfi_futures_instrument_active("ESH26", "not-a-date") is True

    # -----------------------------------------------------------------------
    # December year-boundary correctness
    # -----------------------------------------------------------------------

    @pytest.mark.unit
    def test_december_active_on_dec_1(self) -> None:
        """ESZ26 (December 2026) on 2026-12-01 → active."""
        assert is_tradfi_futures_instrument_active("ESZ26", "2026-12-01") is True

    @pytest.mark.unit
    def test_december_active_on_dec_31(self) -> None:
        """ESZ26 (December 2026) on 2026-12-31 → active (last day of December)."""
        assert is_tradfi_futures_instrument_active("ESZ26", "2026-12-31") is True

    @pytest.mark.unit
    def test_december_expired_on_jan_1_next_year(self) -> None:
        """ESZ26 (December 2026) on 2027-01-01 → expired."""
        assert is_tradfi_futures_instrument_active("ESZ26", "2027-01-01") is False

    # -----------------------------------------------------------------------
    # 2-digit year expansion correctness
    # -----------------------------------------------------------------------

    @pytest.mark.unit
    def test_2digit_year_2049_boundary(self) -> None:
        """NQZ49 → year 2049. On 2049-12-01 → active."""
        assert is_tradfi_futures_instrument_active("NQZ49", "2049-12-01") is True

    @pytest.mark.unit
    def test_2digit_year_50_maps_to_1950(self) -> None:
        """Contract with year=50 → 1950. On any date in 2026 → expired (far past)."""
        # ESH50 would be 1950 under the <50 = 2000, >=50 = 1900 rule.
        # 2026 is past 1950-03-31, so this should return expired.
        assert is_tradfi_futures_instrument_active("ESH50", "2026-05-14") is False
