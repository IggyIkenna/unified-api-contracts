"""TradFi OHLCV-only MVP contract pins (2026-05-15 operator direction).

These tests pin the empty-windows contract introduced by
`plans/active/tradfi_ohlcv_only_mvp_backfill_2026_05_15.md` Phase 1+2:

1. `TRADFI_TICK_DATA_WINDOWS == []` — empty list means OHLCV-only mode.
2. `is_in_tradfi_tick_window(...)` returns False for ALL dates when the
   windows list is empty (the orchestrator-side gate suppresses every
   trades / tbbo fetch attempt).
3. `_DEFERRED_TRADFI_TICK_DATA_WINDOWS` preserves the prior windows
   (May 2023 + Jul 2024) so the post-cutover successor plan can restore
   them without re-deriving from operator history.
4. `VENUE_DATA_TYPE_COVERAGE_WINDOWS == {}` — empty dict means no
   per-(venue, data_type) coverage clipping in MVP scope.
5. `_DEFERRED_VENUE_DATA_TYPE_COVERAGE_WINDOWS` preserves the CME tbbo
   + mbp_10 windows for the post-cutover restoration.
6. TradFi venues in `VENUE_DATA_TYPE_CAPABILITIES` advertise ONLY
   ohlcv_1m (no trades, no tbbo) — the live SSOT MUST not regress.

Plan: tradfi_ohlcv_only_mvp_backfill_2026_05_15.md Phase 4.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry import (
    TRADFI_TICK_DATA_WINDOWS,
    VENUE_DATA_TYPE_CAPABILITIES,
    is_in_tradfi_tick_window,
)
from unified_api_contracts.registry.market_data_categories import (
    _DEFERRED_TRADFI_TICK_DATA_WINDOWS,
    _DEFERRED_VENUE_DATA_TYPE_COVERAGE_WINDOWS,
    VENUE_DATA_TYPE_COVERAGE_WINDOWS,
)


@pytest.mark.unit
def test_tradfi_tick_data_windows_is_empty() -> None:
    """OHLCV-only MVP: live TRADFI_TICK_DATA_WINDOWS must be empty."""
    assert TRADFI_TICK_DATA_WINDOWS == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "date_str",
    [
        "2019-01-01",  # earliest TradFi date in operator scope
        "2023-05-15",  # mid prior training window
        "2024-07-15",  # mid prior validation window
        "2026-05-17",  # today
        "2099-12-31",  # far future
    ],
)
def test_is_in_tradfi_tick_window_returns_false_on_empty_windows(date_str: str) -> None:
    """Empty TRADFI_TICK_DATA_WINDOWS => any([]) => False for ALL dates.

    This is the orchestrator-side suppression contract: when the gate
    returns False, MTDS skips every trades / tbbo fetch attempt for the
    given date. With the windows empty, every TradFi date is suppressed.
    """
    assert is_in_tradfi_tick_window(date_str) is False


@pytest.mark.unit
def test_deferred_tradfi_tick_data_windows_preserves_prior_windows() -> None:
    """The two operator-acked prior windows (May 2023 + Jul 2024) MUST be preserved.

    The post-cutover successor plan restores these into TRADFI_TICK_DATA_WINDOWS;
    if this constant gets accidentally cleared the restoration would silently lose
    the operator's prior choice of training/validation months.
    """
    assert _DEFERRED_TRADFI_TICK_DATA_WINDOWS == [
        {"start": "2023-05-01", "end": "2023-05-31"},
        {"start": "2024-07-01", "end": "2024-07-31"},
    ]


@pytest.mark.unit
def test_venue_data_type_coverage_windows_is_empty() -> None:
    """OHLCV-only MVP: no per-(venue, data_type) coverage clipping."""
    assert VENUE_DATA_TYPE_COVERAGE_WINDOWS == {}


@pytest.mark.unit
def test_deferred_coverage_windows_preserves_cme_tbbo_mbp10() -> None:
    """Deferred coverage windows MUST still contain CME tbbo + mbp_10 for the post-cutover restore."""
    assert ("CME", "tbbo") in _DEFERRED_VENUE_DATA_TYPE_COVERAGE_WINDOWS
    assert ("CME", "mbp_10") in _DEFERRED_VENUE_DATA_TYPE_COVERAGE_WINDOWS
    # Two reference windows per data_type
    assert len(_DEFERRED_VENUE_DATA_TYPE_COVERAGE_WINDOWS[("CME", "tbbo")]) == 2
    assert len(_DEFERRED_VENUE_DATA_TYPE_COVERAGE_WINDOWS[("CME", "mbp_10")]) == 2


@pytest.mark.unit
# ICE removed from this Databento-OHLCV-only-MVP parametrize (2026-07-13,
# tradfi_ice_ohlcv_1m_no_working_fetch_path_2026_07_13.md, operator decision):
# ICE's Databento datasets were dropped from the 3-dataset subscription lockdown
# (2026-06-18) and it never had a working ohlcv_1m fetch path at all — it now
# advertises Yahoo-sourced ohlcv_24h only (the real DXY-index daily series),
# not the Databento ohlcv_1m grain this test pins for CME/NASDAQ/NYSE.
@pytest.mark.parametrize("venue", ["CME", "NASDAQ", "NYSE"])
def test_live_tradfi_venues_advertise_ohlcv_only(venue: str) -> None:
    """Live VENUE_DATA_TYPE_CAPABILITIES MUST NOT regress: TradFi venues advertise ONLY ohlcv_1m.

    A regression that re-adds `trades` or `tbbo` would force MTDS to attempt
    L1-L3 captures, racking up Databento PAYG cost — the OHLCV-only operator
    direction (2026-05-15) explicitly excludes these until post-cutover.
    """
    caps = VENUE_DATA_TYPE_CAPABILITIES[venue]
    assert "ohlcv_1m" in caps
    assert "trades" not in caps, f"{venue}: trades MUST NOT be in live capabilities (OHLCV-only MVP)"
    assert "tbbo" not in caps, f"{venue}: tbbo MUST NOT be in live capabilities (OHLCV-only MVP)"


@pytest.mark.unit
def test_ice_advertises_ohlcv_24h_only_not_ohlcv_1m() -> None:
    """ICE narrowed off the Databento ohlcv_1m grain entirely (2026-07-13) —
    it now advertises the real Yahoo-sourced ohlcv_24h DXY-index series only.
    See tradfi_ice_ohlcv_1m_no_working_fetch_path_2026_07_13.md."""
    caps = VENUE_DATA_TYPE_CAPABILITIES["ICE"]
    assert "ohlcv_24h" in caps
    assert "ohlcv_1m" not in caps
    assert "trades" not in caps
    assert "tbbo" not in caps
