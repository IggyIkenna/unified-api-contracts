"""Unit tests for the venue→source write-time capability validator.

The ``--source`` free-switch (operator 2026-06-19) drives BOTH the fetching
adapter AND the provenance stamp. ``assert_source_capable_for_venue`` is the
fail-closed gate that makes a mis-stamp (the VX/CFE ``batch_massive`` incident)
impossible: SOURCE_PRIORITY is the read-time order, this is the write-time gate.

SSOT: codex/02-data/tradfi-databento-sourcing-ssot.md.
"""

from __future__ import annotations

import pytest

from unified_api_contracts import (
    SourceNotCapableForVenueError,
    assert_source_capable_for_venue,
    is_source_capable_for_venue,
)


class TestSourceCapableForVenue:
    """The CBOE/VX override is the canonical case: Massive carries no CFE."""

    def test_cboe_massive_ohlcv_1m_raises(self) -> None:
        # --source massive for CBOE/VX futures MUST fail (Massive has no CFE).
        with pytest.raises(SourceNotCapableForVenueError, match="massive"):
            assert_source_capable_for_venue("tradfi", "ohlcv_1m", "CBOE", "massive")

    def test_cboe_massive_ohlcv_1s_raises(self) -> None:
        with pytest.raises(SourceNotCapableForVenueError):
            assert_source_capable_for_venue("tradfi", "ohlcv_1s", "CBOE", "massive")

    def test_cboe_databento_ohlcv_1m_passes(self) -> None:
        # Databento IS capable for CBOE (XCBF.PITCH).
        assert_source_capable_for_venue("tradfi", "ohlcv_1m", "CBOE", "databento")

    def test_nasdaq_massive_ohlcv_1m_now_rejected(self) -> None:
        # massive routing removed 2026-07-19 → no longer a registered source anywhere,
        # so even the venues it once served (NASDAQ equities) reject it.
        with pytest.raises(SourceNotCapableForVenueError, match="not a registered source"):
            assert_source_capable_for_venue("tradfi", "ohlcv_1m", "NASDAQ", "massive")

    def test_cme_databento_ohlcv_1m_passes(self) -> None:
        assert_source_capable_for_venue("tradfi", "ohlcv_1m", "CME", "databento")

    def test_cme_massive_ohlcv_1m_now_rejected(self) -> None:
        # massive was the CME 1m flat-file archive; routing removed 2026-07-19 → rejected.
        with pytest.raises(SourceNotCapableForVenueError, match="not a registered source"):
            assert_source_capable_for_venue("tradfi", "ohlcv_1m", "CME", "massive")

    def test_ohlcv_1s_massive_raises_everywhere(self) -> None:
        # ohlcv_1s is databento-only in SOURCE_PRIORITY → massive never capable.
        with pytest.raises(SourceNotCapableForVenueError, match="not a registered source"):
            assert_source_capable_for_venue("tradfi", "ohlcv_1s", "CME", "massive")

    def test_unregistered_pair_raises(self) -> None:
        with pytest.raises(SourceNotCapableForVenueError, match="No SOURCE_PRIORITY"):
            assert_source_capable_for_venue("tradfi", "not_a_real_data_type", "CME", "databento")

    def test_is_source_capable_helper(self) -> None:
        assert is_source_capable_for_venue("tradfi", "ohlcv_1m", "CBOE", "databento") is True
        assert is_source_capable_for_venue("tradfi", "ohlcv_1m", "CBOE", "massive") is False
        # NASDAQ massive was True pre-2026-07-19; routing removed → massive unregistered → False.
        assert is_source_capable_for_venue("tradfi", "ohlcv_1m", "NASDAQ", "massive") is False
        # Unregistered pair → False (never raises).
        assert is_source_capable_for_venue("tradfi", "not_a_real_dt", "CME", "databento") is False

    def test_case_insensitive(self) -> None:
        # venue / source / asset_group case must not matter.
        assert_source_capable_for_venue("TRADFI", "ohlcv_1m", "cboe", "DATABENTO")
        with pytest.raises(SourceNotCapableForVenueError):
            assert_source_capable_for_venue("TRADFI", "ohlcv_1m", "cboe", "MASSIVE")


class TestLighterZkSyncOhlcvSourceExclusion:
    """LIGHTER-ZKSYNC/ohlcv_1m: tardis is excluded; lighter_api is the first capable source.

    Regression guard for issues/onchain_venues_mislabeled_batch_tardis_lane_2026_07_20.md
    item 4: the sentinel path must NOT fabricate batch_tardis for a venue that
    self-archives ohlcv_1m via its own REST /candles (source=lighter_api).
    """

    def test_lighter_zksync_ohlcv_1m_tardis_excluded(self) -> None:
        assert is_source_capable_for_venue("cefi", "ohlcv_1m", "LIGHTER-ZKSYNC", "tardis") is False

    def test_lighter_zksync_ohlcv_1m_lighter_api_capable(self) -> None:
        assert is_source_capable_for_venue("cefi", "ohlcv_1m", "LIGHTER-ZKSYNC", "lighter_api") is True

    def test_lighter_zksync_ohlcv_1m_tardis_assert_raises(self) -> None:
        with pytest.raises(SourceNotCapableForVenueError, match="tardis"):
            assert_source_capable_for_venue("cefi", "ohlcv_1m", "LIGHTER-ZKSYNC", "tardis")
