"""Write-time guardrail: any `*-PERP` venue record must be genuinely PERPETUAL.

Pins the fix for prediction_satellite_ao_dispatch_batch1_2026_07_25.md's todo:
closes the class of bug that let the KALSHI-PERP adapter's category-filter gap
contaminate cefi with 25,473 fake PERPETUAL rows (binary event contracts, e.g.
KXMVESPORTSMULTIGAMEEXTENDED / KXMVECROSSCATEGORY*, silently accepted as
PERPETUAL). Covers both halves of the guardrail: the declared instrument_type
must be PERPETUAL, and the ticker itself must not match a known event-contract
naming pattern even if mislabeled PERPETUAL.
"""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.internal.reference.instrument import InstrumentRecord, InstrumentType
from unified_api_contracts.internal.reference.instrument_validation import validate_instrument_records


def _kalshi_perp_record(**overrides: object) -> InstrumentRecord:
    """Minimal valid KALSHI-PERP PERPETUAL record — passes every OTHER check."""
    kwargs: dict[str, object] = {
        "instrument_key": "KXBTCUSD-PERP",
        "canonical_instrument_id": "KXBTCUSD-PERP",
        "venue": "KALSHI-PERP",
        "raw_symbol": "KXBTCUSD-PERP",
        "instrument_type": InstrumentType.PERPETUAL,
        "base_asset": "BTC",
        "quote_asset": "USD",
        "tick_size": Decimal("0.01"),
    }
    kwargs.update(overrides)
    return InstrumentRecord(**kwargs)  # type: ignore[arg-type]


def _assert_rejected(records: list[InstrumentRecord], expected_fragment: str) -> None:
    valid, rejected = validate_instrument_records(records)
    assert len(valid) == 0, f"Expected all rejected, got valid={valid}"
    assert len(rejected) == 1
    _, reason = rejected[0]
    assert expected_fragment in reason, f"Expected {expected_fragment!r} in reason {reason!r}"


def _assert_passes(records: list[InstrumentRecord]) -> None:
    valid, rejected = validate_instrument_records(records)
    assert len(rejected) == 0, f"Expected no rejections, got {rejected}"
    assert len(valid) == len(records)


class TestPerpVenueInstrumentTypeGuardrail:
    def test_genuine_perpetual_on_perp_venue_passes(self) -> None:
        _assert_passes([_kalshi_perp_record()])

    def test_non_perpetual_instrument_type_on_perp_venue_rejected(self) -> None:
        # The exact contamination shape: a binary event contract mis-tagged with
        # a non-PERPETUAL-looking ticker but written to a *-PERP venue.
        rec = _kalshi_perp_record(
            instrument_type=InstrumentType.SPOT_PAIR,
            instrument_key="SOMETHING-ELSE",
            raw_symbol="SOMETHING-ELSE",
        )
        _assert_rejected([rec], "must be instrument_type=PERPETUAL")


class TestPerpVenueEventContractTickerGuardrail:
    def test_event_contract_ticker_rejected_even_if_labeled_perpetual(self) -> None:
        # The REAL incident shape: instrument_type says PERPETUAL (adapter bug
        # mislabeled it) but the ticker itself is a Kalshi binary event contract.
        rec = _kalshi_perp_record(
            instrument_key="KXMVESPORTSMULTIGAMEEXTENDED",
            raw_symbol="KXMVESPORTSMULTIGAMEEXTENDED",
        )
        _assert_rejected([rec], "matches a known event-contract naming pattern")

    def test_kxmvecrosscategory_ticker_rejected(self) -> None:
        rec = _kalshi_perp_record(
            instrument_key="KXMVECROSSCATEGORY",
            raw_symbol="KXMVECROSSCATEGORY",
        )
        _assert_rejected([rec], "matches a known event-contract naming pattern")

    def test_real_kx_prefixed_perp_ticker_not_caught_by_broad_kx_match(self) -> None:
        # KXBTCUSD-PERP starts with "KX" but NOT "KXMVE" — must NOT be rejected;
        # a broad "KX" prefix match would incorrectly reject genuine perp tickers.
        _assert_passes([_kalshi_perp_record(instrument_key="KXBTCUSD-PERP", raw_symbol="KXBTCUSD-PERP")])


class TestNonPerpVenueUnaffected:
    def test_non_perp_venue_skips_the_guardrail_entirely(self) -> None:
        # A CeFi venue with no "-PERP" suffix (e.g. BINANCE-FUTURES) must be
        # entirely unaffected by this guardrail, even for a non-PERPETUAL type.
        rec = InstrumentRecord(
            instrument_key="BINANCE-FUTURES:SPOT_PAIR:BTCUSDT",
            canonical_instrument_id="BINANCE-FUTURES:SPOT_PAIR:BTCUSDT",
            venue="BINANCE-FUTURES",
            raw_symbol="BTCUSDT",
            instrument_type=InstrumentType.SPOT_PAIR,
            base_asset="BTC",
            quote_asset="USDT",
            tick_size=Decimal("0.01"),
        )  # type: ignore[arg-type]
        _assert_passes([rec])
