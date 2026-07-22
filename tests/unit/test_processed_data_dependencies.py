"""Tests for registry/processed_data_dependencies.py — raw/processed dependency map.

Covers mdps_datatype_axis_switch_breaks_generic_classifier_2026_07_21 (B1/B2):
post-752eaff MDPS manifest rows carry the RAW SOURCE data_type token (not the
legacy AGGREGATED ``{prefix}_{tf}`` key), so ``is_processed_data_type``/
``get_raw_source_data_types`` must recognise that convention when called with
``service="market-data-processing-service"`` while staying byte-for-byte
unchanged for every other (default) caller.
"""

from __future__ import annotations

from unified_api_contracts.registry.processed_data_dependencies import (
    MDPS_CANONICAL_TIMEFRAMES,
    PROCESSED_REQUIRES_RAW,
    get_raw_source_data_types,
    is_processed_data_type,
)

_MDPS = "market-data-processing-service"
_MTDS = "market-tick-data-service"


class TestLegacyAggregatedKeyUnaffected:
    """Default (no ``service``) behaviour is byte-for-byte unchanged."""

    def test_aggregated_key_is_processed(self) -> None:
        assert is_processed_data_type("ohlcv_5m") is True
        assert is_processed_data_type("deriv_ohlcv_1h") is True

    def test_raw_key_is_not_processed_by_default(self) -> None:
        assert is_processed_data_type("trades") is False
        assert is_processed_data_type("derivative_ticker") is False

    def test_raw_key_is_not_processed_under_mtds_service(self) -> None:
        """A genuine MTDS raw-tick row must NOT be misclassified as processed
        just because the token also happens to be an MDPS-derivable source."""
        assert is_processed_data_type("trades", service=_MTDS) is False
        assert is_processed_data_type("derivative_ticker", service=_MTDS) is False

    def test_get_raw_source_data_types_for_aggregated_key(self) -> None:
        assert get_raw_source_data_types("deriv_ohlcv_1h") == ["derivative_ticker"]
        assert set(get_raw_source_data_types("ohlcv_5m")) == {"trades", "ohlcv_1m"}

    def test_unknown_key_returns_false_and_empty(self) -> None:
        assert is_processed_data_type("unexpected_type") is False
        assert get_raw_source_data_types("unexpected_type") == []


class TestSourceAxisMdpsClassification:
    """``service="market-data-processing-service"`` recognises post-752eaff
    SOURCE-keyed MDPS manifest rows as processed (the B1 fix)."""

    def test_source_token_is_processed_under_mdps_service(self) -> None:
        assert is_processed_data_type("trades", service=_MDPS) is True
        assert is_processed_data_type("derivative_ticker", service=_MDPS) is True
        assert is_processed_data_type("book_snapshot_5", service=_MDPS) is True
        assert is_processed_data_type("liquidations", service=_MDPS) is True

    def test_non_derivable_source_token_stays_unprocessed_under_mdps_service(self) -> None:
        assert is_processed_data_type("gas_fees", service=_MDPS) is False

    def test_get_raw_source_for_non_ohlcv_source_token_is_itself(self) -> None:
        """deriv_ohlcv_*'s raw precondition was `derivative_ticker` itself
        pre-cutover; post-cutover the SOURCE token IS that same raw source."""
        assert get_raw_source_data_types("derivative_ticker", service=_MDPS) == ["derivative_ticker"]
        assert get_raw_source_data_types("liquidations", service=_MDPS) == ["liquidations"]
        assert get_raw_source_data_types("book_snapshot_5", service=_MDPS) == ["book_snapshot_5"]

    def test_get_raw_source_for_ohlcv_passthrough_source_token(self) -> None:
        assert set(get_raw_source_data_types("trades", service=_MDPS)) == {"trades", "ohlcv_1m"}
        assert set(get_raw_source_data_types("ohlcv_1m", service=_MDPS)) == {"trades", "ohlcv_1m"}

    def test_unknown_source_token_under_mdps_service_is_still_unprocessed(self) -> None:
        assert is_processed_data_type("unexpected_type", service=_MDPS) is False
        assert get_raw_source_data_types("unexpected_type", service=_MDPS) == []


class TestTimeframeVocabulary:
    """B2: _TIMEFRAMES (legacy-aggregated-key generation) must cover every
    timeframe MDPS_CANONICAL_TIMEFRAMES (the writer's real going-forward
    output) declares, so a legacy row at any real candle grain still
    resolves via is_processed_data_type."""

    def test_every_canonical_timeframe_yields_a_recognised_aggregated_key(self) -> None:
        for tf in MDPS_CANONICAL_TIMEFRAMES:
            key = f"deriv_ohlcv_{tf}"
            assert key in PROCESSED_REQUIRES_RAW, f"{key} missing from PROCESSED_REQUIRES_RAW"

    def test_15s_aggregated_key_recognised(self) -> None:
        """Regression: _TIMEFRAMES previously omitted '15s', a real MDPS
        candle grain (MDPS_CANONICAL_TIMEFRAMES includes it) — a legacy
        pre-cutover book5_ohlcv_15s/liq_agg_15s row was invisible."""
        assert is_processed_data_type("book5_ohlcv_15s") is True
        assert is_processed_data_type("liq_agg_15s") is True
        assert get_raw_source_data_types("liq_agg_15s") == ["liquidations"]

    def test_legacy_24h_and_canonical_1d_both_resolve(self) -> None:
        """Intentional dual-key (not a bug) — both the legacy '24h' suffix
        and the UAC-canonical '1d' suffix must resolve for already-written
        manifest rows under either token."""
        assert is_processed_data_type("deriv_ohlcv_24h") is True
        assert is_processed_data_type("deriv_ohlcv_1d") is True
