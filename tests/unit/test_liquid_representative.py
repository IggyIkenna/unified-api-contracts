"""Unit tests for
:mod:`unified_api_contracts.canonical.crosscutting.liquid_representative`.

Covers item 003 of
``plans/active/mvp_for_mdps_and_features_universe_uac_2026_06_28.md``:
``execution_spot_representative(base, asset_group, venue_volumes)`` —
returns a single ``(venue, instrument)`` for the most-liquid SPOT
representative of ``base`` in ``asset_group``, chosen by measured volume
with a deterministic tie-break.
"""

from __future__ import annotations

import pytest

# Public import surface — must reach the top-level facade.
from unified_api_contracts import (
    VenueVolumeObservation,
    execution_spot_representative,
)


def _obs(
    venue: str,
    instrument: str,
    instrument_type: str,
    base: str,
    volume: float,
) -> VenueVolumeObservation:
    return VenueVolumeObservation(
        venue=venue,
        instrument=instrument,
        instrument_type=instrument_type,
        base=base,
        volume=volume,
    )


class TestPublicSurface:
    def test_importable_from_package_root(self) -> None:
        import unified_api_contracts

        assert hasattr(unified_api_contracts, "execution_spot_representative")
        assert hasattr(unified_api_contracts, "VenueVolumeObservation")
        assert "execution_spot_representative" in unified_api_contracts.__all__
        assert "VenueVolumeObservation" in unified_api_contracts.__all__

    def test_observation_is_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        obs = _obs("BINANCE-SPOT", "BTCUSDT", "SPOT_PAIR", "BTC", 1.0)
        with pytest.raises(FrozenInstanceError):
            obs.volume = 2.0  # pyright: ignore[reportAttributeAccessIssue]  # frozen dataclass — assignment forbidden


class TestSelectionBasic:
    def test_picks_highest_volume(self) -> None:
        observations = [
            _obs("BINANCE-SPOT", "BTCUSDT", "SPOT_PAIR", "BTC", 5_000_000_000.0),
            _obs("COINBASE-SPOT", "BTC-USD", "SPOT_PAIR", "BTC", 800_000_000.0),
            _obs("KRAKEN-SPOT", "XBT/USD", "SPOT_PAIR", "BTC", 200_000_000.0),
        ]
        assert execution_spot_representative("BTC", "cefi", observations) == (
            "BINANCE-SPOT",
            "BTCUSDT",
        )

    def test_returns_tuple_of_strings(self) -> None:
        observations = [_obs("BINANCE-SPOT", "BTCUSDT", "SPOT_PAIR", "BTC", 1.0)]
        result = execution_spot_representative("BTC", "cefi", observations)
        assert result is not None
        venue, instrument = result
        assert isinstance(venue, str)
        assert isinstance(instrument, str)

    def test_returns_none_when_no_observations(self) -> None:
        assert execution_spot_representative("BTC", "cefi", []) is None

    def test_returns_none_when_base_does_not_match(self) -> None:
        observations = [
            _obs("BINANCE-SPOT", "ETHUSDT", "SPOT_PAIR", "ETH", 1.0),
        ]
        assert execution_spot_representative("BTC", "cefi", observations) is None


class TestFiltering:
    def test_excludes_non_spot_instrument_types_for_cefi(self) -> None:
        """A PERPETUAL observation must NEVER be picked by the SPOT selector,
        even if it has the highest volume (perps usually dominate perps-vs-spot
        but execution wants the spot leg)."""
        observations = [
            _obs(
                "BINANCE-FUTURES", "BTCUSDT", "PERPETUAL", "BTC", 50_000_000_000.0
            ),
            _obs("COINBASE-SPOT", "BTC-USD", "SPOT_PAIR", "BTC", 800_000_000.0),
        ]
        assert execution_spot_representative("BTC", "cefi", observations) == (
            "COINBASE-SPOT",
            "BTC-USD",
        )

    def test_excludes_venue_not_in_mvp_scope(self) -> None:
        """A SPOT venue that is NOT declared in MVP_SCOPE['cefi'].venues
        (e.g. an unsupported CEX) is excluded — execution will only route to
        venues we've MVP-scoped."""
        observations = [
            _obs(
                "MEXC-SPOT",  # NOT in cefi MVP venues
                "BTCUSDT",
                "SPOT_PAIR",
                "BTC",
                10_000_000_000.0,
            ),
            _obs("BINANCE-SPOT", "BTCUSDT", "SPOT_PAIR", "BTC", 1.0),
        ]
        assert execution_spot_representative("BTC", "cefi", observations) == (
            "BINANCE-SPOT",
            "BTCUSDT",
        )

    def test_filters_other_bases_out(self) -> None:
        observations = [
            _obs("BINANCE-SPOT", "ETHUSDT", "SPOT_PAIR", "ETH", 999_999_999.0),
            _obs("BINANCE-SPOT", "BTCUSDT", "SPOT_PAIR", "BTC", 1.0),
        ]
        assert execution_spot_representative("BTC", "cefi", observations) == (
            "BINANCE-SPOT",
            "BTCUSDT",
        )


class TestDeterministicTieBreak:
    def test_ties_break_on_venue_ascending(self) -> None:
        """Equal volume → venue ASC. ``BINANCE-SPOT`` < ``COINBASE-SPOT``
        lexicographically, so Binance wins."""
        observations = [
            _obs("COINBASE-SPOT", "BTC-USD", "SPOT_PAIR", "BTC", 1.0),
            _obs("BINANCE-SPOT", "BTCUSDT", "SPOT_PAIR", "BTC", 1.0),
        ]
        assert execution_spot_representative("BTC", "cefi", observations) == (
            "BINANCE-SPOT",
            "BTCUSDT",
        )

    def test_ties_break_on_instrument_when_venue_equal(self) -> None:
        """Same venue + same volume → instrument ASC. ``BTC-USD`` <
        ``BTC-USDT`` lexicographically."""
        observations = [
            _obs("BINANCE-SPOT", "BTC-USDT", "SPOT_PAIR", "BTC", 1.0),
            _obs("BINANCE-SPOT", "BTC-USD", "SPOT_PAIR", "BTC", 1.0),
        ]
        assert execution_spot_representative("BTC", "cefi", observations) == (
            "BINANCE-SPOT",
            "BTC-USD",
        )

    def test_selection_is_stable_across_input_order(self) -> None:
        """Same observations passed in either order MUST select the same rep
        — the function must not depend on iteration order of the input."""
        a = _obs("BINANCE-SPOT", "BTCUSDT", "SPOT_PAIR", "BTC", 100.0)
        b = _obs("COINBASE-SPOT", "BTC-USD", "SPOT_PAIR", "BTC", 100.0)
        assert execution_spot_representative("BTC", "cefi", [a, b]) == (
            execution_spot_representative("BTC", "cefi", [b, a])
        )


class TestTradFi:
    def test_picks_equity_basis_carve_out_for_tradfi(self) -> None:
        """TradFi spot rep = the cash equity / ETF twin (the equity-basis
        carve-out's basis leg). NASDAQ/NYSE/ARCA/... × {EQUITY, ETF} cells
        are in mdps_mvp_universe('tradfi')."""
        observations = [
            _obs("NASDAQ", "AAPL", "EQUITY", "AAPL", 1_000_000.0),
            _obs("ARCA", "SPY", "ETF", "AAPL", 500_000.0),
        ]
        assert execution_spot_representative(
            "AAPL", "tradfi", observations
        ) == ("NASDAQ", "AAPL")

    def test_cme_future_not_selected_as_spot_for_tradfi(self) -> None:
        """CME FUTURE must not be selected as a SPOT representative — for
        tradfi the spot leg is the cash equity, not the futures leg."""
        observations = [
            _obs("CME", "ESM5", "FUTURE", "ES", 50_000_000.0),
            _obs("NASDAQ", "SPY", "ETF", "ES", 1.0),
        ]
        # Note: ES doesn't have a literal NASDAQ ticker but the test only
        # cares that the FUTURE is filtered out and the ETF wins.
        assert execution_spot_representative("ES", "tradfi", observations) == (
            "NASDAQ",
            "SPY",
        )


class TestDeFi:
    def test_picks_dex_pool_for_defi(self) -> None:
        """DeFi spot rep = the DEX pool (POOL or DEX_POOL)."""
        observations = [
            _obs("UNISWAP_V3-ETHEREUM", "ETH-USDC", "POOL", "ETH", 100.0),
            _obs("CURVE-ETHEREUM", "ETH-USDT", "POOL", "ETH", 50.0),
        ]
        assert execution_spot_representative("ETH", "defi", observations) == (
            "UNISWAP_V3-ETHEREUM",
            "ETH-USDC",
        )


class TestUnsupportedAssetGroups:
    @pytest.mark.parametrize("ag", ["sports", "prediction"])
    def test_raises_for_non_market_data_asset_groups(self, ag: str) -> None:
        with pytest.raises(ValueError, match="no spot-execution representative"):
            execution_spot_representative("FOO", ag, [])

    def test_raises_for_unknown_asset_group(self) -> None:
        with pytest.raises(ValueError, match="no spot-execution representative"):
            execution_spot_representative("FOO", "not-an-asset-group", [])


class TestPurity:
    def test_does_not_mutate_input(self) -> None:
        observations = [
            _obs("BINANCE-SPOT", "BTCUSDT", "SPOT_PAIR", "BTC", 1.0),
            _obs("COINBASE-SPOT", "BTC-USD", "SPOT_PAIR", "BTC", 2.0),
        ]
        snapshot = list(observations)
        execution_spot_representative("BTC", "cefi", observations)
        assert observations == snapshot

    def test_accepts_generator(self) -> None:
        from collections.abc import Iterator

        def gen() -> Iterator[VenueVolumeObservation]:
            yield _obs("BINANCE-SPOT", "BTCUSDT", "SPOT_PAIR", "BTC", 1.0)
            yield _obs("COINBASE-SPOT", "BTC-USD", "SPOT_PAIR", "BTC", 2.0)

        assert execution_spot_representative("BTC", "cefi", gen()) == (
            "COINBASE-SPOT",
            "BTC-USD",
        )
