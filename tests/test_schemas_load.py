"""Test that schema modules load and example validation works."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

# Import schema modules to ensure they load


def test_prediction_market_arb_schemas() -> None:
    """Test CrossVenueLink, ProbabilityBucket, BucketMarket, SportsbookLink, NegRiskArbSignal."""
    from unified_api_contracts.schemas.prediction_market_arb import (
        BucketMarket,
        CrossVenueLink,
        NegRiskArbSignal,
        NegRiskBucket,
        ProbabilityBucket,
        SportsbookLink,
    )

    # CrossVenueLink
    link = CrossVenueLink(
        venue_a="kalshi",
        market_id_a="KXCPI-24DEC-T3.2",
        venue_b="polymarket",
        market_id_b="0x123",
        link_type="equivalent",
        basis_bps=500.0,
        verified_by="structured_match",
        created_at=datetime.now(UTC),
    )
    assert link.venue_a == "kalshi"
    assert link.basis_bps == 500.0

    # BucketMarket and ProbabilityBucket
    bucket = BucketMarket(
        market_id="pm-1",
        lower_bound=2600.0,
        upper_bound=2800.0,
        yes_bid=0.07,
        yes_ask=0.08,
    )
    pb = ProbabilityBucket(
        group_id="gold-june",
        underlying="GOLD_JUNE_2025",
        expiry="2025-06-30",
        venue="polymarket",
        buckets=[bucket],
    )
    assert len(pb.buckets) == 1
    assert pb.buckets[0].yes_ask == Decimal("0.08")

    # SportsbookLink
    sl = SportsbookLink(
        polymarket_market_id="0xabc",
        sportsbook="pinnacle",
        sportsbook_event_id="ev-1",
        sportsbook_market_type="moneyline",
        sportsbook_implied_prob=0.62,
        polymarket_yes_mid=0.38,
        discrepancy_bps=2400.0,
        captured_at=datetime.now(UTC),
    )
    assert sl.discrepancy_bps == 2400.0

    # NegRiskArbSignal with new fields
    signal = NegRiskArbSignal(
        neg_risk_market_id="nr-1",
        underlying="GOLD_JUN2025",
        expiry="2025-06-30",
        venue="polymarket",
        buckets=[
            NegRiskBucket(label="Gold above $3200", yes_ask=0.31),
            NegRiskBucket(label="Gold $3000-$3200", yes_ask=0.29),
        ],
        sum_of_asks=0.94,
        implied_profit_pct=6.0,
        bucket_markets=["cond-1", "cond-2"],
        yes_ask_sum=0.94,
        no_bid_sum=0.06,
        arb_bps=600.0,
        capital_required_usdc=1000.0,
        expected_profit_usdc=60.0,
    )
    assert signal.arb_bps == 600.0
    assert signal.expected_profit_usdc == 60.0


def test_databento_ohlcv_bar_schema() -> None:
    from unified_api_contracts.databento.schemas import DatabentoOhlcvBar

    example = {
        "ts_event": 1609459200000000000,
        "rtype": 32,
        "publisher_id": 1,
        "instrument_id": 12345,
        "open": 5000000000000,
        "high": 5010000000000,
        "low": 4990000000000,
        "close": 5005000000000,
        "volume": 1000,
    }
    bar = DatabentoOhlcvBar.model_validate(example)
    assert bar.close == 5005000000000
    assert bar.volume == 1000


def test_ccxt_order_schema() -> None:
    from unified_api_contracts.ccxt.schemas import CcxtOrder

    example = {
        "id": "order-123",
        "clientOrderId": "client-456",
        "timestamp": 1609459200000,
        "symbol": "BTC/USDT",
        "type": "limit",
        "side": "buy",
        "price": 50000.0,
        "amount": 0.01,
        "filled": 0.0,
        "remaining": 0.01,
        "status": "open",
        "timeInForce": "GTC",
    }
    order = CcxtOrder.model_validate(example)
    assert order.id == "order-123"
    assert order.side == "buy"


def test_validate_examples_if_present() -> None:
    """Validate all JSON files under api_contracts/*/examples/ with the matching schema if we have a loader."""
    root = Path(__file__).resolve().parent.parent / "unified_api_contracts"
    if not root.exists():
        pytest.skip("api_contracts package not found")

    validated = 0
    for api_dir in root.iterdir():
        if not api_dir.is_dir():
            continue
        examples_dir = api_dir / "examples"
        if examples_dir.exists():
            for path in examples_dir.glob("*.json"):
                data = json.loads(path.read_text())
                if api_dir.name == "databento" and "ts_event" in data and "close" in data:
                    from unified_api_contracts.databento.schemas import DatabentoOhlcvBar

                    DatabentoOhlcvBar.model_validate(data)
                    validated += 1
                elif api_dir.name == "ccxt" and "id" in data and "symbol" in data:
                    from unified_api_contracts.ccxt.schemas import CcxtOrder

                    CcxtOrder.model_validate(data)
                    validated += 1
        elif api_dir.name == "unified_api_contracts_external":
            for vendor_dir in api_dir.iterdir():
                if not vendor_dir.is_dir():
                    continue
                vendor_examples_dir = vendor_dir / "examples"
                if vendor_examples_dir.exists():
                    for path in vendor_examples_dir.glob("*.json"):
                        data = json.loads(path.read_text())
                        if vendor_dir.name == "databento" and "ts_event" in data and "close" in data:
                            from unified_api_contracts.databento.schemas import DatabentoOhlcvBar

                            DatabentoOhlcvBar.model_validate(data)
                            validated += 1
                        elif vendor_dir.name == "ccxt" and "id" in data and "symbol" in data:
                            from unified_api_contracts.ccxt.schemas import CcxtOrder

                            CcxtOrder.model_validate(data)
                            validated += 1
    assert validated >= 1, "At least one example should validate"
