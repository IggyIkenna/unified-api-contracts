"""Tests for ``normalize_tardis_derivative_ticker`` funding_timestamp semantics.

Regression coverage for
plans/active/issues/perp_funding_data_semantics_and_cadence_2026_06_16.md
Finding 2: Tardis's raw wire field literally named ``funding_timestamp`` is
forward-looking (the venue's NEXT settlement instant), not the charge instant.
Previously this normalizer never populated the canonical ``funding_timestamp``
field at all (it only ever read into ``next_funding_timestamp``, and never
even looked up the raw ``funding_timestamp`` key). It must now derive the true
charge instant by shifting the raw value back one cadence period, for any
venue registered in ``perp_funding_cadence.FUNDING_CADENCE_SECONDS``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from unified_api_contracts.normalize_utils import normalize_tardis_derivative_ticker


class TestNormalizeTardisDerivativeTicker:
    def test_funding_timestamp_derived_one_cadence_before_raw_value(self) -> None:
        # Binance: 8h cadence. Raw Tardis funding_timestamp = 16:00 UTC (forward-
        # looking); the true charge instant for the paired funding_rate is 08:00 UTC.
        raw = {
            "symbol": "BTCUSDT",
            "timestamp": int(datetime(2026, 4, 29, 7, 59, tzinfo=UTC).timestamp() * 1000),
            "fundingRate": "0.00001305",
            "funding_timestamp": int(datetime(2026, 4, 29, 16, 0, tzinfo=UTC).timestamp() * 1000),
        }
        ticker = normalize_tardis_derivative_ticker(raw, venue="binance")
        assert ticker.next_funding_timestamp == datetime(2026, 4, 29, 16, 0, tzinfo=UTC)
        assert ticker.funding_timestamp == datetime(2026, 4, 29, 8, 0, tzinfo=UTC)

    def test_explicit_next_funding_time_key_still_supported(self) -> None:
        raw = {
            "symbol": "BTCUSDT",
            "timestamp": 0,
            "fundingRate": "0.0001",
            "nextFundingTime": int(datetime(2026, 1, 1, 8, 0, tzinfo=UTC).timestamp() * 1000),
        }
        ticker = normalize_tardis_derivative_ticker(raw, venue="okx")
        assert ticker.next_funding_timestamp == datetime(2026, 1, 1, 8, 0, tzinfo=UTC)
        assert ticker.funding_timestamp == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)

    def test_unregistered_venue_leaves_funding_timestamp_none(self) -> None:
        raw = {
            "symbol": "XYZ",
            "timestamp": 0,
            "fundingRate": "0.0001",
            "funding_timestamp": int(datetime(2026, 1, 1, 8, 0, tzinfo=UTC).timestamp() * 1000),
        }
        ticker = normalize_tardis_derivative_ticker(raw, venue="not-a-real-venue")
        assert ticker.next_funding_timestamp == datetime(2026, 1, 1, 8, 0, tzinfo=UTC)
        assert ticker.funding_timestamp is None

    def test_no_funding_timestamp_field_leaves_both_none(self) -> None:
        raw = {"symbol": "BTCUSDT", "timestamp": 0, "fundingRate": "0.0001"}
        ticker = normalize_tardis_derivative_ticker(raw, venue="binance")
        assert ticker.next_funding_timestamp is None
        assert ticker.funding_timestamp is None
