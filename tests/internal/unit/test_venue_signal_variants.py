"""Tests for G2.9 gap #2 — supported_signal_variants per venue."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ArchetypeInstrumentType,
)
from unified_api_contracts.internal.architecture_v2.venue_signal_variants import (
    CONSUMER_CALL_SITES,
    VENUE_SIGNAL_VARIANT_REGISTRY,
    SignalVariant,
    VenueInstrumentNotRegisteredError,
    VenueInstrumentSignalSupport,
    _validate_registry_invariants,
    signal_variants_for,
    venue_supports_variant,
    venues_supporting,
)


class TestRegistryShape:
    def test_registry_not_empty(self) -> None:
        assert len(VENUE_SIGNAL_VARIANT_REGISTRY) >= 10

    def test_all_rows_unique_venue_instrument(self) -> None:
        keys = [(e.venue_id, e.instrument_type) for e in VENUE_SIGNAL_VARIANT_REGISTRY]
        assert len(keys) == len(set(keys))

    def test_all_rows_non_empty_variants(self) -> None:
        for entry in VENUE_SIGNAL_VARIANT_REGISTRY:
            assert entry.supported_signal_variants, f"empty variants on {entry.venue_id}"


class TestContent:
    def test_binance_perp_supports_funding_rate(self) -> None:
        variants = signal_variants_for("binance", ArchetypeInstrumentType.PERP)
        assert SignalVariant.FUNDING_RATE in variants
        assert SignalVariant.PRICE in variants
        assert SignalVariant.BASIS in variants

    def test_coinbase_spot_only_price(self) -> None:
        variants = signal_variants_for("coinbase", ArchetypeInstrumentType.SPOT)
        assert variants == frozenset({SignalVariant.PRICE})

    def test_deribit_option_supports_iv_dispersion(self) -> None:
        variants = signal_variants_for("deribit", ArchetypeInstrumentType.OPTION)
        assert SignalVariant.IV_DISPERSION in variants
        assert SignalVariant.VOL_METRIC in variants

    def test_aave_lending_supports_liquidation_bonus(self) -> None:
        variants = signal_variants_for("aave", ArchetypeInstrumentType.LENDING)
        assert SignalVariant.LIQUIDATION_BONUS in variants
        assert SignalVariant.RATE_SPREAD in variants

    def test_betfair_event_settled_supports_odds(self) -> None:
        variants = signal_variants_for("betfair", ArchetypeInstrumentType.EVENT_SETTLED)
        assert SignalVariant.ODDS in variants


class TestHelpers:
    def test_unknown_venue_instrument_raises(self) -> None:
        with pytest.raises(VenueInstrumentNotRegisteredError):
            signal_variants_for("nonexistent", ArchetypeInstrumentType.SPOT)

    def test_venue_supports_variant_true(self) -> None:
        assert venue_supports_variant(
            "binance",
            ArchetypeInstrumentType.PERP,
            SignalVariant.FUNDING_RATE,
        )

    def test_venue_supports_variant_false_wrong_variant(self) -> None:
        assert not venue_supports_variant(
            "coinbase",
            ArchetypeInstrumentType.SPOT,
            SignalVariant.FUNDING_RATE,
        )

    def test_venue_supports_variant_false_unknown_venue(self) -> None:
        # Silent-on-unknown semantics.
        assert not venue_supports_variant(
            "nonexistent",
            ArchetypeInstrumentType.SPOT,
            SignalVariant.PRICE,
        )

    def test_venues_supporting_funding_rate(self) -> None:
        results = venues_supporting(SignalVariant.FUNDING_RATE)
        ids = {e.venue_id for e in results}
        assert "binance" in ids
        assert "hyperliquid" in ids
        assert "coinbase" not in ids

    def test_venues_supporting_filter_by_instrument(self) -> None:
        results = venues_supporting(
            SignalVariant.PRICE,
            instrument_type=ArchetypeInstrumentType.SPOT,
        )
        ids = {e.venue_id for e in results}
        assert "binance" in ids
        assert "coinbase" in ids
        # Perp-supporting venues shouldn't show up under spot filter.
        for entry in results:
            assert entry.instrument_type == ArchetypeInstrumentType.SPOT


class TestInvariants:
    def test_duplicate_venue_instrument_pair_rejected(self) -> None:
        bad = (
            VenueInstrumentSignalSupport(
                venue_id="dup",
                instrument_type=ArchetypeInstrumentType.SPOT,
                supported_signal_variants=frozenset({SignalVariant.PRICE}),
            ),
            VenueInstrumentSignalSupport(
                venue_id="dup",
                instrument_type=ArchetypeInstrumentType.SPOT,
                supported_signal_variants=frozenset({SignalVariant.PRICE, SignalVariant.BASIS}),
            ),
        )
        with pytest.raises(ValueError, match="duplicate"):
            _validate_registry_invariants(bad)

    def test_empty_variants_rejected(self) -> None:
        bad = (
            VenueInstrumentSignalSupport(
                venue_id="empty",
                instrument_type=ArchetypeInstrumentType.SPOT,
                supported_signal_variants=frozenset(),
            ),
        )
        with pytest.raises(ValueError, match="non-empty"):
            _validate_registry_invariants(bad)

    def test_entry_is_frozen(self) -> None:
        entry = VENUE_SIGNAL_VARIANT_REGISTRY[0]
        with pytest.raises(ValidationError):
            entry.venue_id = "mutated"  # type: ignore[misc]


class TestConsumerReferences:
    def test_consumer_call_sites_non_empty(self) -> None:
        assert len(CONSUMER_CALL_SITES) >= 1
