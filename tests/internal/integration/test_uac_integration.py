"""Layer 1.5 mock integration tests: UIC private dependency boundary with UAC.

These tests verify the actual wiring between unified-internal-contracts (UIC)
and unified-api-contracts (UAC) without making any live calls.  They use
unittest.mock for all external side-effects, keeping tests hermetic.

Scope:
1. UIC market_data_processing adapter models are structurally compatible with
   UAC's CanonicalTrade / CanonicalOrderBook / CanonicalFill.
2. UAC normalization functions produce output whose field names and types align
   with UIC's CandleOutput / InstrumentInfo schemas.
3. UIC INSTRUMENTS_SCHEMA round-trips through ColumnSchema / SchemaDefinition.
4. UIC CascadeConfig / CascadePredictionEvent are compatible with the UAC
   ML-prediction message contract (MLPredictionMessage).
5. All InternalPubSubTopic topic-name constants are non-empty strings.
"""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal

# ---------------------------------------------------------------------------
# UAC imports (level 1: top-level or public facade paths only)
# ---------------------------------------------------------------------------
from unified_api_contracts import (
    CanonicalFill,
    CanonicalOrderBook,
    CanonicalTrade,
)

# UAC external binance schemas (level 1: binance __init__ re-exports)
from unified_api_contracts.external.binance import (
    BinanceMyTrades,
    BinanceOrderBook,
    BinanceTrade,
)

# ---------------------------------------------------------------------------
# UIC imports
# ---------------------------------------------------------------------------
from unified_api_contracts.internal.domain.instruments import (
    INSTRUMENTS_SCHEMA,
)
from unified_api_contracts.internal.domain.market_data_processing.adapter_models import (
    CandleOutput,
    InstrumentInfo,
)
from unified_api_contracts.internal.domain.ml_inference_service.cascade_prediction import (
    CascadeConfig,
    CascadePredictionEvent,
    PredictionSnapshot,
)
from unified_api_contracts.internal.pubsub import InternalPubSubTopic, MLPredictionMessage
from unified_api_contracts.internal.schema_definition import ColumnSchema, SchemaDefinition
from unified_api_contracts.normalize_utils.orderbooks import (
    normalize_binance_orderbook,
)
from unified_api_contracts.normalize_utils.orders_fills import (
    normalize_binance_fill,
)
from unified_api_contracts.normalize_utils.trades import (
    normalize_binance_trade,
)

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_binance_trade(
    trade_id: int = 1001,
    price: Decimal = Decimal("50000.00"),
    qty: Decimal = Decimal("0.5"),
    time_ms: int = 1_700_000_000_000,
    is_buyer_maker: bool = False,
) -> BinanceTrade:
    return BinanceTrade(
        id=trade_id,
        price=price,
        qty=qty,
        quoteQty=price * qty,
        time=time_ms,
        isBuyerMaker=is_buyer_maker,
        isBestMatch=True,
    )


def _make_binance_orderbook(
    last_update_id: int = 9999,
    bids: list[list[str]] | None = None,
    asks: list[list[str]] | None = None,
) -> BinanceOrderBook:
    # BinanceOrderBook.bids / .asks are list[list[str]] — [[price_str, qty_str], ...]
    if bids is None:
        bids = [["49999.00", "1.0"], ["49998.00", "2.0"]]
    if asks is None:
        asks = [["50001.00", "1.5"], ["50002.00", "0.5"]]
    return BinanceOrderBook(lastUpdateId=last_update_id, bids=bids, asks=asks)


def _make_binance_fill(
    fill_id: int = 5001,
    order_id: int = 3001,
    symbol: str = "BTCUSDT",
    side: str = "BUY",
    price: str = "50000.00",
    qty: str = "0.5",
    commission: str = "0.00025",
    commission_asset: str = "BTC",
    time_ms: int = 1_700_000_000_000,
    maker: bool = False,
) -> BinanceMyTrades:
    return BinanceMyTrades(
        symbol=symbol,
        id=fill_id,
        orderId=order_id,
        pair=None,
        side=side,
        price=price,
        qty=qty,
        realizedPnl=None,
        marginAsset=None,
        baseQty=None,
        commission=commission,
        commissionAsset=commission_asset,
        time=time_ms,
        positionSide=None,
        buyer=True,
        maker=maker,
        quoteQty=None,
    )


# ===========================================================================
# Test 1 — UIC adapter models are compatible with UAC canonical types
# ===========================================================================


class TestUICSchemaReferencesUACCanonicalTypes(unittest.TestCase):
    """UIC market_data_processing adapter models are structurally compatible
    with UAC's CanonicalTrade / CanonicalOrderBook / CanonicalFill."""

    def test_canonical_trade_required_fields_are_present(self) -> None:
        """CanonicalTrade exposes the fields that UIC processing pipeline expects."""
        required_by_uic = {"venue", "symbol", "trade_id", "timestamp", "price", "quantity", "side"}
        actual = set(CanonicalTrade.model_fields.keys())
        missing = required_by_uic - actual
        self.assertEqual(
            missing,
            set(),
            f"CanonicalTrade is missing fields expected by UIC: {missing}",
        )

    def test_canonical_orderbook_required_fields_are_present(self) -> None:
        """CanonicalOrderBook exposes the fields that UIC book_update processing expects."""
        required_by_uic = {"venue", "symbol", "timestamp", "bids", "asks"}
        actual = set(CanonicalOrderBook.model_fields.keys())
        missing = required_by_uic - actual
        self.assertEqual(
            missing,
            set(),
            f"CanonicalOrderBook is missing fields expected by UIC: {missing}",
        )

    def test_canonical_fill_required_fields_are_present(self) -> None:
        """CanonicalFill exposes the fields that UIC execution processing expects."""
        required_by_uic = {
            "fill_id",
            "order_id",
            "timestamp",
            "venue",
            "instrument_id",
            "side",
            "price",
            "quantity",
        }
        actual = set(CanonicalFill.model_fields.keys())
        missing = required_by_uic - actual
        self.assertEqual(
            missing,
            set(),
            f"CanonicalFill is missing fields expected by UIC: {missing}",
        )

    def test_canonical_trade_instrument_key_field_present(self) -> None:
        """CanonicalTrade has instrument_key — the canonical cross-venue key used in UIC."""
        self.assertIn("instrument_key", CanonicalTrade.model_fields)

    def test_canonical_orderbook_instrument_key_field_present(self) -> None:
        """CanonicalOrderBook has instrument_key for UIC market_data_api compatibility."""
        self.assertIn("instrument_key", CanonicalOrderBook.model_fields)

    def test_uic_instrument_info_keys_match_canonical_trade_venue_symbol(self) -> None:
        """InstrumentInfo.venue and .symbol properties map to CanonicalTrade.venue/.symbol."""
        info = InstrumentInfo(instrument_id="BINANCE:SPOT:BTCUSDT", venue="BINANCE", symbol="BTCUSDT")
        # UAC CanonicalTrade uses lowercase venue strings; InstrumentInfo stores raw venue.
        # Verify the property accessors work (the bridge layer applies .lower()).
        self.assertEqual(info.venue, "BINANCE")
        self.assertEqual(info.symbol, "BTCUSDT")
        # The canonical trade model accepts both — validate field coercion is fine
        trade = normalize_binance_trade(
            _make_binance_trade(),
            venue=info.venue.lower(),
            symbol=info.symbol,
        )
        self.assertIsInstance(trade, CanonicalTrade)
        self.assertEqual(trade.venue, "binance")
        self.assertEqual(trade.symbol, "BTCUSDT")

    def test_canonical_fill_schema_version_present(self) -> None:
        """CanonicalFill carries schema_version — versioned contract for UIC pub-sub."""
        self.assertIn("schema_version", CanonicalFill.model_fields)

    def test_canonical_trade_schema_version_present(self) -> None:
        """CanonicalTrade carries schema_version constant."""
        self.assertIn("schema_version", CanonicalTrade.model_fields)

    def test_uic_candle_output_identifier_fields_align_with_uac_canonical(self) -> None:
        """CandleOutput identifier fields (venue, symbol, instrument_id) align with UAC."""
        import dataclasses

        co_fields = {f.name for f in dataclasses.fields(CandleOutput)}
        # These three map to UAC canonical fields: venue → venue, symbol → symbol,
        # instrument_id → instrument_key (VENUE:TYPE:SYMBOL format).
        for expected in ("venue", "symbol", "instrument_id"):
            self.assertIn(expected, co_fields, f"CandleOutput missing field: {expected}")


# ===========================================================================
# Test 2 — UAC normalization output aligns with UIC domain schemas
# ===========================================================================


class TestUACNormalizationAlignsWithUICDomainOutput(unittest.TestCase):
    """UAC normalize functions produce output compatible with UIC CandleOutput/InstrumentInfo."""

    def test_normalize_binance_trade_produces_canonical_trade(self) -> None:
        """normalize_binance_trade returns a CanonicalTrade with all required fields set."""
        raw = _make_binance_trade(trade_id=42, price=Decimal("30000"), qty=Decimal("1.0"))
        result = normalize_binance_trade(raw, venue="binance", symbol="BTCUSDT")
        self.assertIsInstance(result, CanonicalTrade)
        self.assertGreater(result.price, Decimal("0"))
        self.assertGreater(result.quantity, Decimal("0"))
        self.assertIn(result.side, ("buy", "sell"))
        self.assertIsNotNone(result.timestamp)
        self.assertEqual(result.venue, "binance")
        self.assertEqual(result.symbol, "BTCUSDT")

    def test_normalize_binance_trade_buyer_maker_maps_correctly(self) -> None:
        """isBuyerMaker=True → side='sell'; isBuyerMaker=False → side='buy'."""
        raw_maker = _make_binance_trade(is_buyer_maker=True)
        raw_taker = _make_binance_trade(is_buyer_maker=False)
        self.assertEqual(normalize_binance_trade(raw_maker).side, "sell")
        self.assertEqual(normalize_binance_trade(raw_taker).side, "buy")

    def test_normalize_binance_orderbook_produces_canonical_orderbook(self) -> None:
        """normalize_binance_orderbook returns CanonicalOrderBook compatible with UIC."""
        raw = _make_binance_orderbook()
        result = normalize_binance_orderbook(raw, venue="binance", symbol="BTCUSDT")
        self.assertIsInstance(result, CanonicalOrderBook)
        self.assertEqual(result.venue, "binance")
        self.assertEqual(result.symbol, "BTCUSDT")
        self.assertGreater(len(result.bids), 0)
        self.assertGreater(len(result.asks), 0)
        # Each level is a (price, qty) tuple of Decimals
        bid0_price, bid0_qty = result.bids[0]
        self.assertIsInstance(bid0_price, Decimal)
        self.assertIsInstance(bid0_qty, Decimal)

    def test_normalize_binance_orderbook_sequence_number(self) -> None:
        """CanonicalOrderBook.sequence_number maps from BinanceOrderBook.lastUpdateId."""
        raw = _make_binance_orderbook(last_update_id=12345)
        result = normalize_binance_orderbook(raw, venue="binance", symbol="ETHUSDT")
        self.assertEqual(result.sequence_number, 12345)

    def test_normalize_binance_fill_produces_canonical_fill(self) -> None:
        """normalize_binance_fill returns a CanonicalFill compatible with UIC pub-sub envelope."""
        raw = _make_binance_fill(fill_id=77, order_id=88, symbol="ETHUSDT", side="BUY")
        result = normalize_binance_fill(raw, venue="binance")
        self.assertIsInstance(result, CanonicalFill)
        self.assertEqual(result.venue, "binance")
        self.assertEqual(result.instrument_id, "ETHUSDT")
        self.assertGreater(result.price, Decimal("0"))
        self.assertGreater(result.quantity, Decimal("0"))

    def test_normalize_binance_fill_fee_fields_align_with_uic_fill_event_message(self) -> None:
        """CanonicalFill fee fields align with UIC FillEventMessage fee fields."""
        raw = _make_binance_fill(commission="0.001", commission_asset="USDT")
        fill = normalize_binance_fill(raw)
        # UIC FillEventMessage has fee and fee_currency fields
        self.assertIsNotNone(fill.fee)
        self.assertEqual(fill.fee_currency, "USDT")

    def test_canonical_trade_venue_symbol_can_build_instrument_key(self) -> None:
        """CanonicalTrade.venue + symbol can be used to build an instrument_key for UIC."""
        raw = _make_binance_trade()
        trade = normalize_binance_trade(raw, venue="binance", symbol="BTCUSDT")
        # UIC InstrumentInfo format: VENUE:TYPE:SYMBOL
        mock_instrument_key = f"{trade.venue.upper()}:SPOT:{trade.symbol}"
        self.assertEqual(mock_instrument_key, "BINANCE:SPOT:BTCUSDT")

    def test_uic_candle_output_venue_symbol_match_canonical_trade(self) -> None:
        """CandleOutput can hold the venue/symbol values produced by UAC normalize."""
        import numpy as np

        raw = _make_binance_trade(price=Decimal("42000"), qty=Decimal("0.25"))
        trade = normalize_binance_trade(raw, venue="binance", symbol="BTCUSDT")
        co = CandleOutput(
            venue=np.array([trade.venue], dtype=object),
            symbol=np.array([trade.symbol], dtype=object),
            instrument_id=np.array(["BINANCE:SPOT:BTCUSDT"], dtype=object),
            close=np.array([float(trade.price)]),
            volume=np.array([float(trade.quantity)]),
        )
        df = co.to_dataframe()
        self.assertEqual(df["venue"].iloc[0], "binance")
        self.assertEqual(df["symbol"].iloc[0], "BTCUSDT")


# ===========================================================================
# Test 3 — INSTRUMENTS_SCHEMA round-trip through ColumnSchema / SchemaDefinition
# ===========================================================================


class TestUICDomainInstrumentsSchemaRoundTrip(unittest.TestCase):
    """INSTRUMENTS_SCHEMA from UIC round-trips through ColumnSchema/SchemaDefinition."""

    def test_instruments_schema_is_schema_definition_instance(self) -> None:
        """INSTRUMENTS_SCHEMA is a proper SchemaDefinition."""
        self.assertIsInstance(INSTRUMENTS_SCHEMA, SchemaDefinition)

    def test_instruments_schema_name_and_version(self) -> None:
        """Schema name and version are set correctly."""
        self.assertEqual(INSTRUMENTS_SCHEMA.name, "instruments")
        self.assertIsInstance(INSTRUMENTS_SCHEMA.version, str)
        self.assertTrue(len(INSTRUMENTS_SCHEMA.version) > 0)

    def test_instruments_schema_columns_are_column_schema_instances(self) -> None:
        """Every column in INSTRUMENTS_SCHEMA is a ColumnSchema."""
        for col in INSTRUMENTS_SCHEMA.columns:
            self.assertIsInstance(col, ColumnSchema, f"Column {col!r} is not a ColumnSchema")

    def test_instruments_schema_required_columns_non_nullable(self) -> None:
        """Core required columns (instrument_key, venue, symbol) are non-nullable."""
        non_nullable = {col.name for col in INSTRUMENTS_SCHEMA.columns if not col.nullable}
        for required in ("instrument_key", "venue", "symbol", "instrument_type"):
            self.assertIn(required, non_nullable, f"{required!r} must be non-nullable")

    def test_instruments_schema_to_dict_round_trip(self) -> None:
        """SchemaDefinition.to_dict() → SchemaDefinition.from_dict() preserves structure."""
        serialised = INSTRUMENTS_SCHEMA.to_dict()
        restored = SchemaDefinition.from_dict(serialised)
        self.assertEqual(restored.name, INSTRUMENTS_SCHEMA.name)
        self.assertEqual(len(restored.columns), len(INSTRUMENTS_SCHEMA.columns))
        original_names = [col.name for col in INSTRUMENTS_SCHEMA.columns]
        restored_names = [col.name for col in restored.columns]
        self.assertEqual(original_names, restored_names)

    def test_instruments_schema_column_dtypes_dict(self) -> None:
        """get_column_dtypes() returns a non-empty dict with string values."""
        dtypes = INSTRUMENTS_SCHEMA.get_column_dtypes()
        self.assertIsInstance(dtypes, dict)
        self.assertGreater(len(dtypes), 0)
        for col_name, dtype in dtypes.items():
            self.assertIsInstance(col_name, str)
            self.assertIsInstance(dtype, str)
            self.assertTrue(len(dtype) > 0, f"Empty dtype for column {col_name!r}")

    def test_instruments_schema_nullable_override_cefi(self) -> None:
        """tardis_exchange is NOT nullable for CEFI dimension."""
        is_nullable = INSTRUMENTS_SCHEMA.is_nullable("tardis_exchange", {"asset_group": "CEFI"})
        self.assertFalse(is_nullable, "tardis_exchange must be required for CEFI")

    def test_instruments_schema_nullable_override_tradfi(self) -> None:
        """databento_symbol is NOT nullable for TRADFI dimension."""
        is_nullable = INSTRUMENTS_SCHEMA.is_nullable("databento_symbol", {"asset_group": "TRADFI"})
        self.assertFalse(is_nullable, "databento_symbol must be required for TRADFI")

    def test_instruments_schema_required_columns_include_timestamp(self) -> None:
        """timestamp is a required (non-nullable) column in INSTRUMENTS_SCHEMA."""
        col = INSTRUMENTS_SCHEMA.get_column("timestamp")
        self.assertIsNotNone(col)
        self.assertFalse(col.nullable)  # type: ignore[union-attr]

    def test_instruments_schema_column_count_matches_uac_instrument_warehouse_row(self) -> None:
        """INSTRUMENTS_SCHEMA column count is >= required fields in UAC CanonicalInstrument."""
        from unified_api_contracts import CanonicalInstrument

        # UAC CanonicalInstrument required fields (no default) must all be coverable
        # by INSTRUMENTS_SCHEMA columns.
        uac_required = {name for name, field in CanonicalInstrument.model_fields.items() if field.is_required()}
        uic_column_names = {col.name for col in INSTRUMENTS_SCHEMA.columns}
        missing = uac_required - uic_column_names
        self.assertEqual(
            missing,
            set(),
            f"INSTRUMENTS_SCHEMA is missing columns for UAC CanonicalInstrument required fields: {missing}",
        )


# ===========================================================================
# Test 4 — CascadeConfig / CascadePredictionEvent compatible with UAC contracts
# ===========================================================================


class TestUICCascadePredictionCompatibleWithUACContracts(unittest.TestCase):
    """UIC cascade prediction types are compatible with UAC MLPredictionMessage contract."""

    def _make_prediction_snapshot(
        self,
        instrument_id: str = "BINANCE:SPOT:BTCUSDT",
        timeframe: str = "1h",
        direction: int = 1,
        confidence: float = 0.72,
    ) -> PredictionSnapshot:
        return PredictionSnapshot(
            instrument_id=instrument_id,
            timeframe=timeframe,
            direction=direction,
            confidence=confidence,
            model_id="xgb-v2",
            predicted_at=datetime.now(UTC),
        )

    def _make_cascade_config(self) -> CascadeConfig:
        return CascadeConfig(
            profile_name="momentum_cascade",
            trigger_timeframe="1h",
            context_timeframes=["1d", "4h"],
            entry_timeframes=["15m", "5m"],
            confidence_threshold=0.6,
            require_context_alignment=True,
        )

    def _make_cascade_event(
        self,
        config: CascadeConfig | None = None,
    ) -> CascadePredictionEvent:
        cfg = config or self._make_cascade_config()
        context_snap = self._make_prediction_snapshot(timeframe="4h")
        return CascadePredictionEvent(
            instrument_id="BINANCE:SPOT:BTCUSDT",
            profile_name=cfg.profile_name,
            trigger_timeframe=cfg.trigger_timeframe,
            trigger_direction=1,
            trigger_confidence=0.78,
            context={"4h": context_snap},
            cascade_confidence_score=0.74,
            cascade_aligned=True,
            recommended_entry_timeframes=cfg.entry_timeframes,
        )

    def test_prediction_snapshot_fields_are_complete(self) -> None:
        """PredictionSnapshot has all fields required to populate MLPredictionMessage."""
        snap = self._make_prediction_snapshot()
        self.assertIsInstance(snap.instrument_id, str)
        self.assertTrue(len(snap.instrument_id) > 0)
        self.assertIsInstance(snap.confidence, float)
        self.assertGreaterEqual(snap.confidence, 0.0)
        self.assertLessEqual(snap.confidence, 1.0)
        self.assertIn(snap.direction, (-1, 0, 1))
        self.assertIsInstance(snap.model_id, str)
        self.assertIsNotNone(snap.predicted_at)

    def test_cascade_config_profile_name_is_non_empty_string(self) -> None:
        """CascadeConfig.profile_name is non-empty string (used as MLPredictionMessage.model_id)."""
        cfg = self._make_cascade_config()
        self.assertIsInstance(cfg.profile_name, str)
        self.assertTrue(len(cfg.profile_name) > 0)

    def test_cascade_config_timeframes_are_non_empty_lists(self) -> None:
        """CascadeConfig timeframe lists are non-empty and contain strings."""
        cfg = self._make_cascade_config()
        for attr in ("context_timeframes", "entry_timeframes"):
            tfs = getattr(cfg, attr)
            self.assertIsInstance(tfs, list)
            self.assertGreater(len(tfs), 0)
            for tf in tfs:
                self.assertIsInstance(tf, str)
                self.assertTrue(len(tf) > 0)

    def test_cascade_prediction_event_fields_map_to_uac_ml_prediction_message(self) -> None:
        """CascadePredictionEvent fields can be mapped to UAC MLPredictionMessage fields."""
        event = self._make_cascade_event()
        # Build a mock MLPredictionMessage from the cascade event fields — verifies
        # that instrument_id, model_id (profile_name), confidence, prediction are
        # all available as the correct types.
        ml_msg = MLPredictionMessage(
            request_id="cascade-req-001",
            model_id=event.profile_name,
            instrument_id=event.instrument_id,
            timestamp=event.published_at.isoformat(),
            prediction=float(event.trigger_direction),
            confidence=event.cascade_confidence_score,
            target_type="direction",
        )
        self.assertEqual(ml_msg.model_id, "momentum_cascade")
        self.assertEqual(ml_msg.instrument_id, "BINANCE:SPOT:BTCUSDT")
        self.assertAlmostEqual(ml_msg.confidence, 0.74)  # type: ignore[arg-type]

    def test_cascade_prediction_event_context_is_dict_of_snapshots(self) -> None:
        """CascadePredictionEvent.context is a dict mapping timeframe → PredictionSnapshot."""
        event = self._make_cascade_event()
        self.assertIsInstance(event.context, dict)
        for tf, snap in event.context.items():
            self.assertIsInstance(tf, str)
            self.assertIsInstance(snap, PredictionSnapshot)

    def test_cascade_prediction_event_published_at_is_aware_datetime(self) -> None:
        """CascadePredictionEvent.published_at is timezone-aware (UTC)."""
        event = self._make_cascade_event()
        self.assertIsNotNone(event.published_at.tzinfo)

    def test_cascade_confidence_score_in_valid_range(self) -> None:
        """cascade_confidence_score is in [0.0, 1.0] — aligns with UAC confidence field."""
        event = self._make_cascade_event()
        self.assertGreaterEqual(event.cascade_confidence_score, 0.0)
        self.assertLessEqual(event.cascade_confidence_score, 1.0)

    def test_mock_ml_prediction_published_via_pubsub_topic(self) -> None:
        """CascadePredictionEvent can be wrapped into a PubSubMessageEnvelope mock."""
        from unified_api_contracts.internal.pubsub import PubSubMessageEnvelope

        event = self._make_cascade_event()
        envelope = PubSubMessageEnvelope(
            topic=InternalPubSubTopic.ML_PREDICTIONS.value,
            message_type="CascadePredictionEvent",
            source_service="ml-inference-service",
            timestamp=event.published_at,
            payload={
                "instrument_id": event.instrument_id,
                "profile_name": event.profile_name,
                "cascade_confidence_score": event.cascade_confidence_score,
                "cascade_aligned": event.cascade_aligned,
            },
        )
        self.assertEqual(envelope.topic, "ml-predictions")
        self.assertEqual(envelope.message_type, "CascadePredictionEvent")
        self.assertEqual(envelope.payload["instrument_id"], "BINANCE:SPOT:BTCUSDT")


# ===========================================================================
# Test 5 — Topic name constants are non-empty strings
# ===========================================================================


class TestTopicNamesAreStrings(unittest.TestCase):
    """All topic name constants in UIC are non-empty strings (no None, no empty)."""

    def test_all_internal_pubsub_topic_values_are_non_empty_strings(self) -> None:
        """Every InternalPubSubTopic member has a non-empty string value."""
        for member in InternalPubSubTopic:
            self.assertIsInstance(
                member.value,
                str,
                f"InternalPubSubTopic.{member.name}.value is not a str",
            )
            self.assertTrue(
                len(member.value) > 0,
                f"InternalPubSubTopic.{member.name}.value is empty",
            )

    def test_all_topic_values_are_not_none(self) -> None:
        """No topic value is None."""
        for member in InternalPubSubTopic:
            self.assertIsNotNone(
                member.value,
                f"InternalPubSubTopic.{member.name}.value is None",
            )

    def test_topic_names_have_no_leading_or_trailing_whitespace(self) -> None:
        """Topic values have no leading/trailing whitespace."""
        for member in InternalPubSubTopic:
            self.assertEqual(
                member.value,
                member.value.strip(),
                f"InternalPubSubTopic.{member.name}.value has leading/trailing whitespace",
            )

    def test_execution_layer_topics_present(self) -> None:
        """Execution-layer topics (fill-events, order-requests, execution-results) are defined."""
        values = {m.value for m in InternalPubSubTopic}
        for expected in (
            "fill-events-{venue}",
            "order-requests",
            "execution-results",
        ):
            self.assertIn(expected, values, f"Missing execution topic: {expected!r}")

    def test_market_data_topics_present(self) -> None:
        """Market-data live-mode topics are defined."""
        values = {m.value for m in InternalPubSubTopic}
        for expected in ("market-ticks", "order-book-updates", "liquidations"):
            self.assertIn(expected, values, f"Missing market-data topic: {expected!r}")

    def test_ml_predictions_topic_present(self) -> None:
        """ml-predictions topic is defined (required by cascade prediction pipeline)."""
        values = {m.value for m in InternalPubSubTopic}
        self.assertIn("ml-predictions", values)

    def test_circuit_breaker_events_topic_present(self) -> None:
        """circuit-breaker-events topic is defined (required by alerting pipeline)."""
        values = {m.value for m in InternalPubSubTopic}
        self.assertIn("circuit-breaker-events", values)

    def test_topic_count_is_at_least_expected_minimum(self) -> None:
        """At least 10 distinct topics are defined — guards against accidental truncation."""
        self.assertGreaterEqual(len(list(InternalPubSubTopic)), 10)

    def test_all_topic_values_are_unique(self) -> None:
        """No two InternalPubSubTopic members share the same value."""
        values = [m.value for m in InternalPubSubTopic]
        self.assertEqual(len(values), len(set(values)), "Duplicate topic values found")

    def test_fill_events_venue_placeholder_format(self) -> None:
        """fill-events-{venue} topic value uses the correct template placeholder."""
        fill_topic = InternalPubSubTopic.FILL_EVENTS.value
        self.assertIn("{venue}", fill_topic)
        # Verify it templates correctly
        concrete = fill_topic.format(venue="binance")
        self.assertEqual(concrete, "fill-events-binance")


# ===========================================================================
# Test 6 — UIC market_data re-exports CanonicalLiquidation / CanonicalTicker
# ===========================================================================


class TestUICMarketDataReExportsCanonicalTypes(unittest.TestCase):
    """UIC market_data re-exports CanonicalLiquidation and CanonicalTicker from UAC."""

    def test_canonical_liquidation_instantiation(self) -> None:
        """CanonicalLiquidation can be instantiated with required fields."""
        from unified_api_contracts.internal.market_data import CanonicalLiquidation

        liq = CanonicalLiquidation(
            instrument_key="BINANCE:PERP:BTCUSDT",
            venue="binance",
            timestamp=datetime.now(UTC),
            side="sell",
            price=Decimal("49500.00"),
            size=Decimal("1.5"),
        )
        self.assertEqual(liq.venue, "binance")
        self.assertEqual(liq.instrument_key, "BINANCE:PERP:BTCUSDT")
        self.assertEqual(liq.side, "sell")
        self.assertGreater(liq.price, Decimal("0"))
        self.assertGreater(liq.size, Decimal("0"))

    def test_canonical_liquidation_optional_fields(self) -> None:
        """CanonicalLiquidation optional fields default to None."""
        from unified_api_contracts.internal.market_data import CanonicalLiquidation

        liq = CanonicalLiquidation(
            instrument_key="BINANCE:PERP:ETHUSDT",
            venue="binance",
            timestamp=datetime.now(UTC),
            side="buy",
            price=Decimal("3200.00"),
            size=Decimal("10.0"),
        )
        self.assertIsNone(liq.order_id)
        self.assertIsNone(liq.liquidated_account_value)

    def test_canonical_liquidation_with_order_id(self) -> None:
        """CanonicalLiquidation accepts order_id and account value."""
        from unified_api_contracts.internal.market_data import CanonicalLiquidation

        liq = CanonicalLiquidation(
            instrument_key="BINANCE:PERP:BTCUSDT",
            venue="binance",
            timestamp=datetime.now(UTC),
            side="sell",
            price=Decimal("49000.00"),
            size=Decimal("2.0"),
            order_id="liq-ord-001",
            liquidated_account_value=Decimal("98000.00"),
        )
        self.assertEqual(liq.order_id, "liq-ord-001")
        self.assertEqual(liq.liquidated_account_value, Decimal("98000.00"))

    def test_canonical_ticker_instantiation(self) -> None:
        """CanonicalTicker can be instantiated with required fields."""
        from unified_api_contracts.internal.market_data import CanonicalTicker

        ticker = CanonicalTicker(
            instrument_key="BINANCE:SPOT:BTCUSDT",
            venue="binance",
            timestamp=datetime.now(UTC),
            last_price=Decimal("50123.45"),
        )
        self.assertEqual(ticker.venue, "binance")
        self.assertEqual(ticker.instrument_key, "BINANCE:SPOT:BTCUSDT")
        self.assertEqual(ticker.last_price, Decimal("50123.45"))

    def test_canonical_ticker_with_all_optional_fields(self) -> None:
        """CanonicalTicker accepts all optional quote fields."""
        from unified_api_contracts.internal.market_data import CanonicalTicker

        ticker = CanonicalTicker(
            instrument_key="BINANCE:SPOT:ETHUSDT",
            venue="binance",
            timestamp=datetime.now(UTC),
            last_price=Decimal("3200.00"),
            bid_price=Decimal("3199.50"),
            ask_price=Decimal("3200.50"),
            volume_24h=Decimal("150000.0"),
            quote_volume_24h=Decimal("480000000.0"),
            price_change_24h=Decimal("50.00"),
            price_change_percent_24h=Decimal("1.59"),
        )
        self.assertEqual(ticker.bid_price, Decimal("3199.50"))
        self.assertEqual(ticker.ask_price, Decimal("3200.50"))
        self.assertGreater(ticker.volume_24h, Decimal("0"))

    def test_canonical_ticker_model_fields_cover_uic_expectations(self) -> None:
        """CanonicalTicker has all fields that UIC market_data pipeline requires."""
        from unified_api_contracts.internal.market_data import CanonicalTicker

        required_by_uic = {"instrument_key", "venue", "timestamp", "last_price"}
        actual = set(CanonicalTicker.model_fields.keys())
        missing = required_by_uic - actual
        self.assertEqual(missing, set(), f"CanonicalTicker missing fields: {missing}")


# ===========================================================================
# Test 7 — UAC sports enums used in UIC sports tick schemas
# ===========================================================================


class TestUACSportsEnumsUsedInUICSportsSchemas(unittest.TestCase):
    """UAC sports enums (OddsType, OutcomeType, MarketStatus) are usable in UIC schemas."""

    def test_sports_odds_tick_instantiation_with_uac_enums(self) -> None:
        """SportsOddsTick can be instantiated with UAC OddsType/OutcomeType/MarketStatus."""
        from unified_api_contracts import MarketStatus, OddsType, OutcomeType
        from unified_api_contracts.internal.domain.market_tick_data.sports import SportsOddsTick

        tick = SportsOddsTick(
            timestamp_utc=datetime.now(UTC),
            bookmaker_key="pinnacle",
            fixture_key="SOCCER:EPL:2024-MCI-ARS",
            market_type=OddsType.H2H,
            outcome=OutcomeType.HOME,
            odds_value=Decimal("1.85"),
            market_status=MarketStatus.ACTIVE,
        )
        self.assertEqual(tick.market_type, OddsType.H2H)
        self.assertEqual(tick.outcome, OutcomeType.HOME)
        self.assertEqual(tick.market_status, MarketStatus.ACTIVE)
        self.assertEqual(tick.bookmaker_key, "pinnacle")

    def test_sports_odds_tick_implied_probability_computation(self) -> None:
        """SportsOddsTick.implied_probability computes 1/odds correctly."""
        from unified_api_contracts import OddsType, OutcomeType
        from unified_api_contracts.internal.domain.market_tick_data.sports import SportsOddsTick

        tick = SportsOddsTick(
            timestamp_utc=datetime.now(UTC),
            bookmaker_key="betfair",
            fixture_key="TENNIS:ATP:2024-FED-NAD",
            market_type=OddsType.H2H,
            outcome=OutcomeType.HOME,
            odds_value=Decimal("2.00"),
        )
        self.assertEqual(tick.implied_probability, Decimal("0.5"))

    def test_sports_odds_tick_instrument_key_format(self) -> None:
        """SportsOddsTick.instrument_key uses BOOKMAKER:MARKET_TYPE:FIXTURE_KEY format."""
        from unified_api_contracts import OddsType, OutcomeType
        from unified_api_contracts.internal.domain.market_tick_data.sports import SportsOddsTick

        tick = SportsOddsTick(
            timestamp_utc=datetime.now(UTC),
            bookmaker_key="pinnacle",
            fixture_key="NBA:2024-LAL-GSW",
            market_type=OddsType.H2H,
            outcome=OutcomeType.HOME,
            odds_value=Decimal("1.90"),
        )
        self.assertEqual(tick.instrument_key, "pinnacle:h2h:NBA:2024-LAL-GSW")

    def test_sports_book_update_with_multiple_ticks(self) -> None:
        """SportsBookUpdate aggregates ticks using UAC enum types."""
        from unified_api_contracts import MarketStatus, OddsType, OutcomeType
        from unified_api_contracts.internal.domain.market_tick_data.sports import (
            SportsBookUpdate,
            SportsOddsTick,
        )

        ts = datetime.now(UTC)
        tick_home = SportsOddsTick(
            timestamp_utc=ts,
            bookmaker_key="bet365",
            fixture_key="EPL:MCI-ARS",
            market_type=OddsType.H2H,
            outcome=OutcomeType.HOME,
            odds_value=Decimal("1.80"),
        )
        tick_away = SportsOddsTick(
            timestamp_utc=ts,
            bookmaker_key="bet365",
            fixture_key="EPL:MCI-ARS",
            market_type=OddsType.H2H,
            outcome=OutcomeType.AWAY,
            odds_value=Decimal("4.20"),
        )
        tick_draw = SportsOddsTick(
            timestamp_utc=ts,
            bookmaker_key="pinnacle",
            fixture_key="EPL:MCI-ARS",
            market_type=OddsType.H2H,
            outcome=OutcomeType.DRAW,
            odds_value=Decimal("3.50"),
        )
        update = SportsBookUpdate(
            timestamp_utc=ts,
            fixture_key="EPL:MCI-ARS",
            market_type=OddsType.H2H,
            market_status=MarketStatus.ACTIVE,
            ticks=(tick_home, tick_away, tick_draw),
        )
        self.assertEqual(update.bookmaker_count, 2)  # bet365 + pinnacle
        self.assertEqual(update.outcome_count, 3)  # home + away + draw
        self.assertEqual(len(update.ticks), 3)

    def test_market_status_enum_values_accessible(self) -> None:
        """All MarketStatus enum members can be accessed and are strings."""
        from unified_api_contracts import MarketStatus

        for member in MarketStatus:
            self.assertIsInstance(member.value, str)
            self.assertTrue(len(member.value) > 0)
        # Verify expected members exist
        self.assertEqual(MarketStatus.ACTIVE.value, "active")
        self.assertEqual(MarketStatus.SUSPENDED.value, "suspended")
        self.assertEqual(MarketStatus.CLOSED.value, "closed")
        self.assertEqual(MarketStatus.SETTLED.value, "settled")

    def test_odds_type_enum_has_expected_markets(self) -> None:
        """OddsType enum contains the market types used by UIC sports schemas."""
        from unified_api_contracts import OddsType

        expected = {"h2h", "over_under", "asian_handicap"}
        actual = {m.value for m in OddsType}
        missing = expected - actual
        self.assertEqual(missing, set(), f"OddsType missing expected markets: {missing}")


# ===========================================================================
# Test 8 — UAC CanonicalOrder / CanonicalFill as base classes for sports execution
# ===========================================================================


class TestUACSportsExecutionInheritance(unittest.TestCase):
    """CanonicalSportsOrder / CanonicalSportsFill correctly extend UAC base types."""

    def test_canonical_sports_order_inherits_canonical_order(self) -> None:
        """CanonicalSportsOrder is a subclass of UAC CanonicalOrder."""
        from unified_api_contracts import CanonicalOrder
        from unified_api_contracts.internal.domain.sports.execution import CanonicalSportsOrder

        self.assertTrue(issubclass(CanonicalSportsOrder, CanonicalOrder))

    def test_canonical_sports_order_instantiation(self) -> None:
        """CanonicalSportsOrder can be instantiated with base + sports-specific fields."""
        from unified_api_contracts.internal.domain.sports.execution import CanonicalSportsOrder

        order = CanonicalSportsOrder(
            order_id="sports-ord-001",
            timestamp=datetime.now(UTC),
            venue="betfair",
            instrument_id="1.234567890/12345678",
            side="buy",
            order_type="limit",
            quantity=Decimal("50.00"),
            price=Decimal("2.50"),
            market_id="1.234567890",
            selection_id="12345678",
            bet_side="BACK",
            persistence_type="LAPSE",
            bookmaker_key="betfair",
            decimal_odds=Decimal("2.50"),
        )
        self.assertEqual(order.venue, "betfair")
        self.assertEqual(order.market_id, "1.234567890")
        self.assertEqual(order.bet_side, "BACK")
        self.assertEqual(order.bookmaker_key, "betfair")
        self.assertEqual(order.quantity, Decimal("50.00"))

    def test_canonical_sports_fill_inherits_canonical_fill(self) -> None:
        """CanonicalSportsFill is a subclass of UAC CanonicalFill."""
        from unified_api_contracts import CanonicalFill
        from unified_api_contracts.internal.domain.sports.execution import CanonicalSportsFill

        self.assertTrue(issubclass(CanonicalSportsFill, CanonicalFill))

    def test_canonical_sports_fill_instantiation(self) -> None:
        """CanonicalSportsFill can be instantiated with base + sports-specific fields."""
        from unified_api_contracts.internal.domain.sports.execution import CanonicalSportsFill

        fill = CanonicalSportsFill(
            fill_id="sports-fill-001",
            order_id="sports-ord-001",
            timestamp=datetime.now(UTC),
            venue="betfair",
            instrument_id="1.234567890/12345678",
            side="buy",
            price=Decimal("2.50"),
            quantity=Decimal("50.00"),
            market_id="1.234567890",
            selection_id="12345678",
            bet_id="betfair-bet-00123",
            size_matched=Decimal("50.00"),
            size_remaining=Decimal("0.00"),
            bookmaker_key="betfair",
            decimal_odds_matched=Decimal("2.50"),
        )
        self.assertEqual(fill.venue, "betfair")
        self.assertEqual(fill.bet_id, "betfair-bet-00123")
        self.assertEqual(fill.size_matched, Decimal("50.00"))
        self.assertEqual(fill.size_remaining, Decimal("0.00"))

    def test_canonical_sports_order_polymarket_fields(self) -> None:
        """CanonicalSportsOrder accepts Polymarket-specific fields."""
        from unified_api_contracts.internal.domain.sports.execution import CanonicalSportsOrder

        order = CanonicalSportsOrder(
            order_id="poly-ord-001",
            timestamp=datetime.now(UTC),
            venue="polymarket",
            instrument_id="token-abc123",
            side="buy",
            order_type="limit",
            quantity=Decimal("100.00"),
            price=Decimal("0.65"),
            token_id="token-abc123",
            outcome="Yes",
            bookmaker_key="polymarket",
        )
        self.assertEqual(order.token_id, "token-abc123")
        self.assertEqual(order.outcome, "Yes")

    def test_canonical_sports_order_base_fields_accessible(self) -> None:
        """Base CanonicalOrder fields (order_id, status, time_in_force) are accessible."""
        from unified_api_contracts.internal.domain.sports.execution import CanonicalSportsOrder

        order = CanonicalSportsOrder(
            order_id="sports-ord-002",
            timestamp=datetime.now(UTC),
            venue="pinnacle",
            instrument_id="evt-123/line-456",
            side="buy",
            order_type="limit",
            quantity=Decimal("25.00"),
            price=Decimal("1.95"),
        )
        self.assertEqual(order.order_id, "sports-ord-002")
        self.assertEqual(order.status.value, "pending")  # default from base
        self.assertEqual(order.time_in_force.value, "GTC")  # default from base


# ===========================================================================
# Test 9 — UAC BetStatus used in UIC execution_service sports domain
# ===========================================================================


class TestUACBetStatusInUICExecutionService(unittest.TestCase):
    """BetStatus enum from UAC is used functionally in UIC execution_service."""

    def test_bet_status_enum_members_accessible(self) -> None:
        """All BetStatus enum members can be accessed from UIC re-export."""
        from unified_api_contracts.internal.domain.execution_service.sports import BetStatus

        expected_statuses = {
            "pending",
            "placed",
            "partially_matched",
            "matched",
            "settled_win",
            "settled_loss",
            "settled_void",
            "cancelled",
            "rejected",
        }
        actual = {m.value for m in BetStatus}
        self.assertEqual(actual, expected_statuses)

    def test_sports_bet_result_with_success_status(self) -> None:
        """SportsBetResult.is_success is True for PLACED status."""
        from unified_api_contracts.internal.domain.execution_service.sports import (
            BetStatus,
            SportsBetResult,
        )

        result = SportsBetResult(
            execution_id="exec-001",
            order_id="ord-001",
            bet_id="bet-001",
            status=BetStatus.PLACED,
            bookmaker_key="betfair",
            executed_at_utc=datetime.now(UTC),
            filled_odds=Decimal("2.50"),
            filled_stake=Decimal("100.00"),
        )
        self.assertTrue(result.is_success)
        self.assertFalse(result.is_failed)

    def test_sports_bet_result_with_failure_status(self) -> None:
        """SportsBetResult.is_failed is True for REJECTED status."""
        from unified_api_contracts.internal.domain.execution_service.sports import (
            BetStatus,
            SportsBetResult,
        )

        result = SportsBetResult(
            execution_id="exec-002",
            order_id="ord-002",
            status=BetStatus.REJECTED,
            bookmaker_key="pinnacle",
            executed_at_utc=datetime.now(UTC),
            error_message="Insufficient funds",
        )
        self.assertTrue(result.is_failed)
        self.assertFalse(result.is_success)

    def test_sports_bet_result_matched_status_is_success(self) -> None:
        """SportsBetResult.is_success is True for MATCHED status."""
        from unified_api_contracts.internal.domain.execution_service.sports import (
            BetStatus,
            SportsBetResult,
        )

        result = SportsBetResult(
            execution_id="exec-003",
            order_id="ord-003",
            bet_id="bet-003",
            status=BetStatus.MATCHED,
            bookmaker_key="betfair",
            executed_at_utc=datetime.now(UTC),
            filled_odds=Decimal("1.85"),
            filled_stake=Decimal("50.00"),
        )
        self.assertTrue(result.is_success)

    def test_sports_bet_result_settled_win_is_success(self) -> None:
        """SportsBetResult.is_success is True for SETTLED_WIN status."""
        from unified_api_contracts.internal.domain.execution_service.sports import (
            BetStatus,
            SportsBetResult,
        )

        result = SportsBetResult(
            execution_id="exec-004",
            order_id="ord-004",
            bet_id="bet-004",
            status=BetStatus.SETTLED_WIN,
            bookmaker_key="polymarket",
            executed_at_utc=datetime.now(UTC),
            filled_odds=Decimal("1.60"),
            filled_stake=Decimal("200.00"),
        )
        self.assertTrue(result.is_success)

    def test_sports_bet_result_cancelled_is_failure(self) -> None:
        """SportsBetResult.is_failed is True for CANCELLED status."""
        from unified_api_contracts.internal.domain.execution_service.sports import (
            BetStatus,
            SportsBetResult,
        )

        result = SportsBetResult(
            execution_id="exec-005",
            order_id="ord-005",
            status=BetStatus.CANCELLED,
            bookmaker_key="pinnacle",
            executed_at_utc=datetime.now(UTC),
        )
        self.assertTrue(result.is_failed)
        self.assertFalse(result.is_success)

    def test_sports_bet_result_schema_version_present(self) -> None:
        """SportsBetResult includes schema_version field."""
        from unified_api_contracts.internal.domain.execution_service.sports import (
            BetStatus,
            SportsBetResult,
        )

        result = SportsBetResult(
            execution_id="exec-006",
            order_id="ord-006",
            status=BetStatus.PLACED,
            bookmaker_key="betfair",
            executed_at_utc=datetime.now(UTC),
        )
        self.assertIsInstance(result.schema_version, str)
        self.assertTrue(len(result.schema_version) > 0)

    def test_sports_venue_score_instantiation(self) -> None:
        """SportsVenueScore can be instantiated with all required fields."""
        from unified_api_contracts.internal.domain.execution_service.sports import SportsVenueScore

        score = SportsVenueScore(
            bookmaker_key="betfair",
            margin_score=0.95,
            liquidity_score=0.88,
            latency_score=0.72,
            total_score=0.85,
            expected_margin_pct=1.5,
            is_exchange=True,
        )
        self.assertEqual(score.bookmaker_key, "betfair")
        self.assertTrue(score.is_exchange)
        self.assertAlmostEqual(score.total_score, 0.85)


if __name__ == "__main__":
    unittest.main()
