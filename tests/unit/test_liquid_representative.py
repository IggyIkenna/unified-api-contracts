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
    feature_perp_representative,
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


# ---------------------------------------------------------------------------
# feature_perp_representative — item 002. Same shared VenueVolumeObservation
# basis + deterministic (venue ASC, instrument ASC) tie-break as the spot
# selector; per-AG filter switches to PERP-class instrument_types (PERPETUAL /
# EQUITY_PERP for cefi, FUTURE for tradfi-no-perp).
# ---------------------------------------------------------------------------


class TestPerpPublicSurface:
    def test_importable_from_package_root(self) -> None:
        import unified_api_contracts

        assert hasattr(unified_api_contracts, "feature_perp_representative")
        assert "feature_perp_representative" in unified_api_contracts.__all__


class TestPerpSelectionCefi:
    def test_btc_picks_highest_volume_perp(self) -> None:
        """Highest measured volume wins — Binance-Futures usually but BY VOLUME."""
        observations = [
            _obs("BINANCE-FUTURES", "BTC-USDT", "PERPETUAL", "BTC", 12_500_000_000.0),
            _obs("BYBIT", "BTC-USDT", "PERPETUAL", "BTC", 4_200_000_000.0),
            _obs("OKX-SWAP", "BTC-USDT-SWAP", "PERPETUAL", "BTC", 3_100_000_000.0),
        ]
        assert feature_perp_representative("BTC", "cefi", observations) == (
            "BINANCE-FUTURES",
            "BTC-USDT",
        )

    def test_volume_is_the_rule_not_venue_hardcode(self) -> None:
        """If BYBIT happens to lead on volume, BYBIT wins — selection is by volume."""
        observations = [
            _obs("BINANCE-FUTURES", "ETH-USDT", "PERPETUAL", "ETH", 1_000_000_000.0),
            _obs("BYBIT", "ETH-USDT", "PERPETUAL", "ETH", 9_000_000_000.0),
        ]
        assert feature_perp_representative("ETH", "cefi", observations) == (
            "BYBIT",
            "ETH-USDT",
        )

    def test_equity_perp_also_eligible(self) -> None:
        """EQUITY_PERP (tokenized-stock perps) is also a delta-one feature instrument."""
        observations = [
            _obs("BYBIT", "AAPLPERP", "EQUITY_PERP", "AAPL", 5_000_000.0),
            _obs("OKX-SWAP", "AAPL-PERP", "EQUITY_PERP", "AAPL", 3_000_000.0),
        ]
        assert feature_perp_representative("AAPL", "cefi", observations) == (
            "BYBIT",
            "AAPLPERP",
        )

    def test_spot_filtered_out_for_features(self) -> None:
        """SPOT_PAIR cells are ignored — features run on the PERP representative only."""
        observations = [
            # Spot has higher volume but is filtered out — features use perps.
            _obs("BINANCE-SPOT", "BTCUSDT", "SPOT_PAIR", "BTC", 20_000_000_000.0),
            _obs("BINANCE-FUTURES", "BTC-USDT", "PERPETUAL", "BTC", 12_500_000_000.0),
        ]
        assert feature_perp_representative("BTC", "cefi", observations) == (
            "BINANCE-FUTURES",
            "BTC-USDT",
        )

    def test_excludes_venue_not_in_mvp_scope(self) -> None:
        """A perp venue NOT in MVP_SCOPE['cefi'].venues is dropped even with leading volume."""
        observations = [
            # MEXC-FUTURES not in cefi MVP — must be excluded.
            _obs("MEXC-FUTURES", "BTC-USDT", "PERPETUAL", "BTC", 99_999_999_999.0),
            _obs("BINANCE-FUTURES", "BTC-USDT", "PERPETUAL", "BTC", 1.0),
        ]
        assert feature_perp_representative("BTC", "cefi", observations) == (
            "BINANCE-FUTURES",
            "BTC-USDT",
        )

    def test_no_perp_returns_none(self) -> None:
        """A base with NO perp candidates returns None — fail-loud, no silent default."""
        observations = [
            _obs("BINANCE-SPOT", "BTCUSDT", "SPOT_PAIR", "BTC", 1_000_000.0),
        ]
        assert feature_perp_representative("BTC", "cefi", observations) is None

    def test_empty_returns_none(self) -> None:
        assert feature_perp_representative("BTC", "cefi", []) is None

    def test_other_bases_dropped(self) -> None:
        observations = [
            _obs("BINANCE-FUTURES", "ETH-USDT", "PERPETUAL", "ETH", 99_999_999_999.0),
            _obs("BYBIT", "BTC-USDT", "PERPETUAL", "BTC", 42.0),
        ]
        assert feature_perp_representative("BTC", "cefi", observations) == (
            "BYBIT",
            "BTC-USDT",
        )


class TestPerpDeterministicTieBreak:
    def test_ties_break_on_venue_ascending(self) -> None:
        """Equal volume → venue ASC — same rule as the spot selector."""
        observations = [
            _obs("BYBIT", "SOL-USDT", "PERPETUAL", "SOL", 1.0),
            _obs("BINANCE-FUTURES", "SOL-USDT", "PERPETUAL", "SOL", 1.0),
        ]
        assert feature_perp_representative("SOL", "cefi", observations) == (
            "BINANCE-FUTURES",
            "SOL-USDT",
        )

    def test_ties_break_on_instrument_when_venue_equal(self) -> None:
        observations = [
            _obs("BINANCE-FUTURES", "BTC-USDT", "PERPETUAL", "BTC", 1.0),
            _obs("BINANCE-FUTURES", "BTC-BUSD", "PERPETUAL", "BTC", 1.0),
        ]
        assert feature_perp_representative("BTC", "cefi", observations) == (
            "BINANCE-FUTURES",
            "BTC-BUSD",
        )

    def test_selection_is_stable_across_input_order(self) -> None:
        a = _obs("BINANCE-FUTURES", "BTC-USDT", "PERPETUAL", "BTC", 100.0)
        b = _obs("BYBIT", "BTC-USDT", "PERPETUAL", "BTC", 100.0)
        assert feature_perp_representative("BTC", "cefi", [a, b]) == feature_perp_representative(
            "BTC", "cefi", [b, a]
        )


class TestPerpTradFi:
    def test_tradfi_picks_most_liquid_future(self) -> None:
        """TradFi has no perp — the perp representative is the most-liquid FUTURE source."""
        observations = [
            _obs("CME", "ESH26", "FUTURE", "ES", 80_000_000_000.0),
            _obs("CME", "ESM26", "FUTURE", "ES", 5_000_000_000.0),
        ]
        assert feature_perp_representative("ES", "tradfi", observations) == (
            "CME",
            "ESH26",
        )

    def test_tradfi_excludes_option(self) -> None:
        """CME OPTION rows are ignored — delta-one features do not run on options."""
        observations = [
            _obs("CME", "ES H26 5500 C", "OPTION", "ES", 10_000_000_000.0),
            _obs("CME", "ESH26", "FUTURE", "ES", 1_000.0),
        ]
        assert feature_perp_representative("ES", "tradfi", observations) == (
            "CME",
            "ESH26",
        )

    def test_tradfi_empty_returns_none(self) -> None:
        assert feature_perp_representative("ES", "tradfi", []) is None


class TestPerpUnsupportedAssetGroups:
    @pytest.mark.parametrize("ag", ["defi", "sports", "prediction"])
    def test_unsupported_raises(self, ag: str) -> None:
        with pytest.raises(ValueError, match=r"asset_group .* not supported"):
            feature_perp_representative("BTC", ag, [])

    def test_unknown_asset_group_raises(self) -> None:
        with pytest.raises(ValueError, match=r"asset_group .* not supported"):
            feature_perp_representative("BTC", "not-a-group", [])


class TestPerpPurity:
    def test_does_not_mutate_input(self) -> None:
        observations = [
            _obs("BINANCE-FUTURES", "BTC-USDT", "PERPETUAL", "BTC", 1.0),
            _obs("BYBIT", "BTC-USDT", "PERPETUAL", "BTC", 2.0),
        ]
        snapshot = list(observations)
        feature_perp_representative("BTC", "cefi", observations)
        assert observations == snapshot

    def test_accepts_generator(self) -> None:
        from collections.abc import Iterator

        def gen() -> Iterator[VenueVolumeObservation]:
            yield _obs("BINANCE-FUTURES", "BTC-USDT", "PERPETUAL", "BTC", 1.0)
            yield _obs("BYBIT", "BTC-USDT", "PERPETUAL", "BTC", 2.0)

        assert feature_perp_representative("BTC", "cefi", gen()) == (
            "BYBIT",
            "BTC-USDT",
        )


# ---------------------------------------------------------------------------
# Plan item 005 — cross-AG matrix
#
# One consolidated class that exercises the delta-one perp-representative
# contract across ALL FIVE asset_groups declared in MVP_SCOPE
# (cefi / defi / tradfi / sports / prediction), so the gate
# "options/futures excluded from delta-one; non-CeFi pass-through behaviour
# decided + tested; perp chosen by measured volume not venue hardcode;
# tie-breaks deterministically" is readable as one test class instead of
# scattered across the per-AG suites above.
# ---------------------------------------------------------------------------


class TestFiveAssetGroupDeltaOneMatrix:
    """Cross-AG matrix for the delta-one perp representative contract.

    Each row in the MVP-for-features universe (plan
    ``mvp_for_mdps_and_features_universe_uac_2026_06_28.md``, Concept 2)
    asserts one of:

    * ``cefi`` / ``tradfi`` — delta-one IS supported; the selector returns
      a ``(venue, instrument)`` for an in-MVP perp/future observation, and
      filters non-linear types (OPTION, dated FUTURE in cefi) out even when
      their volume dwarfs the legitimate representative.
    * ``defi`` / ``sports`` / ``prediction`` — delta-one is NOT supported
      via this selector; the function raises so callers don't silently get
      ``None`` and proceed without a representative.
    """

    @pytest.mark.parametrize(
        ("asset_group", "supported"),
        [
            ("cefi", True),
            ("tradfi", True),
            ("defi", False),
            ("sports", False),
            ("prediction", False),
        ],
    )
    def test_delta_one_support_per_asset_group(self, asset_group: str, supported: bool) -> None:
        """The supported / unsupported split is the AG contract — supported
        AGs accept the selector call (returning ``None`` for empty input is
        the "no rep available" path, not a rejection); unsupported AGs raise."""
        if supported:
            assert feature_perp_representative("BTC", asset_group, []) is None
        else:
            with pytest.raises(ValueError, match=r"asset_group .* not supported"):
                feature_perp_representative("BTC", asset_group, [])

    def test_cefi_excludes_option_even_with_dominant_volume(self) -> None:
        """cefi: ``(DERIBIT, OPTION)`` is in MVP_SCOPE, but the perp filter
        only admits ``PERPETUAL`` / ``EQUITY_PERP`` — so a DERIBIT OPTION row
        with overwhelming volume is dropped and the PERPETUAL leg wins.
        Delta-one features do not run on options."""
        observations = [
            _obs("DERIBIT", "BTC-27JUN26-50000-C", "OPTION", "BTC", 9_999_999_999.0),
            _obs("BINANCE-FUTURES", "BTC-USDT", "PERPETUAL", "BTC", 1.0),
        ]
        assert feature_perp_representative("BTC", "cefi", observations) == (
            "BINANCE-FUTURES",
            "BTC-USDT",
        )

    def test_cefi_excludes_dated_future_even_with_dominant_volume(self) -> None:
        """cefi: dated ``FUTURE`` instruments (term-structure leg) are
        excluded from delta-one — that family is ``futures_basis``, not the
        delta-one rep. The PERPETUAL leg wins regardless of volume."""
        observations = [
            _obs("BINANCE-FUTURES", "BTC-USD_MAR26", "FUTURE", "BTC", 9_999_999_999.0),
            _obs("BINANCE-FUTURES", "BTC-USDT", "PERPETUAL", "BTC", 1.0),
        ]
        assert feature_perp_representative("BTC", "cefi", observations) == (
            "BINANCE-FUTURES",
            "BTC-USDT",
        )

    def test_tradfi_excludes_option_picks_future_rep(self) -> None:
        """tradfi: no perpetual exists, so ``FUTURE`` IS the delta-one rep
        (the non-CeFi pass-through decision — TradFi reps are chosen, not
        skipped). ``OPTION`` is still excluded: delta-one features do not
        run on options regardless of AG."""
        observations = [
            _obs("CME", "ESH26-5500-C", "OPTION", "ES", 9_999_999_999.0),
            _obs("CME", "ESH26", "FUTURE", "ES", 1.0),
        ]
        assert feature_perp_representative("ES", "tradfi", observations) == (
            "CME",
            "ESH26",
        )

    def test_tradfi_picks_highest_volume_future_among_curve(self) -> None:
        """Non-CeFi pass-through (TradFi): given a CME curve, the most-liquid
        contract is the rep — front-month wins in real markets because its
        VOLUME is highest, not because the selector hardcodes the month."""
        observations = [
            _obs("CME", "ESM26", "FUTURE", "ES", 5_000_000_000.0),  # back-month
            _obs("CME", "ESH26", "FUTURE", "ES", 80_000_000_000.0),  # front-month
            _obs("CME", "ESU26", "FUTURE", "ES", 1_000_000_000.0),  # further out
        ]
        assert feature_perp_representative("ES", "tradfi", observations) == (
            "CME",
            "ESH26",
        )

    @pytest.mark.parametrize("asset_group", ["defi", "sports", "prediction"])
    def test_non_perp_supported_asset_groups_raise_loudly(self, asset_group: str) -> None:
        """Non-CeFi pass-through decision (DeFi / sports / prediction):
        the selector RAISES rather than silently returning ``None``.

        * ``defi`` — DeFi-native perps (Hyperliquid / Aster / Drift) are
          classified ``cefi`` everywhere in this codebase, so a caller
          passing ``defi`` is a programming error, not a no-rep case.
        * ``sports`` / ``prediction`` — these AGs don't run delta-one
          features at all (no price-time-series concept).

        Caller getting back a clear ``ValueError`` is the contract; it
        prevents the silent-fall-through bug where a downstream pipeline
        proceeds with ``None`` and emits zero rows.
        """
        observations = [
            _obs("ANY-VENUE", "ANY-INSTRUMENT", "PERPETUAL", "BTC", 1.0),
        ]
        with pytest.raises(ValueError, match=r"asset_group .* not supported"):
            feature_perp_representative("BTC", asset_group, observations)

    def test_perp_chosen_by_measured_volume_not_venue_hardcode(self) -> None:
        """Plan acceptance — 'the perp representative is chosen by measured
        volume (Binance usually wins for crypto but via volume, not
        hardcode)'. Same observations with the volume column flipped → the
        winner flips too. The selector never references a venue by name."""
        binance_leads = [
            _obs("BINANCE-FUTURES", "BTC-USDT", "PERPETUAL", "BTC", 12_500_000_000.0),
            _obs("BYBIT", "BTC-USDT", "PERPETUAL", "BTC", 4_200_000_000.0),
        ]
        bybit_leads = [
            _obs("BINANCE-FUTURES", "BTC-USDT", "PERPETUAL", "BTC", 1.0),
            _obs("BYBIT", "BTC-USDT", "PERPETUAL", "BTC", 9_999_999_999.0),
        ]
        assert feature_perp_representative("BTC", "cefi", binance_leads) == (
            "BINANCE-FUTURES",
            "BTC-USDT",
        )
        assert feature_perp_representative("BTC", "cefi", bybit_leads) == (
            "BYBIT",
            "BTC-USDT",
        )

    @pytest.mark.parametrize(
        ("asset_group", "instrument_type", "base"),
        [
            ("cefi", "PERPETUAL", "SOL"),
            ("tradfi", "FUTURE", "ES"),
        ],
    )
    def test_deterministic_tie_break_is_ag_uniform(
        self, asset_group: str, instrument_type: str, base: str
    ) -> None:
        """Same shape of deterministic tie-break (``venue ASC, instrument
        ASC``) for both AGs that support delta-one. Equal volume on the same
        venue collapses to the lexicographically smaller instrument — the
        same selector behaviour both pipelines depend on."""
        venue = "BINANCE-FUTURES" if asset_group == "cefi" else "CME"
        observations = [
            _obs(venue, "ZZZZ", instrument_type, base, 1.0),
            _obs(venue, "AAAA", instrument_type, base, 1.0),
        ]
        assert feature_perp_representative(base, asset_group, observations) == (
            venue,
            "AAAA",
        )
